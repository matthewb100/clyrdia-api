"""
Background tasks for contract analysis
"""
from celery import current_task
from app.celery_app import celery_app
from app.services.openai_service import openai_service
from app.services.supabase_service import supabase_service
from app.core.cache import cache
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="analyze_contract_async")
def analyze_contract_async(self, contract_text: str, industry: str = None, analysis_types: list = None):
    """
    Background task for contract analysis
    """
    try:
        # Update task state
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Starting analysis", "progress": 0}
        )
        
        logger.info(
            "Starting background contract analysis",
            task_id=self.request.id,
            industry=industry
        )
        
        # Perform analysis
        analysis_result = None
        progress = 0
        
        for chunk in openai_service.analyze_contract(contract_text, industry, analysis_types):
            if chunk["type"] == "analysis_complete":
                analysis_result = chunk["data"]
                progress = 100
                break
            elif chunk["type"] == "progress":
                progress = min(90, progress + 10)  # Increment progress
                current_task.update_state(
                    state="PROGRESS",
                    meta={"status": "Analyzing contract", "progress": progress}
                )
            elif chunk["type"] == "error":
                raise Exception(f"Analysis failed: {chunk['data']['message']}")
        
        if not analysis_result:
            raise Exception("Analysis failed to complete")
        
        # Update task state
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Storing results", "progress": 95}
        )
        
        # Store results in database
        contract_hash = f"bg_task_{self.request.id}"
        analysis_id = supabase_service.store_analysis(
            analysis_result,
            contract_hash
        )
        
        if analysis_result.get("issues"):
            supabase_service.store_issues(analysis_id, analysis_result["issues"])
        
        # Cache results
        cache_key = f"bg_analysis:{self.request.id}"
        cache.set(cache_key, analysis_result, 3600)
        
        logger.info(
            "Background analysis completed",
            task_id=self.request.id,
            analysis_id=analysis_id
        )
        
        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "result": analysis_result,
            "progress": 100
        }
        
    except Exception as e:
        logger.error(
            "Background analysis failed",
            task_id=self.request.id,
            error=str(e)
        )
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        
        raise


@celery_app.task(bind=True, name="batch_analyze_contracts")
def batch_analyze_contracts(self, contracts_data: list):
    """
    Background task for batch contract analysis
    """
    try:
        total_contracts = len(contracts_data)
        completed = 0
        failed = 0
        results = []
        
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Starting batch analysis", "progress": 0}
        )
        
        logger.info(
            "Starting batch contract analysis",
            task_id=self.request.id,
            total_contracts=total_contracts
        )
        
        for i, contract_data in enumerate(contracts_data):
            try:
                # Update progress
                progress = int((i / total_contracts) * 100)
                current_task.update_state(
                    state="PROGRESS",
                    meta={
                        "status": f"Analyzing contract {i+1}/{total_contracts}",
                        "progress": progress
                    }
                )
                
                # Analyze single contract
                contract_text = contract_data.get("text", "")
                industry = contract_data.get("industry")
                analysis_types = contract_data.get("analysis_types", ["legal", "financial", "compliance"])
                
                analysis_result = None
                for chunk in openai_service.analyze_contract(contract_text, industry, analysis_types):
                    if chunk["type"] == "analysis_complete":
                        analysis_result = chunk["data"]
                        break
                
                if analysis_result:
                    # Store results
                    contract_hash = f"batch_{self.request.id}_{i}"
                    analysis_id = supabase_service.store_analysis(
                        analysis_result,
                        contract_hash
                    )
                    
                    if analysis_result.get("issues"):
                        supabase_service.store_issues(analysis_id, analysis_result["issues"])
                    
                    results.append({
                        "contract_id": contract_data.get("id"),
                        "analysis_id": analysis_id,
                        "status": "completed",
                        "result": analysis_result
                    })
                    
                    completed += 1
                else:
                    failed += 1
                    results.append({
                        "contract_id": contract_data.get("id"),
                        "status": "failed",
                        "error": "Analysis failed to complete"
                    })
                    
            except Exception as e:
                failed += 1
                logger.error(
                    "Failed to analyze contract in batch",
                    task_id=self.request.id,
                    contract_index=i,
                    error=str(e)
                )
                
                results.append({
                    "contract_id": contract_data.get("id"),
                    "status": "failed",
                    "error": str(e)
                })
        
        # Final update
        current_task.update_state(
            state="SUCCESS",
            meta={
                "status": "Batch analysis completed",
                "total": total_contracts,
                "completed": completed,
                "failed": failed,
                "results": results
            }
        )
        
        logger.info(
            "Batch analysis completed",
            task_id=self.request.id,
            total=total_contracts,
            completed=completed,
            failed=failed
        )
        
        return {
            "total": total_contracts,
            "completed": completed,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "Batch analysis failed",
            task_id=self.request.id,
            error=str(e)
        )
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        
        raise


@celery_app.task(bind=True, name="reanalyze_contract")
def reanalyze_contract(self, analysis_id: str, new_analysis_types: list = None):
    """
    Background task for reanalyzing a contract with different parameters
    """
    try:
        current_task.update_state(
            state="PROGRESS",
            meta={"status": "Starting reanalysis", "progress": 0}
        )
        
        logger.info(
            "Starting contract reanalysis",
            task_id=self.request.id,
            analysis_id=analysis_id
        )
        
        # Get original analysis
        original_analysis = supabase_service.get_analysis(analysis_id)
        if not original_analysis:
            raise Exception("Original analysis not found")
        
        # Extract contract text (this would need to be stored or retrieved)
        contract_text = original_analysis.get("contract_text", "")
        if not contract_text:
            raise Exception("Contract text not available for reanalysis")
        
        # Use new analysis types or defaults
        analysis_types = new_analysis_types or ["legal", "financial", "compliance"]
        
        # Perform new analysis
        analysis_result = None
        progress = 0
        
        for chunk in openai_service.analyze_contract(contract_text, None, analysis_types):
            if chunk["type"] == "analysis_complete":
                analysis_result = chunk["data"]
                progress = 100
                break
            elif chunk["type"] == "progress":
                progress = min(90, progress + 10)
                current_task.update_state(
                    state="PROGRESS",
                    meta={"status": "Reanalyzing contract", "progress": progress}
                )
        
        if not analysis_result:
            raise Exception("Reanalysis failed to complete")
        
        # Store new analysis
        contract_hash = f"reanalysis_{self.request.id}"
        new_analysis_id = supabase_service.store_analysis(
            analysis_result,
            contract_hash
        )
        
        if analysis_result.get("issues"):
            supabase_service.store_issues(new_analysis_id, analysis_result["issues"])
        
        # Link to original analysis
        supabase_service.update_fix_status(
            new_analysis_id,
            "completed",
            {"original_analysis_id": analysis_id, "reanalysis": True}
        )
        
        logger.info(
            "Contract reanalysis completed",
            task_id=self.request.id,
            original_analysis_id=analysis_id,
            new_analysis_id=new_analysis_id
        )
        
        return {
            "status": "completed",
            "original_analysis_id": analysis_id,
            "new_analysis_id": new_analysis_id,
            "result": analysis_result
        }
        
    except Exception as e:
        logger.error(
            "Contract reanalysis failed",
            task_id=self.request.id,
            analysis_id=analysis_id,
            error=str(e)
        )
        
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        
        raise 