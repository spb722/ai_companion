"""
LLM service for provider-agnostic AI interactions
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from app.config import settings, LLMProviderConfig

logger = logging.getLogger(__name__)


class LLMService:
    """Provider-agnostic LLM service using OpenAI SDK"""
    
    def __init__(self):
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._current_provider: Optional[str] = None
        self._fallback_provider: Optional[str] = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers based on configuration"""
        llm_config = settings.llm
        
        # Set provider priorities
        self._current_provider = llm_config.primary_provider
        self._fallback_provider = llm_config.fallback_provider
        
        # Initialize available providers
        for provider_name, provider_config in llm_config.providers.items():
            if provider_config.api_key:
                try:
                    client = AsyncOpenAI(
                        api_key=provider_config.api_key,
                        base_url=provider_config.base_url
                    )
                    self._clients[provider_name] = client
                    logger.info(f"Initialized {provider_name} LLM provider")
                except Exception as e:
                    logger.error(f"Failed to initialize {provider_name} provider: {e}")
            else:
                logger.warning(f"No API key configured for {provider_name} provider")
    
    def get_client(self, provider: Optional[str] = None) -> AsyncOpenAI:
        """Get LLM client for specified provider or current provider"""
        target_provider = provider or self._current_provider
        
        if target_provider not in self._clients:
            available = list(self._clients.keys())
            if not available:
                raise ValueError("No LLM providers are configured with valid API keys")
            target_provider = available[0]
            logger.warning(f"Provider {target_provider} not available, using {target_provider}")
        
        return self._clients[target_provider]
    
    def get_model(self, provider: Optional[str] = None) -> str:
        """Get appropriate model for the specified provider"""
        target_provider = provider or self._current_provider
        llm_config = settings.llm
        
        if target_provider in llm_config.providers:
            models = llm_config.providers[target_provider].models
            return models[0] if models else "gpt-3.5-turbo"  # Fallback model
        
        return "gpt-3.5-turbo"  # Default fallback
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider information"""
        return {
            "current_provider": self._current_provider,
            "fallback_provider": self._fallback_provider,
            "available_providers": list(self._clients.keys()),
            "current_model": self.get_model()
        }
    
    async def test_connection(self, provider: Optional[str] = None) -> bool:
        """Test connection to specified provider"""
        try:
            client = self.get_client(provider)
            model = self.get_model(provider)
            
            # Simple test completion
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0
            )
            
            return bool(response.choices and response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Connection test failed for provider {provider}: {e}")
            return False
    
    async def get_available_provider(self) -> Optional[str]:
        """Get first available provider that passes connection test"""
        # Try current provider first
        if await self.test_connection(self._current_provider):
            return self._current_provider
        
        # Try fallback provider
        if self._fallback_provider and await self.test_connection(self._fallback_provider):
            logger.warning(f"Primary provider {self._current_provider} failed, using fallback {self._fallback_provider}")
            return self._fallback_provider
        
        # Try any available provider
        for provider in self._clients.keys():
            if provider not in [self._current_provider, self._fallback_provider]:
                if await self.test_connection(provider):
                    logger.warning(f"Using alternative provider {provider}")
                    return provider
        
        logger.error("No LLM providers are available")
        return None
    
    def switch_provider(self, provider: str) -> bool:
        """Switch to a different provider"""
        if provider in self._clients:
            self._current_provider = provider
            logger.info(f"Switched to provider: {provider}")
            return True
        else:
            logger.error(f"Provider {provider} is not available")
            return False


# Global LLM service instance
llm_service = LLMService()