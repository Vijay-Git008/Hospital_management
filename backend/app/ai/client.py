import abc
import httpx
from typing import Optional

class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def generate_text(self, prompt: str) -> str:
        """Sends a prompt to the LLM and returns the text response."""
        pass

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model_name: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model_name = model_name or "gpt-4o-mini"
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate_text(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"OpenAI error: {response.status_code} - {response.text}")
            data = response.json()
            return data["choices"][0]["message"]["content"]

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model_name: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        # Default to gemini-3.5-flash as the modern primary model
        self.model_name = model_name or "gemini-3.5-flash"
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate_text(self, prompt: str) -> str:
        from google import genai
        
        # Initialize GenAI Client with key
        client = genai.Client(api_key=self.api_key)
        
        # Use modern interactions.create API
        interaction = client.interactions.create(
            model=self.model_name,
            input=prompt
        )
        return interaction.output_text

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model_name: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model_name = model_name or "claude-3-5-sonnet-20241022"
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate_text(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"Anthropic error: {response.status_code} - {response.text}")
            data = response.json()
            return data["content"][0]["text"]

def get_client_by_provider(provider: str, api_key: str, model_name: str, temperature: float, max_tokens: int) -> LLMClient:
    prov = provider.lower()
    if prov == "openai":
        return OpenAIClient(api_key, model_name, temperature, max_tokens)
    elif prov == "gemini":
        return GeminiClient(api_key, model_name, temperature, max_tokens)
    elif prov == "anthropic":
        return AnthropicClient(api_key, model_name, temperature, max_tokens)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

async def test_llm_connection(provider: str, api_key: str, model_name: str, temperature: float) -> bool:
    """Verifies API connection with a simple lightweight ping request."""
    try:
        client = get_client_by_provider(provider, api_key, model_name, temperature, max_tokens=10)
        # Fast query
        res = await client.generate_text("respond with 'pong' and nothing else.")
        return "pong" in res.lower()
    except Exception as e:
        print(f"LLM connection test failed: {e}")
        return False
