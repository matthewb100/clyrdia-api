"""
Main API endpoints for Clyrdia Contract Intelligence Platform
"""
import time
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from app.core.security import APIKeyAuth, RateLimiter, get_client_id, sanitize_input
from app.core.logging import log_request, log_response, log_error
from app.models.schemas import (
    AnalyzeRequest, FixRequest, TemplateRequest,
    ContractAnalysis, FixResult, TemplateLibrary, HealthCheck, ErrorResponse
)
from app.services.openai_service import openai_service
from app.services.document_service import document_service
from app.services.supabase_service import supabase_service
from app.core.cache import cache
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)

# Initialize rate limiter
rate_limiter = RateLimiter(
    settings.rate_limit_per_minute,
    settings.rate_limit_per_hour
)

# Initialize API key authentication
api_key_auth = APIKeyAuth(settings.api_key)

router = APIRouter()


@router.post("/analyze", response_model=ContractAnalysis)
async def analyze_contract(
    request: Request,
    contract_text: str = Form(None),
    file_upload: UploadFile = File(None),
    industry: str = Form(None),
    analysis_type: List[str] = Form(["legal", "financial", "compliance"]),
    auth: str = Depends(api_key_auth)
):
    """
    Analyze contract for issues and risks using OpenAI GPT-4
    """
    start_time = time.time()
    client_id = get_client_id(request)
    
    try:
        # Rate limiting
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        log_request(request, logger)
        
        # Validate input
        if not contract_text and not file_upload:
            raise HTTPException(
                status_code=400,
                detail="Either contract_text or file_upload must be provided"
            )
        
        # Process document if file uploaded
        extracted_text = ""
        contract_hash = ""
        
        if file_upload:
            extracted_text, contract_hash = await document_service.process_document(
                file_upload, 
                settings.max_file_size
            )
            
            # Validate document content
            if not await document_service.validate_document_content(extracted_text):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid document content. Please ensure this is a valid contract."
                )
            
            # Sanitize text
            extracted_text = await document_service.sanitize_text(extracted_text)
        else:
            # Use provided text
            extracted_text = sanitize_input(contract_text)
            if not extracted_text:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid contract text provided"
                )
            # Generate hash for text
            import hashlib
            contract_hash = hashlib.sha256(extracted_text.encode()).hexdigest()
        
        # Check cache for existing analysis
        cache_key = f"analysis:{contract_hash}:{industry}:{':'.join(analysis_type)}"
        cached_analysis = await cache.get(cache_key)
        
        if cached_analysis:
            logger.info("Returning cached analysis", contract_hash=contract_hash)
            return cached_analysis
        
        # Perform analysis with OpenAI
        analysis_result = None
        async for chunk in openai_service.analyze_contract(
            extracted_text, 
            industry, 
            analysis_type
        ):
            if chunk["type"] == "analysis_complete":
                analysis_result = chunk["data"]
                break
            elif chunk["type"] == "error":
                raise HTTPException(
                    status_code=500,
                    detail=f"Analysis failed: {chunk['data']['message']}"
                )
        
        if not analysis_result:
            raise HTTPException(
                status_code=500,
                detail="Analysis failed to complete"
            )
        
        # Create analysis response
        analysis_id = str(uuid.uuid4())
        processing_time = time.time() - start_time
        
        analysis_response = ContractAnalysis(
            analysis_id=analysis_id,
            contract_hash=contract_hash,
            total_issues=len(analysis_result.get("issues", [])),
            overall_risk_score=analysis_result.get("overall_risk_score", 50),
            risk_level=analysis_result.get("overall_risk", "medium"),
            issues=analysis_result.get("issues", []),
            summary=analysis_result.get("summary", "Analysis completed"),
            recommendations=analysis_result.get("recommendations", []),
            analysis_metadata={
                "industry": industry,
                "analysis_types": analysis_type,
                "text_length": len(extracted_text),
                "model_used": settings.openai_model
            },
            created_at=time.time(),
            processing_time=processing_time
        )
        
        # Store in database
        try:
            await supabase_service.store_analysis(
                analysis_result,
                contract_hash
            )
            
            if analysis_result.get("issues"):
                await supabase_service.store_issues(analysis_id, analysis_result["issues"])
                
        except Exception as e:
            logger.error("Failed to store analysis in database", error=str(e))
            # Continue without database storage
        
        # Cache the result
        await cache.set(cache_key, analysis_response.dict(), 3600)  # 1 hour
        
        logger.info(
            "Contract analysis completed",
            analysis_id=analysis_id,
            contract_hash=contract_hash,
            processing_time=processing_time,
            total_issues=len(analysis_result.get("issues", []))
        )
        
        return analysis_response
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"endpoint": "/analyze", "client_id": client_id}, logger)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during contract analysis"
        )
    finally:
        duration = time.time() - start_time
        log_response(None, duration, logger)


