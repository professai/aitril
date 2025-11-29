# AiTril Production Dockerfile
# Using official Python 3.14 image
# Installs AiTril v0.0.34 from PyPI with web interface and specialized providers

FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal for production)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version
RUN pip install --upgrade pip setuptools wheel

# Install AiTril from PyPI with web extras
RUN pip install 'aitril[web]==0.0.34'

# Expose web server port
EXPOSE 37142

# Environment variables for specialized providers
ENV USE_SPECIALIZED_PROVIDERS=true

# Default command: start web server
CMD ["aitril", "web", "--host", "0.0.0.0", "--port", "37142"]

# Usage examples:
# Web interface:
# docker run -p 37142:37142 --env-file .env professai/aitril:0.0.33
# Then open http://localhost:37142
#
# CLI usage:
# docker run -it --env-file .env professai/aitril:0.0.33 aitril --help
# docker run -it --env-file .env professai/aitril:0.0.33 aitril tri "your prompt"
#
# With specialized providers (requires API keys in .env):
# OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
# Optionally: OPENAI_CODEX_MODEL, CLAUDE_CODE_CLI_PATH, GEMINI_ADK_MODEL
