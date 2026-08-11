import logging
from abc import ABC, abstractmethod
from typing import Any

import requests
from django.utils import timezone

from core.llm_providers.models import LLMProvider, TokenUsageLog, TokenUsageSummary
from core.llm_providers.schemas import LLMResponse

logger = logging.getLogger(__name__)

class LLMService(ABC):
    """Abstract Base Class defining the standard interface for all LLM Provider integrations.

    Ensures that any external AI service (like OpenAI, Gemini, etc.) implements
    a consistent method for generating content, logging usage, and calculating costs.
    """
    def __init__(self, api_key: str, model_name: str, provider_record: LLMProvider):
        """Initialize the service with credentials and the database provider record."""
        self.api_key = api_key
        self.model_name = model_name
        self.provider_record = provider_record
        self.last_usage: dict[str, int] | None = None

    @staticmethod
    def get_service(provider_code: str | None = None, provider: LLMProvider | None = None) -> 'LLMService':
        """Factory method to instantiate the correct LLMService subclass (e.g., GeminiService, OpenAIService).

        It attempts to resolve the provider either by direct DB record, by a provider_code,
        or by falling back to the system-wide default provider.
        """
        if not provider:
            if provider_code:
                provider = LLMProvider.objects.filter(code=provider_code, enabled=True).first()
            else:
                provider = LLMProvider.objects.filter(is_default=True, enabled=True).first()
                if not provider:
                    provider = LLMProvider.objects.filter(enabled=True).first()

        if not provider:
            raise Exception(f"No active LLM provider found for code: {provider_code or 'default'}")

        from core.llm_providers.models import LLMProviderCodes

        provider_code_val = provider.code

        # Use decrypted API key
        api_key = provider.get_decrypted_api_key() if hasattr(provider, 'get_decrypted_api_key') else provider.api_key

        if provider_code_val == LLMProviderCodes.GEMINI.value:
            return GeminiService(api_key, provider.model, provider)
        elif provider_code_val == LLMProviderCodes.OPENAI.value:
            return OpenAIService(api_key, provider.model, provider)
        elif provider_code_val == LLMProviderCodes.ANTHROPIC.value:
            return AnthropicService(api_key, provider.model, provider)
        else:
            raise Exception(f"Unsupported LLM Provider code: {provider_code_val} (name: {provider.name})")

    def test_connection(self) -> str:
        """Tests the connection by sending a basic Ping prompt.

        Returns the string response from the LLM.
        """
        messages = [{'role': 'user', 'content': 'Ping. Reply with exactly the word: Pong'}]
        response = self.generate_content(messages, action='test_connection')
        return response.text if response and hasattr(response, 'text') else str(response)

    @abstractmethod
    def generate_content(
        self,
        messages: list[dict[str, str]],
        action: str | None = None,
        brand_id: int | None = None,
        brand_name: str | None = None,
        response_type: str | None = None
    ) -> LLMResponse:
        """Send a conversation history to the LLM and return the generated response.

        Must be implemented by subclasses to handle provider-specific API formats.
        `messages` format: [{'role': 'system'|'user'|'assistant', 'content': '...'}]
        Returns an LLMResponse (a string subclass) containing the text and token metadata.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name."""
        pass

    def get_last_usage(self) -> dict[str, int] | None:
        """Get last usage."""
        return self.last_usage

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Override this in subclasses to provide cost calculation."""
        return 0.0

    def log_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        success: bool = True,
        error_message: str | None = None,
        action: str | None = None,
        brand_id: int | None = None,
        brand_name: str | None = None
    ):
        """Log granular token usage and update the daily aggregated TokenUsageSummary."""
        brand_name = brand_name or ''

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
        summary, _ = TokenUsageSummary.objects.get_or_create(
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

    def _save_llm_conversation(
        self,
        messages: list[dict[str, str]],
        response_text: str,
        action: str | None,
        brand_name: str | None,
        finish_reason: str | None = None
    ):
        """Save the prompt and response to a local JSON file in MEDIA_ROOT."""
        try:
            import json
            import os
            from datetime import datetime

            from django.conf import settings
            from django.utils.text import get_valid_filename

            date_folder = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            provider = get_valid_filename(self.get_provider_name().replace(" ", "_").lower())
            b_name = get_valid_filename(brand_name) if brand_name else "unknown"
            act = get_valid_filename(action) if action else "unknown"

            base_dir = os.path.join(
                settings.MEDIA_ROOT,
                "llm",
                provider,
                date_folder,
                b_name,
                act
            )
            os.makedirs(base_dir, exist_ok=True)

            filename = f"{act}_{timestamp}.json"
            filepath = os.path.join(base_dir, filename)

            payload = {
                "timestamp": datetime.now().isoformat(),
                "provider": self.get_provider_name(),
                "action": action,
                "brand_name": brand_name,
                "model": self.model_name,
                "finish_reason": finish_reason,
                "messages": messages,
                "response": response_text
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)

            logger.info(f"Saved LLM conversation to {filepath}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to save LLM conversation: {e}")

class GeminiService(LLMService):
    """Gemini Service."""
    # Gemini 1.5 Flash USD Pricing per 1M tokens
    PRICE_PROMPT_1M = 0.075
    PRICE_COMPLETION_1M = 0.30

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost."""
        prompt_cost = (prompt_tokens / 1000000.0) * self.PRICE_PROMPT_1M
        completion_cost = (completion_tokens / 1000000.0) * self.PRICE_COMPLETION_1M
        return prompt_cost + completion_cost

    def get_provider_name(self) -> str:
        """Get provider name."""
        return 'Google Gemini'

    def generate_content(
        self,
        messages: list[dict[str, str]],
        action: str | None = None,
        brand_id: int | None = None,
        brand_name: str | None = None,
        response_type: str | None = None
    ) -> LLMResponse:
        """Send a conversation payload to the Google Gemini API.

        Translates our standard message format into Gemini's required parts/contents
        schema, handles system instructions, and executes the HTTP request.
        """
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

        data: dict[str, Any] = {
            'contents': gemini_content,
            'generationConfig': {
                'temperature': 0.7,
                'maxOutputTokens': 8192,
            }
        }

        if response_type == 'json':
            data['generationConfig']['responseMimeType'] = 'application/json'

        if system_parts:
            data['system_instruction'] = {
                'parts': system_parts
            }

        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=60)
            http_code = response.status_code

            try:
                decoded = response.json()
            except ValueError:
                decoded = None

            if http_code != 200 or (decoded and 'error' in decoded):
                err_msg = decoded.get('error', {}).get('message', 'Unknown error') if decoded else 'Unknown error'
                err_code = decoded.get('error', {}).get('code', http_code) if decoded else http_code

                if (
                    http_code == 429 or
                    'quota' in err_msg.lower() or
                    'billing' in err_msg.lower() or
                    'RESOURCE_EXHAUSTED' in err_msg
                ):
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

            if (
                'candidates' in decoded and
                decoded['candidates'] and
                'content' in decoded['candidates'][0] and
                'parts' in decoded['candidates'][0]['content']
            ):
                text_content = decoded['candidates'][0]['content']['parts'][0]['text']
                finish_reason = decoded['candidates'][0].get('finishReason', 'UNKNOWN')

                self.log_usage(
                    prompt_tokens, completion_tokens, total_tokens,
                    success=True, action=action, brand_id=brand_id, brand_name=brand_name
                )

                self._save_llm_conversation(messages, text_content, action, brand_name, finish_reason)

                return LLMResponse(
                    text_content, prompt_tokens, completion_tokens,
                    total_tokens, self.get_provider_name()
                )

            if 'promptFeedback' in decoded and 'blockReason' in decoded['promptFeedback']:
                raise Exception(
                    f"Gemini blocked this request due to safety filters: "
                    f"{decoded['promptFeedback']['blockReason']}"
                )

            raise Exception(f"Gemini returned an unexpected response format. Raw: {response.text[:300]}")

        except Exception as e:
            self.log_usage(
                0, 0, 0, success=False, error_message=str(e),
                action=action, brand_id=brand_id, brand_name=brand_name
            )
            raise e

class OpenAIService(LLMService):
    """OpenAI Service."""
    def get_provider_name(self) -> str:
        """Get provider name."""
        return 'OpenAI'

    def generate_content(
        self,
        messages: list[dict[str, str]],
        action: str | None = None,
        brand_id: int | None = None,
        brand_name: str | None = None,
        response_type: str | None = None
    ) -> LLMResponse:
        """Generate content from OpenAI API."""
        raise NotImplementedError("OpenAI integration is pending.")

class AnthropicService(LLMService):
    """Anthropic Service."""
    def get_provider_name(self) -> str:
        """Get provider name."""
        return 'Anthropic'

    def generate_content(
        self,
        messages: list[dict[str, str]],
        action: str | None = None,
        brand_id: int | None = None,
        brand_name: str | None = None,
        response_type: str | None = None
    ) -> LLMResponse:
        """Generate content from Anthropic API."""
        raise NotImplementedError("Anthropic integration is pending.")
