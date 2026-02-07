# Changelog

All notable changes to Smol Claw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2026-02-07

### Added
- 🔥 **Event-Driven Architecture** ([#22](https://github.com/suojae/smol-claw/pull/22))
  - Replaced polling with true event-driven architecture using asyncio.Queue
  - OS-level file watching with `watchdog` (instant detection, no polling)
  - GitHub webhook endpoint for push-based event notifications
  - CPU 0% when idle, instant reaction to events
  - 2-hour fallback timer (only remaining periodic check)

- 🧠 **Session Reuse for 75% Token Savings** ([#20](https://github.com/suojae/smol-claw/pull/20))
  - Autonomous loop reuses Claude sessions for up to 50 calls
  - Pattern and memory sent once per session instead of every call
  - Reduces token usage from ~65k/day to ~16k/day
  - Auto-reset after 50 calls to prevent context bloat

- 💬 **Discord Conversation Memory** ([#18](https://github.com/suojae/smol-claw/pull/18))
  - Channel-specific session persistence for Discord conversations
  - AI remembers previous messages in the same channel
  - Maintains independent sessions per Discord channel
  - Fixes [#17](https://github.com/suojae/smol-claw/issues/17)

- 🛡️ **Usage Tracker & Rate Limiting** ([#16](https://github.com/suojae/smol-claw/pull/16))
  - Single chokepoint enforcement in ClaudeExecutor.execute()
  - Per-minute (5), per-hour (20), per-day (500) call limits
  - 5-second cooldown between calls
  - 80% warning threshold with Discord notifications
  - Persistent usage tracking (memory/usage.json)
  - Web dashboard usage monitoring with progress bars
  - Autonomous loop crash protection on limit exceeded

### Changed
- Updated autonomous loop to consume events from queue (event-driven)
- think() method now accepts optional events parameter for context
- Added Request import to FastAPI for webhook handling

### Dependencies
- Added `watchdog==6.0.0` for file system event monitoring

### Technical Details
**Event Architecture:**
```
[watchdog]           → event_queue (file changes)
[/webhook/github]    → event_queue (PR/CI events)
[Discord on_message] → already event-driven
[2hr fallback]       → event_queue (periodic backup)
                           ↓
                autonomous_loop blocks on queue.get()
                           ↓
                      think(events)
```

**Token Optimization:**
- Before: 1,300 tokens × 50 calls/day = 65,000 tokens
- After: 1,300 + (300 × 49) = 16,000 tokens (75% reduction)

**Test Coverage:**
- test_event_watcher.py: 9 tests (GitFileHandler, event queue, webhook parsing)
- test_session_reuse.py: 6 tests (session persistence, reset logic)
- test_usage_tracker.py: 12 tests (rate limits, cooldown, persistence, warnings)

## [0.0.2] - 2026-02-07

### Fixed
- 🚨 **Critical**: Fixed Discord bot parameter bug causing server crashes ([#13](https://github.com/suojae/smol-claw/pull/13))
  - `discord_bot` was incorrectly passed as positional argument, landing in `memory` parameter slot
  - This caused `AttributeError: 'DiscordBot' object has no attribute 'get_context'`
  - Now correctly passed as keyword argument: `discord_bot=discord_bot`
  - Fixes [#12](https://github.com/suojae/smol-claw/issues/12)

**Impact**: Server would crash immediately on startup when Discord bot was configured. This hotfix restores functionality.

## [0.0.1] - 2026-02-07

### Added
- 🦞 **Initial Release** - First stable version of Smol Claw!

#### Core Features
- Autonomous AI engine with 30-minute check intervals
- FastAPI web server with REST API endpoints
- Context collection (Git, TODO, calendar)
- Discord webhook integration for notifications

#### Memory Management 🧠
- SimpleMemory: JSON-based storage (zero dependencies)
- GuardrailMemory: Security-focused violation tracking
- Duplicate detection with 24-hour window
- Auto-summarization when exceeding 100 decisions
- Pattern learning from security violations

#### Security Protection 🛡️
- Pre-commit hooks for secrets detection
- CI/CD security checks in GitHub Actions
- 15+ sensitive pattern detection (API keys, passwords, tokens, etc.)
- `.env` file protection
- Comprehensive GUARDRAILS.md guide

#### Infrastructure
- GitHub Actions CI/CD pipeline
- Branch protection rules (main, develop)
- Test suite with pytest
- Quick start installation script (`quickstart.sh`)

#### Documentation
- README.md (English) and README.ko.md (Korean)
- CONTRIBUTING.md with commit conventions
- STRATEGY.md with competitive positioning
- GUARDRAILS.md with security best practices
- IMPROVEMENTS.md with roadmap

#### Developer Experience
- MIT License
- PR templates
- Code formatting with Black
- Linting with Flake8
- Cute crayfish branding 🦞

### Technical Stack
- Python 3.11+
- FastAPI 0.115.0
- discord.py 2.3.2
- python-dotenv 1.0.0
- aiohttp 3.10.0

### Installation
```bash
bash quickstart.sh
```

### What's Next (v0.0.2)
- Enhanced guardrails with command whitelist
- Plugin system for extensibility
- Web dashboard improvements
- Multi-LLM support (OpenAI, local models)

---

[0.0.1]: https://github.com/suojae/smol-claw/releases/tag/v0.0.1
