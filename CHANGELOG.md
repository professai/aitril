# Changelog

All notable changes to AiTril will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.38] - 2025-11-30

### Added
- **System Prompt Support**: Global system prompt injection across all LLM providers
  - New `AITRIL_SYSTEM_PROMPT` environment variable
  - Injected into OpenAI, Anthropic, Gemini, Ollama, and LlamaCpp providers
  - Enables consistent, focused engineering collaboration tone
  - Configured via `.env` file for persistence

### Fixed
- **Gemini Function Call Empty Name Error**: Robust handling of empty/invalid function names
  - Filter invalid function calls at collection time (before processing)
  - Added `getattr()` and `str().strip()` validation for function names
  - Skip function calls with empty, None, or whitespace-only names
  - Prevents `400 GenerateContentRequest.contents[].parts[].function_response.name: Name cannot be empty` error

- **FileTool Output Directory**: Files now correctly written to `AITRIL_OUTPUTS_DIR`
  - Write operations always go to the configured outputs directory
  - Read operations check outputs dir first, then fall back to literal path
  - List operations default to outputs dir for `.` or empty path
  - Parent directories created automatically for nested paths

### Changed
- **Docker Volume Mounts**: Simplified container output directory handling
  - Container uses `/outputs` internally (mounted from host)
  - Host `AITRIL_OUTPUTS_DIR` maps directly to container `/outputs`
  - Default: `./aitril_build_session/projects` if env var not set
  - Fixed issue where files were created inside container but not visible on host

- Updated Dockerfile to install v0.0.38 from PyPI
- Updated docker-compose.yml with cleaner volume mount configuration

## [0.0.37] - 2025-11-29

### Added
- **One-Command Installation**: Quick install scripts for all platforms
  - `install.sh`: Bash installer for Linux/macOS with curl
  - `install.ps1`: PowerShell installer for Windows
  - Auto-detects Python version (3.8+ required)
  - Optional web interface installation
  - Downloads .env.example template automatically
  - Verifies PATH configuration and provides setup guidance
  - Usage: `curl -fsSL https://raw.githubusercontent.com/professai/aitril/main/install.sh | bash`
  - Usage (Windows): `iwr -useb https://raw.githubusercontent.com/professai/aitril/main/install.ps1 | iex`

- **Tech Stack Configuration in .env**:
  - Tech stack preferences now saved to `.env` file with `AITRIL_TECH_` prefix
  - Added `--frontend` argument to `aitril config set-stack` command
  - Default values: Python, FastAPI, vanilla JavaScript and HTML
  - Read from `.env` with proper fallback to defaults
  - Environment variables: `AITRIL_TECH_LANGUAGE`, `AITRIL_TECH_FRAMEWORK`, `AITRIL_TECH_FRONTEND`

### Fixed
- **Gemini Provider NoneType Error**: Fixed `'NoneType' object is not iterable` error in function calling
  - Added None check for `func_call.args` in both `ask()` and `ask_stream()` methods (lines 618, 699)
  - Added None check for `response.parts` before iteration
  - Added None check for `chunk.parts` before iteration
  - Improved error handling in Gemini's function calling implementation

### Changed
- Updated all Docker version references from 0.0.36 to 0.0.37
- Updated README with "Quick Install (Recommended)" section
- Updated landing page with one-command installers
- Dockerfile updated to install v0.0.37 from PyPI

### Documentation
- Added installation scripts documentation to README
- Updated "What's New" section in README
- Updated meta tags and version references in landing page

## [0.0.36] - 2025-11-29

### Added
- **Artifact-Based Coordination**: Full content transfer between agents
  - `AgentArtifact` system for plans, code, files, and data
  - `ArtifactRegistry` tracks all artifacts across collaboration phases
  - No truncation of agent outputs

- **File Verification System**:
  - Ensures generated files have actual content (not 0 bytes)
  - `FileVerifier` checks file size and structure
  - `ContentVerifier` validates notebook cells and code quality

- **Automated Deployment**:
  - Strategy pattern supporting multiple targets
  - Local: Configurable outputs directory (`AITRIL_OUTPUTS_DIR`)
  - GitHub Pages: Auto-push to gh-pages branch
  - AWS EC2: Deploy to EC2 instances
  - Docker Hub: Build and push containers
  - Vercel: Deploy web apps
  - Heroku: Deploy backends
  - `DeploymentManager` with auto-detection of project types
  - Integrated into web interface with real-time UI

