# 🦞 Smol Marketing Claw 🦞 (작은 마케팅 가재봇)

<div align="center">
  <img src=".github/crayfish.svg" alt="귀여운 가재" width="400"/>

  ### *나의 작고 귀여운 AI 마케팅 비서* 🦞

  **AI 기반 SNS 마케팅 플러그인 — 글 작성, 댓글, 알림을 자동으로.**

  *마치 소셜 미디어를 관리해주는 작은 가재가 있는 것처럼!* 🦞
</div>

---

[English Documentation](./README.md)

## 특징

- **X (Twitter) 연동** - 트윗 작성 및 대화에 답글
- **Threads (Meta) 연동** - 게시글 작성 및 답글
- **Discord 알림** - 실시간 마케팅 알림
- **스마트 메모리** 🧠 - 과거 작업 기억 및 중복 게시 방지
- **비밀 정보 보호** 🔒 - API 키, 토큰, 자격증명 유출 방지
- **기본적으로 안전** - pre-commit hook과 CI 체크로 민감 데이터 보호
- **Claude AI 기반** - Anthropic Claude를 통한 지능적 콘텐츠 판단
- **의존성 제로** - 간단한 JSON 기반 메모리 (외부 DB 불필요)

## 빠른 시작

### 1. 환경 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# X (Twitter) API 키 — X 연동에 필요
X_CONSUMER_KEY=your_consumer_key
X_CONSUMER_SECRET=your_consumer_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret

# Threads (Meta) API — Threads 연동에 필요
THREADS_USER_ID=your_threads_user_id
THREADS_ACCESS_TOKEN=your_threads_access_token

# Discord (선택 — 알림용)
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 2. 설치

```bash
git clone https://github.com/suojae/smol-claw.git
cd smol-claw
pip install -r requirements.txt
```

### 3. 실행

```bash
python autonomous-ai-server.py
```

### 4. 확인

- 웹: http://localhost:3000
- API: `curl http://localhost:3000/status`

## 사용 예시

### 트윗 작성

```bash
curl -X POST http://localhost:3000/sns/x/post \
  -H "Content-Type: application/json" \
  -d '{"text": "Smol Marketing Claw에서 인사드려요! 🦞"}'
```

### 트윗에 답글

```bash
curl -X POST http://localhost:3000/sns/x/reply \
  -H "Content-Type: application/json" \
  -d '{"text": "피드백 감사합니다!", "post_id": "1234567890"}'
```

### Threads에 게시

```bash
curl -X POST http://localhost:3000/sns/threads/post \
  -H "Content-Type: application/json" \
  -d '{"text": "신제품 출시 예정! 🦞"}'
```

### Threads에 답글

```bash
curl -X POST http://localhost:3000/sns/threads/reply \
  -H "Content-Type: application/json" \
  -d '{"text": "좋은 질문이에요 — 프로필 링크를 확인해주세요!", "post_id": "9876543210"}'
```

### 서버 상태 확인

```bash
curl http://localhost:3000/status
```

### Claude에게 질문

```bash
curl -X POST http://localhost:3000/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "새 기능에 대한 트윗 초안 작성해줘"}'
```

## 마케팅 시나리오

### 시나리오 1: 제품 출시 트윗

```bash
# X에 공지 게시
curl -X POST http://localhost:3000/sns/x/post \
  -d '{"text": "새로운 대시보드를 출시했습니다! example.com에서 확인하세요 🚀"}' \
  -H "Content-Type: application/json"

# Threads에 교차 게시
curl -X POST http://localhost:3000/sns/threads/post \
  -d '{"text": "새로운 대시보드를 출시했습니다! example.com에서 확인하세요 🚀"}' \
  -H "Content-Type: application/json"
```

### 시나리오 2: 커뮤니티 소통

```bash
# X에서 고객 피드백에 답글
curl -X POST http://localhost:3000/sns/x/reply \
  -d '{"text": "좋은 말씀 감사합니다! 응원에 감사드려요 🦞", "post_id": "1234567890"}' \
  -H "Content-Type: application/json"
```

## API 엔드포인트

