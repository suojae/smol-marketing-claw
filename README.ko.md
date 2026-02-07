# Smol Claw (작은 가재봇)

```
    (\/)
   (o.o)
  />   <\
 /  ___  \
|  /   \  |
 \/     \/
```

> 나의 작고 귀여운 자율 AI 비서

AI가 스스로 생각하고 먼저 연락하는 자율 AI 서버

[English Documentation](./README.md)

## 특징

- **While(true) 서버** - 계속 실행
- **자율 판단** - AI가 스스로 생각
- **먼저 연락** - 명령 없이도 알림
- **컨텍스트 기반** - Git, TODO, 시간 등 분석

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

## 확장

### 텔레그램 연동

```python
# notify_user() 메소드에 추가
from telegram import Bot

bot = Bot(token='YOUR_TOKEN')
await bot.send_message(chat_id='YOUR_CHAT_ID', text=message)
```

### Slack 연동

```python
# notify_user() 메소드에 추가
from slack_sdk.web.async_client import AsyncWebClient

slack = AsyncWebClient(token='YOUR_TOKEN')
await slack.chat_postMessage(
    channel='YOUR_CHANNEL',
    text=message
)
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
