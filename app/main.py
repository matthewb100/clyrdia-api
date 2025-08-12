"""
Main FastAPI application for Clyrdia Contract Intelligence Platform
"""
import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.logging import setup_logging, MetricsMiddleware, get_metrics, get_logger
from app.core.cache import cache
from app.services.supabase_service import supabase_service
from app.api.v1.endpoints import router as api_v1_router

# Setup logging
setup_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Clyrdia Contract Intelligence API")
    
    # Initialize services
    try:
        await cache.connect()
        await supabase_service.connect()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Clyrdia Contract Intelligence API")
    try:
        await cache.disconnect()
        await supabase_service.disconnect()
        logger.info("All services disconnected successfully")
    except Exception as e:
        logger.error("Failed to disconnect services", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered contract analysis and risk assessment platform",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(MetricsMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure based on your deployment
    )


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(
        "Request validation error",
        path=request.url.path,
        errors=exc.errors(),
        client_ip=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": "Invalid request data",
            "errors": exc.errors(),
            "timestamp": time.time()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
        client_ip=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error_type=type(exc).__name__,
        error_message=str(exc),
        client_ip=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Clyrdia Contract Intelligence API",
        "version": settings.app_version,
        "status": "operational",
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }


# Health check endpoint (basic)
@app.get("/health")
async def basic_health():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version
    }


# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics()


# Include API routes
app.include_router(
    api_v1_router,
    prefix="/api/v1",
    tags=["v1"]
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(
        "Clyrdia API starting up",
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Clyrdia API shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower()
    ) 