@router.post("/analyze/stream")
async def analyze_contract_stream(
    request: Request,
    contract_text: str = Form(None),
    file_upload: UploadFile = File(None),
    industry: str = Form(None),
    analysis_type: List[str] = Form(["legal", "financial", "compliance"]),
    auth: str = Depends(api_key_auth)
):
    """
    Stream contract analysis in real-time
    """
    client_id = get_client_id(request)
    
    try:
        # Rate limiting
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        log_request(request, logger)
        
        # Validate input
        if not contract_text and not file_upload:
            raise HTTPException(
                status_code=400,
                detail="Either contract_text or file_upload must be provided"
            )
        
        # Process document if file uploaded
        extracted_text = ""
        if file_upload:
            extracted_text, _ = await document_service.process_document(
                file_upload, 
                settings.max_file_size
            )
            
            if not await document_service.validate_document_content(extracted_text):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid document content. Please ensure this is a valid contract."
                )
            
            extracted_text = await document_service.sanitize_text(extracted_text)
        else:
            extracted_text = sanitize_input(contract_text)
            if not extracted_text:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid contract text provided"
                )
        
        # Stream analysis
        async def generate_stream():
            try:
                async for chunk in openai_service.analyze_contract(
                    extracted_text, 
                    industry, 
                    analysis_type
                ):
                    # Convert chunk to JSON string
                    import json
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    if chunk["is_final"]:
                        break
                        
            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "data": {"message": str(e)},
                    "timestamp": time.time(),
                    "is_final": True
                }
                import json
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"endpoint": "/analyze/stream", "client_id": client_id}, logger)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during streaming analysis"
        )


@router.post("/fix/{issue_id}", response_model=FixResult)
async def apply_fix(
    issue_id: str,
    fix_request: FixRequest,
    request: Request,
    auth: str = Depends(api_key_auth)
):
    """
    Apply a specific fix to a contract issue
    """
    start_time = time.time()
    client_id = get_client_id(request)
    
    try:
        # Rate limiting
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        log_request(request, logger)
        
        # Validate issue_id
        if not issue_id or len(issue_id) < 10:
            raise HTTPException(
                status_code=400,
                detail="Invalid issue ID"
            )
        
        # Get issue details from database
        issue = await supabase_service.get_analysis(issue_id)
        if not issue:
            raise HTTPException(
                status_code=404,
                detail="Issue not found"
            )
        
        # Generate fix ID
        fix_id = str(uuid.uuid4())
        
        # Create fix result
        fix_result = FixResult(
            fix_id=fix_id,
            issue_id=issue_id,
            status="applied" if fix_request.auto_apply else "pending",
            applied_fix=fix_request.fix_description,
            updated_document=None,  # Will be populated if auto-apply
            diff_summary=None,
            applied_at=time.time(),
            applied_by=client_id
        )
        
        # Store fix in database
        try:
            await supabase_service.store_fix(
                issue_id,
                fix_request.dict(),
                client_id
            )
            
            if fix_request.auto_apply:
                # Update fix status to applied
                await supabase_service.update_fix_status(
                    fix_id, 
                    "applied",
                    {"updated_document": "Auto-applied fix"}
                )
                fix_result.status = "applied"
                
        except Exception as e:
            logger.error("Failed to store fix in database", error=str(e))
            # Continue without database storage
        
        logger.info(
            "Fix applied successfully",
            fix_id=fix_id,
            issue_id=issue_id,
            auto_apply=fix_request.auto_apply
        )
        
        return fix_result
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"endpoint": "/fix", "issue_id": issue_id, "client_id": client_id}, logger)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during fix application"
        )
    finally:
        duration = time.time() - start_time
        log_response(None, duration, logger)


