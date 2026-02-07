# 🦞 Smol Claw 🦞 (작은 가재봇)

<div align="center">
  <img src=".github/crayfish.svg" alt="귀여운 가재" width="400"/>

  ### *나의 작고 귀여운 자율 AI 비서* 🦞

  **AI가 스스로 생각하고 먼저 연락하는 자율 AI 서버**

  *마치 코드를 지켜주는 작은 가재가 있는 것처럼!* 🦞
</div>

---

[English Documentation](./README.md)

## 특징

- **While(true) 서버** - 계속 실행
- **자율 판단** - AI가 스스로 생각
- **먼저 연락** - 명령 없이도 알림
- **컨텍스트 기반** - Git, TODO, 시간 등 분석
- **스마트 메모리** 🧠 - 과거 결정 기억 및 중복 방지
- **보안 우선** 🛡️ - 가드레일 위반 추적 및 안전 패턴 학습
- **비밀 정보 보호** 🔒 - API 키, 비밀번호, .env 파일 커밋 방지
- **기본적으로 안전** - pre-commit hook과 CI 체크로 민감 데이터 보호
- **의존성 제로** - 간단한 JSON 기반 메모리 (외부 DB 불필요)

## 빠른 시작

### 1. 설치

```bash
cd ~/Documents/ai-assistant
pip install -r requirements.txt
```

### 2. 실행

```bash
python autonomous-ai-server.py
```

### 3. 확인

- 웹: http://localhost:3000
- API: `curl http://localhost:3000/status`

## 사용법

### 수동 질문

```bash
curl -X POST http://localhost:3000/ask \
  -H "Content-Type: application/json" \
  -d '{"message":"안녕"}'
```

### 수동 사고 트리거

```bash
curl http://localhost:3000/think
```

### 상태 확인

```bash
curl http://localhost:3000/status
```

## 자율 동작 예시

### 시나리오 1: Git 변경사항 감지

```
[10:30] AI 사고 중...
컨텍스트: Git 변경사항 5개 발견
AI 판단: "커밋하지 않은 파일이 있습니다"

알림:
━━━━━━━━━━━━━━━━━━━
안녕하세요!

지금 Git에 커밋하지 않은
변경사항이 5개 있어요.
혹시 커밋하시겠어요?
━━━━━━━━━━━━━━━━━━━
```

### 시나리오 2: 시간 기반 리마인드

```
[14:00] AI 사고 중...
컨텍스트: 점심 시간 이후
AI 판단: "오후 작업 시작 제안"

알림:
━━━━━━━━━━━━━━━━━━━
점심 드셨나요?

할 일 목록에 3개 작업이
남아있어요. 시작해볼까요?
━━━━━━━━━━━━━━━━━━━
```

## 설정

`autonomous-ai-server.py` 파일의 `CONFIG` 객체 수정:

```python
CONFIG = {
    "port": 3000,                    # 포트 번호
    "check_interval": 30 * 60,       # 30분 (초 단위)
    "autonomous_mode": True          # 자율 모드 on/off
}
```

## 비밀 정보 보호 🛡️

Smol Claw는 실수로 민감한 정보를 커밋하는 것을 방지합니다!

### 보호 대상

자동으로 감지하고 차단:
- 🔑 API 키 (OpenAI, Anthropic, AWS 등)
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

### 예시: 차단된 커밋

```bash
$ git commit -m "설정 추가"
🦞 민감한 정보 확인 중...

======================================================================
🛡️  보안 경고: 민감한 정보가 감지되었습니다! 🛡️
======================================================================

❌ API Key 감지!
   파일: config.py:5
   라인: api_key=[삭제됨]

❌ 금지된 파일!
   파일: .env

======================================================================
🦞 Smol Claw가 민감한 데이터 커밋을 방지했습니다!

해결 방법:
  1. 파일에서 민감한 정보 제거
  2. 환경 변수 사용: os.getenv('API_KEY')
  3. .gitignore에 민감한 파일 추가
  4. GUARDRAILS.md에 보호 규칙 업데이트
======================================================================

# 커밋이 차단되었습니다! ✅
```

### 모범 사례

