"""
Configuration management for Clyrdia API
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # FastAPI Configuration
    app_name: str = Field(default="Clyrdia Contract Intelligence API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    api_key: str = Field(env="API_KEY")
    
    # OpenAI Configuration
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    
    # Supabase Configuration
    supabase_url: str = Field(env="SUPABASE_URL")
    supabase_key: str = Field(env="SUPABASE_KEY")
    supabase_service_role_key: str = Field(env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["https://lovable.ai", "https://app.lovable.ai", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # File Upload Configuration
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        default=["pdf", "docx", "txt"], 
        env="ALLOWED_FILE_TYPES"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    sentry_dsn: str = Field(default="", env="SENTRY_DSN")
    prometheus_multiproc_dir: str = Field(default="/tmp", env="PROMETHEUS_MULTIPROC_DIR")
    
    # Webhook Configuration
    webhook_secret: str = Field(env="WEBHOOK_SECRET")
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings() 