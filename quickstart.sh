#!/bin/bash
set -e

echo "🦞 Smol Claw Quick Start"
echo "========================="
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION found, but $REQUIRED_VERSION+ required"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check for Claude CLI
echo "Checking for Claude CLI..."
if ! command -v claude &> /dev/null; then
    echo "⚠️  Claude CLI not found. Install from: https://claude.ai/code"
    echo "   Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Claude CLI found"
fi
echo ""

# Interactive setup
echo "🦞 Quick Setup"
echo ""
echo "Do you want to enable Discord notifications? (y/n)"
read -r discord_enabled

if [[ "$discord_enabled" =~ ^[Yy]$ ]]; then
    echo "Enter your Discord webhook URL:"
    read -r webhook_url
    echo "export DISCORD_WEBHOOK_URL=\"$webhook_url\"" >> venv/bin/activate
    echo "✅ Discord webhook configured"
else
    echo "⏭️  Skipping Discord setup"
fi

echo ""
echo "🛡️  Security Setup"
echo ""
echo "Do you want to install git hooks to prevent committing secrets? (y/n)"
read -r install_hooks

if [[ "$install_hooks" =~ ^[Yy]$ ]]; then
    bash scripts/install-hooks.sh
    echo "✅ Git hooks installed"
else
    echo "⏭️  Skipping git hooks (you can install later with: bash scripts/install-hooks.sh)"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start Smol Claw:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the server: python autonomous-ai-server.py"
echo ""
echo "Visit http://localhost:3000 when ready"
echo ""
echo "🛡️  Your secrets are protected! Check GUARDRAILS.md for details."
echo ""
echo "🦞 Happy coding!"
