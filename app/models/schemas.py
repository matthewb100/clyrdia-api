"""
Pydantic schemas for API requests and responses
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class RiskLevel(str, Enum):
    """Contract risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Types of contract issues"""
    LEGAL = "legal"
    FINANCIAL = "financial"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    SECURITY = "security"
    OTHER = "other"


class FixStatus(str, Enum):
    """Status of contract fixes"""
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    REVIEWED = "reviewed"


class Industry(str, Enum):
    """Supported industries"""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    REAL_ESTATE = "real_estate"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    EDUCATION = "education"
    GOVERNMENT = "government"
    OTHER = "other"


# Request Schemas
class AnalyzeRequest(BaseModel):
    """Request schema for contract analysis"""
    contract_text: Optional[str] = Field(None, description="Contract text content")
    file_upload: Optional[bytes] = Field(None, description="Contract file upload")
    industry: Optional[Industry] = Field(None, description="Contract industry context")
    analysis_type: Optional[List[str]] = Field(
        default=["legal", "financial", "compliance"],
        description="Types of analysis to perform"
    )
    
    @validator('contract_text', 'file_upload')
    def validate_input(cls, v, values):
        """Ensure either text or file is provided"""
        if not values.get('contract_text') and not values.get('file_upload'):
            raise ValueError("Either contract_text or file_upload must be provided")
        return v


class FixRequest(BaseModel):
    """Request schema for applying fixes"""
    fix_description: str = Field(..., description="Description of the fix to apply")
    fix_code: Optional[str] = Field(None, description="Code/script to apply the fix")
    auto_apply: bool = Field(False, description="Whether to automatically apply the fix")


class TemplateRequest(BaseModel):
    """Request schema for template requests"""
    industry: Industry = Field(..., description="Industry for template selection")
    contract_type: Optional[str] = Field(None, description="Specific contract type")
    include_variables: bool = Field(True, description="Include template variables")


# Response Schemas
class ContractIssue(BaseModel):
    """Schema for contract issues"""
    id: str = Field(..., description="Unique issue identifier")
    issue_type: IssueType = Field(..., description="Type of issue")
    severity: RiskLevel = Field(..., description="Risk severity level")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Detailed issue description")
    line_number: Optional[int] = Field(None, description="Line number in document")
    clause_reference: Optional[str] = Field(None, description="Reference to specific clause")
    suggested_fix: str = Field(..., description="Suggested fix for the issue")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    confidence: float = Field(..., ge=0, le=100, description="AI confidence (0-100)")
    created_at: datetime = Field(..., description="Issue creation timestamp")


class ContractAnalysis(BaseModel):
    """Schema for contract analysis results"""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    contract_hash: str = Field(..., description="Hash of analyzed contract")
    total_issues: int = Field(..., description="Total number of issues found")
    overall_risk_score: float = Field(..., ge=0, le=100, description="Overall risk score")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    issues: List[ContractIssue] = Field(..., description="List of identified issues")
    summary: str = Field(..., description="Analysis summary")
    recommendations: List[str] = Field(..., description="General recommendations")
    analysis_metadata: Dict[str, Any] = Field(..., description="Analysis metadata")
    created_at: datetime = Field(..., description="Analysis creation timestamp")
    processing_time: float = Field(..., description="Processing time in seconds")


class FixResult(BaseModel):
    """Schema for fix application results"""
    fix_id: str = Field(..., description="Unique fix identifier")
    issue_id: str = Field(..., description="ID of the fixed issue")
    status: FixStatus = Field(..., description="Fix status")
    applied_fix: str = Field(..., description="Description of applied fix")
    updated_document: Optional[str] = Field(None, description="Updated document content")
    diff_summary: Optional[str] = Field(None, description="Summary of changes made")
    applied_at: datetime = Field(..., description="Fix application timestamp")
    applied_by: Optional[str] = Field(None, description="Who applied the fix")


class ContractTemplate(BaseModel):
    """Schema for contract templates"""
    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    industry: Industry = Field(..., description="Industry category")
    contract_type: str = Field(..., description="Type of contract")
    description: str = Field(..., description="Template description")
    content: str = Field(..., description="Template content")
    variables: List[str] = Field(..., description="Template variables")
    tags: List[str] = Field(..., description="Template tags")
    version: str = Field(..., description="Template version")
    created_at: datetime = Field(..., description="Template creation timestamp")
    updated_at: datetime = Field(..., description="Template last update timestamp")


class TemplateLibrary(BaseModel):
    """Schema for template library response"""
    industry: Industry = Field(..., description="Industry category")
    templates: List[ContractTemplate] = Field(..., description="Available templates")
    total_count: int = Field(..., description="Total number of templates")
    categories: List[str] = Field(..., description="Available contract categories")


class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    services: Dict[str, str] = Field(..., description="Dependent services status")
    uptime: float = Field(..., description="Service uptime in seconds")


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")


class StreamingResponse(BaseModel):
    """Schema for streaming responses"""
    type: str = Field(..., description="Response type")
    data: Any = Field(..., description="Response data")
    timestamp: datetime = Field(..., description="Response timestamp")
    is_final: bool = Field(False, description="Whether this is the final response") 