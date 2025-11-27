"""
Multi-agent coordination for AiTril.

Enables LLM providers to coordinate, share context, and build on each other's
responses for more comprehensive and collaborative outputs.
"""

import asyncio
from typing import Dict, List, Optional, Any

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

    async def coordinate_code_build(
        self,
        task_description: str,
        tech_stack: Optional[Dict[str, Any]] = None,
        project_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Coordinate agents to plan and build code collaboratively.

        Phase 1: Consensus on architecture and approach
        Phase 2: Implementation (sequential build)
        Phase 3: Code review and validation

        Args:
            task_description: Description of what to build
            tech_stack: Tech stack preferences (language, framework, tools, etc.)
            project_context: Project context (root dir, type, existing files, etc.)

        Returns:
            Dictionary with plan, code, and review results
        """
        # Phase 1: Plan with consensus
        planning_prompt = self._build_planning_prompt(task_description, tech_stack, project_context)

        planning_results = await self.coordinate_consensus(planning_prompt)

        # Phase 2: Implementation (sequential build)
        implementation_prompt = self._build_implementation_prompt(
            task_description,
            planning_results["consensus"],
            tech_stack,
            project_context
        )

        implementation_results = await self.coordinate_sequential(implementation_prompt)

        # Phase 3: Code review
        review_prompt = self._build_review_prompt(
            task_description,
            implementation_results,
            tech_stack
        )

        review_results = await self.coordinate_consensus(review_prompt)

        return {
            "task": task_description,
            "tech_stack": tech_stack,
            "planning": planning_results,
            "implementation": implementation_results,
            "review": review_results,
            "status": "completed"
        }

    async def coordinate_code_review(
        self,
        code_content: str,
        file_path: Optional[str] = None,
        tech_stack: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Coordinate multi-agent code review.

        Args:
            code_content: Code to review
            file_path: Optional path to file being reviewed
            tech_stack: Tech stack context for style guidelines

        Returns:
            Dictionary with individual reviews and consensus
        """
        review_prompt = (
            f"Please review the following code:\n\n"
            f"{'File: ' + file_path if file_path else ''}\n"
            f"```\n{code_content}\n```\n\n"
            f"Please provide a code review covering:\n"
            f"1. Code quality and best practices\n"
            f"2. Potential bugs or issues\n"
            f"3. Performance considerations\n"
            f"4. Security concerns\n"
            f"5. Suggested improvements\n"
        )

        if tech_stack:
            stack_info = ", ".join([f"{k}: {v}" for k, v in tech_stack.items()])
            review_prompt += f"\nTech stack context: {stack_info}"

        return await self.coordinate_consensus(review_prompt)

    def _build_planning_prompt(
        self,
        task: str,
        tech_stack: Optional[Dict[str, Any]],
        project_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for code planning phase."""
        prompt = (
            f"Task: {task}\n\n"
            f"Please provide a detailed implementation plan that includes:\n"
            f"1. Overall architecture and approach\n"
            f"2. File structure and organization\n"
            f"3. Key components and their responsibilities\n"
            f"4. Dependencies and tools needed\n"
            f"5. Implementation steps in order\n"
            f"6. Testing strategy\n"
        )

        if tech_stack:
            stack_info = "\n".join([f"  - {k}: {v}" for k, v in tech_stack.items()])
            prompt += f"\nTech stack preferences:\n{stack_info}\n"

        if project_context:
            context_info = "\n".join([f"  - {k}: {v}" for k, v in project_context.items()])
            prompt += f"\nProject context:\n{context_info}\n"

        prompt += "\nProvide a clear, actionable plan that can be implemented step by step."

        return prompt

    def _build_implementation_prompt(
        self,
        task: str,
        plan: str,
        tech_stack: Optional[Dict[str, Any]],
        project_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for code implementation phase."""
        prompt = (
            f"Task: {task}\n\n"
            f"Implementation Plan:\n{plan}\n\n"
            f"Please implement the code following the plan above. Provide:\n"
            f"1. Complete, working code\n"
            f"2. Clear comments explaining key sections\n"
            f"3. File paths where code should be placed\n"
            f"4. Any configuration or setup needed\n"
        )

        if tech_stack:
            stack_info = "\n".join([f"  - {k}: {v}" for k, v in tech_stack.items()])
            prompt += f"\nTech stack:\n{stack_info}\n"

        return prompt

    def _build_review_prompt(
        self,
        task: str,
        implementation: Dict[str, str],
        tech_stack: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for code review phase."""
        impl_summary = "\n\n".join([
            f"From {provider}:\n{code[:500]}..." if len(code) > 500 else f"From {provider}:\n{code}"
            for provider, code in implementation.items()
        ])

        prompt = (
            f"Task: {task}\n\n"
            f"Implementation:\n{impl_summary}\n\n"
            f"Please review the implementation and provide:\n"
            f"1. Assessment of correctness and completeness\n"
            f"2. Code quality evaluation\n"
            f"3. Potential issues or improvements\n"
            f"4. Testing recommendations\n"
            f"5. Final verdict: Ready to deploy / Needs revisions\n"
        )

        if tech_stack:
            stack_info = "\n".join([f"  - {k}: {v}" for k, v in tech_stack.items()])
            prompt += f"\nTech stack:\n{stack_info}\n"

        return prompt

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
    CODE_BUILD = "code_build"  # Plan -> Implement -> Review cycle
    CODE_REVIEW = "code_review"  # Multi-agent code review
