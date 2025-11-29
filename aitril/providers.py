"""
Provider abstraction and implementations for AiTril.

Supports OpenAI (GPT), Anthropic (Claude), Google Gemini, Ollama, and Llama.cpp providers.
Includes function calling / tool use support for all providers.
"""

import asyncio
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator

import openai
import anthropic
import google.generativeai as genai
import httpx

from .tools import get_tool_registry, ToolRegistry


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
        self.tool_registry: ToolRegistry = get_tool_registry()
        self.enable_tools: bool = config.get("enable_tools", True)

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
    """OpenAI (GPT) provider implementation with tool calling support."""

    def _get_env_var_name(self) -> str:
        return "OPENAI_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "OPENAI_MODEL"

    def _default_model(self) -> str:
        return "gpt-4o"  # gpt-4o supports function calling better than gpt-5.1

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to OpenAI and return the response.
        Handles tool calls automatically.

        Args:
            prompt: The prompt to send.

        Returns:
            GPT's response as a string.
        """
        client = openai.AsyncOpenAI(api_key=self.api_key)

        messages = [{"role": "user", "content": prompt}]
        tools = self.tool_registry.get_openai_tools() if self.enable_tools else None

        # Tool calling loop
        max_iterations = 5  # Prevent infinite loops
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                max_completion_tokens=2000
            )

            message = response.choices[0].message

            # If no tool calls, return the response
            if not message.tool_calls:
                return message.content or ""

            # Add assistant's response to messages
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            # Execute each tool call
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # Execute tool
                result = await self.tool_registry.execute_tool(function_name, **function_args)

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        # If we hit max iterations, return last message
        return message.content or ""

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to OpenAI and yield response chunks in real-time.
        Handles tool calls by yielding tool execution info and continuing stream.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from OpenAI, plus tool execution info.
        """
        client = openai.AsyncOpenAI(api_key=self.api_key)

        messages = [{"role": "user", "content": prompt}]
        tools = self.tool_registry.get_openai_tools() if self.enable_tools else None

        # Tool calling loop with streaming
        max_iterations = 5
        for iteration in range(max_iterations):
            tool_calls_accumulator = []
            current_tool_call = {"id": "", "function": {"name": "", "arguments": ""}}
            content_parts = []

            # Use max_completion_tokens for newer models (gpt-4-turbo, gpt-4o, etc.)
            # Use max_tokens for older models (fallback)
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                max_completion_tokens=2000,
                stream=True
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Stream text content
                if delta.content:
                    content_parts.append(delta.content)
                    yield delta.content

                # Accumulate tool calls
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if tc_delta.id:
                            # New tool call
                            if current_tool_call["id"]:
                                tool_calls_accumulator.append(current_tool_call.copy())
                            current_tool_call = {
                                "id": tc_delta.id,
                                "function": {"name": "", "arguments": ""}
                            }

                        if tc_delta.function:
                            if tc_delta.function.name:
                                current_tool_call["function"]["name"] = tc_delta.function.name
                            if tc_delta.function.arguments:
                                current_tool_call["function"]["arguments"] += tc_delta.function.arguments

            # Add final tool call if exists
            if current_tool_call["id"]:
                tool_calls_accumulator.append(current_tool_call)

            # If no tool calls, we're done
            if not tool_calls_accumulator:
                break

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": "".join(content_parts) if content_parts else None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"]
                        }
                    }
                    for tc in tool_calls_accumulator
                ]
            })

            # Execute tool calls and yield results
            for tool_call in tool_calls_accumulator:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])

                # Yield tool execution indicator
                yield f"\n\n🔧 **Executing tool:** `{function_name}`\n"
                yield f"**Arguments:** {json.dumps(function_args, indent=2)}\n"

                # Execute tool
                result = await self.tool_registry.execute_tool(function_name, **function_args)

                # Yield tool result
                yield f"**Result:**\n```\n{result}\n```\n\n"

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                })

            # If this was the last iteration, break
            if iteration == max_iterations - 1:
                yield "\n(Maximum tool iterations reached)\n"
                break