**✅ 좋음: 환경 변수 사용**
```python
import os

# .env에 저장 (.gitignore에 추가!)
api_key = os.getenv("OPENAI_API_KEY")
webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
```

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**❌ 나쁨: 비밀 하드코딩**
```python
# 절대 이렇게 하지 마세요! ❌
api_key = "sk-1234567890abcdef"
password = "mypassword123"
```

### 가드레일

`GUARDRAILS.md`에서 확인하세요:
- 완전한 보호 규칙
- 사용자 정의 가드레일 설정
- 테스트 및 우회 옵션
- 보안 모범 사례

🦞 **Smol Claw와 함께 비밀을 안전하게!** 🛡️

## API 엔드포인트

| 메소드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 웹 대시보드 |
| GET | `/status` | 서버 상태 |
| GET | `/think` | 수동 사고 트리거 |
| POST | `/ask` | 수동 질문 |

## 맥북 재부팅 시 자동 시작

### launchd 사용 (macOS)

1. plist 파일 생성:

```bash
cat > ~/Library/LaunchAgents/com.smolclaw.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.smolclaw</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/jeon/Documents/ai-assistant/autonomous-ai-server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
```

2. 등록:

```bash
launchctl load ~/Library/LaunchAgents/com.smolclaw.plist
```

3. 상태 확인:

```bash
launchctl list | grep smolclaw
```

## 메모리 관리 🧠

Smol Claw는 24/7 운영을 위해 자동으로 메모리를 관리합니다:

### 작동 방식

```
memory/
├── decisions.json              # 최근 100개 결정
├── summary.txt                 # 자동 생성 요약
└── guardrail_violations.json   # 보안 추적 🛡️
```

### 기능

**1. 단기 메모리 (최근 100개 결정)**
- 타임스탬프와 함께 최근 결정 저장
- 제한 초과시 자동으로 오래된 결정 요약
- AI에게 컨텍스트 제공하여 더 나은 결정 지원

**2. 중복 감지**
- 24시간 내 동일 알림 방지
- 단어 기반 유사도 매칭 사용
- 반복되는 성가신 알림 방지!

**3. 가드레일 추적 🛡️** (킬러 피처!)
- 보안 위반 기록
- 안전 패턴 학습
- 자주 시도되는 위험한 작업에 대해 경고

### 메모리 컨텍스트 예시

```json
{
  "id": "a3f7b2c1",
  "timestamp": "2026-02-07T15:30:00",
  "action": "notify",
  "message": "커밋하지 않은 변경사항이 5개 있습니다",
  "reasoning": "Git 변경사항 감지, 커밋 제안"
}
```

### 메모리 통계

AI는 다음을 확인합니다:
- 과거 활동 요약
- 최근 10개 결정
- 보안 위반 패턴
- 자주 차단된 대상

**결과**: 토큰 낭비 없이 스마트하고 컨텍스트를 인지하는 결정! 🦞

## Discord 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. Bot 설정에서 **Message Content Intent** 활성화
3. `Send Messages` 권한으로 봇을 서버에 초대
4. `.env` 파일 생성:

```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
```

5. 채널 ID 확인: Discord 설정 > 고급 > 개발자 모드 > 채널 우클릭 > 채널 ID 복사

## 확장

### Discord 연동 (내장) 🦞

환경 변수로 Discord webhook URL을 설정하세요:

```bash
# Discord에서 webhook 생성:
# 서버 설정 → 연동 → 웹후크 → 새 웹후크

export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
python autonomous-ai-server.py
```

또는 셸 프로필에 추가 (~/.zshrc 또는 ~/.bashrc):

```bash
echo 'export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"' >> ~/.zshrc
source ~/.zshrc
```

## 참고사항

- Claude Pro 구독 또는 API 키 필요
- 맥북이 켜져 있어야 작동 (또는 서버 배포로 24/7 가능)
- Claude Code CLI 설치 필요

## 라이선스

MIT

## 기여

기여를 환영합니다! 자유롭게:
- 버그 리포트
- 기능 제안
- 풀 리퀘스트 제출

---

인간과 Claude Code가 함께 만들었습니다
