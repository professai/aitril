# 🧬 AiTril

**Multi-LLM Orchestration CLI Tool**

AiTril is a neutral, open-source command-line interface that orchestrates multiple Large Language Model (LLM) providers through a single unified interface. Query OpenAI, Anthropic, and Google Gemini in parallel and compare their responses side-by-side.

## Features

- **Multi-Provider Support**: Integrate with OpenAI (GPT), Anthropic (Claude), and Google Gemini
- **Parallel Queries**: Send prompts to all providers simultaneously (tri-lam mode)
- **Agent Coordination**: Multiple collaboration modes (sequential, consensus, debate)
- **Session Management**: Track conversations across chat and build sessions
- **Smart Caching**: Store history, preferences, and context for continuity
- **Real-Time Streaming**: See responses as they're generated with visual progress indicators
- **Rich CLI Display**: Visual feedback with thinking indicators, task progress, and timing stats
- **Simple Configuration**: Interactive setup wizard for easy provider configuration
- **Async-First Design**: Built on Python asyncio for efficient concurrent operations
- **Privacy-Focused**: API keys and cache stored locally in your home directory
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

### 4. Agent Coordination Modes

Leverage multi-agent collaboration for more sophisticated responses:

**Sequential Mode** - Each agent builds on previous responses:
```bash
aitril tri --coordinate sequential "Solve this problem step by step: What's the best way to learn Python?"
```

**Consensus Mode** - Get a synthesized agreement from all agents:
```bash
aitril tri --coordinate consensus "What is the best programming language for web development?"
```

**Debate Mode** - Agents debate over multiple rounds:
```bash
aitril tri --coordinate debate "Discuss the pros and cons of microservices architecture"
```

### 5. Session Management

Track conversations across named sessions:

```bash
# Start a project session
aitril ask --session "my-project" -p gpt "Help me design a REST API"

# Continue in the same session
aitril tri --session "my-project" "What authentication should I use?"

# View session history
aitril cache history

# Quick question without caching
aitril ask --no-cache -p claude "What's 2+2?"
```

### 6. Cache Management

Manage your conversation history and preferences:

```bash
# Show cache summary
aitril cache show

# List all sessions
aitril cache list

# View session history
aitril cache history

# Clear a specific session
aitril cache clear --session "old-project"

# Clear all cache (with confirmation)
aitril cache clear
```

## Configuration

AiTril stores configuration in `~/.config/aitril/config.toml` (or `%APPDATA%\aitril\config.toml` on Windows).

### Configuration File Structure

```toml
[providers.openai]
enabled = true
api_key = "sk-..."  # Optional: can use OPENAI_API_KEY env var instead
model = "gpt-5.1"

[providers.anthropic]
enabled = true
api_key = "sk-ant-..."  # Optional: can use ANTHROPIC_API_KEY env var instead
model = "claude-opus-4-5-20250929"

[providers.gemini]
enabled = true
api_key = "..."  # Optional: can use GOOGLE_API_KEY env var instead
model = "gemini-3-pro-preview"
```

### Environment Variables

Instead of storing API keys in the config file, you can use environment variables:

```bash
# API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."  # Google's standard env var for Gemini

# Model Selection (optional)
export OPENAI_MODEL="gpt-5.1"
export ANTHROPIC_MODEL="claude-opus-4-5-20250929"
export GEMINI_MODEL="gemini-3-pro-preview"
```

AiTril will automatically use these environment variables if no API key is specified in the configuration file.

### Cache and Session Storage

AiTril stores cache and session data separately from configuration:

- **Config**: `~/.config/aitril/config.toml` (or `%APPDATA%\aitril\config.toml` on Windows)
- **Cache**: `~/.cache/aitril/cache.json` (or `%LOCALAPPDATA%\aitril\cache\cache.json` on Windows)

The cache includes:
- **Session history**: All prompts and responses organized by session
- **Global preferences**: Settings that persist across all sessions
- **Session preferences**: Settings specific to individual sessions
- **Context data**: Coordination context for multi-agent interactions

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

Build and run AiTril in a Docker container using Docker Compose:

```bash
# 1. Copy the example environment file and add your API keys
cp .env.example .env
# Edit .env and add your actual API keys

# 2. Build and start the container
docker-compose up -d

# 3. Run aitril commands inside the container
docker-compose exec aitril aitril --help
docker-compose exec aitril aitril --version

# 4. Enter interactive shell
docker-compose exec aitril bash

# 5. Stop and remove the container
docker-compose down
```

**Environment Setup:**

The `.env` file should contain your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GEMINI_API_KEY=your-key-here
```

See `.env.example` for a template with links to get API keys.

## Architecture

AiTril follows a modular architecture:

- **`config.py`**: Configuration loading, saving, and interactive wizard
- **`providers.py`**: Provider abstraction and implementations (OpenAI, Anthropic, Gemini)
- **`orchestrator.py`**: Multi-provider orchestration and parallel query coordination
- **`coordinator.py`**: Multi-agent coordination strategies (sequential, consensus, debate)
- **`cache.py`**: Session management, history tracking, and preference storage
- **`display.py`**: Rich CLI feedback with progress indicators and visual symbols
- **`cli.py`**: Command-line interface using argparse

All provider calls are async-first using native async clients (`AsyncOpenAI`, `AsyncAnthropic`) for true concurrent streaming responses.

## Roadmap

**Completed (v0.0.1):**
- [x] Core multi-provider orchestration
- [x] Interactive configuration wizard
- [x] Parallel tri-lam queries
- [x] Real-time streaming responses
- [x] Multi-agent coordination (sequential, consensus, debate modes)
- [x] Session management and caching
- [x] Conversation history tracking
- [x] Rich CLI display with progress indicators
- [x] Environment variable configuration
- [x] Native async client implementation

**Planned:**
- [ ] Additional provider support (Cohere, Mistral, local models via Ollama)
- [ ] Plugin system for custom providers
- [ ] Advanced preference learning
- [ ] Database navigation tools
- [ ] Agentic daemon framework
- [ ] Web interface
- [ ] REST API mode

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
