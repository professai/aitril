"""
Orchestration logic for AiTril.

Manages multiple LLM providers and coordinates parallel queries.
"""

import asyncio
from typing import Dict

from .providers import create_provider, Provider


class AiTril:
    """Main orchestration class for managing multiple LLM providers."""

    def __init__(self, config: dict):
        """
        Initialize AiTril with configuration.

        Args:
            config: Configuration dictionary containing provider settings.
        """
        self.config = config
        self.providers: Dict[str, Provider] = {}

        # Initialize all enabled providers
        if "providers" in config:
            for name, provider_config in config["providers"].items():
                if isinstance(provider_config, dict) and provider_config.get("enabled", False):
                    try:
                        self.providers[name] = create_provider(name, provider_config)
                    except Exception as e:
                        print(f"Warning: Failed to initialize {name} provider: {e}")

    def get_enabled_providers(self) -> list[str]:
        """
        Get list of enabled provider names.

        Returns:
            List of enabled provider names.
        """
        return list(self.providers.keys())

    async def ask_single(self, provider_name: str, prompt: str) -> str:
        """
        Send a prompt to a single provider.

        Args:
            provider_name: Name of the provider to query.
            prompt: The prompt to send.

        Returns:
            The provider's response.

        Raises:
            ValueError: If provider is not enabled or doesn't exist.
        """
        if provider_name not in self.providers:
            available = ", ".join(self.providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' is not enabled. "
                f"Available providers: {available}"
            )

        return await self.providers[provider_name].ask(prompt)

    async def ask_tri(self, prompt: str) -> Dict[str, str]:
        """
        Send a prompt to all enabled providers in parallel.

        Args:
            prompt: The prompt to send.

        Returns:
            Dictionary mapping provider names to their responses.
            Providers that error will have their error message as the value.
        """
        if not self.providers:
            raise ValueError("No providers enabled. Run 'aitril init' to configure providers.")

        async def _query_provider(name: str, provider: Provider) -> tuple[str, str]:
            """Query a single provider and handle errors."""
            try:
                response = await provider.ask(prompt)
                return name, response
            except Exception as e:
                return name, f"ERROR: {str(e)}"

        # Query all providers in parallel
        tasks = [
            _query_provider(name, provider)
            for name, provider in self.providers.items()
        ]

        results = await asyncio.gather(*tasks)

        # Convert list of tuples to dictionary
        return dict(results)

    def provider_display_name(self, provider_name: str) -> str:
        """
        Get a human-readable display name for a provider.

        Args:
            provider_name: Internal provider name.

        Returns:
            Display name for the provider.
        """
        display_names = {
            "openai": "GPT (OpenAI)",
            "anthropic": "Claude (Anthropic)",
            "gemini": "Gemini (Google)",
        }
        return display_names.get(provider_name, provider_name.title())
