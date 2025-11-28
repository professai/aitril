# AiTril Production Dockerfile
# Using Ubuntu 24.04 LTS with Python 3.14.0
# Installs AiTril v0.0.7 from PyPI

FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies and Python 3.14
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    build-essential \
    curl \
    git \
    ca-certificates \
    libffi-dev \
    libssl-dev \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    python3.14 \
    python3.14-dev \
    python3.14-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.14 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.14 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.14 1

# Upgrade pip to latest version (ignore system packages to avoid conflicts)
RUN python3 -m pip install --upgrade pip setuptools wheel --break-system-packages --ignore-installed

# Install cffi explicitly to avoid conflicts with system packages
RUN pip install cffi --break-system-packages

# Install AiTril from PyPI
RUN pip install aitril==0.0.7 --break-system-packages

# Reset environment
ENV DEBIAN_FRONTEND=

# Default command: show help
CMD ["aitril", "--help"]

# Usage examples:
# docker run -it professai/aitril:latest aitril --help
# docker run -it professai/aitril:latest aitril tri "your prompt"
# docker run -it --env-file .env professai/aitril:latest aitril tri "your prompt"
