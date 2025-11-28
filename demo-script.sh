#!/bin/bash

# Demo script for AiTril showing tri-lam consensus mode
# This will be recorded with asciinema

# Function to simulate typing
type_command() {
    echo -n "$ "
    for ((i=0; i<${#1}; i++)); do
        echo -n "${1:$i:1}"
        sleep 0.05
    done
    echo
    sleep 0.3
}

# Function to show a command and execute it
demo_command() {
    type_command "$1"
    eval "$1"
    sleep 1
}

# Clear screen
clear

# Show banner
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧬 AiTril Demo - Multi-LLM Orchestration"
echo "  Pronounced: \"8-real\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
sleep 2

# Show quick tri-lam query
echo "Demo 1: Tri-Lam Query (Parallel Multi-Provider)"
echo "─────────────────────────────────────────────────"
echo
sleep 1

demo_command "aitril tri \"What makes a good Dockerfile?\""

sleep 2
echo
echo

# Show consensus mode for code building
echo "Demo 2: Consensus Mode - Build Dockerfile"
echo "──────────────────────────────────────────"
echo
sleep 1

demo_command "aitril build --session docker-demo \"Create an optimized Dockerfile for AiTril Python CLI\""

sleep 2
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Multi-agent consensus achieved!"
echo "  📦 Install: pip install aitril"
echo "  🔗 GitHub: github.com/professai/aitril"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

sleep 2
