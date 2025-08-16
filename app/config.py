"""
Configuration management using Pydantic BaseSettings
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator
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


class LLMProviderConfig(BaseModel):
    """LLM Provider configuration"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    models: List[str]
    
    
class LLMSettings(BaseModel):
    """LLM configuration with provider support"""
    primary_provider: str = Field(default="groq", description="Primary LLM provider (groq/openai)")
    fallback_provider: Optional[str] = Field(default="openai", description="Fallback LLM provider")
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=dict)
    
    @field_validator('providers', mode='before')
    @classmethod
    def set_default_providers(cls, v):
        """Set default provider configurations"""
        if not v:
            v = {}
        
        # Default Groq configuration
        if 'groq' not in v:
            v['groq'] = {
                'name': 'groq',
                'base_url': 'https://api.groq.com/openai/v1',
                'models': ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
            }
        
        # Default OpenAI configuration
        if 'openai' not in v:
            v['openai'] = {
                'name': 'openai', 
                'base_url': 'https://api.openai.com/v1',
                'models': ['gpt-3.5-turbo', 'gpt-4o-mini']
            }
        
        return v


class OpenAISettings(BaseModel):
    """OpenAI configuration (legacy - kept for compatibility)"""
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
    
    # LLM Providers
    llm_primary_provider: str = Field(default="groq", alias="LLM_PRIMARY_PROVIDER")
    llm_fallback_provider: Optional[str] = Field(default="openai", alias="LLM_FALLBACK_PROVIDER")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    
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
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_llm_keys(cls, v, info):
        """Ensure at least one LLM provider has an API key"""
        # Get the groq_api_key from the data being validated
        data = info.data if hasattr(info, 'data') else {}
        groq_key = data.get('groq_api_key')
        
        if not groq_key and not v:
            raise ValueError("At least one LLM provider API key (GROQ_API_KEY or OPENAI_API_KEY) must be configured")
        return v
        
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
    def llm(self) -> LLMSettings:
        """Get LLM settings with provider configurations"""
        providers = {
            'groq': LLMProviderConfig(
                name='groq',
                base_url='https://api.groq.com/openai/v1',
                api_key=self.groq_api_key,
                models=['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
            ),
            'openai': LLMProviderConfig(
                name='openai',
                base_url='https://api.openai.com/v1', 
                api_key=self.openai_api_key,
                models=['gpt-3.5-turbo', 'gpt-4o-mini']
            )
        }
        
        return LLMSettings(
            primary_provider=self.llm_primary_provider,
            fallback_provider=self.llm_fallback_provider,
            providers=providers
        )
    
    @property
    def openai(self) -> OpenAISettings:
        """Get OpenAI settings (legacy - for compatibility)"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not configured")
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