- **Environment Configuration**:
  - `AITRIL_OUTPUTS_DIR` environment variable for custom output paths
  - Comprehensive `.env.example` with 275+ lines of documentation
  - Docker volume mounting for seamless host/container file sharing

### Changed
- **Web Interface Improvements**:
  - Port changed to 37142 (previously 8888)
  - Deployment phase UI with target selection
  - Real-time artifact visualization
  - Enhanced settings management

## [0.0.32] - 2025-11-28

### Added
- **🔧 Tool Use System**: Comprehensive function calling / tool use across all providers
  - **Tool Framework** (`aitril/tools.py`): Base Tool class with execute() interface
  - **ShellTool**: Execute whitelisted shell commands (curl, date, ls, cat, echo, etc.)
  - **SystemInfoTool**: Get system time, timezone, OS information - solves "what time is it?" issues
  - **FileTool**: Read, write, and list file operations
  - **WebTool**: HTTP GET and POST requests to APIs
  - **ToolRegistry**: Manages all tools with provider-specific format conversion

- **Provider Function Calling**: All 3 major providers have full tool support
  - **OpenAI (GPT-4o)**: Chat Completions API with function calling
    - Tool execution loop (max 5 iterations)
    - Streaming accumulates tool calls, yields execution results
    - Switched default model from gpt-5.1 to gpt-4o for better function support
  - **Anthropic (Claude Opus 4.5)**: Messages API with tool use
    - Event-driven streaming with tool execution
    - Multi-tool scenario support
    - Updated default to claude-opus-4-5-20251124
  - **Gemini (2.0 Flash)**: GenerativeModel with function declarations
    - FunctionDeclaration format conversion
    - Chat-based function calling with start_chat()
    - Changed default from gemini-3-pro-preview to gemini-2.0-flash-exp

- **Universal Tool Integration**: Tools work across ALL modes
  - **Tri-lam Mode**: Each provider uses tools independently in parallel
  - **Consensus Mode**: All agents use tools, then synthesize results
  - **Sequential Mode**: Agents use tools, building on previous tool results
  - **Debate Mode**: Tools available in each debate round
  - **Code Build Mode**: Tools in planning, implementation, and review phases
  - **Code Review Mode**: Tools assist in code analysis

### Changed
- **Default Models Updated** for better tool support:
  - OpenAI: gpt-5.1 → gpt-4o
  - Gemini: gemini-3-pro-preview → gemini-2.0-flash-exp
  - Anthropic: claude-opus-4-5-20250929 → claude-opus-4-5-20251124

- **Provider Base Class**: Added tool_registry and enable_tools properties
  - All providers have access to global ToolRegistry instance
  - Tools can be disabled per-provider with enable_tools: false config

### Technical Details
- **Tool Execution Flow**:
  1. LLM decides to use a tool (function call)
  2. Tool executes asynchronously (shell, HTTP, file ops, etc.)
  3. Result sent back to LLM
  4. LLM continues reasoning with tool results
  5. All output streamed in real-time to user

- **Safety Features**:
  - ShellTool: Whitelisted commands only (curl, date, ls, cat, echo, which, uname, pwd, whoami, uptime, cal)
  - Command timeout: 10 seconds max execution time
  - File size limits: 5000 chars for reads, truncated displays
  - HTTP timeout: 10 seconds per request
  - Max tool iterations: 5 per conversation to prevent loops

- **Architecture**:
  - 417 lines in `aitril/tools.py` - Complete tool framework
  - 892 total lines added across providers.py and tools.py
  - All providers use async tool execution
  - Streaming yields formatted tool execution info

### Use Cases Enabled
- **Accurate Time/Timezone Queries**: "What time is it in Colorado?" → Uses SystemInfoTool
- **Web API Integration**: "Check the weather API" → Uses WebTool with HTTP requests
- **File Operations**: "Read config.json" → Uses FileTool
- **System Commands**: "Curl this endpoint" → Uses ShellTool
- **Multi-tool Chains**: Agents can use multiple tools in sequence

## [0.0.31] - 2025-11-28

### Added
- **Web Interface**: Full-featured web UI with FastAPI backend and WebSocket support
  - Real-time agent collaboration visualization
  - Settings management UI for providers and deployment targets
  - Live streaming of agent responses
  - Deployment options selector