| 메소드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 웹 대시보드 |
| GET | `/status` | 서버 상태 및 사용량 정보 |
| POST | `/ask` | Claude에게 질문 |
| POST | `/sns/x/post` | X (Twitter)에 트윗 작성 |
| POST | `/sns/x/reply` | X에서 트윗에 답글 |
| POST | `/sns/threads/post` | Threads (Meta)에 게시 |
| POST | `/sns/threads/reply` | Threads에서 게시글에 답글 |

### SNS 요청/응답 형식

**게시 요청 본문:**
```json
{ "text": "게시할 내용" }
```

**답글 요청 본문:**
```json
{ "text": "답글 내용", "post_id": "대상_게시글_ID" }
```

**응답:**
```json
{
  "success": true,
  "post_id": "1234567890",
  "text": "게시한 내용"
}
```

**글자 수 제한:**
- X (Twitter): 280자 (자동 잘림)
- Threads (Meta): 500자 (자동 잘림)

## 설정

환경 변수 또는 `src/config.py`의 `CONFIG` 객체 수정:

```python
CONFIG = {
    "port": 3000,                    # 포트 번호
    "check_interval": 30 * 60,       # 30분 (초 단위)
    "autonomous_mode": True          # 자율 모드 on/off
}
```

## 비밀 정보 보호 🛡️

Smol Marketing Claw는 실수로 마케팅 API 자격증명을 유출하는 것을 방지합니다!

### 보호 대상

자동으로 감지하고 차단:
- 🔑 API 키 (X Consumer Key, Threads Access Token 등)
- 🔐 비밀번호와 인증 토큰
- 🔒 개인 키와 인증서
- 💳 데이터베이스 연결 문자열
- 🪝 비밀이 포함된 웹훅 URL
- 📄 .env 파일과 자격증명

### 작동 방식

**1. Pre-commit Hook** (로컬 보호)
```bash
# 훅 설치 (quickstart.sh가 자동으로 수행)
bash scripts/install-hooks.sh

# 이제 git이 매 커밋마다 체크합니다!
git commit -m "기능 추가"
# 🦞 민감한 정보 확인 중...
# ✅ 민감한 정보가 감지되지 않았습니다! 안전하게 커밋 가능. 🦞
```

**2. CI/CD 체크** (원격 보호)
```yaml
# 모든 push/PR에서 자동 실행
- name: 비밀 정보 체크 🛡️
  run: python3 scripts/check-secrets.py --all
```

**3. 수동 체크**
```bash
# staged 파일 체크
python scripts/check-secrets.py

# 모든 추적 파일 체크
python scripts/check-secrets.py --all

# 특정 파일 체크
python scripts/check-secrets.py config.py
```

### 모범 사례

**✅ 좋음: 환경 변수 사용**
```python
import os

# .env에 저장 (.gitignore에 추가!)
x_key = os.getenv("X_CONSUMER_KEY")
threads_token = os.getenv("THREADS_ACCESS_TOKEN")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
```

**❌ 나쁨: 비밀 하드코딩**
```python
# 절대 이렇게 하지 마세요! ❌
x_key = "ck-1234567890abcdef"
threads_token = "IGQ..."
```

### 가드레일

`GUARDRAILS.md`에서 확인하세요:
- 완전한 보호 규칙
- 사용자 정의 가드레일 설정
- 테스트 및 우회 옵션
- 보안 모범 사례

🦞 **Smol Marketing Claw와 함께 API 키를 안전하게!** 🛡️

## Discord 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. Bot 설정에서 **Message Content Intent** 활성화
3. `Send Messages` 권한으로 봇을 서버에 초대
4. `.env` 파일에 자격증명 추가:

```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
```

5. 채널 ID 확인: Discord 설정 > 고급 > 개발자 모드 > 채널 우클릭 > 채널 ID 복사

## 요구사항

- Python 3.9+
- X (Twitter) 개발자 계정 (X 연동용)
- Threads/Meta 개발자 계정 (Threads 연동용)
- Discord 봇 (선택, 알림용)
- Claude Pro 구독 또는 API 키 (AI 기능용)

## 라이선스

MIT

## 기여

기여를 환영합니다! 자유롭게:
- 버그 리포트
- 기능 제안
- 풀 리퀘스트 제출

가이드라인은 [CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.

---

인간과 Claude Code가 함께 만들었습니다 🦞
