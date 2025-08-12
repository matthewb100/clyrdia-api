"""
Security and authentication utilities
"""
import time
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

logger = structlog.get_logger(__name__)


class APIKeyAuth(HTTPBearer):
    """API Key authentication scheme"""
    
    def __init__(self, api_key: str, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.api_key = api_key
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if credentials.credentials != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return credentials


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int, requests_per_hour: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = {}
        self.hour_requests = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for the client"""
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Check minute limit
        if client_id not in self.minute_requests:
            self.minute_requests[client_id] = []
        
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            return False
        
        # Check hour limit
        if client_id not in self.hour_requests:
            self.hour_requests[client_id] = []
        
        if len(self.hour_requests[client_id]) >= self.requests_per_hour:
            return False
        
        # Add current request
        self.minute_requests[client_id].append(current_time)
        self.hour_requests[client_id].append(current_time)
        
        return True
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove old entries from tracking dictionaries"""
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        for client_id in list(self.minute_requests.keys()):
            self.minute_requests[client_id] = [
                req_time for req_time in self.minute_requests[client_id]
                if req_time > minute_ago
            ]
            if not self.minute_requests[client_id]:
                del self.minute_requests[client_id]
        
        for client_id in list(self.hour_requests.keys()):
            self.hour_requests[client_id] = [
                req_time for req_time in self.hour_requests[client_id]
                if req_time > hour_ago
            ]
            if not self.hour_requests[client_id]:
                del self.hour_requests[client_id]


def get_client_id(request: Request) -> str:
    """Extract client identifier from request"""
    # Use X-Forwarded-For header if available, otherwise use client host
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    return request.client.host if request.client else "unknown"


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "&", '"', "'", "javascript:", "data:"]
    sanitized = text
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    
    # Limit length
    if len(sanitized) > 10000:  # 10KB limit
        sanitized = sanitized[:10000]
    
    return sanitized.strip() 