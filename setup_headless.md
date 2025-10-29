# Headless 모드 설정 (서버용)

Oracle Cloud나 다른 서버에서 실행하려면 Chrome을 headless 모드로 설정해야 합니다.

## 🔧 main.py 수정

`setup_chrome_driver()` 함수를 다음과 같이 수정하세요:

### 기존 코드 위치
약 470번 줄 근처의 `setup_chrome_driver()` 함수 찾기

### 수정 내용

**Before:**
```python
def setup_chrome_driver():
    options = Options()

    # 프로필 사용 설정
    if Config.USE_PROFILE:
        # ... 프로필 설정 ...
    
    # Chrome 옵션 (봇 감지 우회)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
```

**After:**
```python
def setup_chrome_driver():
    options = Options()

    # 프로필 사용 설정
    if Config.USE_PROFILE:
        # ... 프로필 설정 ...
    
    # Headless 모드 (서버용) - 추가 ✅
    import platform
    if platform.system() == 'Linux':
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        Logger.debug("Headless 모드로 실행 (Linux)")
    
    # Chrome 옵션 (봇 감지 우회)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Windows에서만 maximized (Linux에서는 headless)
    if platform.system() != 'Linux':
        options.add_argument("--start-maximized")
```

---

## 🚀 자동 감지 방식 (추천)

더 나은 방법: Config에 설정 추가

### 1. Config 클래스에 추가
```python
class Config:
    # ... 기존 설정 ...
    
    # 서버 모드 설정
    HEADLESS_MODE = False  # 로컬: False, 서버: True로 변경
```

### 2. setup_chrome_driver() 수정
```python
def setup_chrome_driver():
    options = Options()

    # Headless 모드 (Config 기반)
    if Config.HEADLESS_MODE:
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        Logger.debug("Headless 모드로 실행")
    else:
        options.add_argument("--start-maximized")
        Logger.debug("일반 모드로 실행")
    
    # ... 나머지 코드 동일 ...
```

---

## 📝 서버에서 직접 수정하기

### 방법 1: nano 에디터 사용
```bash
cd ~/naver_cafe_crawler
nano main.py
```

- `Ctrl+W` → "setup_chrome_driver" 검색
- 위의 코드 추가
- `Ctrl+X` → `Y` → `Enter` (저장)

### 방법 2: 로컬 수정 후 push
```bash
# 로컬 PC에서
git add main.py
git commit -m "Add headless mode for server"
git push

# 서버에서
git pull
```

---

## ✅ 테스트

서버에서 실행:
```bash
cd ~/naver_cafe_crawler
source venv/bin/activate

# Headless 모드 테스트
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
python main.py
```

성공하면:
- 화면은 안 보이지만 정상 작동
- DB 파일 생성됨
- 로그 정상 출력

---

## 🎯 최종 확인

1. ✅ Headless 모드 설정 완료
2. ✅ 수동 실행 성공
3. ✅ DB 생성 확인
4. ✅ 텔레그램 알림 테스트
5. ✅ Cron 스케줄 등록

→ 이제 24/7 자동으로 작동합니다! 🎉