class AnthropicProvider(Provider):
    """Anthropic (Claude) provider implementation with tool use support."""

    def _get_env_var_name(self) -> str:
        return "ANTHROPIC_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "ANTHROPIC_MODEL"

    def _default_model(self) -> str:
        return "claude-opus-4-5-20251124"  # Latest Opus 4.5

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Anthropic Claude and return the response.
        Handles tool use automatically.

        Args:
            prompt: The prompt to send.

        Returns:
            Claude's response as a string.
        """
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        messages = [{"role": "user", "content": prompt}]
        tools = self.tool_registry.get_anthropic_tools() if self.enable_tools else None

        # Tool use loop
        max_iterations = 5
        for _ in range(max_iterations):
            response = await client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=messages,
                tools=tools if tools else anthropic.NOT_GIVEN
            )

            # Extract text content
            text_content = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_content.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # If no tool uses, return the text
            if not tool_uses:
                return "".join(text_content)

            # Add assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Execute tools and add results
            tool_results = []
            for tool_use in tool_uses:
                result = await self.tool_registry.execute_tool(
                    tool_use.name,
                    **tool_use.input
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Add tool results as user message
            messages.append({
                "role": "user",
                "content": tool_results
            })

        # Return last text if max iterations reached
        return "".join(text_content)

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Anthropic Claude and yield response chunks in real-time.
        Handles tool use by yielding tool execution info and continuing stream.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Claude, plus tool execution info.
        """
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        messages = [{"role": "user", "content": prompt}]
        tools = self.tool_registry.get_anthropic_tools() if self.enable_tools else None

        # Tool use loop with streaming
        max_iterations = 5
        for iteration in range(max_iterations):
            text_content = []
            tool_uses = []
            current_tool_use = None
            current_tool_input = ""

            async with client.messages.stream(
                model=self.model,
                max_tokens=2000,
                messages=messages,
                tools=tools if tools else anthropic.NOT_GIVEN
            ) as stream:
                async for event in stream:
                    # Handle text content
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block") and event.content_block.type == "text":
                            pass  # Text block started
                        elif hasattr(event, "content_block") and event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input": {}
                            }
                            current_tool_input = ""

                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta"):
                            if event.delta.type == "text_delta":
                                text = event.delta.text
                                text_content.append(text)
                                yield text
                            elif event.delta.type == "input_json_delta":
                                current_tool_input += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_use:
                            # Parse accumulated JSON input
                            try:
                                current_tool_use["input"] = json.loads(current_tool_input)
                            except json.JSONDecodeError:
                                current_tool_use["input"] = {}
                            tool_uses.append(current_tool_use)
                            current_tool_use = None
                            current_tool_input = ""

            # If no tool uses, we're done
            if not tool_uses:
                break

            # Build content list with text and tool uses
            content_blocks = []
            if text_content:
                content_blocks.append({"type": "text", "text": "".join(text_content)})
            for tu in tool_uses:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tu["id"],
                    "name": tu["name"],
                    "input": tu["input"]
                })

            # Add assistant message
            messages.append({
                "role": "assistant",
                "content": content_blocks
            })

            # Execute tools and yield results
            tool_results = []
            for tool_use in tool_uses:
                # Yield tool execution indicator
                yield f"\n\n🔧 **Executing tool:** `{tool_use['name']}`\n"
                yield f"**Arguments:** {json.dumps(tool_use['input'], indent=2)}\n"

                # Execute tool
                result = await self.tool_registry.execute_tool(
                    tool_use["name"],
                    **tool_use["input"]
                )

                # Yield tool result
                yield f"**Result:**\n```\n{result}\n```\n\n"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "content": result
                })

            # Add tool results as user message
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # If this was the last iteration, break
            if iteration == max_iterations - 1:
                yield "\n(Maximum tool iterations reached)\n"
                break


