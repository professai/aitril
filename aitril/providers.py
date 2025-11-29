"""
Provider abstraction and implementations for AiTril.

Supports OpenAI (GPT), Anthropic (Claude), Google Gemini, Ollama, and Llama.cpp providers.
"""

import asyncio
import os
import json
from abc import ABC, abstractmethod
from typing import Optional

import openai
import anthropic
import google.generativeai as genai
import httpx


class Provider(ABC):
    """Base class for LLM providers."""

    def __init__(self, config: dict):
        """
        Initialize provider with configuration.

        Args:
            config: Provider configuration dictionary containing 'api_key' and 'model'.
        """
        self.config = config
        self.api_key = self._get_api_key()
        self.model = self._get_model()

    @abstractmethod
    def _get_env_var_name(self) -> str:
        """Return the environment variable name for the API key."""
        pass

    @abstractmethod
    def _get_model_env_var_name(self) -> str:
        """Return the environment variable name for the model."""
        pass

    @abstractmethod
    def _default_model(self) -> str:
        """Return the default model name."""
        pass

    def _get_model(self) -> str:
        """
        Get model name from config or environment variable.

        Priority: config > environment variable > default

        Returns:
            Model name string.
        """
        # Try config first
        model = self.config.get("model")

        # Fall back to environment variable
        if not model:
            model = os.environ.get(self._get_model_env_var_name())

        # Fall back to default
        if not model:
            model = self._default_model()

        return model

    def _requires_api_key(self) -> bool:
        """Return True if provider requires an API key. Override for local models."""
        return True

    def _get_api_key(self) -> Optional[str]:
        """
        Get API key from config or environment variable.

        Returns:
            API key string, or None for local models.

        Raises:
            ValueError: If no API key is found and provider requires one.
        """
        # Try config first
        api_key = self.config.get("api_key")

        # Fall back to environment variable
        if not api_key:
            api_key = os.environ.get(self._get_env_var_name())

        if not api_key and self._requires_api_key():
            raise ValueError(
                f"No API key found for {self.__class__.__name__}. "
                f"Set {self._get_env_var_name()} environment variable or configure via 'aitril init'."
            )

        return api_key

    @abstractmethod
    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to the provider and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            The provider's response as a string.
        """
        pass

    @abstractmethod
    async def ask_stream(self, prompt: str):
        """
        Send a prompt to the provider and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from the provider.
        """
        pass


class OpenAIProvider(Provider):
    """OpenAI (GPT) provider implementation."""

    def _get_env_var_name(self) -> str:
        return "OPENAI_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "OPENAI_MODEL"

    def _default_model(self) -> str:
        return "gpt-5.1"

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to OpenAI and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            GPT's response as a string.
        """
        client = openai.OpenAI(api_key=self.api_key)

        # Wrap sync SDK call in executor to maintain async interface
        loop = asyncio.get_running_loop()

        def _sync_call():
            response = client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": prompt}],
                text={"format": {"type": "text"}},
                max_output_tokens=1000
            )
            return response.output_text

        result = await loop.run_in_executor(None, _sync_call)
        return result or ""

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to OpenAI and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from OpenAI.
        """
        # Use native async client for true async streaming
        client = openai.AsyncOpenAI(api_key=self.api_key)

        stream = await client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": prompt}],
            text={"format": {"type": "text"}},
            max_output_tokens=1000,
            stream=True
        )

        async for chunk in stream:
            # The responses API uses event-based streaming
            # Text content comes in response.output_text.delta events
            if hasattr(chunk, 'type') and chunk.type == 'response.output_text.delta':
                if hasattr(chunk, 'delta') and chunk.delta:
                    yield chunk.delta


class AnthropicProvider(Provider):
    """Anthropic (Claude) provider implementation."""

    def _get_env_var_name(self) -> str:
        return "ANTHROPIC_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "ANTHROPIC_MODEL"

    def _default_model(self) -> str:
        return "claude-opus-4-5-20250929"

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Anthropic Claude and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            Claude's response as a string.
        """
        client = anthropic.Anthropic(api_key=self.api_key)

        # Wrap sync SDK call in executor to maintain async interface
        loop = asyncio.get_running_loop()

        def _sync_call():
            message = client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text

        result = await loop.run_in_executor(None, _sync_call)
        return result or ""

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Anthropic Claude and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Claude.
        """
        # Use native async client for true async streaming
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        async with client.messages.stream(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text


class GeminiProvider(Provider):
    """Google Gemini provider implementation."""

    def _get_env_var_name(self) -> str:
        return "GOOGLE_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "GEMINI_MODEL"

    def _default_model(self) -> str:
        return "gemini-3-pro-preview"

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Google Gemini and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            Gemini's response as a string.
        """
        genai.configure(api_key=self.api_key)

        # Wrap sync SDK call in executor to maintain async interface
        loop = asyncio.get_running_loop()

        def _sync_call():
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text

        result = await loop.run_in_executor(None, _sync_call)
        return result or ""

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Google Gemini and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Gemini.
        """
        genai.configure(api_key=self.api_key)
        loop = asyncio.get_running_loop()

        def _sync_stream():
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        # Run the sync streaming generator in executor and yield chunks
        for chunk in await loop.run_in_executor(None, lambda: list(_sync_stream())):
            yield chunk


class OllamaProvider(Provider):
    """Ollama local model provider implementation."""

    def _requires_api_key(self) -> bool:
        return False

    def _get_env_var_name(self) -> str:
        return "OLLAMA_API_KEY"  # Not required but kept for consistency

    def _get_model_env_var_name(self) -> str:
        return "OLLAMA_MODEL"

    def _default_model(self) -> str:
        return "llama2"

    def _get_base_url(self) -> str:
        """Get Ollama base URL from config or environment."""
        base_url = self.config.get("base_url")
        if not base_url:
            base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return base_url

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            Ollama's response as a string.
        """
        base_url = self._get_base_url()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Ollama and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Ollama.
        """
        base_url = self._get_base_url()
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]


class LlamaCppProvider(Provider):
    """Llama.cpp server provider implementation."""

    def _requires_api_key(self) -> bool:
        return False

    def _get_env_var_name(self) -> str:
        return "LLAMACPP_API_KEY"  # Not required but kept for consistency

    def _get_model_env_var_name(self) -> str:
        return "LLAMACPP_MODEL"

    def _default_model(self) -> str:
        return "default"  # llama.cpp server uses a single model

    def _get_base_url(self) -> str:
        """Get Llama.cpp server base URL from config or environment."""
        base_url = self.config.get("base_url")
        if not base_url:
            base_url = os.environ.get("LLAMACPP_BASE_URL", "http://localhost:8080")
        return base_url

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Llama.cpp server and return the response.

        Args:
            prompt: The prompt to send.

        Returns:
            Llama.cpp's response as a string.
        """
        base_url = self._get_base_url()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{base_url}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": 1000,
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("content", "")

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Llama.cpp server and yield response chunks in real-time.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Llama.cpp.
        """
        base_url = self._get_base_url()
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": 1000,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line_data = line[6:]  # Remove "data: " prefix
                        if line_data.strip() and line_data.strip() != "[DONE]":
                            data = json.loads(line_data)
                            if "content" in data:
                                yield data["content"]


def create_provider(name: str, config: dict) -> Provider:
    """
    Factory function to create a provider instance.

    Args:
        name: Provider name ('openai', 'anthropic', 'gemini', 'ollama', 'llamacpp').
        config: Provider configuration dictionary.

    Returns:
        Provider instance.

    Raises:
        ValueError: If provider name is unknown.
    """
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
        "llamacpp": LlamaCppProvider,
    }

    provider_class = providers.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(providers.keys())}")

    return provider_class(config)
