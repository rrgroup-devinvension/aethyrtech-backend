import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from django.utils import timezone
from core.llm_providers.models import LLMProvider, TokenUsageLog, TokenUsageSummary
from core.llm_providers.schemas import LLMResponse

logger = logging.getLogger(__name__)

class LLMService(ABC):
    def __init__(self, api_key: str, model_name: str, provider_record: LLMProvider):
        self.api_key = api_key
        self.model_name = model_name
        self.provider_record = provider_record
        self.last_usage = None

    @staticmethod
    def get_service(provider_code: str = None) -> 'LLMService':
        if provider_code:
            provider = None
            try:
                # In case provider_code field doesn't exist yet in the DB model
                provider = LLMProvider.objects.filter(provider_code=provider_code, enabled=True).first()
            except Exception:
                pass
            
            # Fallback to provider_code as name if provider_code field isn't in DB yet
            if not provider:
                provider = LLMProvider.objects.filter(name__icontains=provider_code, enabled=True).first()
        else:
            provider = LLMProvider.objects.filter(is_default=True, enabled=True).first()
            if not provider:
                provider = LLMProvider.objects.filter(enabled=True).first()

        if not provider:
            raise Exception(f"No active LLM provider found for code: {provider_code or 'default'}")

        # Map provider name to correct subclass
        name_lower = provider.name.lower()
        if 'gemini' in name_lower:
            return GeminiService(provider.api_key, provider.model, provider)
        elif 'openai' in name_lower:
            return OpenAIService(provider.api_key, provider.model, provider)
        elif 'anthropic' in name_lower:
            return AnthropicService(provider.api_key, provider.model, provider)
        else:
            raise Exception(f"Unsupported LLM Provider: {provider.name}")

    @abstractmethod
    def generate_content(self, messages: List[Dict[str, str]], action: str = None, brand_id: int = None, brand_name: str = None) -> LLMResponse:
        """
        Generates content from the LLM provider based on the messages.
        messages format: [{'role': 'system'|'user'|'assistant', 'content': '...'}]
        Returns an LLMResponse (a string subclass) containing the text and token metadata.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    def get_last_usage(self) -> Optional[Dict[str, int]]:
        return self.last_usage

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Override this in subclasses to provide cost calculation"""
        return 0.0

    def log_usage(self, prompt_tokens: int, completion_tokens: int, total_tokens: int, success: bool = True, error_message: str = None, action: str = None, brand_id: int = None, brand_name: str = None):
        """
        Logs the token usage to the TokenUsageLog and updates the daily TokenUsageSummary.
        """
        self.last_usage = {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
        }

        # Calculate estimated cost
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens) if success else 0.0

        # 1. Create Log Entry
        TokenUsageLog.objects.create(
            provider=self.provider_record,
            type=action,  # Model field is 'type'
            brand_id=brand_id,
            brand_name=brand_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )

        # 2. Update Daily Summary
        today = timezone.now().date()
        summary, created = TokenUsageSummary.objects.get_or_create(
            provider=self.provider_record,
            date=today,
            type=action,
            brand_id=brand_id,
            defaults={
                'brand_name': brand_name,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0,
                'requests': 0,
                'estimated_cost': 0.0
            }
        )
        
        summary.requests += 1
        if success:
            summary.prompt_tokens += prompt_tokens
            summary.completion_tokens += completion_tokens
            summary.total_tokens += total_tokens
            # We use float/decimal addition. 
            # Because estimated_cost is a DecimalField, we should convert to decimal or just let django cast the float
            from decimal import Decimal
            summary.estimated_cost = Decimal(str(summary.estimated_cost)) + Decimal(str(estimated_cost))
            
        summary.save()

class GeminiService(LLMService):
    # Gemini 1.5 Flash USD Pricing per 1M tokens
    PRICE_PROMPT_1M = 0.075
    PRICE_COMPLETION_1M = 0.30

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        prompt_cost = (prompt_tokens / 1000000.0) * self.PRICE_PROMPT_1M
        completion_cost = (completion_tokens / 1000000.0) * self.PRICE_COMPLETION_1M
        return prompt_cost + completion_cost

    def get_provider_name(self) -> str:
        return 'Google Gemini'

    def generate_content(self, messages: List[Dict[str, str]], action: str = None, brand_id: int = None, brand_name: str = None) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        gemini_content = []
        system_parts = []

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            if role == 'system':
                system_parts.append({'text': content})
            elif role == 'user':
                gemini_content.append({
                    'role': 'user',
                    'parts': [{'text': content}]
                })
            elif role in ('assistant', 'model'):
                gemini_content.append({
                    'role': 'model',
                    'parts': [{'text': content}]
                })

        data = {
            'contents': gemini_content,
            'generationConfig': {
                'temperature': 0.7,
                'maxOutputTokens': 8192,
            }
        }

        if system_parts:
            data['system_instruction'] = {
                'parts': system_parts
            }

        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json=data, headers=headers)
            http_code = response.status_code
            
            try:
                decoded = response.json()
            except ValueError:
                decoded = None

            if http_code != 200 or (decoded and 'error' in decoded):
                err_msg = decoded.get('error', {}).get('message', 'Unknown error') if decoded else 'Unknown error'
                err_code = decoded.get('error', {}).get('code', http_code) if decoded else http_code
                
                if http_code == 429 or 'quota' in err_msg.lower() or 'billing' in err_msg.lower() or 'RESOURCE_EXHAUSTED' in err_msg:
                    raise Exception(f"Gemini API quota/billing limit reached. (API: {err_msg})")
                raise Exception(f"Gemini API error [{err_code}]: {err_msg}")

            if not decoded:
                snippet = response.text[:200]
                raise Exception(f"Gemini returned a non-JSON response (HTTP {http_code}). Snippet: {snippet}")

            # Extract Usage Metadata
            usage = decoded.get('usageMetadata', {})
            prompt_tokens = usage.get('promptTokenCount', 0)
            completion_tokens = usage.get('candidatesTokenCount', 0)
            total_tokens = usage.get('totalTokenCount', 0)

            if 'candidates' in decoded and decoded['candidates'] and 'content' in decoded['candidates'][0] and 'parts' in decoded['candidates'][0]['content']:
                text_content = decoded['candidates'][0]['content']['parts'][0]['text']
                self.log_usage(prompt_tokens, completion_tokens, total_tokens, success=True, action=action, brand_id=brand_id, brand_name=brand_name)
                return LLMResponse(text_content, prompt_tokens, completion_tokens, total_tokens, self.get_provider_name())

            if 'promptFeedback' in decoded and 'blockReason' in decoded['promptFeedback']:
                raise Exception(f"Gemini blocked this request due to safety filters: {decoded['promptFeedback']['blockReason']}")

            raise Exception(f"Gemini returned an unexpected response format. Raw: {response.text[:300]}")

        except Exception as e:
            self.log_usage(0, 0, 0, success=False, error_message=str(e), action=action, brand_id=brand_id, brand_name=brand_name)
            raise e

class OpenAIService(LLMService):
    def get_provider_name(self) -> str:
        return 'OpenAI'

    def generate_content(self, messages: List[Dict[str, str]], action: str = None, brand_id: int = None, brand_name: str = None) -> LLMResponse:
        raise NotImplementedError("OpenAI integration is pending.")

class AnthropicService(LLMService):
    def get_provider_name(self) -> str:
        return 'Anthropic'

    def generate_content(self, messages: List[Dict[str, str]], action: str = None, brand_id: int = None, brand_name: str = None) -> LLMResponse:
        raise NotImplementedError("Anthropic integration is pending.")