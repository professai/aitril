"""
AiTril Tool System - v0.0.32

Provides tools for LLM agents to execute commands, access system info,
and interact with the environment.

Architecture:
- Tool base class: Defines interface for all tools
- ToolRegistry: Manages tools and converts to function definitions
- Built-in tools: Shell, System, File, Web operations

Integration:
- Works with OpenAI function calling
- Works with Anthropic tool use
- Works with Gemini function calling
"""

import asyncio
import subprocess
import json
import os
import platform
from datetime import datetime
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import httpx


class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the function definition schema for this tool."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters."""
        pass


class ShellTool(Tool):
    """Execute shell commands safely."""

    def __init__(self):
        super().__init__(
            name="execute_shell_command",
            description="Execute a shell command and return the output. Use this to run system commands like curl, ls, date, etc."
        )
        self.allowed_commands = [
            "curl", "wget", "date", "cal", "uptime", "whoami",
            "pwd", "ls", "cat", "echo", "which", "uname"
        ]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute (e.g., 'curl https://api.example.com', 'date +%Z')"
                        }
                    },
                    "required": ["command"]
                }
            }
        }

    async def execute(self, command: str) -> str:
        """Execute shell command with safety checks."""
        # Extract the base command
        base_cmd = command.split()[0] if command.strip() else ""

        # Safety check: only allow whitelisted commands
        if base_cmd not in self.allowed_commands:
            return f"Error: Command '{base_cmd}' not allowed. Allowed commands: {', '.join(self.allowed_commands)}"

        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)
            except asyncio.TimeoutError:
                process.kill()
                return "Error: Command timed out after 10 seconds"

            if process.returncode == 0:
                output = stdout.decode('utf-8').strip()
                return output if output else "(command executed successfully, no output)"
            else:
                error = stderr.decode('utf-8').strip()
                return f"Error (exit code {process.returncode}): {error}"

        except Exception as e:
            return f"Error executing command: {str(e)}"


class SystemInfoTool(Tool):
    """Get system information like time, timezone, OS, etc."""

    def __init__(self):
        super().__init__(
            name="get_system_info",
            description="Get system information including current time, timezone, operating system, and location data."
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "info_type": {
                            "type": "string",
                            "enum": ["time", "timezone", "os", "all"],
                            "description": "Type of information to retrieve"
                        }
                    },
                    "required": ["info_type"]
                }
            }
        }

    async def execute(self, info_type: str = "all") -> str:
        """Get requested system information."""
        try:
            info = {}

            if info_type in ["time", "all"]:
                now = datetime.now()
                info["current_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                info["iso_format"] = now.isoformat()

            if info_type in ["timezone", "all"]:
                # Try to get timezone info
                try:
                    process = await asyncio.create_subprocess_shell(
                        "date +%Z",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
                    if process.returncode == 0:
                        info["timezone"] = stdout.decode('utf-8').strip()
                except:
                    info["timezone"] = "UTC"

            if info_type in ["os", "all"]:
                info["operating_system"] = platform.system()
                info["os_version"] = platform.release()
                info["machine"] = platform.machine()

            return json.dumps(info, indent=2)

        except Exception as e:
            return f"Error getting system info: {str(e)}"


class FileTool(Tool):
    """Read, write, and list files."""

    def __init__(self):
        super().__init__(
            name="file_operation",
            description="Perform file operations: read, write, or list files in a directory."
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["read", "write", "list"],
                            "description": "The file operation to perform"
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory path"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write (only for 'write' operation)"
                        }
                    },
                    "required": ["operation", "path"]
                }
            }
        }

    async def execute(self, operation: str, path: str, content: Optional[str] = None) -> str:
        """Execute file operation."""
        try:
            if operation == "read":
                if not os.path.exists(path):
                    return f"Error: File '{path}' does not exist"

                with open(path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    # Limit output size
                    if len(file_content) > 5000:
                        return f"{file_content[:5000]}\n... (truncated, {len(file_content)} total characters)"
                    return file_content

            elif operation == "write":
                if content is None:
                    return "Error: Content parameter required for write operation"

                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Successfully wrote {len(content)} characters to {path}"

            elif operation == "list":
                if not os.path.exists(path):
                    return f"Error: Directory '{path}' does not exist"

                if os.path.isfile(path):
                    return f"'{path}' is a file, not a directory"

                entries = os.listdir(path)
                result = []
                for entry in sorted(entries):
                    full_path = os.path.join(path, entry)
                    if os.path.isdir(full_path):
                        result.append(f"📁 {entry}/")
                    else:
                        size = os.path.getsize(full_path)
                        result.append(f"📄 {entry} ({size} bytes)")

                return "\n".join(result) if result else "(empty directory)"

            else:
                return f"Error: Unknown operation '{operation}'"

        except Exception as e:
            return f"Error performing file operation: {str(e)}"


class WebTool(Tool):
    """Make HTTP requests."""

    def __init__(self):
        super().__init__(
            name="http_request",
            description="Make HTTP GET or POST requests to web APIs and services."
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to request"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST"],
                            "description": "HTTP method to use"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Optional HTTP headers as key-value pairs"
                        },
                        "body": {
                            "type": "string",
                            "description": "Request body for POST requests"
                        }
                    },
                    "required": ["url", "method"]
                }
            }
        }

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None
    ) -> str:
        """Execute HTTP request."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(
                        url,
                        headers=headers,
                        content=body if body else ""
                    )
                else:
                    return f"Error: Unsupported method '{method}'"

                # Format response
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text
                }

                # Limit body size in output
                if len(result["body"]) > 2000:
                    result["body"] = result["body"][:2000] + f"\n... (truncated, {len(response.text)} total characters)"

                return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error making HTTP request: {str(e)}"


class ToolRegistry:
    """Registry for managing and accessing tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register all default tools."""
        default_tools = [
            ShellTool(),
            SystemInfoTool(),
            FileTool(),
            WebTool()
        ]

        for tool in default_tools:
            self.register(tool)

    def register(self, tool: Tool):
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get function definition schemas for all tools."""
        return [tool.get_schema() for tool in self.tools.values()]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get tools in OpenAI format."""
        return self.get_all_schemas()

    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic format."""
        tools = []
        for tool in self.tools.values():
            schema = tool.get_schema()
            # Anthropic uses slightly different format
            tools.append({
                "name": schema["function"]["name"],
                "description": schema["function"]["description"],
                "input_schema": schema["function"]["parameters"]
            })
        return tools

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Get tools in Gemini format."""
        # Gemini uses function declarations
        return self.get_all_schemas()

    async def execute_tool(self, name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters."""
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"


# Global tool registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
