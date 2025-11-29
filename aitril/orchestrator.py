"""
Orchestration logic for AiTril.

Manages multiple LLM providers and coordinates parallel queries.
"""

import asyncio
from typing import Dict, Optional

from .providers import create_provider, Provider
from .cache import SessionCache
from .coordinator import AgentCoordinator, CoordinationStrategy


class AiTril:
    """Main orchestration class for managing multiple LLM providers."""

    def __init__(self, config: dict, session_name: Optional[str] = None, use_cache: bool = True):
        """
        Initialize AiTril with configuration.

        Args:
            config: Configuration dictionary containing provider settings.
            session_name: Name of session for caching. Auto-generated if None.
            use_cache: Whether to enable caching.
        """
        self.config = config
        self.providers: Dict[str, Provider] = {}
        self.use_cache = use_cache
        self.cache = SessionCache(session_name) if use_cache else None
        self.coordinator = None

        # Initialize all enabled providers (up to 8: openai, anthropic, gemini, ollama, llamacpp, custom1-3)
        if "providers" in config:
            for name, provider_config in config["providers"].items():
                if isinstance(provider_config, dict) and provider_config.get("enabled", False):
                    try:
                        # For custom providers, use provider_type to determine implementation
                        provider_type = provider_config.get("provider_type", name)

                        # Ensure base_url is passed through to provider
                        # This is critical for local models and Docker networking
                        provider_init_config = provider_config.copy()

                        self.providers[name] = create_provider(provider_type, provider_init_config)
                    except Exception as e:
                        print(f"Warning: Failed to initialize {name} provider: {e}")

        # Initialize coordinator with available providers
        if self.providers:
            self.coordinator = AgentCoordinator(self.providers)

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

    async def ask_single_stream(self, provider_name: str, prompt: str):
        """
        Send a prompt to a single provider and yield response chunks.

        Args:
            provider_name: Name of the provider to query.
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from the provider.

        Raises:
            ValueError: If provider is not enabled or doesn't exist.
        """
        if provider_name not in self.providers:
            available = ", ".join(self.providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' is not enabled. "
                f"Available providers: {available}"
            )

        async for chunk in self.providers[provider_name].ask_stream(prompt):
            yield chunk

    async def ask_tri(self, prompt: str, strategy: str = CoordinationStrategy.PARALLEL,
                      initial_planner: str = "none") -> Dict[str, any]:
        """
        Send a prompt to all enabled providers in parallel.

        Args:
            prompt: The prompt to send.
            strategy: Coordination strategy to use (parallel, sequential, consensus, debate, specialist)
            initial_planner: Provider to use as initial planner ("none" for parallel, or provider name)

        Returns:
            Dictionary mapping provider names to their responses.
            Providers that error will have their error message as the value.
        """
        if not self.providers:
            raise ValueError("No providers enabled. Run 'aitril init' to configure providers.")

        # Check if using planner-first mode
        if initial_planner != "none" and initial_planner in self.providers:
            responses = await self._ask_with_planner(prompt, initial_planner)
        # Execute with coordination strategy
        elif strategy == CoordinationStrategy.PARALLEL:
            responses = await self._ask_parallel(prompt)
        elif strategy == CoordinationStrategy.SEQUENTIAL:
            responses = await self.coordinator.coordinate_sequential(prompt)
        elif strategy == CoordinationStrategy.CONSENSUS:
            responses = await self.coordinator.coordinate_consensus(prompt)
        elif strategy == CoordinationStrategy.DEBATE:
            responses = await self.coordinator.coordinate_debate(prompt)
        else:
            responses = await self._ask_parallel(prompt)

        # Save to cache if enabled
        if self.use_cache and self.cache:
            # For complex responses (consensus/debate), save the full structure
            if isinstance(responses, dict) and "individual_responses" in responses:
                self.cache.add_to_history(prompt, responses)
            else:
                self.cache.add_to_history(prompt, responses)

        return responses

    async def _ask_with_planner(self, prompt: str, planner_name: str) -> Dict[str, str]:
        """
        Query with planner-first strategy: designated planner creates initial plan,
        then other agents improve and build on it.

        Args:
            prompt: The original user prompt.
            planner_name: Name of the provider to use as initial planner.

        Returns:
            Dictionary mapping provider names to their responses.
        """
        responses = {}

        # Step 1: Planner creates initial design/plan
        planner_prompt = f"""You are the initial planner for this request. Create a comprehensive plan/design/approach to address the following:

{prompt}

Focus on:
1. Overall strategy and architecture
2. Key components and their relationships
3. Implementation approach and considerations
4. Potential challenges and solutions

Provide a clear, structured plan that other agents can build upon and improve."""

        try:
            planner_response = await self.providers[planner_name].ask(planner_prompt)
            responses[planner_name] = planner_response
        except Exception as e:
            responses[planner_name] = f"ERROR: {str(e)}"
            # If planner fails, fall back to parallel mode
            return await self._ask_parallel(prompt)

        # Step 2: Other agents improve and build on the plan
        other_providers = {k: v for k, v in self.providers.items() if k != planner_name}

        if not other_providers:
            # Only one provider enabled, return planner's response
            return responses

        async def _query_builder(name: str, provider: Provider) -> tuple[str, str]:
            """Query a builder agent to improve on the plan."""
            builder_prompt = f"""The following is an initial plan created by another AI agent to address a user request.

USER REQUEST:
{prompt}

INITIAL PLAN:
{planner_response}

Your role is to:
1. Analyze and critique the plan
2. Suggest improvements and optimizations
3. Identify any gaps or issues
4. Provide additional implementation details
5. Offer alternative approaches if beneficial

Build upon and enhance the initial plan with your unique perspective."""

            try:
                response = await provider.ask(builder_prompt)
                return name, response
            except Exception as e:
                return name, f"ERROR: {str(e)}"

        # Query builder agents in parallel
        tasks = [
            _query_builder(name, provider)
            for name, provider in other_providers.items()
        ]

        builder_results = await asyncio.gather(*tasks)

        # Add builder responses to results
        for name, response in builder_results:
            responses[name] = response

        return responses

    async def _ask_parallel(self, prompt: str) -> Dict[str, str]:
        """
        Query all providers in parallel (default behavior).

        Args:
            prompt: The prompt to send.

        Returns:
            Dictionary mapping provider names to their responses.
        """
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
            "ollama": "Ollama (Local)",
            "llamacpp": "Llama.cpp (Local)",
            "custom1": "Custom Model 1",
            "custom2": "Custom Model 2",
            "custom3": "Custom Model 3",
        }
        return display_names.get(provider_name, provider_name.title())