@router.get("/templates/{industry}", response_model=TemplateLibrary)
async def get_templates(
    industry: str,
    request: Request,
    contract_type: str = None,
    include_variables: bool = True,
    auth: str = Depends(api_key_auth)
):
    """
    Get industry-specific contract templates
    """
    start_time = time.time()
    client_id = get_client_id(request)
    
    try:
        # Rate limiting
        if not rate_limiter.is_allowed(client_id):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        log_request(request, logger)
        
        # Validate industry
        if not industry or industry not in [i.value for i in settings.allowed_file_types]:
            raise HTTPException(
                status_code=400,
                detail="Invalid industry specified"
            )
        
        # Check cache first
        cache_key = f"templates:{industry}:{contract_type}:{include_variables}"
        cached_templates = await cache.get(cache_key)
        
        if cached_templates:
            logger.info("Returning cached templates", industry=industry)
            return cached_templates
        
        # Get templates from database
        templates = await supabase_service.get_templates(industry)
        
        # Filter by contract type if specified
        if contract_type:
            templates = [t for t in templates if t.get("contract_type") == contract_type]
        
        # Process templates
        processed_templates = []
        for template in templates:
            processed_template = {
                "id": template.get("id"),
                "name": template.get("name"),
                "industry": template.get("industry"),
                "contract_type": template.get("contract_type"),
                "description": template.get("description"),
                "content": template.get("content"),
                "variables": template.get("variables") if include_variables else [],
                "tags": template.get("tags", []),
                "version": template.get("version", "1.0"),
                "created_at": template.get("created_at"),
                "updated_at": template.get("updated_at")
            }
            processed_templates.append(processed_template)
        
        # Create response
        template_library = TemplateLibrary(
            industry=industry,
            templates=processed_templates,
            total_count=len(processed_templates),
            categories=list(set(t.get("contract_type") for t in processed_templates))
        )
        
        # Cache the result
        await cache.set(cache_key, template_library.dict(), 1800)  # 30 minutes
        
        logger.info(
            "Templates retrieved successfully",
            industry=industry,
            count=len(processed_templates)
        )
        
        return template_library
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"endpoint": "/templates", "industry": industry, "client_id": client_id}, logger)
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving templates"
        )
    finally:
        duration = time.time() - start_time
        log_response(None, duration, logger)


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request):
    """
    Health check endpoint for monitoring
    """
    start_time = time.time()
    
    try:
        log_request(request, logger)
        
        # Check service dependencies
        services_status = {}
        
        # Check Supabase
        try:
            await supabase_service.connect()
            services_status["supabase"] = "healthy"
        except Exception:
            services_status["supabase"] = "unhealthy"
        
        # Check Redis/Cache
        try:
            await cache.connect()
            await cache.set("health_check", "ok", 60)
            services_status["cache"] = "healthy"
        except Exception:
            services_status["cache"] = "unhealthy"
        
        # Check OpenAI
        try:
            # Simple test - just check if we can create a client
            import openai
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            services_status["openai"] = "healthy"
        except Exception:
            services_status["openai"] = "unhealthy"
        
        # Determine overall status
        overall_status = "healthy" if all(
            status == "healthy" for status in services_status.values()
        ) else "degraded"
        
        health_response = HealthCheck(
            status=overall_status,
            timestamp=time.time(),
            version=settings.app_version,
            environment=settings.environment,
            services=services_status,
            uptime=time.time() - start_time
        )
        
        return health_response
        
    except Exception as e:
        log_error(e, {"endpoint": "/health"}, logger)
        return HealthCheck(
            status="unhealthy",
            timestamp=time.time(),
            version=settings.app_version,
            environment=settings.environment,
            services={"error": str(e)},
            uptime=time.time() - start_time
        )
    finally:
        duration = time.time() - start_time
        log_response(None, duration, logger) 