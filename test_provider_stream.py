#!/usr/bin/env python3
"""Test streaming with AiTril provider."""

import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, '.')

from aitril.providers import OpenAIProvider

async def test_provider_stream():
    """Test streaming with OpenAI provider."""
    config = {
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "model": "gpt-5.1"
    }

    provider = OpenAIProvider(config)
    print(f"Testing streaming with model: {provider.model}")
    print("Sending prompt: 'Count to 5'")
    print("-" * 60)

    try:
        async for chunk in provider.ask_stream("Count to 5"):
            print(chunk, end='', flush=True)

        print("\n" + "-" * 60)
        print("Streaming test completed successfully!")
        return True
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_provider_stream())
    sys.exit(0 if success else 1)
