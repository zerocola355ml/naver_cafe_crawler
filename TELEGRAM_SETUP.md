# 텔레그램 알림 설정 가이드

## 📱 1단계: 텔레그램 봇 생성 (5분)

### 1. BotFather와 대화 시작
1. 텔레그램 앱에서 `@BotFather` 검색
2. 대화 시작 버튼 클릭

### 2. 봇 생성
```
/newbot
```
- 봇 이름 입력 (예: `Naver Cafe Notifier`)
- 봇 사용자명 입력 (예: `naver_cafe_bot`) - 반드시 `bot`으로 끝나야 함

### 3. 토큰 저장
```
✅ 성공 메시지와 함께 토큰이 표시됩니다:
Use this token to access the HTTP API:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz...

⚠️ 이 토큰을 안전하게 보관하세요!
```

---

## 🆔 2단계: Chat ID 얻기 (2분)

### 1. 봇과 대화 시작
1. BotFather가 준 링크로 봇 접속
2. `/start` 메시지 보내기

### 2. Chat ID 확인
브라우저에서 다음 URL 접속:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

결과에서 `"chat":{"id":` 뒤의 숫자를 찾으세요:
```json
{
  "ok": true,
  "result": [{
    "message": {
      "chat": {
        "id": 1234567890,  ← 이 숫자가 Chat ID
        ...
      }
    }
  }]
}
```

---

## ⚙️ 3단계: Config 설정

`main.py`의 `Config` 클래스에서 다음을 수정:

```python
# 텔레그램 알림 설정
TELEGRAM_ENABLED = True  # False → True로 변경
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz..."  # 봇 토큰 입력
TELEGRAM_CHAT_ID = "1234567890"  # Chat ID 입력
```

---

## 🧪 4단계: 테스트

### 테스트 1: 설정 확인
```bash
python send_notifications.py
```

설정이 올바르면 알림 대기 중인 글이 표시됩니다.

### 테스트 2: 직접 메시지 보내기 (선택)
```python
# test_telegram.py
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": "🎉 텔레그램 알림 테스트 성공!"
}

response = requests.post(url, data=data)
print(response.json())
```

---

## 🚀 사용 방법

### 1. 스크래핑 + 알림 (권장)
```bash
# 1. 스크래핑 실행
python main.py

# 2. 알림 발송
python send_notifications.py
```

### 2. 알림만 발송
```bash
python send_notifications.py
```

---

## 📊 작동 흐름

```
1. main.py 실행
   └─> 키워드 인기글 발견
   └─> keyword_articles에 저장 (notification_sent = 0)

2. send_notifications.py 실행
   └─> notification_sent = 0인 글 조회
   └─> 텔레그램으로 발송
   └─> notification_sent = 1로 업데이트
```

---

## 🔒 보안 주의사항

### ⚠️ 절대 GitHub에 토큰 올리지 마세요!

**안전한 방법:**

#### 옵션 1: 환경 변수 (추천)
```python
# main.py
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
```

```bash
# Windows에서 설정
setx TELEGRAM_BOT_TOKEN "1234567890:ABC..."
setx TELEGRAM_CHAT_ID "1234567890"
```

#### 옵션 2: 별도 설정 파일 (.gitignore에 추가)
```python
# config_secret.py (Git에서 제외)
TELEGRAM_BOT_TOKEN = "1234567890:ABC..."
TELEGRAM_CHAT_ID = "1234567890"
```

```python
# main.py
try:
    from config_secret import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
```

---

## 🛠️ 문제 해결

### requests 모듈이 없다는 오류
```bash
pip install requests
```

### 알림이 안 옴
1. 봇과 대화를 시작했는지 확인 (`/start`)
2. Chat ID가 정확한지 확인
3. 토큰이 정확한지 확인
4. 방화벽 확인

### Chat ID를 못 찾겠어요
다른 방법:
```
1. @userinfobot에게 메시지 보내기
2. 자신의 Chat ID 확인
```

---

## 💡 고급 기능 (선택)

### 여러 명에게 알림
```python
TELEGRAM_CHAT_IDS = ["1234567890", "9876543210"]  # 리스트로 변경

for chat_id in TELEGRAM_CHAT_IDS:
    send_telegram(message, BOT_TOKEN, chat_id)
```

### 그룹 채팅방에 알림
1. 봇을 그룹에 추가
2. 그룹의 Chat ID 사용 (음수로 시작)

---

## ✅ 체크리스트

- [ ] 텔레그램 봇 생성 완료
- [ ] 봇 토큰 저장
- [ ] 봇과 `/start` 대화
- [ ] Chat ID 확인
- [ ] Config 설정 완료
- [ ] `TELEGRAM_ENABLED = True` 설정
- [ ] `pip install requests` 실행
- [ ] 테스트 실행 성공

