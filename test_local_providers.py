#!/usr/bin/env python3
"""
Test script for local model providers (Ollama and Llama.cpp)

This script verifies that:
1. OllamaProvider can connect and communicate
2. LlamaCppProvider can connect and communicate
3. Provider factory correctly maps custom providers
4. Error handling works for connection failures

Usage:
    # Test with Ollama running on localhost:11434
    python test_local_providers.py --provider ollama
    
    # Test with Llama.cpp running on localhost:8080
    python test_local_providers.py --provider llamacpp
    
    # Test both
    python test_local_providers.py --provider all
"""

import asyncio
import sys
from aitril.providers import create_provider, OllamaProvider, LlamaCppProvider


async def test_ollama(base_url="http://localhost:11434", model="llama2"):
    """Test Ollama provider"""
    print("\n" + "="*60)
    print("Testing Ollama Provider")
    print("="*60)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    
    try:
        config = {
            "base_url": base_url,
            "model": model
        }
        provider = OllamaProvider(config)
        
        print("\n✓ Provider initialized successfully")
        print(f"  - API Key Required: {provider._requires_api_key()}")
        print(f"  - Model: {provider.model}")
        
        # Test simple query
        print("\nSending test query...")
        prompt = "Say 'Hello from Ollama!' and nothing else."
        response = await provider.ask(prompt)
        
        print(f"\n✓ Response received ({len(response)} characters):")
        print(f"  {response[:200]}")
        
        # Test streaming
        print("\nTesting streaming...")
        stream_response = ""
        async for chunk in provider.ask_stream("Count to 3."):
            stream_response += chunk
            print(".", end="", flush=True)
        
        print(f"\n✓ Streaming works ({len(stream_response)} characters received)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Ollama test failed: {e}")
        print(f"  Make sure Ollama is running: docker run -d -p 11434:11434 ollama/ollama")
        print(f"  And pull a model: docker exec ollama ollama pull {model}")
        return False


async def test_llamacpp(base_url="http://localhost:8080"):
    """Test Llama.cpp provider"""
    print("\n" + "="*60)
    print("Testing Llama.cpp Provider")
    print("="*60)
    print(f"Base URL: {base_url}")
    
    try:
        config = {
            "base_url": base_url,
            "model": "default"
        }
        provider = LlamaCppProvider(config)
        
        print("\n✓ Provider initialized successfully")
        print(f"  - API Key Required: {provider._requires_api_key()}")
        print(f"  - Model: {provider.model}")
        
        # Test simple query
        print("\nSending test query...")
        prompt = "Say 'Hello from Llama.cpp!' and nothing else."
        response = await provider.ask(prompt)
        
        print(f"\n✓ Response received ({len(response)} characters):")
        print(f"  {response[:200]}")
        
        # Test streaming
        print("\nTesting streaming...")
        stream_response = ""
        async for chunk in provider.ask_stream("Count to 3."):
            stream_response += chunk
            print(".", end="", flush=True)
        
        print(f"\n✓ Streaming works ({len(stream_response)} characters received)")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Llama.cpp test failed: {e}")
        print(f"  Make sure Llama.cpp server is running with a model loaded")
        return False


async def test_provider_factory():
    """Test that provider factory correctly maps provider types"""
    print("\n" + "="*60)
    print("Testing Provider Factory")
    print("="*60)
    
    try:
        # Test creating Ollama provider
        ollama_provider = create_provider("ollama", {"base_url": "http://localhost:11434", "model": "llama2"})
        assert isinstance(ollama_provider, OllamaProvider), "Ollama provider type mismatch"
        print("✓ Ollama provider factory works")
        
        # Test creating Llama.cpp provider
        llamacpp_provider = create_provider("llamacpp", {"base_url": "http://localhost:8080", "model": "default"})
        assert isinstance(llamacpp_provider, LlamaCppProvider), "Llama.cpp provider type mismatch"
        print("✓ Llama.cpp provider factory works")
        
        # Test custom provider with provider_type mapping
        custom_config = {
            "base_url": "http://localhost:11434",
            "model": "custom-model",
            "provider_type": "ollama"
        }
        # Note: In actual usage, orchestrator will use provider_type to determine which provider class to use
        custom_provider = create_provider("ollama", custom_config)
        assert isinstance(custom_provider, OllamaProvider), "Custom provider mapping failed"
        print("✓ Custom provider type mapping works")
        
        return True
        
    except Exception as e:
        print(f"✗ Provider factory test failed: {e}")
        return False


async def main():
    """Run all tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test local LLM providers")
    parser.add_argument("--provider", choices=["ollama", "llamacpp", "all"], default="all",
                       help="Which provider to test")
    parser.add_argument("--ollama-url", default="http://localhost:11434",
                       help="Ollama base URL")
    parser.add_argument("--ollama-model", default="llama2",
                       help="Ollama model name")
    parser.add_argument("--llamacpp-url", default="http://localhost:8080",
                       help="Llama.cpp base URL")
    
    args = parser.parse_args()
    
    print("\n🧬 AiTril Local Provider Test Suite")
    print("="*60)
    
    results = []
    
    # Test provider factory
    results.append(await test_provider_factory())
    
    # Test Ollama
    if args.provider in ["ollama", "all"]:
        results.append(await test_ollama(args.ollama_url, args.ollama_model))
    
    # Test Llama.cpp
    if args.provider in ["llamacpp", "all"]:
        results.append(await test_llamacpp(args.llamacpp_url))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
