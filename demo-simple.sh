#!/bin/bash

# Simple AiTril demo for asciinema
# Shows key features without actual API calls

clear

# Show banner
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧬 AiTril - Multi-LLM Orchestration
  Pronounced: "8-real"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

sleep 1

# Demo 1: Quick tri-lam query
echo "$ aitril tri \"Compare your strengths\""
sleep 0.5
echo

cat << 'EOF'
━━━ Querying 3 providers in parallel ━━━

🟢 GPT-4o
I excel at creative problem-solving and broad
knowledge integration across domains...

🔵 Claude Sonnet
My strengths include nuanced analysis, careful
reasoning, and detailed explanations...

🟡 Gemini Flash
I specialize in rapid inference and efficient
multimodal processing...

✓ Completed in 2.1s
EOF

sleep 3
clear

# Demo 2: Consensus mode
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧬 AiTril - Consensus Mode Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

sleep 0.5

echo "$ aitril tri --coordinate consensus \"Best practices for Python CLIs?\""
sleep 0.5
echo

cat << 'EOF'
━━━ Phase 1: Independent responses ━━━
All providers responding in parallel...

━━━ Phase 2: Consensus synthesis ━━━
Analyzing agreements...

📊 Consensus Report

✓ Strong agreement (3/3):
  • Use argparse or click for CLI parsing
  • Implement proper error handling
  • Add --help and --version flags
  • Support environment variables

⚠ Partial agreement (2/3):
  • Configuration files (GPT-4o, Claude)
  • Color output with rich (Claude, Gemini)

✓ Consensus achieved in 4.3s
EOF

sleep 3
clear

# Demo 3: Build command
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧬 AiTril - Code Building Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

sleep 0.5

echo "$ aitril config set-stack --language python --framework click"
sleep 0.3
echo "✓ Tech stack preferences saved"
echo
sleep 0.5

echo "$ aitril build \"Create setup.py for PyPI package\""
sleep 0.5
echo

cat << 'EOF'
━━━ Planning Phase ━━━
Building consensus on architecture...
✓ Plan approved by all agents

━━━ Implementation Phase ━━━
Agent 1: Core setup configuration...
Agent 2: Dependencies and metadata...
Agent 3: Entry points and scripts...

━━━ Review Phase ━━━
Consensus review checking quality...

📝 Review Summary
✓ Correctness: 3/3 approved
✓ Best practices: All checks passed
✓ Ready to deploy

✓ Build completed in 12.7s
EOF

sleep 3
clear

# Final screen
cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧬 AiTril - Multi-LLM Orchestration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Features:
  • Parallel queries across OpenAI, Anthropic, Gemini
  • Consensus mode for collaborative decisions
  • Code building with multi-agent review
  • Session management and tech stack preferences

📦 Install:
  pip install aitril

🔗 Links:
  GitHub: github.com/professai/aitril
  PyPI:   pypi.org/project/aitril

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

sleep 2
