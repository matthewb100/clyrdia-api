"""
Supabase service for data persistence
"""
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)


class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.url = settings.supabase_url
        self.key = settings.supabase_key
        self.service_role_key = settings.supabase_service_role_key
    
    async def connect(self):
        """Connect to Supabase"""
        try:
            self.client = create_client(self.url, self.key)
            # Test connection
            response = self.client.table("health_check").select("id").limit(1).execute()
            logger.info("Connected to Supabase successfully")
        except Exception as e:
            logger.error("Failed to connect to Supabase", error=str(e))
            # Create client anyway for potential operations
            self.client = create_client(self.url, self.key)
    
    async def disconnect(self):
        """Disconnect from Supabase"""
        if self.client:
            self.client = None
            logger.info("Disconnected from Supabase")
    
    async def store_analysis(
        self, 
        analysis_data: Dict[str, Any],
        contract_hash: str,
        user_id: Optional[str] = None
    ) -> str:
        """Store contract analysis results"""
        try:
            if not self.client:
                await self.connect()
            
            analysis_record = {
                "contract_hash": contract_hash,
                "user_id": user_id,
                "analysis_data": analysis_data,
                "overall_risk_score": analysis_data.get("overall_risk_score", 0),
                "overall_risk_level": analysis_data.get("overall_risk", "medium"),
                "total_issues": len(analysis_data.get("issues", [])),
                "status": "completed"
            }
            
            response = self.client.table("contract_analyses").insert(analysis_record).execute()
            
            if response.data:
                analysis_id = response.data[0]["id"]
                logger.info("Analysis stored successfully", analysis_id=analysis_id)
                return analysis_id
            else:
                raise Exception("No data returned from insert operation")
                
        except Exception as e:
            logger.error("Failed to store analysis", error=str(e))
            raise
    
    async def store_issues(
        self, 
        analysis_id: str, 
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Store individual contract issues"""
        try:
            if not self.client:
                await self.connect()
            
            issue_records = []
            for issue in issues:
                issue_record = {
                    "analysis_id": analysis_id,
                    "issue_type": issue.get("type", "other"),
                    "severity": issue.get("severity", "medium"),
                    "title": issue.get("title", ""),
                    "description": issue.get("description", ""),
                    "suggested_fix": issue.get("suggested_fix", ""),
                    "risk_score": issue.get("risk_score", 0),
                    "confidence": issue.get("confidence", 0),
                    "clause_reference": issue.get("clause_reference"),
                    "line_number": issue.get("line_number")
                }
                issue_records.append(issue_record)
            
            if issue_records:
                response = self.client.table("contract_issues").insert(issue_records).execute()
                
                if response.data:
                    issue_ids = [issue["id"] for issue in response.data]
                    logger.info("Issues stored successfully", count=len(issue_ids))
                    return issue_ids
                else:
                    raise Exception("No data returned from issues insert")
            else:
                return []
                
        except Exception as e:
            logger.error("Failed to store issues", error=str(e))
            raise
    
    async def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve contract analysis by ID"""
        try:
            if not self.client:
                await self.connect()
            
            response = self.client.table("contract_analyses").select("*").eq("id", analysis_id).execute()
            
            if response.data:
                analysis = response.data[0]
                
                # Get associated issues
                issues_response = self.client.table("contract_issues").select("*").eq("analysis_id", analysis_id).execute()
                analysis["issues"] = issues_response.data or []
                
                return analysis
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to retrieve analysis", analysis_id=analysis_id, error=str(e))
            return None
    
    async def get_analysis_by_hash(self, contract_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve contract analysis by contract hash"""
        try:
            if not self.client:
                await self.connect()
            
            response = self.client.table("contract_analyses").select("*").eq("contract_hash", contract_hash).order("created_at", desc=True).limit(1).execute()
            
            if response.data:
                analysis = response.data[0]
                
                # Get associated issues
                issues_response = self.client.table("contract_issues").select("*").eq("analysis_id", analysis["id"]).execute()
                analysis["issues"] = issues_response.data or []
                
                return analysis
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to retrieve analysis by hash", contract_hash=contract_hash, error=str(e))
            return None
    
    async def store_fix(
        self, 
        issue_id: str, 
        fix_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Store contract fix application"""
        try:
            if not self.client:
                await self.connect()
            
            fix_record = {
                "issue_id": issue_id,
                "user_id": user_id,
                "fix_description": fix_data.get("fix_description", ""),
                "fix_code": fix_data.get("fix_code"),
                "auto_apply": fix_data.get("auto_apply", False),
                "status": "pending",
                "applied_fix": fix_data.get("applied_fix", ""),
                "updated_document": fix_data.get("updated_document"),
                "diff_summary": fix_data.get("diff_summary")
            }
            
            response = self.client.table("contract_fixes").insert(fix_record).execute()
            
            if response.data:
                fix_id = response.data[0]["id"]
                logger.info("Fix stored successfully", fix_id=fix_id)
                return fix_id
            else:
                raise Exception("No data returned from fix insert")
                
        except Exception as e:
            logger.error("Failed to store fix", error=str(e))
            raise
    
    async def update_fix_status(self, fix_id: str, status: str, additional_data: Dict[str, Any] = None):
        """Update fix status"""
        try:
            if not self.client:
                await self.connect()
            
            update_data = {"status": status}
            if additional_data:
                update_data.update(additional_data)
            
            response = self.client.table("contract_fixes").update(update_data).eq("id", fix_id).execute()
            
            if response.data:
                logger.info("Fix status updated", fix_id=fix_id, status=status)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Failed to update fix status", fix_id=fix_id, error=str(e))
            return False
    
    async def get_templates(self, industry: str) -> List[Dict[str, Any]]:
        """Retrieve contract templates for an industry"""
        try:
            if not self.client:
                await self.connect()
            
            response = self.client.table("contract_templates").select("*").eq("industry", industry).eq("active", True).execute()
            
            if response.data:
                logger.info("Templates retrieved", industry=industry, count=len(response.data))
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error("Failed to retrieve templates", industry=industry, error=str(e))
            return []
    
    async def store_template(
        self, 
        template_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Store new contract template"""
        try:
            if not self.client:
                await self.connect()
            
            template_record = {
                "name": template_data.get("name", ""),
                "industry": template_data.get("industry", ""),
                "contract_type": template_data.get("contract_type", ""),
                "description": template_data.get("description", ""),
                "content": template_data.get("content", ""),
                "variables": template_data.get("variables", []),
                "tags": template_data.get("tags", []),
                "version": template_data.get("version", "1.0"),
                "created_by": user_id,
                "active": True
            }
            
            response = self.client.table("contract_templates").insert(template_record).execute()
            
            if response.data:
                template_id = response.data[0]["id"]
                logger.info("Template stored successfully", template_id=template_id)
                return template_id
            else:
                raise Exception("No data returned from template insert")
                
        except Exception as e:
            logger.error("Failed to store template", error=str(e))
            raise
    
    async def get_user_analyses(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve user's contract analyses"""
        try:
            if not self.client:
                await self.connect()
            
            response = self.client.table("contract_analyses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            
            if response.data:
                logger.info("User analyses retrieved", user_id=user_id, count=len(response.data))
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error("Failed to retrieve user analyses", user_id=user_id, error=str(e))
            return []
    
    async def delete_analysis(self, analysis_id: str, user_id: Optional[str] = None) -> bool:
        """Delete contract analysis (soft delete)"""
        try:
            if not self.client:
                await self.connect()
            
            # Soft delete by setting status to deleted
            update_data = {"status": "deleted"}
            if user_id:
                update_data["deleted_by"] = user_id
            
            response = self.client.table("contract_analyses").update(update_data).eq("id", analysis_id).execute()
            
            if response.data:
                logger.info("Analysis deleted", analysis_id=analysis_id)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Failed to delete analysis", analysis_id=analysis_id, error=str(e))
            return False
    
    async def get_analytics(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get analytics data"""
        try:
            if not self.client:
                await self.connect()
            
            # Get analysis count
            analysis_query = self.client.table("contract_analyses").select("id", count="exact")
            if user_id:
                analysis_query = analysis_query.eq("user_id", user_id)
            
            analysis_response = analysis_query.execute()
            total_analyses = analysis_response.count or 0
            
            # Get issue count
            issue_query = self.client.table("contract_issues").select("id", count="exact")
            if user_id:
                issue_query = issue_query.eq("user_id", user_id)
            
            issue_response = issue_query.execute()
            total_issues = issue_response.count or 0
            
            # Get risk distribution
            risk_response = self.client.table("contract_analyses").select("overall_risk_level").execute()
            risk_distribution = {}
            if risk_response.data:
                for analysis in risk_response.data:
                    risk_level = analysis.get("overall_risk_level", "unknown")
                    risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
            
            analytics = {
                "total_analyses": total_analyses,
                "total_issues": total_issues,
                "risk_distribution": risk_distribution,
                "period_days": days
            }
            
            logger.info("Analytics retrieved", analytics=analytics)
            return analytics
            
        except Exception as e:
            logger.error("Failed to retrieve analytics", error=str(e))
            return {
                "total_analyses": 0,
                "total_issues": 0,
                "risk_distribution": {},
                "period_days": days
            }


# Global service instance
supabase_service = SupabaseService() 