"""
Provider abstraction and implementations for AiTril.

Supports OpenAI (GPT), Anthropic (Claude), and Google Gemini providers.
"""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Optional

import openai
import anthropic
import google.generativeai as genai


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
        self.model = config.get("model", self._default_model())

    @abstractmethod
    def _get_env_var_name(self) -> str:
        """Return the environment variable name for the API key."""
        pass

    @abstractmethod
    def _default_model(self) -> str:
        """Return the default model name."""
        pass

    def _get_api_key(self) -> str:
        """
        Get API key from config or environment variable.

        Returns:
            API key string.

        Raises:
            ValueError: If no API key is found.
        """
        # Try config first
        api_key = self.config.get("api_key")

        # Fall back to environment variable
        if not api_key:
            api_key = os.environ.get(self._get_env_var_name())

        if not api_key:
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


class OpenAIProvider(Provider):
    """OpenAI (GPT) provider implementation."""

    def _get_env_var_name(self) -> str:
        return "OPENAI_API_KEY"

    def _default_model(self) -> str:
        return "gpt-4"

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
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            return response.choices[0].message.content

        result = await loop.run_in_executor(None, _sync_call)
        return result or ""


class AnthropicProvider(Provider):
    """Anthropic (Claude) provider implementation."""

    def _get_env_var_name(self) -> str:
        return "ANTHROPIC_API_KEY"

    def _default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"

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


class GeminiProvider(Provider):
    """Google Gemini provider implementation."""

    def _get_env_var_name(self) -> str:
        return "GEMINI_API_KEY"

    def _default_model(self) -> str:
        return "gemini-pro"

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


def create_provider(name: str, config: dict) -> Provider:
    """
    Factory function to create a provider instance.

    Args:
        name: Provider name ('openai', 'anthropic', 'gemini').
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
    }

    provider_class = providers.get(name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(providers.keys())}")

    return provider_class(config)
