# Contributing to Smol Marketing Claw

Thank you for your interest in contributing to Smol Marketing Claw! 🦞

## Code of Conduct

- Be respectful and inclusive
- Write clear, maintainable code
- Follow the project's conventions
- Help others learn and grow

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/smol-claw.git`
3. Create a feature branch from `develop`: `git checkout -b feature/your-feature`
4. Make your changes
5. Test your changes thoroughly
6. Commit with proper commit message format
7. Push to your fork
8. Create a Pull Request to `develop` branch

## Branch Strategy

- `main` - Production-ready code
- `develop` - Development branch (create PRs here)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

## Commit Message Convention

### Format

```
🦞 type: brief description

Optional detailed explanation of what changed and why.

Co-Authored-By: Your Name <your.email@example.com>
```

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance tasks
- `perf` - Performance improvements

### Rules

1. **Write in English**
2. **Start with crayfish emoji** 🦞
3. **Use lowercase** for type and description
4. **Keep the first line under 72 characters**
5. **Use imperative mood** ("add" not "added")
6. **NO other emojis** (only crayfish 🦞)

### Good Examples

```
🦞 feat: add Telegram notification support

Implements Telegram bot integration for sending autonomous
notifications to users via Telegram API.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
🦞 fix: prevent duplicate notifications

Fixed race condition where notifications could be sent twice
when multiple context changes occur simultaneously.
```

```
🦞 docs: update installation instructions

Added Python version requirements and virtual environment setup.
```

### Bad Examples

```
❌ Add feature
(Missing crayfish emoji, no type)

❌ ✨ feat: Add cool new feature!
(Wrong emoji - only 🦞 allowed)

❌ 🦞 Added new feature
(Wrong tense - use imperative)

❌ 🦞 FEAT: ADD FEATURE
(Wrong case - use lowercase)
```

## Pull Request Guidelines

### Title Format

```
🦞 Brief description of changes
```

### PR Description Template

Use this template for your PRs:

```markdown
## Summary 🦞

Brief description of what this PR does.

## Changes

- Change 1
- Change 2
- Change 3

## Testing

How you tested these changes:
- [ ] Local testing completed
- [ ] All tests passing
- [ ] Documentation updated

## Related Issues

Closes #123
Related to #456

---

Made with 🦞 by [Your Name]
```

### PR Rules

1. **Target `develop` branch** for all PRs
2. **One feature per PR** - keep changes focused
3. **Update documentation** if needed
4. **Add tests** for new features
5. **Ensure all tests pass** before submitting
6. **Write clear description** of changes
7. **Reference related issues** if applicable
8. **Use crayfish emoji** 🦞 in title

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

### Example

```python
async def send_notification(self, message: str) -> bool:
    """
    Send notification to user via configured channels.

    Args:
        message: The notification message to send

    Returns:
        True if notification was sent successfully
    """
    # Implementation
    pass
```

## Testing

- Write tests for new features
- Ensure existing tests still pass
- Test edge cases and error conditions
- Manual testing on your local environment

## Documentation

- Update README.md if adding features
- Update code comments for complex logic
- Keep examples up to date
- Document configuration options

## Questions?

Feel free to:
- Open an issue for discussion
- Ask in pull request comments
- Check existing issues and PRs

---

Thank you for contributing to Smol Marketing Claw! 🦞
