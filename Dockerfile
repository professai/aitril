# AiTril Development/Test Dockerfile
#
# TODO: Update to python:3.14-slim when official image is available
# Currently using 3.13 as 3.14 may not have stable official images yet

FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . /app

# Upgrade pip and install the package in editable mode
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .

# Default command: show help
CMD ["aitril", "--help"]

# Alternative commands you can run:
# docker run -it --rm aitril-dev bash
# docker run -it --rm -e OPENAI_API_KEY="..." aitril-dev aitril ask --provider gpt "Hello"
# docker run -it --rm -e OPENAI_API_KEY="..." -e ANTHROPIC_API_KEY="..." aitril-dev aitril tri "Hello"
