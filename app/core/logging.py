"""
Logging and monitoring configuration
"""
import sys
import os
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory
import logging
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
import time

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"]
)


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup structured logging configuration"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Set log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class MetricsMiddleware:
    """Middleware to collect HTTP metrics"""
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint (remove query params)
        endpoint = request.url.path
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        # Record errors
        if response.status_code >= 400:
            error_type = "client_error" if response.status_code < 500 else "server_error"
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()
        
        return response


def get_metrics():
    """Get Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def log_request(request: Request, logger: structlog.BoundLogger = None):
    """Log incoming request details"""
    if logger is None:
        logger = get_logger()
    
    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown"),
        content_length=request.headers.get("content-length", "0"),
    )


def log_response(response: Response, duration: float, logger: structlog.BoundLogger = None):
    """Log response details"""
    if logger is None:
        logger = get_logger()
    
    logger.info(
        "Response sent",
        status_code=response.status_code,
        duration=duration,
        content_length=response.headers.get("content-length", "0"),
    )


def log_error(error: Exception, context: Dict[str, Any] = None, logger: structlog.BoundLogger = None):
    """Log error with context"""
    if logger is None:
        logger = get_logger()
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_traceback": getattr(error, "__traceback__", None),
    }
    
    if context:
        log_data.update(context)
    
    logger.error("Application error", **log_data) 