class GeminiProvider(Provider):
    """Google Gemini provider implementation with function calling support."""

    def _get_env_var_name(self) -> str:
        return "GOOGLE_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "GEMINI_MODEL"

    def _default_model(self) -> str:
        return "gemini-2.0-flash-exp"  # Latest with function calling

    def _convert_tools_to_gemini_format(self) -> List[Any]:
        """Convert our tool definitions to Gemini's function declaration format."""
        tools = self.tool_registry.get_openai_tools()

        gemini_tools = []
        for tool in tools:
            func_def = tool["function"]
            gemini_tools.append(
                genai.protos.FunctionDeclaration(
                    name=func_def["name"],
                    description=func_def["description"],
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            k: genai.protos.Schema(
                                type=genai.protos.Type.STRING if v.get("type") == "string" else genai.protos.Type.OBJECT,
                                description=v.get("description", "")
                            )
                            for k, v in func_def["parameters"]["properties"].items()
                        },
                        required=func_def["parameters"].get("required", [])
                    )
                )
            )

        return [genai.protos.Tool(function_declarations=gemini_tools)] if gemini_tools else []

    async def ask(self, prompt: str) -> str:
        """
        Send a prompt to Google Gemini and return the response.
        Handles function calling automatically.

        Args:
            prompt: The prompt to send.

        Returns:
            Gemini's response as a string.
        """
        genai.configure(api_key=self.api_key)
        loop = asyncio.get_running_loop()

        def _sync_call():
            # Create model with tools if enabled
            if self.enable_tools:
                tools = self._convert_tools_to_gemini_format()
                model = genai.GenerativeModel(self.model, tools=tools)
            else:
                model = genai.GenerativeModel(self.model)

            chat = model.start_chat()
            current_prompt = prompt

            # Function calling loop
            max_iterations = 5
            for _ in range(max_iterations):
                response = chat.send_message(current_prompt)

                # Check if there are function calls
                function_calls = []
                text_parts = []

                for part in response.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                    elif hasattr(part, 'function_call'):
                        function_calls.append(part.function_call)

                # If no function calls, return the text
                if not function_calls:
                    return "".join(text_parts)

                # Execute function calls
                function_responses = []
                for func_call in function_calls:
                    # Convert function call args to dict
                    args = dict(func_call.args)

                    # Execute the tool (sync version since we're in executor)
                    result = asyncio.run(
                        self.tool_registry.execute_tool(func_call.name, **args)
                    )

                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=func_call.name,
                                response={"result": result}
                            )
                        )
                    )

                # Send function responses back (this becomes the new prompt for next iteration)
                current_prompt = genai.protos.Content(parts=function_responses)

            # Return last text if max iterations reached
            return "".join(text_parts)

        result = await loop.run_in_executor(None, _sync_call)
        return result or ""

    async def ask_stream(self, prompt: str):
        """
        Send a prompt to Google Gemini and yield response chunks in real-time.
        Handles function calling by yielding execution info and continuing stream.

        Args:
            prompt: The prompt to send.

        Yields:
            Text chunks as they arrive from Gemini, plus tool execution info.
        """
        genai.configure(api_key=self.api_key)
        loop = asyncio.get_running_loop()

        def _sync_stream_with_tools(initial_prompt):
            # Create model with tools if enabled
            if self.enable_tools:
                tools = self._convert_tools_to_gemini_format()
                model = genai.GenerativeModel(self.model, tools=tools)
            else:
                model = genai.GenerativeModel(self.model)

            chat = model.start_chat()
            current_prompt = initial_prompt

            # Function calling loop with streaming
            max_iterations = 5
            for iteration in range(max_iterations):
                response = chat.send_message(current_prompt, stream=True)

                function_calls = []
                text_parts = []

                # Stream the response
                for chunk in response:
                    for part in chunk.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                            yield ("text", part.text)
                        elif hasattr(part, 'function_call'):
                            function_calls.append(part.function_call)

                # If no function calls, we're done
                if not function_calls:
                    break

                # Execute function calls
                function_responses = []
                for func_call in function_calls:
                    # Convert function call args to dict
                    args = dict(func_call.args)

                    # Yield tool execution info
                    yield ("tool_start", f"\n\n🔧 **Executing tool:** `{func_call.name}`\n")
                    yield ("tool_args", f"**Arguments:** {json.dumps(args, indent=2)}\n")

                    # Execute the tool
                    result = asyncio.run(
                        self.tool_registry.execute_tool(func_call.name, **args)
                    )

                    # Yield tool result
                    yield ("tool_result", f"**Result:**\n```\n{result}\n```\n\n")

                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=func_call.name,
                                response={"result": result}
                            )
                        )
                    )

                # Send function responses back for next iteration
                current_prompt = genai.protos.Content(parts=function_responses)

                # Check if we hit max iterations
                if iteration == max_iterations - 1:
                    yield ("text", "\n(Maximum tool iterations reached)\n")
                    break

        # Run the streaming generator in executor
        for item in await loop.run_in_executor(None, lambda: list(_sync_stream_with_tools(prompt))):
            # item is a tuple of (type, content)
            if item[0] == "text":
                yield item[1]
            else:
                # Tool execution info - yield as-is
                yield item[1]


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
            # Check both OLLAMA_API_URL and OLLAMA_BASE_URL for compatibility
            base_url = os.environ.get("OLLAMA_API_URL") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
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


# ============================================================================
# SPECIALIZED PROVIDERS (v0.0.33+)
# ============================================================================
# These providers use code/agent-specialized tools instead of general APIs


