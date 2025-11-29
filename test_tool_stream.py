#!/usr/bin/env python3
"""
Test tool execution with streaming in v0.0.32
Shows real-time tool execution
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import AiTril components
from aitril.providers import OpenAIProvider

async def test_tool_streaming():
    """Test that OpenAI provider shows tool execution in streaming"""

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    print("Testing tool execution with streaming...")
    print("="*70)

    # Create provider
    config = {
        "api_key": api_key,
        "model": "gpt-4o",
        "enable_tools": True
    }
    provider = OpenAIProvider(config)

    # Test query that REQUIRES a tool (checking a URL)
    query = "Use curl to check if https://pypi.org/project/aitril/ is accessible. What status code does it return?"

    print(f"\nQuery: {query}\n")
    print("="*70)

    # Stream response
    async for chunk in provider.ask_stream(query):
        print(chunk, end="", flush=True)

    print("\n" + "="*70)
    print("✓ Streaming test completed")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_tool_streaming())
    exit(0 if result else 1)
