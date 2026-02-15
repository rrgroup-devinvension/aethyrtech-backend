import requests
from django.conf import settings

class GeminiService:
    @staticmethod
    def generate(prompt):
        config = settings.LLM_CONFIG
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{config['model']}:generateContent?key={config['api_key']}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload)
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

class LLMService:

    @staticmethod
    def generate_content(prompt):
        results = []
        if settings.LLM_CONFIG["service"]=='gemini':
            try:
                content = GeminiService.generate(prompt)
                results.append({"provider": "Gemini", "content": content})
            except Exception as e:
                print("Gemini error:", e)
        # Future OpenAI / Anthropic support
        return results