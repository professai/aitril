#!/usr/bin/env python3
"""
Test v0.0.33 specialized providers with fallback logic
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

from aitril.providers import create_provider

async def test_provider_creation():
    """Test that specialized providers are created with proper fallback"""

    print("="*70)
    print("AiTril v0.0.33 - Specialized Provider Tests")
    print("="*70)

    # Test configuration
    config = {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": "claude-opus-4-5-20251101"
    }

    tests = [
        ("claudecode", "ClaudeCodeProvider with fallback to AnthropicProvider"),
        ("openaicodex", "OpenAICodexProvider (or OpenAIProvider fallback)"),
        ("geminiadk", "GeminiADKProvider (or GeminiProvider fallback)"),
        ("anthropic", "AnthropicProvider (general API)"),
        ("openai", "OpenAIProvider (general API)"),
        ("gemini", "GeminiProvider (general API)"),
    ]

    results = []

    for provider_name, description in tests:
        print(f"\n{description}")
        print("-" * 70)

        try:
            # Override config for each provider
            test_config = {**config}

            # Set appropriate API key
            if provider_name in ["openaicodex", "openai"]:
                test_config["api_key"] = os.getenv("OPENAI_API_KEY")
            elif provider_name in ["geminiadk", "gemini"]:
                test_config["api_key"] = os.getenv("GOOGLE_API_KEY")

            provider = create_provider(provider_name, test_config)

            print(f"✓ Created: {provider.__class__.__name__}")
            print(f"  Model: {provider.model}")
            print(f"  Has API key: {'Yes' if provider.api_key else 'No'}")
            print(f"  Tools enabled: {provider.enable_tools}")

            results.append((provider_name, "SUCCESS", provider.__class__.__name__))

        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append((provider_name, "FAILED", str(e)))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for name, status, detail in results:
        symbol = "✓" if status == "SUCCESS" else "✗"
        print(f"{symbol} {name:15s} {status:10s} → {detail}")

    success_count = sum(1 for _, status, _ in results if status == "SUCCESS")
    print(f"\nTotal: {success_count}/{len(results)} providers initialized")

    return success_count == len(results)

async def test_specialized_provider_query():
    """Test actual query with specialized provider"""

    print("\n" + "="*70)
    print("QUERY TEST: OpenAI Codex Provider")
    print("="*70)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ Skipping: No OPENAI_API_KEY found")
        return True

    config = {
        "api_key": api_key,
        "enable_tools": True
    }

    try:
        provider = create_provider("openaicodex", config)
        print(f"✓ Provider: {provider.__class__.__name__}")
        print(f"  Model: {provider.model}")

        # Test query
        query = "Write a Python function to check if a number is prime"
        print(f"\nQuery: {query}")
        print("-" * 70)

        response = await provider.ask(query)

        print(f"Response ({len(response)} chars):")
        print(response[:500] + "..." if len(response) > 500 else response)

        return True

    except Exception as e:
        print(f"✗ Query failed: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 Testing AiTril v0.0.33 Specialized Providers\n")

    # Run tests
    loop = asyncio.get_event_loop()

    # Test 1: Provider creation
    creation_ok = loop.run_until_complete(test_provider_creation())

    # Test 2: Actual query
    query_ok = loop.run_until_complete(test_specialized_provider_query())

    # Final result
    print("\n" + "="*70)
    if creation_ok and query_ok:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*70 + "\n")

    exit(0 if (creation_ok and query_ok) else 1)