class ClaudeCodeProvider(Provider):
    """
    Claude Code CLI Provider - shells out to actual claude binary.

    Executes: claude -p "prompt" --model claude-opus-4-5-20251101

    This uses the ACTUAL Claude Code CLI tool instead of general Anthropic API,
    providing proper code/agent context and capabilities.
    """

    def _get_env_var_name(self) -> str:
        return "ANTHROPIC_API_KEY"

    def _get_model_env_var_name(self) -> str:
        return "CLAUDE_CODE_MODEL"

    def _default_model(self) -> str:
        return "claude-opus-4-5-20251101"

    def _get_claude_cli_path(self) -> str:
        """Get path to claude CLI binary."""
        # Try environment variable first
        cli_path = os.environ.get("CLAUDE_CODE_CLI_PATH")
        if cli_path:
            return cli_path

        # Try to find in PATH
        import shutil
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path

        # Default fallback
        return "/usr/local/bin/claude"

    async def ask(self, prompt: str) -> str:
        """
        Execute claude CLI and return response.

        Args:
            prompt: User prompt

        Returns:
            Claude Code response
        """
        claude_cli = self._get_claude_cli_path()

        # Build command
        cmd = [
            claude_cli,
            "-p", prompt,
            "--model", self.model
        ]

        try:
            # Execute claude CLI
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "ANTHROPIC_API_KEY": self.api_key}
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8')
                raise RuntimeError(f"Claude Code CLI error: {error_msg}")

            return stdout.decode('utf-8').strip()

        except FileNotFoundError:
            raise RuntimeError(
                f"Claude Code CLI not found at {claude_cli}. "
                "Install Claude Code or set CLAUDE_CODE_CLI_PATH environment variable."
            )

    async def ask_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Execute claude CLI with streaming output.

        Args:
            prompt: User prompt

        Yields:
            Text chunks from Claude Code
        """
        claude_cli = self._get_claude_cli_path()

        # Build command (streaming mode)
        cmd = [
            claude_cli,
            "-p", prompt,
            "--model", self.model,
            "--stream"  # Enable streaming if supported
        ]

        try:
            # Execute claude CLI with streaming
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "ANTHROPIC_API_KEY": self.api_key}
            )

            # Stream output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8')

            await process.wait()

            if process.returncode != 0:
                stderr_output = await process.stderr.read()
                error_msg = stderr_output.decode('utf-8')
                raise RuntimeError(f"Claude Code CLI error: {error_msg}")

        except FileNotFoundError:
            raise RuntimeError(
                f"Claude Code CLI not found at {claude_cli}. "
                "Install Claude Code or set CLAUDE_CODE_CLI_PATH environment variable."
            )


class OpenAICodexProvider(OpenAIProvider):
    """
    OpenAI Codex Provider - uses code-specialized models.

    Extends OpenAIProvider but uses Codex models optimized for code tasks
    instead of general chat models.
    """

    def _get_model_env_var_name(self) -> str:
        return "OPENAI_CODEX_MODEL"

    def _default_model(self) -> str:
        """Use code-specialized model instead of general chat."""
        # Priority: OPENAI_CODEX_MODEL > OPENAI_MODEL > hardcoded fallback
        # This ensures we never downgrade from .env model
        specialized = os.environ.get("OPENAI_CODEX_MODEL")
        if specialized:
            return specialized

        # Fall back to general OPENAI_MODEL from .env
        general = os.environ.get("OPENAI_MODEL")
        if general:
            return general

        # Only if both missing, use hardcoded fallback
        return "gpt-4-turbo"

    async def ask(self, prompt: str) -> str:
        """
        Query Codex with code-optimized prompting.

        Args:
            prompt: User prompt

        Returns:
            Codex response
        """
        # Enhance prompt for code context
        code_prompt = f"[CODE/AGENT TASK] {prompt}"
        return await super().ask(code_prompt)

    async def ask_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Query Codex with streaming and code-optimized prompting.

        Args:
            prompt: User prompt

        Yields:
            Text chunks from Codex
        """
        # Enhance prompt for code context
        code_prompt = f"[CODE/AGENT TASK] {prompt}"
        async for chunk in super().ask_stream(code_prompt):
            yield chunk


