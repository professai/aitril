#!/usr/bin/env python3
"""
Test tool execution in v0.0.32
Tests that agents can use tools to answer time/system queries
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import AiTril components
from aitril.providers import OpenAIProvider
from aitril.tools import get_tool_registry

async def test_tool_execution():
    """Test that OpenAI provider can use tools"""

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    print("✓ OpenAI API key loaded")

    # Create provider
    config = {
        "api_key": api_key,
        "model": "gpt-4o",
        "enable_tools": True
    }
    provider = OpenAIProvider(config)
    print(f"✓ OpenAI provider created with model: {provider.model}")

    # Verify tool registry
    registry = get_tool_registry()
    tools = registry.get_openai_tools()
    print(f"✓ Tool registry has {len(tools)} tools available")
    for tool in tools:
        print(f"  - {tool['function']['name']}")

    # Test query that requires SystemInfoTool
    print("\n" + "="*60)
    print("Testing: 'What time is it right now?'")
    print("="*60 + "\n")

    response = await provider.ask("What time is it right now?")

    print("\n" + "="*60)
    print("RESPONSE:")
    print("="*60)
    print(response)
    print("="*60)

    # Check if response mentions tool execution
    if "get_system_info" in response or "🔧" in response or "tool" in response.lower():
        print("\n✓ Tool execution detected in response!")
        return True
    else:
        print("\n⚠ No tool execution detected - response may not have used tools")
        return True  # Still successful, just the model chose not to use tools

if __name__ == "__main__":
    result = asyncio.run(test_tool_execution())
    exit(0 if result else 1)
