#!/usr/bin/env python3
"""
🦞 Smol Claw Secrets Protection 🛡️

Prevents committing sensitive information like:
- Environment variables (.env files)
- API keys, passwords, tokens
- Private keys, certificates
- Personal information

Usage:
    python scripts/check-secrets.py [files...]
    python scripts/check-secrets.py --all  # Check all tracked files
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# ============================================
# Sensitive Patterns 🛡️
# ============================================

SENSITIVE_PATTERNS = [
    # API Keys & Tokens
    (r'api[_-]?key\s*[=:]\s*["\']?[\w\-]{20,}["\']?', "API Key"),
    (r'api[_-]?secret\s*[=:]\s*["\']?[\w\-]{20,}["\']?', "API Secret"),
    (r'access[_-]?token\s*[=:]\s*["\']?[\w\-]{20,}["\']?', "Access Token"),
    (r'auth[_-]?token\s*[=:]\s*["\']?[\w\-]{20,}["\']?', "Auth Token"),
    (r'bearer\s+[\w\-\.]+', "Bearer Token"),

    # Passwords
    (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
    (r'passwd\s*[=:]\s*["\'][^"\']+["\']', "Password"),
    (r'pwd\s*[=:]\s*["\'][^"\']+["\']', "Password"),

    # Private Keys
    (r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', "Private Key"),
    (r'private[_-]?key\s*[=:]\s*["\']?[\w\-/+=]+["\']?', "Private Key"),

    # Database Credentials
    (r'database[_-]?url\s*[=:]\s*["\']?[^"\']+://[^"\']+["\']?', "Database URL"),
    (r'db[_-]?password\s*[=:]\s*["\'][^"\']+["\']', "Database Password"),
    (r'mongodb[+]?srv://[^"\']+', "MongoDB Connection String"),
    (r'postgres://[^"\']+', "PostgreSQL Connection String"),

    # Cloud Provider Keys
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    (r'aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\']?[\w/+=]{40}["\']?', "AWS Secret Key"),
    (r'sk-[a-zA-Z0-9]{48}', "OpenAI API Key"),
    (r'sk-ant-[a-zA-Z0-9\-]+', "Anthropic API Key"),

    # Webhooks
    (r'https://hooks\.slack\.com/services/[A-Z0-9/]+', "Slack Webhook"),
    (r'https://discord\.com/api/webhooks/\d+/[\w\-]+', "Discord Webhook"),

    # Generic Secrets
    (r'secret\s*[=:]\s*["\'][^"\']{8,}["\']', "Secret"),
    (r'token\s*[=:]\s*["\'][^"\']{20,}["\']', "Token"),
]

# Files that should never be committed
FORBIDDEN_FILES = [
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "secrets.json",
    "private.key",
    "id_rsa",
    "id_dsa",
]

# File extensions to check
CHECK_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".sh", ".bash", ".zsh",
    ".yml", ".yaml", ".json", ".toml",
    ".txt", ".md", ".env", ".cfg", ".conf"
}


# ============================================
# Checker Functions
# ============================================

def check_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Check a file for sensitive information.

    Returns:
        List of (line_number, pattern_name, matched_text)
    """
    if not file_path.exists() or file_path.is_dir():
        return []

    # Skip binary files
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return []

    findings = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for pattern, name in SENSITIVE_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Mask the sensitive part
                masked = re.sub(r'[=:]\s*["\']?[\w\-/+=]{8,}["\']?', '=[REDACTED]', line)
                findings.append((line_num, name, masked.strip()))

    return findings


def check_forbidden_filename(file_path: Path) -> bool:
    """Check if filename is in forbidden list"""
    return file_path.name in FORBIDDEN_FILES


def should_check_file(file_path: Path) -> bool:
    """Determine if file should be checked"""
    # Check extension
    if file_path.suffix not in CHECK_EXTENSIONS:
        return False

    # Skip certain directories
    skip_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache"}
    if any(part in skip_dirs for part in file_path.parts):
        return False

    return True


def get_staged_files() -> List[Path]:
    """Get list of staged files in git"""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.strip().split("\n")
        return [Path(f) for f in files if f]
    except subprocess.CalledProcessError:
        return []


def main():
    """Main entry point"""
    # Determine which files to check
    if "--all" in sys.argv:
        # Check all tracked files
        import subprocess
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        files = [Path(f) for f in result.stdout.strip().split("\n") if f]
    elif len(sys.argv) > 1:
        # Check specified files
        files = [Path(f) for f in sys.argv[1:] if f != "--all"]
    else:
        # Check staged files (default for pre-commit hook)
        files = get_staged_files()

    if not files:
        print("✅ No files to check")
        return 0

    # Check files
    violations = []

    for file_path in files:
        # Check forbidden filename
        if check_forbidden_filename(file_path):
            violations.append({
                "file": str(file_path),
                "type": "forbidden_file",
                "message": f"🚫 Forbidden file: {file_path.name}"
            })
            continue

        # Check content
        if should_check_file(file_path):
            findings = check_file(file_path)
            for line_num, pattern_name, matched_text in findings:
                violations.append({
                    "file": str(file_path),
                    "line": line_num,
                    "type": pattern_name,
                    "text": matched_text
                })

    # Report findings
    if violations:
        print("\n" + "=" * 70)
        print("🛡️  SECURITY ALERT: Sensitive Information Detected! 🛡️")
        print("=" * 70)
        print()

        for v in violations:
            if v["type"] == "forbidden_file":
                print(f"❌ {v['message']}")
                print(f"   File: {v['file']}")
            else:
                print(f"❌ {v['type']} detected!")
                print(f"   File: {v['file']}:{v.get('line', '?')}")
                print(f"   Line: {v.get('text', '')}")
            print()

        print("=" * 70)
        print("🦞 Smol Claw prevented you from committing sensitive data!")
        print()
        print("What to do:")
        print("  1. Remove sensitive information from the files")
        print("  2. Use environment variables instead: os.getenv('API_KEY')")
        print("  3. Add sensitive files to .gitignore")
        print("  4. Update GUARDRAILS.md with protection rules")
        print()
        print("To bypass this check (NOT RECOMMENDED):")
        print("  git commit --no-verify")
        print("=" * 70)
        print()

        return 1

    print("✅ No sensitive information detected! Safe to commit. 🦞")
    return 0


if __name__ == "__main__":
    sys.exit(main())
