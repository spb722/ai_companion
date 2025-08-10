"""
Configuration management using Pydantic BaseSettings
"""

from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="MySQL database URL")


class RedisSettings(BaseModel):
    """Redis configuration"""
    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")


class SupabaseSettings(BaseModel):
    """Supabase configuration"""
    url: str = Field(..., description="Supabase project URL")
    anon_key: str = Field(..., description="Supabase anonymous key")
    service_key: str = Field(..., description="Supabase service key")


class OpenAISettings(BaseModel):
    """OpenAI configuration"""
    api_key: str = Field(..., description="OpenAI API key")


class SecuritySettings(BaseModel):
    """Security configuration"""
    secret_key: str = Field(..., description="Secret key for JWT tokens")


class RateLimitSettings(BaseModel):
    """Rate limiting configuration"""
    per_minute: int = Field(default=60, description="Requests per minute limit")
    daily_free: int = Field(default=50, description="Daily message limit for free users")
    daily_pro: int = Field(default=500, description="Daily message limit for pro users")


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_anon_key: str = Field(..., alias="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(..., alias="SUPABASE_SERVICE_KEY")
    
    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    
    # Security
    secret_key: str = Field(..., alias="SECRET_KEY")
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8001, alias="PORT")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    daily_message_limit_free: int = Field(default=50, alias="DAILY_MESSAGE_LIMIT_FREE")
    daily_message_limit_pro: int = Field(default=500, alias="DAILY_MESSAGE_LIMIT_PRO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def database(self) -> DatabaseSettings:
        """Get database settings"""
        return DatabaseSettings(url=self.database_url)
    
    @property
    def redis(self) -> RedisSettings:
        """Get Redis settings"""
        return RedisSettings(url=self.redis_url)
    
    @property
    def supabase(self) -> SupabaseSettings:
        """Get Supabase settings"""
        return SupabaseSettings(
            url=self.supabase_url,
            anon_key=self.supabase_anon_key,
            service_key=self.supabase_service_key
        )
    
    @property
    def openai(self) -> OpenAISettings:
        """Get OpenAI settings"""
        return OpenAISettings(api_key=self.openai_api_key)
    
    @property
    def security(self) -> SecuritySettings:
        """Get security settings"""
        return SecuritySettings(secret_key=self.secret_key)
    
    @property
    def rate_limits(self) -> RateLimitSettings:
        """Get rate limit settings"""
        return RateLimitSettings(
            per_minute=self.rate_limit_per_minute,
            daily_free=self.daily_message_limit_free,
            daily_pro=self.daily_message_limit_pro
        )


# Global settings instance
settings = Settings()