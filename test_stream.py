#!/usr/bin/env python3
"""Test streaming with gpt-5.1 responses API."""

import asyncio
import os
import openai

async def test_stream():
    """Test streaming with gpt-5.1."""
    api_key = os.environ.get("OPENAI_API_KEY")
    client = openai.AsyncOpenAI(api_key=api_key)

    print("Testing streaming with gpt-5.1")
    print("-" * 60)

    try:
        stream = await client.responses.create(
            model="gpt-5.1",
            input=[{"role": "user", "content": "Count to 5"}],
            text={"format": {"type": "text"}},
            max_output_tokens=1000,
            stream=True
        )

        print("Stream object:", type(stream))

        chunk_count = 0
        async for chunk in stream:
            chunk_count += 1
            print(f"\n--- Chunk {chunk_count} ---")
            print(f"Type: {type(chunk).__name__}")
            print(f"Event type: {chunk.type if hasattr(chunk, 'type') else 'N/A'}")

            # Show relevant attributes based on event type
            if hasattr(chunk, 'type'):
                if 'delta' in chunk.type:
                    print(f"Delta: {chunk}")
                elif chunk.type == 'response.created':
                    print(f"Response created - status: {chunk.response.status if hasattr(chunk, 'response') else 'N/A'}")
                elif chunk.type == 'response.done':
                    print(f"Response done")
                else:
                    print(f"Full chunk: {chunk}")

            if chunk_count >= 10:  # Just check first 10 chunks
                break

        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_stream())
