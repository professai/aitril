#!/bin/bash
# Test AiTril v0.0.33 CLI with specialized providers

echo "🧪 Testing AiTril v0.0.33 CLI - Tri-lam Mode"
echo "=========================================="
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Loaded .env file"
else
    echo "⚠ No .env file found"
fi

echo ""
echo "Environment Check:"
echo "  USE_SPECIALIZED_PROVIDERS: ${USE_SPECIALIZED_PROVIDERS:-true (default)}"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:20}..."
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."
echo ""

# Test query
python3 -m aitril.cli tri "Write a one-line Python function to double a number"