class GeminiADKProvider(GeminiProvider):
    """
    Gemini ADK Provider - uses Agent Development Kit capabilities.

    Extends GeminiProvider but optimized for agent/code tasks using ADK.
    For now, uses API with agent-optimized prompting. Full ADK integration TBD.
    """

    def _get_model_env_var_name(self) -> str:
        return "GEMINI_ADK_MODEL"

    def _default_model(self) -> str:
        """Use agent-optimized Gemini model."""
        # Priority: GEMINI_ADK_MODEL > GEMINI_MODEL > hardcoded fallback
        # This ensures we never downgrade from .env model
        specialized = os.environ.get("GEMINI_ADK_MODEL")
        if specialized:
            return specialized

        # Fall back to general GEMINI_MODEL from .env
        general = os.environ.get("GEMINI_MODEL")
        if general:
            return general

        # Only if both missing, use hardcoded fallback
        return "gemini-2.0-flash-exp"

    async def ask(self, prompt: str) -> str:
        """
        Query Gemini ADK with agent-optimized prompting.

        Args:
            prompt: User prompt

        Returns:
            Gemini ADK response
        """
        # Enhance prompt for agent/code context
        agent_prompt = f"[AGENT/CODE TASK] {prompt}"
        return await super().ask(agent_prompt)

    async def ask_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Query Gemini ADK with streaming and agent-optimized prompting.

        Args:
            prompt: User prompt

        Yields:
            Text chunks from Gemini ADK
        """
        # Enhance prompt for agent/code context
        agent_prompt = f"[AGENT/CODE TASK] {prompt}"
        async for chunk in super().ask_stream(agent_prompt):
            yield chunk


# ============================================================================
# PROVIDER FACTORY WITH SPECIALIZED/FALLBACK LOGIC
# ============================================================================


def create_provider(name: str, config: dict) -> Provider:
    """
    Factory function to create a provider instance with specialized/fallback logic.

    v0.0.33+ supports specialized code/agent providers:
    - 'claudecode': Claude Code CLI (specialized) → AnthropicProvider (fallback)
    - 'openaicodex': OpenAI Codex (specialized) → OpenAIProvider (fallback)
    - 'geminiadk': Gemini ADK (specialized) → GeminiProvider (fallback)

    Environment variable USE_SPECIALIZED_PROVIDERS controls behavior:
    - "true" (default): Use specialized providers
    - "false": Use general API providers only

    Args:
        name: Provider name
        config: Provider configuration dictionary

    Returns:
        Provider instance

    Raises:
        ValueError: If provider name is unknown
    """
    # Check if specialized providers are enabled
    use_specialized = os.environ.get("USE_SPECIALIZED_PROVIDERS", "true").lower() == "true"

    # Specialized providers (v0.0.33+)
    specialized_providers = {
        "claudecode": ClaudeCodeProvider,
        "openaicodex": OpenAICodexProvider,
        "geminiadk": GeminiADKProvider,
    }

    # General API providers (v0.0.32 compatibility)
    general_providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
        "llamacpp": LlamaCppProvider,
    }

    # Mapping: specialized → general (for fallback)
    fallback_map = {
        "claudecode": "anthropic",
        "openaicodex": "openai",
        "geminiadk": "gemini",
    }

    # Mapping: general → specialized (when USE_SPECIALIZED_PROVIDERS=true)
    upgrade_map = {
        "anthropic": "claudecode",
        "openai": "openaicodex",
        "gemini": "geminiadk",
    }

    name_lower = name.lower()

    # UPGRADE: If using general name but specialized providers are enabled,
    # try to upgrade to specialized provider first
    if use_specialized and name_lower in upgrade_map:
        specialized_name = upgrade_map[name_lower]
        try:
            provider_class = specialized_providers[specialized_name]
            instance = provider_class(config)
            print(f"✓ Using specialized provider: {provider_class.__name__}")
            return instance
        except (RuntimeError, FileNotFoundError) as e:
            # Fall through to general provider
            print(f"⚠ Specialized provider unavailable ({e.__class__.__name__}), using general API")

    # Try specialized provider first (if enabled)
    if use_specialized and name_lower in specialized_providers:
        try:
            provider_class = specialized_providers[name_lower]
            return provider_class(config)
        except (RuntimeError, FileNotFoundError) as e:
            # Fall back to general provider
            print(f"Warning: Specialized provider '{name}' failed ({e}), falling back to general API")
            fallback_name = fallback_map.get(name_lower)
            if fallback_name:
                provider_class = general_providers[fallback_name]
                return provider_class(config)

    # Try general provider
    if name_lower in general_providers:
        provider_class = general_providers[name_lower]
        return provider_class(config)

    # Also support specialized provider names when USE_SPECIALIZED_PROVIDERS=false
    # In this case, map directly to general provider
    if not use_specialized and name_lower in fallback_map:
        fallback_name = fallback_map[name_lower]
        provider_class = general_providers[fallback_name]
        return provider_class(config)

    # Unknown provider
    all_providers = list(specialized_providers.keys()) + list(general_providers.keys())
    raise ValueError(f"Unknown provider: {name}. Available: {', '.join(sorted(set(all_providers)))}")

