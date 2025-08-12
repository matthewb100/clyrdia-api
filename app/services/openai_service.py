"""
OpenAI service for contract analysis using GPT-4
"""
import asyncio
import json
import hashlib
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings
from app.models.schemas import ContractIssue, IssueType, RiskLevel
import structlog

logger = structlog.get_logger(__name__)


class OpenAIService:
    """Service for OpenAI GPT-4 integration"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
    
    async def analyze_contract(
        self, 
        contract_text: str, 
        industry: str = None,
        analysis_types: List[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze contract using GPT-4 with streaming response
        """
        try:
            # Prepare the analysis prompt
            prompt = self._build_analysis_prompt(contract_text, industry, analysis_types)
            
            # Stream the analysis
            async for chunk in self._stream_analysis(prompt):
                yield chunk
                
        except Exception as e:
            logger.error("Contract analysis failed", error=str(e))
            yield {
                "type": "error",
                "data": {"message": f"Analysis failed: {str(e)}"},
                "timestamp": asyncio.get_event_loop().time(),
                "is_final": True
            }
    
    async def _stream_analysis(self, prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the analysis response from OpenAI"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal contract analysis expert. Analyze contracts for legal, financial, compliance, and operational risks. Provide detailed, actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Send progress updates
                    yield {
                        "type": "progress",
                        "data": {"content": content, "full_response": full_response},
                        "timestamp": asyncio.get_event_loop().time(),
                        "is_final": False
                    }
            
            # Process the complete response
            analysis_result = await self._process_analysis_response(full_response)
            
            # Send final result
            yield {
                "type": "analysis_complete",
                "data": analysis_result,
                "timestamp": asyncio.get_event_loop().time(),
                "is_final": True
            }
            
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            yield {
                "type": "error",
                "data": {"message": f"Streaming failed: {str(e)}"},
                "timestamp": asyncio.get_event_loop().time(),
                "is_final": True
            }
    
    def _build_analysis_prompt(
        self, 
        contract_text: str, 
        industry: str = None,
        analysis_types: List[str] = None
    ) -> str:
        """Build the analysis prompt for OpenAI"""
        prompt = f"""
        Please analyze the following contract for potential issues and risks.
        
        Contract Text:
        {contract_text[:8000]}  # Limit text length for token efficiency
        
        Industry Context: {industry or 'General'}
        Analysis Focus: {', '.join(analysis_types or ['legal', 'financial', 'compliance'])}
        
        Please provide a comprehensive analysis including:
        1. Overall risk assessment (low/medium/high/critical)
        2. Specific issues found with:
           - Issue type (legal/financial/compliance/operational/security)
           - Severity level
           - Risk score (0-100)
           - Detailed description
           - Suggested fixes
        3. General recommendations
        4. Summary of findings
        
        Format your response as JSON with the following structure:
        {{
            "overall_risk": "low/medium/high/critical",
            "overall_risk_score": 0-100,
            "issues": [
                {{
                    "type": "issue_type",
                    "severity": "severity_level",
                    "title": "issue_title",
                    "description": "detailed_description",
                    "suggested_fix": "fix_description",
                    "risk_score": 0-100,
                    "confidence": 0-100
                }}
            ],
            "recommendations": ["rec1", "rec2"],
            "summary": "analysis_summary"
        }}
        """
        return prompt
    
    async def _process_analysis_response(self, response: str) -> Dict[str, Any]:
        """Process the OpenAI response into structured data"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            analysis_data = json.loads(json_str)
            
            # Validate and structure the response
            return {
                "overall_risk": analysis_data.get("overall_risk", "medium"),
                "overall_risk_score": analysis_data.get("overall_risk_score", 50),
                "issues": analysis_data.get("issues", []),
                "recommendations": analysis_data.get("recommendations", []),
                "summary": analysis_data.get("summary", "Analysis completed"),
                "raw_response": response
            }
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response as JSON", error=str(e))
            # Fallback: return basic analysis
            return {
                "overall_risk": "medium",
                "overall_risk_score": 50,
                "issues": [],
                "recommendations": ["Review the contract manually for detailed analysis"],
                "summary": "AI analysis completed but response parsing failed",
                "raw_response": response
            }
    
    async def generate_fix_suggestion(
        self, 
        issue_description: str, 
        contract_context: str
    ) -> str:
        """Generate a specific fix suggestion for an issue"""
        try:
            prompt = f"""
            Given this contract issue:
            {issue_description}
            
            And this contract context:
            {contract_context[:2000]}
            
            Please provide a specific, actionable fix suggestion. Be precise and legal-compliant.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal contract expert. Provide specific, actionable fix suggestions for contract issues."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("Fix suggestion generation failed", error=str(e))
            return "Unable to generate fix suggestion at this time."
    
    async def validate_fix(
        self, 
        original_text: str, 
        proposed_fix: str
    ) -> Dict[str, Any]:
        """Validate a proposed fix against the original contract"""
        try:
            prompt = f"""
            Please validate this proposed fix for a contract:
            
            Original Text:
            {original_text}
            
            Proposed Fix:
            {proposed_fix}
            
            Evaluate the fix for:
            1. Legal compliance
            2. Clarity and readability
            3. Potential new issues
            4. Overall improvement
            
            Return JSON response:
            {{
                "is_valid": true/false,
                "confidence": 0-100,
                "issues": ["any_issues_found"],
                "improvements": ["improvements_made"],
                "recommendation": "accept/reject/modify"
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal contract validation expert. Evaluate proposed fixes for legal compliance and effectiveness."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            try:
                validation_result = json.loads(response.choices[0].message.content)
                return validation_result
            except json.JSONDecodeError:
                return {
                    "is_valid": False,
                    "confidence": 0,
                    "issues": ["Failed to parse validation response"],
                    "improvements": [],
                    "recommendation": "reject"
                }
                
        except Exception as e:
            logger.error("Fix validation failed", error=str(e))
            return {
                "is_valid": False,
                "confidence": 0,
                "issues": [f"Validation failed: {str(e)}"],
                "improvements": [],
                "recommendation": "reject"
            }


# Global service instance
openai_service = OpenAIService() 