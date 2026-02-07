#!/bin/bash
# 🦞 Install Smol Claw git hooks

set -e

echo "🦞 Installing Smol Claw git hooks..."

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)" || {
    echo "❌ Not a git repository"
    exit 1
}

HOOKS_DIR="$GIT_DIR/hooks"
PRE_COMMIT="$HOOKS_DIR/pre-commit"

# Create pre-commit hook
cat > "$PRE_COMMIT" << 'EOF'
#!/bin/bash
# 🦞 Smol Claw pre-commit hook
# Checks for sensitive information before commit

echo "🦞 Checking for sensitive information..."

# Run secrets checker
python3 scripts/check-secrets.py

exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "🛡️  Commit blocked by Smol Claw security check!"
    exit 1
fi

exit 0
EOF

# Make executable
chmod +x "$PRE_COMMIT"

echo "✅ Git hooks installed successfully!"
echo ""
echo "The pre-commit hook will now:"
echo "  • Check for API keys, passwords, tokens"
echo "  • Block commits of .env files"
echo "  • Detect private keys and credentials"
echo "  • Protect sensitive information"
echo ""
echo "🦞 Your secrets are safe with Smol Claw! 🛡️"
