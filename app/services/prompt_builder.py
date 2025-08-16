"""
Unified prompt builder for provider-agnostic LLM interactions
"""

import logging
from typing import List, Dict, Any, Optional
from app.prompts.character_prompts import get_character_prompt_by_character_id
from app.models.character import Character

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Provider-agnostic prompt builder for LLM interactions"""
    
    def __init__(self):
        # Token limits for different providers for cost efficiency
        self.provider_limits = {
            'groq': {
                'max_prompt_tokens': 150,  # Keep Groq prompts concise
                'max_context_tokens': 2000,
                'models': ['mixtral-8x7b-32768', 'llama2-70b-4096']
            },
            'openai': {
                'max_prompt_tokens': 500,  # OpenAI can handle longer prompts
                'max_context_tokens': 4000,
                'models': ['gpt-3.5-turbo', 'gpt-4o-mini']
            }
        }
    
    def get_system_prompt(
        self,
        character: Character,
        language: str = "en",
        provider: str = "groq"
    ) -> str:
        """
        Get system prompt for character and language with provider optimization
        
        Args:
            character: Character model instance
            language: Language code (en, hi, ta)
            provider: LLM provider (groq, openai)
            
        Returns:
            str: System prompt optimized for provider
        """
        try:
            # Get the full character prompt template
            full_prompt = get_character_prompt_by_character_id(
                character.id,
                character.personality_type,
                language
            )
            
            if not full_prompt:
                # Fallback system prompt
                fallback_prompt = self._get_fallback_system_prompt(character, language)
                logger.warning(f"Using fallback prompt for character {character.id}")
                return self._optimize_for_provider(fallback_prompt, provider)
            
            # Optimize for provider
            optimized_prompt = self._optimize_for_provider(full_prompt, provider)
            
            logger.debug(f"Generated system prompt for character {character.id} ({character.personality_type}) in {language} for {provider}")
            return optimized_prompt
            
        except Exception as e:
            logger.error(f"Error generating system prompt for character {character.id}: {e}")
            return self._get_fallback_system_prompt(character, language)
    
    def build_messages(
        self,
        character: Character,
        context_messages: List[Dict[str, str]],
        user_message: str,
        language: str = "en",
        provider: str = "groq"
    ) -> List[Dict[str, str]]:
        """
        Build complete message array for LLM with provider optimization
        
        Args:
            character: Character model instance
            context_messages: Previous conversation messages
            user_message: Current user message
            language: Language code (en, hi, ta)
            provider: LLM provider (groq, openai)
            
        Returns:
            List[Dict[str, str]]: Formatted messages for LLM
        """
        try:
            # Get system prompt
            system_prompt = self.get_system_prompt(character, language, provider)
            
            # Start with system message
            messages = [{"role": "system", "content": system_prompt}]
            
            # Optimize context for provider
            optimized_context = self._optimize_context_for_provider(
                context_messages, 
                provider,
                system_prompt
            )
            
            # Add context messages
            messages.extend(optimized_context)
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Final validation
            self._validate_message_structure(messages)
            
            logger.debug(f"Built {len(messages)} messages for {provider} provider")
            return messages
            
        except Exception as e:
            logger.error(f"Error building messages: {e}")
            # Return minimal safe structure
            return [
                {"role": "system", "content": f"You are {character.name}, a helpful AI assistant."},
                {"role": "user", "content": user_message}
            ]
    
    def _optimize_for_provider(self, prompt: str, provider: str) -> str:
        """Optimize prompt for specific provider"""
        if provider not in self.provider_limits:
            provider = "groq"  # Default fallback
        
        limits = self.provider_limits[provider]
        max_tokens = limits['max_prompt_tokens']
        
        # Estimate token count (rough heuristic: 1 token ≈ 4 characters)
        estimated_tokens = len(prompt) // 4
        
        if estimated_tokens <= max_tokens:
            return prompt
        
        # If too long, create optimized version
        if provider == "groq":
            return self._create_concise_prompt(prompt)
        else:
            # For OpenAI, we can be less aggressive with truncation
            return self._create_balanced_prompt(prompt)
    
    def _create_concise_prompt(self, full_prompt: str) -> str:
        """Create concise prompt for Groq (under 150 tokens)"""
        lines = full_prompt.split('\n')
        
        # Extract key information
        name = "Assistant"
        personality = "helpful"
        language_instruction = "Respond in the user's language."
        
        # Try to extract character name and personality from prompt
        for line in lines:
            if "You are" in line and "," in line:
                parts = line.split(',')[0].replace("You are", "").strip()
                if parts:
                    name = parts
                    break
        
        # Look for personality traits
        for line in lines:
            if any(trait in line.lower() for trait in ["friendly", "playful", "caring", "witty", "empathetic"]):
                for trait in ["friendly", "playful", "caring", "witty", "empathetic"]:
                    if trait in line.lower():
                        personality = trait
                        break
                break
        
        # Create concise prompt
        concise_prompt = f"You are {name}, a {personality} AI companion. {language_instruction} Keep responses under 100 words unless asked for more. Be warm, helpful, and engaging."
        
        logger.debug("Created concise prompt for Groq")
        return concise_prompt
    
    def _create_balanced_prompt(self, full_prompt: str) -> str:
        """Create balanced prompt for OpenAI (more detailed but still efficient)"""
        lines = full_prompt.split('\n')
        
        # Keep first paragraph (usually contains core character info)
        first_section = []
        personality_section = []
        style_section = []
        
        current_section = "first"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "personality" in line.lower() or "traits" in line.lower():
                current_section = "personality"
            elif "style" in line.lower() or "communication" in line.lower():
                current_section = "style"
            
            if current_section == "first" and len(first_section) < 3:
                first_section.append(line)
            elif current_section == "personality" and len(personality_section) < 5:
                personality_section.append(line)
            elif current_section == "style" and len(style_section) < 3:
                style_section.append(line)
        
        # Combine sections
        balanced_prompt = '\n'.join(first_section)
        if personality_section:
            balanced_prompt += '\n\nKey traits: ' + ' '.join(personality_section[:3])
        if style_section:
            balanced_prompt += '\n\nStyle: ' + ' '.join(style_section[:2])
        
        logger.debug("Created balanced prompt for OpenAI")
        return balanced_prompt
    
    def _optimize_context_for_provider(
        self,
        context_messages: List[Dict[str, str]],
        provider: str,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Optimize context messages for provider token limits"""
        if not context_messages:
            return []
        
        limits = self.provider_limits.get(provider, self.provider_limits['groq'])
        max_context_tokens = limits['max_context_tokens']
        
        # Estimate system prompt tokens
        system_tokens = len(system_prompt) // 4
        available_tokens = max_context_tokens - system_tokens - 50  # Buffer for user message
        
        # Start from the most recent messages and work backwards
        optimized_context = []
        current_tokens = 0
        
        for message in reversed(context_messages):
            message_tokens = len(message['content']) // 4
            if current_tokens + message_tokens > available_tokens:
                break
            
            optimized_context.insert(0, message)
            current_tokens += message_tokens
        
        logger.debug(f"Optimized context: {len(optimized_context)} messages, ~{current_tokens} tokens")
        return optimized_context
    
    def _get_fallback_system_prompt(self, character: Character, language: str) -> str:
        """Get fallback system prompt when character prompt is not available"""
        language_instructions = {
            'en': 'Respond in English.',
            'hi': 'हिंदी में जवाब दें।',
            'ta': 'தமிழில் பதிலளியுங்கள்।'
        }
        
        lang_instruction = language_instructions.get(language, language_instructions['en'])
        
        personality_descriptions = {
            'friendly': 'warm and supportive',
            'playful': 'fun-loving and witty',
            'caring': 'empathetic and nurturing'
        }
        
        personality_desc = personality_descriptions.get(
            character.personality_type, 
            'helpful and friendly'
        )
        
        return f"You are {character.name}, a {personality_desc} AI companion. {lang_instruction} Be helpful, engaging, and keep responses under 100 words unless asked for more."
    
    def _validate_message_structure(self, messages: List[Dict[str, str]]) -> None:
        """Validate message structure for LLM compatibility"""
        required_roles = {'system', 'user', 'assistant'}
        
        for i, message in enumerate(messages):
            if 'role' not in message:
                raise ValueError(f"Message {i} missing 'role' field")
            if 'content' not in message:
                raise ValueError(f"Message {i} missing 'content' field")
            if message['role'] not in required_roles:
                raise ValueError(f"Message {i} has invalid role: {message['role']}")
            if not message['content'].strip():
                raise ValueError(f"Message {i} has empty content")
    
    def estimate_total_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate total token count for message array"""
        total_chars = sum(len(msg['content']) for msg in messages)
        # Add overhead for structure and formatting
        overhead = len(messages) * 15  # More conservative estimate
        return (total_chars // 4) + overhead
    
    def get_provider_optimization_info(self, provider: str) -> Dict[str, Any]:
        """Get optimization information for provider"""
        return self.provider_limits.get(provider, self.provider_limits['groq']).copy()


# Global prompt builder instance
prompt_builder = PromptBuilder()