- **8-Provider Support**: Expanded from 3 to 8 LLM providers
  - OpenAI (GPT-5.1, GPT-4o, etc.)
  - Anthropic (Claude Opus 4.5, Sonnet, Haiku)
  - Google Gemini (Gemini 3 Pro Preview, 2.0 Flash)
  - Ollama (local models)
  - Llama.cpp (local models)
  - Custom1, Custom2, Custom3 (user-configurable providers)
- **Initial Planner Mode**: Optional planning agent that runs first
  - Sets groundwork for other agents
  - Configurable planner provider (default: OpenAI)
  - Visual distinction in UI with planner icon
- **Deployment Integrations**: Multiple deployment targets
  - Local file system
  - GitHub Pages
  - AWS EC2
  - Docker containers
- **Settings System**: JSON-based persistent settings
  - Provider configuration (models, API keys, enabled status)
  - Deployment target configuration
  - General preferences (theme, default mode, initial planner)
  - Chat history settings
- **Environment Variable Loading**: Automatic .env file loading in web server
  - API key management via .env
  - Model configuration via environment variables
  - Priority: settings.json > .env > defaults
- **Configuration Validation**: Tools to prevent configuration mistakes
  - `.claude-preferences.md` - Checkpoint file for user preferences
  - `.validate-config.sh` - Automated validation script
  - Verification of model versions across all config files

### Changed
- **Port Configuration**: Changed from 8888 to 37142 to avoid conflicts
- **Model Defaults**: Updated to latest 2025 models
  - OpenAI: gpt-5.1
  - Anthropic: claude-opus-4.5-20251124
  - Gemini: gemini-3-pro-preview
- **Settings Location**: Moved from `~/.config/aitril/config.toml` to `~/.aitril/settings.json`

### Fixed
- **Tri-lam Streaming**: Each provider now streams independently without waiting for others
  - Removed blocking behavior when initial_planner is enabled
  - Agents show real-time responses simultaneously
- **Environment Priority**: `.env` models now override `settings.json` values
  - Priority order: `.env` > `settings.json` > defaults
  - Environment reloads on every WebSocket connection
- **Ollama Support**: Added `OLLAMA_API_URL` environment variable support
  - Checks both `OLLAMA_API_URL` and `OLLAMA_BASE_URL`
  - Fixed model name requirements (must include tag, e.g., `granite4:350m`)
- **Coordination Modes**: Fixed consensus, sequential, and debate mode execution
  - Corrected method calls to `coordinate_consensus()`, `coordinate_sequential()`, `coordinate_debate()`
  - Added progress event handlers in frontend
- **Frontend Rendering**: Added support for status and assistant message types
  - Consensus results now display in UI
  - Progress messages show during multi-agent coordination
- **Logging**: Added detailed logging for debugging
  - WebSocket event transmission logging
  - API key and model configuration verification
  - Coordination execution flow tracking
- Provider initialization when using .env files
- Deployment selection not working in web UI
- 404 errors for favicon requests
- Model configuration sync issues between files
- Settings UI display and functionality

## [0.0.30] - 2025-11-27

### Added
- Additional provider testing and validation
- Docker image improvements

## [0.0.7] - 2025-11-20

### Added
- Docker support with multi-stage builds
- DockerHub publishing workflow
- Environment variable configuration examples

## [0.0.3] - 2025-11-15

### Added
- Code building with multi-agent consensus (plan, implement, review)
- Tech stack preference management
- File operations with automatic backups
- Project context tracking
- Build artifact recording
- Code review coordination mode

## [0.0.1] - 2025-11-10

### Added
- Core multi-provider orchestration (OpenAI, Anthropic, Gemini)
- Interactive configuration wizard
- Parallel tri-lam queries
- Real-time streaming responses
- Multi-agent coordination modes:
  - Sequential mode (agents build on previous responses)
  - Consensus mode (synthesized agreement)
  - Debate mode (multi-round discussions)
- Session management and caching
- Conversation history tracking
- Rich CLI display with progress indicators
- Environment variable configuration
- Native async client implementation
- PyPI package publishing

### Infrastructure
- Python 3.14 support
- Async-first architecture with asyncio
- pytest test suite
- GitHub repository setup
- Apache 2.0 license

---

## Version Numbering

AiTril uses semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

Currently in early development (0.0.x releases).
