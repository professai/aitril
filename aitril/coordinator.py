"""
Multi-agent coordination for AiTril.

Enables LLM providers to coordinate, share context, and build on each other's
responses for more comprehensive and collaborative outputs.
"""

import asyncio
from typing import Dict, List, Optional

from .providers import Provider


class AgentCoordinator:
    """Coordinates multiple LLM agents to work together on tasks."""

    def __init__(self, providers: Dict[str, Provider]):
        """
        Initialize coordinator with available providers.

        Args:
            providers: Dictionary of provider name to Provider instance
        """
        self.providers = providers

    async def coordinate_sequential(
        self,
        prompt: str,
        provider_order: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Run providers sequentially, with each seeing previous responses.

        Each agent receives the original prompt plus summaries of previous
        agents' responses, allowing them to build on prior work.

        Args:
            prompt: Original user prompt
            provider_order: Order to run providers. Uses all if None.

        Returns:
            Dictionary of provider responses
        """
        if provider_order is None:
            provider_order = list(self.providers.keys())

        responses = {}
        context_history = []

        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue

            provider = self.providers[provider_name]

            # Build enriched prompt with previous responses
            enriched_prompt = prompt

            if context_history:
                context_str = "\n\n".join([
                    f"[Context from {name}]: {resp[:500]}..."
                    if len(resp) > 500 else f"[Context from {name}]: {resp}"
                    for name, resp in context_history
                ])
                enriched_prompt = (
                    f"{prompt}\n\n"
                    f"Previous agent responses for context:\n{context_str}\n\n"
                    f"Please provide your response, building on or complementing the above if relevant."
                )

            # Get response from provider
            response = await provider.ask(enriched_prompt)
            responses[provider_name] = response
            context_history.append((provider_name, response))

        return responses

    async def coordinate_consensus(
        self,
        prompt: str,
        min_agreement: int = 2
    ) -> Dict[str, any]:
        """
        Run providers in parallel, then synthesize a consensus response.

        All providers respond independently, then a final synthesis step
        identifies common themes and areas of agreement/disagreement.

        Args:
            prompt: User prompt
            min_agreement: Minimum providers that must agree for consensus

        Returns:
            Dictionary with individual responses and consensus summary
        """
        # Get all responses in parallel
        tasks = [
            provider.ask(prompt)
            for provider in self.providers.values()
        ]

        responses_list = await asyncio.gather(*tasks)
        responses = dict(zip(self.providers.keys(), responses_list))

        # Generate consensus summary
        consensus_prompt = self._build_consensus_prompt(prompt, responses)

        # Use first available provider to generate consensus
        first_provider = list(self.providers.values())[0]
        consensus = await first_provider.ask(consensus_prompt)

        return {
            "individual_responses": responses,
            "consensus": consensus,
            "meta": {
                "providers_count": len(responses),
                "min_agreement": min_agreement
            }
        }

    async def coordinate_debate(
        self,
        prompt: str,
        rounds: int = 2
    ) -> Dict[str, any]:
        """
        Run providers in a debate format over multiple rounds.

        Providers respond to the prompt, then in subsequent rounds respond
        to each other's arguments, refining and defending their positions.

        Args:
            prompt: User prompt/topic for debate
            rounds: Number of debate rounds

        Returns:
            Dictionary with all rounds of responses
        """
        debate_history = {
            "prompt": prompt,
            "rounds": []
        }

        current_prompt = prompt

        for round_num in range(rounds):
            # Get responses for this round
            round_responses = {}

            for provider_name, provider in self.providers.items():
                # Build prompt with debate history
                debate_prompt = current_prompt

                if round_num > 0:
                    # Include previous round's responses
                    prev_round = debate_history["rounds"][-1]
                    context = "\n\n".join([
                        f"[{name}'s previous response]: {resp}"
                        for name, resp in prev_round["responses"].items()
                        if name != provider_name
                    ])

                    debate_prompt = (
                        f"Original prompt: {prompt}\n\n"
                        f"Other agents' responses:\n{context}\n\n"
                        f"Please {'refine your position' if round_num > 0 else 'provide your response'}, "
                        f"considering the above perspectives."
                    )

                response = await provider.ask(debate_prompt)
                round_responses[provider_name] = response

            debate_history["rounds"].append({
                "round": round_num + 1,
                "responses": round_responses
            })

        return debate_history

    async def coordinate_specialist(
        self,
        prompt: str,
        roles: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Assign specialist roles to each provider.

        Each provider is given a specific role or perspective to approach
        the prompt from, enabling diverse expert viewpoints.

        Args:
            prompt: User prompt
            roles: Dictionary mapping provider names to role descriptions

        Returns:
            Dictionary of provider responses
        """
        responses = {}

        for provider_name, provider in self.providers.items():
            role = roles.get(provider_name, "general assistant")

            role_prompt = (
                f"You are acting as a {role}. "
                f"Approach the following from that specific perspective:\n\n"
                f"{prompt}"
            )

            response = await provider.ask(role_prompt)
            responses[provider_name] = response

        return responses

    def _build_consensus_prompt(
        self,
        original_prompt: str,
        responses: Dict[str, str]
    ) -> str:
        """
        Build a prompt for generating consensus from multiple responses.

        Args:
            original_prompt: Original user prompt
            responses: Dictionary of provider responses

        Returns:
            Consensus generation prompt
        """
        responses_text = "\n\n".join([
            f"Response from {name}:\n{response}"
            for name, response in responses.items()
        ])

        return (
            f"Original question: {original_prompt}\n\n"
            f"Multiple AI agents provided the following responses:\n\n"
            f"{responses_text}\n\n"
            f"Please provide a synthesized consensus that:\n"
            f"1. Identifies common themes and agreements\n"
            f"2. Notes significant disagreements or different perspectives\n"
            f"3. Provides a balanced, comprehensive answer\n"
            f"4. Highlights which aspects have strong agreement vs. debate"
        )


class CoordinationStrategy:
    """Enumeration of coordination strategies."""

    PARALLEL = "parallel"  # Independent parallel execution (default)
    SEQUENTIAL = "sequential"  # Sequential with context sharing
    CONSENSUS = "consensus"  # Parallel + consensus synthesis
    DEBATE = "debate"  # Multi-round debate format
    SPECIALIST = "specialist"  # Role-based specialization
