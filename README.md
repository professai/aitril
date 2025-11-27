# 🧬 AiTril

**Multi-LLM Orchestration CLI Tool**

AiTril is a neutral, open-source command-line interface that orchestrates multiple Large Language Model (LLM) providers through a single unified interface. Query OpenAI, Anthropic, and Google Gemini in parallel and compare their responses side-by-side.

## Features

- **Multi-Provider Support**: Integrate with OpenAI (GPT), Anthropic (Claude), and Google Gemini
- **Parallel Queries**: Send prompts to all providers simultaneously (tri-lam mode)
- **Simple Configuration**: Interactive setup wizard for easy provider configuration
- **Async-First Design**: Built on Python asyncio for efficient concurrent operations
- **Privacy-Focused**: API keys stored locally in your home directory
- **Extensible**: Clean provider abstraction for adding new LLM providers

## Installation

### Using pip

```bash
pip install aitril
```

### Using uv

```bash
uv pip install aitril
```

### From Source

```bash
git clone https://github.com/professai/aitril.git
cd aitril
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

Run the interactive setup wizard to configure your LLM providers:

```bash
aitril init
```

You'll be prompted to enter API keys for each provider. You can configure one, two, or all three providers. For the best experience (tri-lam mode), configure at least two providers.

### 2. Query a Single Provider

Send a prompt to a specific provider:

```bash
aitril ask --provider gpt "Explain quantum computing in simple terms"
aitril ask --provider claude "Write a haiku about programming"
aitril ask --provider gemini "What are the benefits of async programming?"
```

### 3. Tri-Lam Mode (Parallel Queries)

Send the same prompt to all configured providers and compare responses:

```bash
aitril tri "Compare your strengths and weaknesses as an AI model"
```

This will query all enabled providers in parallel and display their responses in labeled sections.

## Configuration

AiTril stores configuration in `~/.config/aitril/config.toml` (or `%APPDATA%\aitril\config.toml` on Windows).

### Configuration File Structure

```toml
[providers.openai]
enabled = true
api_key = "sk-..."  # Optional: can use OPENAI_API_KEY env var instead
model = "gpt-4"

[providers.anthropic]
enabled = true
api_key = "sk-ant-..."  # Optional: can use ANTHROPIC_API_KEY env var instead
model = "claude-3-5-sonnet-20241022"

[providers.gemini]
enabled = true
api_key = "..."  # Optional: can use GEMINI_API_KEY env var instead
model = "gemini-pro"
```

### Environment Variables

Instead of storing API keys in the config file, you can use environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

AiTril will automatically use these environment variables if no API key is specified in the configuration file.

## Requirements

- Python 3.11 or higher
- API keys for at least one provider:
  - OpenAI: https://platform.openai.com/api-keys
  - Anthropic: https://console.anthropic.com/
  - Google AI: https://makersuite.google.com/app/apikey

For normal usage, **at least two providers** should be configured (the "tri-lam rule").

## Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/professai/aitril.git
cd aitril

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Docker Development Environment

Build and run AiTril in a Docker container:

```bash
# Build the image
docker build -t aitril-dev .

# Run the container
docker run -it --rm aitril-dev

# Run with environment variables for API keys
docker run -it --rm \
  -e OPENAI_API_KEY="sk-..." \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  -e GEMINI_API_KEY="..." \
  aitril-dev aitril tri "Hello, world!"
```

## Architecture

AiTril follows a modular architecture:

- **`config.py`**: Configuration loading, saving, and interactive wizard
- **`providers.py`**: Provider abstraction and implementations (OpenAI, Anthropic, Gemini)
- **`orchestrator.py`**: Multi-provider orchestration and parallel query coordination
- **`cli.py`**: Command-line interface using argparse

All provider calls are async-first, with synchronous SDK calls wrapped using `asyncio.run_in_executor()` for clean concurrency.

## Roadmap

- [x] Core multi-provider orchestration
- [x] Interactive configuration wizard
- [x] Parallel tri-lam queries
- [ ] Streaming responses
- [ ] Additional provider support (Cohere, local models, etc.)
- [ ] Plugin system for custom providers
- [ ] Response caching and history
- [ ] Database navigation tools
- [ ] Agentic daemon framework

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Copyright 2025 Collin Paran

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the LICENSE file for the specific language governing permissions and limitations under the License.

## Disclaimer

AiTril is an independent, neutral, open-source project. It is not affiliated with or endorsed by OpenAI, Anthropic, Google, or any other LLM provider.

---

**Happy tri-lamming!** 🧬
