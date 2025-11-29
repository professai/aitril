#!/bin/bash
# AiTril Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/professai/aitril/main/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║            AiTril Installer v0.0.37                        ║"
    echo "║     Multi-LLM Orchestration CLI Tool                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    print_info "Detected OS: $OS"
}

# Check for Python 3.8+
check_python() {
    print_info "Checking Python installation..."

    # Try different Python commands
    for cmd in python3 python; do
        if command -v $cmd &> /dev/null; then
            PYTHON_CMD=$cmd
            PYTHON_VERSION=$($cmd --version 2>&1 | awk '{print $2}')
            PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
            PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

            if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
                print_success "Found Python $PYTHON_VERSION at $(which $cmd)"
                return 0
            fi
        fi
    done

    print_error "Python 3.8 or higher is required but not found."
    echo ""
    echo "Please install Python from:"
    echo "  - macOS: brew install python@3.14"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  - Fedora/RHEL: sudo dnf install python3 python3-pip"
    echo "  - Or download from: https://www.python.org/downloads/"
    exit 1
}

# Check for pip
check_pip() {
    print_info "Checking pip installation..."

    for cmd in pip3 pip; do
        if command -v $cmd &> /dev/null; then
            PIP_CMD=$cmd
            print_success "Found pip at $(which $cmd)"
            return 0
        fi
    done

    print_warning "pip not found, attempting to install..."
    $PYTHON_CMD -m ensurepip --default-pip || {
        print_error "Failed to install pip"
        exit 1
    }
    PIP_CMD="$PYTHON_CMD -m pip"
    print_success "pip installed successfully"
}

# Install AiTril
install_aitril() {
    print_info "Installing AiTril from PyPI..."

    # Try to install with user flag if not in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        INSTALL_FLAGS="--user"
    else
        INSTALL_FLAGS=""
    fi

    $PIP_CMD install $INSTALL_FLAGS aitril || {
        print_error "Failed to install AiTril"
        exit 1
    }

    print_success "AiTril installed successfully!"
}

# Install with web extras (optional)
install_web_extras() {
    echo ""
    read -p "Install web interface? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing AiTril with web interface..."

        if [ -z "$VIRTUAL_ENV" ]; then
            INSTALL_FLAGS="--user"
        else
            INSTALL_FLAGS=""
        fi

        $PIP_CMD install $INSTALL_FLAGS "aitril[web]" || {
            print_error "Failed to install web extras"
            return 1
        }

        print_success "Web interface installed!"
    fi
}

# Setup .env file
setup_env() {
    echo ""
    read -p "Download .env.example template? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Downloading .env.example..."

        curl -fsSL https://raw.githubusercontent.com/professai/aitril/main/.env.example -o .env.example || {
            print_warning "Failed to download .env.example"
            return 1
        }

        print_success "Downloaded .env.example to current directory"
        print_info "Copy it to .env and add your API keys:"
        echo "  cp .env.example .env"
    fi
}

# Check if aitril command is in PATH
check_path() {
    print_info "Checking if aitril is in PATH..."

    if command -v aitril &> /dev/null; then
        print_success "aitril command is available!"
        AITRIL_VERSION=$(aitril --version 2>&1 || echo "unknown")
        print_info "Version: $AITRIL_VERSION"
    else
        print_warning "aitril command not found in PATH"

        # Check common user installation paths
        USER_BIN="$HOME/.local/bin"
        if [ -d "$USER_BIN" ]; then
            if [ -f "$USER_BIN/aitril" ]; then
                print_info "Found aitril at $USER_BIN/aitril"

                # Check if this path is in PATH
                if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
                    print_warning "$USER_BIN is not in your PATH"
                    echo ""
                    echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
                    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                    echo ""
                    echo "Then reload your shell:"
                    echo "  source ~/.bashrc  # or ~/.zshrc"
                fi
            fi
        fi
    fi
}

# Print next steps
print_next_steps() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                Installation Complete!                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    print_success "AiTril has been installed successfully!"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Set up your API keys:"
    echo "   - Copy .env.example to .env"
    echo "   - Add your OpenAI, Anthropic, and/or Google API keys"
    echo ""
    echo "2. Initialize AiTril:"
    echo "   $ aitril init"
    echo ""
    echo "3. Try a query with Tri-lam mode (3 LLMs):"
    echo "   $ aitril tri \"Explain quantum computing in simple terms\""
    echo ""
    echo "4. Or use the web interface:"
    echo "   $ aitril web"
    echo "   Then open: http://localhost:37142"
    echo ""
    echo "Documentation: https://github.com/professai/aitril"
    echo "Issues: https://github.com/professai/aitril/issues"
    echo ""
}

# Main installation flow
main() {
    print_header
    detect_os
    check_python
    check_pip
    install_aitril
    install_web_extras
    setup_env
    check_path
    print_next_steps
}

# Run main function
main
