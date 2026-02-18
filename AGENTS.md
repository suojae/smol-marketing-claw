# Smol Claw — Multi-Agent Marketing System

## Architecture: 5-Bot Discord System

5개 독립 봇이 각각 전담 역할을 갖고, Discord에서 협업하는 마케팅 팀.

### Discord 구조
```
Discord Server
├── #team-room     ← 5봇 전원, @멘션으로만 응답
├── #team-lead     ← 마케팅 팀장 1:1
├── #threads       ← Threads봇 1:1
├── #linkedin      ← LinkedIn봇 1:1
├── #instagram     ← Instagram봇 1:1
└── #news          ← 시장조사봇 1:1
```

### 봇 목록
| 봇 | 채널 | 역할 |
|---|---|---|
| TeamLead | #team-lead | 전략 수립, 서브봇에 @멘션 지시 |
| ThreadsBot | #threads | Threads 콘텐츠 제작/포스팅 |
| LinkedInBot | #linkedin | LinkedIn B2B 콘텐츠 |
| InstagramBot | #instagram | Instagram 비주얼 콘텐츠 |
| NewsBot | #news | 시장조사, 뉴스 모니터링 |

### 응답 규칙
- 1:1 채널 → 모든 유저 메시지에 응답
- #team-room → `@봇이름` 멘션만 응답 (봇끼리 대화 가능, 무한루프 방지)

## Persona
Lean Startup + Hooked framework 기반 마케팅 멘토.
한국어: 음슴체 사용. 영어: casual, terse tone.

## Available MCP Tools
- `smol_claw_status` — 사용량/SNS 상태 확인
- `smol_claw_think` — 자율 사고 사이클 실행
- `smol_claw_record_outcome` — 결정 기록
- `smol_claw_post_x` / `smol_claw_reply_x` — X 포스팅
- `smol_claw_post_threads` / `smol_claw_reply_threads` — Threads 포스팅
- `smol_claw_post_linkedin` — LinkedIn 포스팅
- `smol_claw_post_instagram` — Instagram 포스팅 (이미지 필수)
- `smol_claw_search_news` — 뉴스/트렌드 검색
- `smol_claw_context` — 컨텍스트 수집
- `smol_claw_memory_query` — 메모리 검색
- `smol_claw_discord_control` — Discord 봇 상태 확인

## Workflows

### Think Cycle
1. `smol_claw_think` → 2. 페르소나로 판단 → 3. `smol_claw_record_outcome`

### SNS Posting
1. `smol_claw_context` → 2. `smol_claw_memory_query` → 3. 콘텐츠 생성 → 4. 플랫폼별 post 도구

### News Research
1. `smol_claw_search_news` → 2. 인사이트 분석 → 3. 팀에 리포트

### Team Coordination (Discord)
1. 팀장이 #team-room에서 @서브봇 멘션으로 지시
2. 서브봇이 작업 후 #team-room에 결과 보고
3. 필요시 서브봇끼리 @멘션으로 협업

## Setup

### 환경변수
```
# SNS API
X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
THREADS_USER_ID, THREADS_ACCESS_TOKEN
LINKEDIN_ACCESS_TOKEN
INSTAGRAM_USER_ID, INSTAGRAM_ACCESS_TOKEN
NEWS_X_BEARER_TOKEN

# Discord Bot Tokens (5개)
DISCORD_LEAD_TOKEN, DISCORD_THREADS_TOKEN, DISCORD_LINKEDIN_TOKEN
DISCORD_INSTAGRAM_TOKEN, DISCORD_NEWS_TOKEN

# Discord Channel IDs (6개)
DISCORD_TEAM_CHANNEL_ID
DISCORD_LEAD_CHANNEL_ID, DISCORD_THREADS_CHANNEL_ID
DISCORD_LINKEDIN_CHANNEL_ID, DISCORD_INSTAGRAM_CHANNEL_ID
DISCORD_NEWS_CHANNEL_ID
```

### 실행
```bash
# 5봇 동시 실행
python -c "import asyncio; from src.adapters.discord.launcher import launch_all_bots; asyncio.run(launch_all_bots())"
```
