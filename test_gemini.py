#!/usr/bin/env python3
"""Test Gemini provider specifically."""

import asyncio
import os
import sys

sys.path.insert(0, '.')

from aitril.providers import GeminiProvider

async def test_gemini():
    """Test Gemini provider."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-3-pro-preview")

    print(f"Testing Gemini with model: {model}")
    print(f"API key: {api_key[:20]}..." if api_key else "No API key")
    print("-" * 60)

    try:
        config = {
            "api_key": api_key,
            "model": model
        }

        provider = GeminiProvider(config)
        response = await provider.ask("What is 2+2? Answer in 5 words.")

        print(f"✓ Success! Response: {response}")
        return True

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gemini())
    sys.exit(0 if success else 1)
