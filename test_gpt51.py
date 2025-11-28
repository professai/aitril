#!/usr/bin/env python3
"""Quick test script for gpt-5.1 responses API."""

import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, '.')

from aitril.providers import OpenAIProvider

async def test_gpt51():
    """Test the gpt-5.1 model with AiTril provider."""
    config = {
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "model": "gpt-5.1"
    }

    provider = OpenAIProvider(config)
    print(f"Testing OpenAI with model: {provider.model}")
    print("Sending prompt: 'What is 2+2?'")
    print("-" * 60)

    try:
        response = await provider.ask("What is 2+2?")
        print(f"Response: {response}")
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gpt51())
    sys.exit(0 if success else 1)
