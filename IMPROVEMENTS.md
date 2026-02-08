# Smol Marketing Claw — Improvements Roadmap

## Current State

### What We Have
- X (Twitter) post & reply API via `tweepy`
- Threads (Meta) post & reply API via `aiohttp`
- Discord bot & webhook notifications
- FastAPI REST API (9 endpoints)
- Smart memory with duplicate detection
- Guardrail-based API key protection
- Pre-commit hooks & CI/CD security scanning
- 52 tests with pytest

### Platform Support

| Platform | Post | Reply | Status |
|----------|------|-------|--------|
| X (Twitter) | ✅ | ✅ | Live |
| Threads (Meta) | ✅ | ✅ | Live |
| Discord | ✅ (notifications) | ✅ (bot) | Live |
| Instagram | ❌ | ❌ | Planned |
| LinkedIn | ❌ | ❌ | Planned |

## Priority 1: High (Next Sprint)

### Scheduled Posting
**Why**: Marketing teams need to schedule posts in advance.

**Features:**
- Post queue with scheduled timestamps
- Cron-like scheduling (`post every Monday at 9am`)
- Timezone-aware scheduling
- Queue management API (list, cancel, reschedule)

**API Design:**
```bash
POST /sns/x/schedule
{
  "text": "Monday motivation! 🚀",
  "scheduled_at": "2026-03-01T09:00:00Z"
}
```

### Content Calendar
**Why**: Visualize and plan marketing activities.

**Features:**
- Calendar view of scheduled/published posts
- Drag-and-drop rescheduling (web dashboard)
- Platform-specific color coding
- Export to iCal/Google Calendar

### Hashtag Recommendations
**Why**: Maximize reach with relevant hashtags.

**Features:**
- AI-powered hashtag suggestions based on post content
- Trending hashtag feed
- Hashtag performance tracking
- Platform-specific hashtag limits

## Priority 2: Medium (This Quarter)

### Post Analytics
**Why**: Measure marketing effectiveness.

**Features:**
- Track likes, retweets, replies per post
- Engagement rate calculation
- Best time to post analysis
- Weekly/monthly performance reports

### AI Content Generation
**Why**: Help users draft compelling posts.

**Features:**
- Claude-powered post drafting via `/ask`
- Tone adjustment (professional, casual, humorous)
- Platform-specific formatting (280 chars for X, 500 for Threads)
- A/B variant generation

**API Design:**
```bash
POST /ask
{
  "message": "Draft 3 tweet variations about our new AI feature"
}
```

### Image/Media Support
**Why**: Visual content gets higher engagement.

**Features:**
- Image upload and attachment to posts
- Auto-resize for platform requirements
- Media library management
- Alt text generation via AI

### Instagram Integration
**Why**: Instagram is essential for visual marketing.

**Features:**
- Post photos/carousels via Instagram Graph API
- Story posting
- Reply to comments
- Cross-post from Threads

## Priority 3: Low (Next Quarter)

### LinkedIn Integration
**Why**: B2B marketing reach.

**Features:**
- Post articles and updates
- Company page management
- Reply to comments

### Web Dashboard
**Why**: Non-developer users need a GUI.

**Features:**
- Post composer with preview
- Analytics dashboard with charts
- Content calendar (visual)
- Account management
- Team collaboration

### Multi-Language Support
**Why**: Reach global audiences.

**Features:**
- AI-powered post translation
- Locale-specific posting times
- Multi-language content calendar

### Campaign Management
**Why**: Coordinate cross-platform marketing efforts.

**Features:**
- Create campaigns spanning multiple platforms
- Track campaign-level metrics
- Budget tracking (for paid promotions)
- Campaign templates

## Infrastructure Improvements

### Docker Support
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "autonomous-ai-server.py"]
```

### Rate Limiting Improvements
- Platform-specific rate limit tracking
- Auto-retry with exponential backoff
- Rate limit dashboard

### Webhook Support
- Incoming webhooks for external triggers
- Outgoing webhooks for post events (posted, failed, scheduled)

## Success Metrics After Improvements

| Metric | Current | 3 Months | 6 Months |
|--------|---------|----------|----------|
| Platforms | 2 (X, Threads) | 3 (+Instagram) | 4 (+LinkedIn) |
| API Endpoints | 9 | 15 | 25 |
| Test Coverage | 52 tests | 80+ tests | 120+ tests |
| Features | Post & Reply | + Scheduling, Analytics | + Campaigns, Dashboard |

---

**Bottom Line**: We have a solid foundation with X and Threads integration. The next priority is scheduling and analytics to make Smol Marketing Claw useful for daily marketing workflows. 🦞
