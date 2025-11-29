#!/bin/bash
# AiTril Configuration Validation Script
# Checks that all configuration files are in sync with user preferences

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Validating AiTril Configuration..."
echo ""

ERRORS=0
WARNINGS=0

# Expected values
EXPECTED_OPENAI="gpt-5.1"
EXPECTED_ANTHROPIC="claude-opus-4.5-20251124"
EXPECTED_GEMINI="gemini-3-pro-preview"
EXPECTED_PORT="37142"

# Check .env file
echo "📄 Checking .env file..."
if [ -f ".env" ]; then
    OPENAI_MODEL=$(grep "^OPENAI_MODEL=" .env | cut -d= -f2)
    ANTHROPIC_MODEL=$(grep "^ANTHROPIC_MODEL=" .env | cut -d= -f2)
    GEMINI_MODEL=$(grep "^GEMINI_MODEL=" .env | cut -d= -f2)

    if [ "$OPENAI_MODEL" != "$EXPECTED_OPENAI" ]; then
        echo -e "${RED}❌ ERROR: .env has wrong OpenAI model: $OPENAI_MODEL (expected: $EXPECTED_OPENAI)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ OpenAI model correct: $OPENAI_MODEL${NC}"
    fi

    if [ "$ANTHROPIC_MODEL" != "$EXPECTED_ANTHROPIC" ]; then
        echo -e "${RED}❌ ERROR: .env has wrong Anthropic model: $ANTHROPIC_MODEL (expected: $EXPECTED_ANTHROPIC)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ Anthropic model correct: $ANTHROPIC_MODEL${NC}"
    fi

    if [ "$GEMINI_MODEL" != "$EXPECTED_GEMINI" ]; then
        echo -e "${RED}❌ ERROR: .env has wrong Gemini model: $GEMINI_MODEL (expected: $EXPECTED_GEMINI)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ Gemini model correct: $GEMINI_MODEL${NC}"
    fi
else
    echo -e "${RED}❌ ERROR: .env file not found${NC}"
    ((ERRORS++))
fi

echo ""

# Check settings.json
echo "📄 Checking ~/.aitril/settings.json..."
if [ -f "$HOME/.aitril/settings.json" ]; then
    SETTINGS_OPENAI=$(cat ~/.aitril/settings.json | grep -A 5 '"openai"' | grep '"model"' | cut -d'"' -f4)
    SETTINGS_ANTHROPIC=$(cat ~/.aitril/settings.json | grep -A 5 '"anthropic"' | grep '"model"' | cut -d'"' -f4)
    SETTINGS_GEMINI=$(cat ~/.aitril/settings.json | grep -A 5 '"gemini"' | grep '"model"' | cut -d'"' -f4)

    if [ "$SETTINGS_OPENAI" != "$EXPECTED_OPENAI" ]; then
        echo -e "${RED}❌ ERROR: settings.json has wrong OpenAI model: $SETTINGS_OPENAI (expected: $EXPECTED_OPENAI)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ OpenAI model correct: $SETTINGS_OPENAI${NC}"
    fi

    if [ "$SETTINGS_ANTHROPIC" != "$EXPECTED_ANTHROPIC" ]; then
        echo -e "${RED}❌ ERROR: settings.json has wrong Anthropic model: $SETTINGS_ANTHROPIC (expected: $EXPECTED_ANTHROPIC)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ Anthropic model correct: $SETTINGS_ANTHROPIC${NC}"
    fi

    if [ "$SETTINGS_GEMINI" != "$EXPECTED_GEMINI" ]; then
        echo -e "${RED}❌ ERROR: settings.json has wrong Gemini model: $SETTINGS_GEMINI (expected: $EXPECTED_GEMINI)${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ Gemini model correct: $SETTINGS_GEMINI${NC}"
    fi

    INITIAL_PLANNER=$(cat ~/.aitril/settings.json | python3 -c "import json, sys; data = json.load(sys.stdin); print(data.get('general', {}).get('initial_planner', 'NOT_SET'))" 2>/dev/null || echo "NOT_SET")
    if [ "$INITIAL_PLANNER" != "openai" ]; then
        echo -e "${YELLOW}⚠️  WARNING: initial_planner is not set to 'openai' (current: $INITIAL_PLANNER)${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓ Initial planner correct: $INITIAL_PLANNER${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  WARNING: settings.json not found (may not be initialized yet)${NC}"
    ((WARNINGS++))
fi

echo ""

# Check settings.py defaults
echo "📄 Checking aitril/settings.py defaults..."
if [ -f "aitril/settings.py" ]; then
    if grep -q "gemini-3-pro-preview" aitril/settings.py; then
        echo -e "${GREEN}✓ Gemini default correct in settings.py${NC}"
    else
        echo -e "${RED}❌ ERROR: settings.py has wrong Gemini default (should be gemini-3-pro-preview)${NC}"
        ((ERRORS++))
    fi

    if grep -q "claude-opus-4.5-20251124" aitril/settings.py; then
        echo -e "${GREEN}✓ Anthropic default correct in settings.py${NC}"
    else
        echo -e "${RED}❌ ERROR: settings.py has wrong Anthropic default (should be claude-opus-4.5-20251124)${NC}"
        ((ERRORS++))
    fi
else
    echo -e "${RED}❌ ERROR: aitril/settings.py not found${NC}"
    ((ERRORS++))
fi

echo ""

# Check web.py for .env loading
echo "📄 Checking aitril/web.py for .env loading..."
if [ -f "aitril/web.py" ]; then
    if grep -q "load_dotenv" aitril/web.py; then
        echo -e "${GREEN}✓ .env loading present in web.py${NC}"
    else
        echo -e "${RED}❌ ERROR: web.py missing .env loading code${NC}"
        ((ERRORS++))
    fi

    if grep -q "port=37142\|port 37142" aitril/web.py; then
        echo -e "${GREEN}✓ Port 37142 configured in web.py${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING: web.py may not be using port 37142${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ ERROR: aitril/web.py not found${NC}"
    ((ERRORS++))
fi

echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All configuration checks passed!${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Configuration has $WARNINGS warning(s)${NC}"
    exit 0
else
    echo -e "${RED}❌ Configuration has $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "💡 To fix configuration issues:"
    echo "   1. Review .claude-preferences.md for correct values"
    echo "   2. Update settings manually or run: aitril init"
    echo "   3. Run this script again to verify"
    exit 1
fi
