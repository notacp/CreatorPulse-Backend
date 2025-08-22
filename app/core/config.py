"""
Application configuration settings.
"""
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=False, env="API_RELOAD")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Supabase (Required for authentication)
    supabase_url: str = Field(..., env="SUPABASE_URL", description="Supabase project URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY", description="Supabase anon key")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY", description="Supabase service role key")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Authentication
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=1440, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # External APIs (optional for auth testing)
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    twitter_bearer_token: Optional[str] = Field(default=None, env="TWITTER_BEARER_TOKEN")
    
    # Email
    sendgrid_from_email: str = Field(default="drafts@creatorpulse.com", env="SENDGRID_FROM_EMAIL")
    sendgrid_from_name: str = Field(default="CreatorPulse", env="SENDGRID_FROM_NAME")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_storage_url: str = Field(default="redis://localhost:6379/3", env="RATE_LIMIT_STORAGE_URL")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,https://localhost:3000,https://creator-pulse-frontend.vercel.app,https://creator-pulse-frontend-m8o7kfino-pradyumn-s-projects.vercel.app,https://creatorpulse.vercel.app,https://creatorpulse.com",
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    

    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()