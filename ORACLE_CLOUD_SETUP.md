# Oracle Cloud 무료 VM 설정 가이드

Oracle Cloud 평생 무료 티어를 사용하여 24/7 자동 스크래핑 시스템을 구축합니다.

## ✨ 장점

- ✅ **평생 무료** (Always Free Tier)
- ✅ **24/7 자동 실행** (컴퓨터 꺼도 됨)
- ✅ **안정적인 네트워크**
- ✅ **원격 접속 가능**

---

## 📋 전체 과정 (약 1-2시간)

1. Oracle Cloud 계정 생성 (20분)
2. VM 인스턴스 생성 (10분)
3. 서버 접속 및 환경 설정 (30분)
4. 코드 업로드 및 설정 (20분)
5. 자동 실행 스케줄 설정 (10분)

---

## 1️⃣ Oracle Cloud 계정 생성 (20분)

### 1. 회원가입
1. https://www.oracle.com/kr/cloud/free/ 접속
2. "무료로 시작하기" 클릭
3. 이메일, 국가 선택 (대한민국)
4. 계정 정보 입력
5. **신용카드 등록 필요** (인증용, 요금 청구 안 됨)
   - ⚠️ Always Free 티어만 사용하면 과금 없음

### 2. 계정 활성화
- 이메일 확인
- 로그인 테스트

---

## 2️⃣ VM 인스턴스 생성 (10분)

### 1. 인스턴스 생성
1. 콘솔 로그인
2. 메뉴 → **Compute** → **Instances** 클릭
3. **Create Instance** 버튼

### 2. 설정

**기본 정보:**
- Name: `naver-cafe-scraper`
- Compartment: (기본값 유지)

**Placement:**
- Availability Domain: (기본값)

**Image and Shape:**
- Image: **Canonical Ubuntu 22.04** (또는 최신 버전)
- Shape: **VM.Standard.E2.1.Micro** (Always Free)
  - OCPU: 1
  - Memory: 1GB
  - ⚠️ 반드시 "Always Free eligible" 표시 확인!

**Networking:**
- VCN: (기본값 또는 새로 생성)
- Subnet: Public Subnet
- **Assign a public IPv4 address** 체크 ✅

**SSH Keys:**
- **Generate SSH key pair** 선택
- **Save Private Key** 클릭 → 다운로드 (중요! 분실하면 접속 불가)
- **Save Public Key** 클릭 → 다운로드

**Boot Volume:**
- 기본값 (50GB)

### 3. 생성 완료
- **Create** 버튼 클릭
- 1-2분 대기 → 상태가 "Running"으로 변경

### 4. Public IP 확인
- Instance Details 페이지에서 **Public IP address** 복사
- 예: `123.456.789.012`

---

## 3️⃣ 서버 접속 (Windows PowerShell)

### 1. SSH 키 권한 설정 (Windows)
```powershell
# 다운로드한 private key를 프로젝트 폴더로 이동
Move-Item ~/Downloads/ssh-key-*.key C:\Users\tlsgj\PycharmProjects\naver_cafe_scrapper\oracle-key.key

# 권한 설정 (읽기 전용)
icacls C:\Users\tlsgj\PycharmProjects\naver_cafe_scrapper\oracle-key.key /inheritance:r
icacls C:\Users\tlsgj\PycharmProjects\naver_cafe_scrapper\oracle-key.key /grant:r "$($env:USERNAME):(R)"
```

### 2. SSH 접속
```bash
ssh -i oracle-key.key ubuntu@123.456.789.012
```
(Public IP를 실제 IP로 교체)

**처음 접속 시:**
```
Are you sure you want to continue connecting (yes/no)? 
→ yes 입력
```

---

## 4️⃣ 서버 환경 설정 (30분)

서버에 접속한 상태에서:

### 1. 시스템 업데이트
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Python 설치 확인
```bash
python3 --version  # Python 3.10+ 확인
```

### 3. Chrome 및 ChromeDriver 설치
```bash
# Chrome 설치
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
google-chrome --version

# ChromeDriver 자동 설치를 위한 패키지
sudo apt install -y python3-pip python3-venv
```

### 4. 가상 디스플레이 설치 (headless 실행용)
```bash
sudo apt install -y xvfb
```

### 5. Git 설치
```bash
sudo apt install -y git
```

---

## 5️⃣ 코드 업로드 및 설정 (20분)

### 1. 코드 다운로드
```bash
cd ~
git clone https://github.com/zerocola355ml/naver_cafe_crawler.git
cd naver_cafe_crawler
```

### 2. 가상환경 생성
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install selenium requests
```

### 4. config_secret.py 생성
```bash
nano config_secret.py
```

내용 입력:
```python
# 텔레그램 설정
TELEGRAM_BOT_TOKEN = "8468153847:AAF5omyTYxB0L9YLdVaL_ByM6wEBcyIe4l0"
TELEGRAM_CHAT_ID = "779885713"
```

저장: `Ctrl+X` → `Y` → `Enter`

### 5. Headless Chrome 실행 스크립트 생성

`run_scraper.sh` 생성:
```bash
nano run_scraper.sh
```

내용:
```bash
#!/bin/bash
cd /home/ubuntu/naver_cafe_crawler
source venv/bin/activate

# Headless 모드로 실행 (가상 디스플레이)
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
XVFB_PID=$!

# 스크래핑 실행
python main.py

# 알림 발송 (5분 후)
sleep 300
python send_notifications.py

# 가상 디스플레이 종료
kill $XVFB_PID
```

실행 권한 부여:
```bash
chmod +x run_scraper.sh
```

### 6. main.py 수정 (Headless 모드)

서버에서 `main.py` 편집:
```bash
nano main.py
```

`setup_chrome_driver()` 함수에서 headless 옵션 추가:
```python
def setup_chrome_driver():
    options = Options()
    
    # Headless 모드 추가 (서버용) ✅
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 기존 옵션들...
    options.add_argument("--disable-blink-features=AutomationControlled")
    ...
```

---

## 6️⃣ 자동 실행 스케줄 설정 (10분)

### 1. Cron 편집
```bash
crontab -e
```

처음이면 에디터 선택: `1` (nano)

### 2. 스케줄 추가
```bash
# 한국 시간 기준 (서버는 UTC이므로 -9시간)
# 한국 10:00 = UTC 01:00
# 한국 15:00 = UTC 06:00
# 한국 20:00 = UTC 11:00

0 1,6,11 * * * /home/ubuntu/naver_cafe_crawler/run_scraper.sh >> /home/ubuntu/scraper.log 2>&1
```

저장: `Ctrl+X` → `Y` → `Enter`

### 3. Cron 서비스 확인
```bash
sudo systemctl status cron
```

### 4. 로그 확인 위치
```bash
tail -f ~/scraper.log  # 실시간 로그 확인
```

---

## 7️⃣ 테스트 (10분)

### 1. 수동 실행 테스트
```bash
cd ~/naver_cafe_crawler
./run_scraper.sh
```

### 2. 로그 확인
```bash
cat ~/scraper.log
```

### 3. DB 확인
```bash
source venv/bin/activate
python view_keyword_articles.py --pending
```

---

## 🔧 문제 해결

### Chrome이 실행 안 됨
```bash
# Chrome 재설치
sudo apt remove google-chrome-stable
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```

### Xvfb 오류
```bash
sudo apt install -y xvfb
ps aux | grep Xvfb  # 실행 중인지 확인
```

### Cron이 실행 안 됨
```bash
# Cron 로그 확인
grep CRON /var/log/syslog

# 스크립트 권한 확인
chmod +x ~/naver_cafe_crawler/run_scraper.sh
```

### 방화벽 (필요시)
Oracle Cloud Console에서:
1. Instance Details → Subnet 클릭
2. Security Lists → Default Security List
3. Ingress Rules → Add (필요시)

---

## 📱 원격 관리

### 1. SSH로 접속
```bash
ssh -i oracle-key.key ubuntu@YOUR_PUBLIC_IP
```

### 2. DB 다운로드 (로컬로)
```bash
# 로컬 PC에서 실행
scp -i oracle-key.key ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/naver_cafe_crawler/naver_cafe_articles.db .
```

### 3. 로그 확인
```bash
ssh -i oracle-key.key ubuntu@YOUR_PUBLIC_IP "tail -100 ~/scraper.log"
```

### 4. 코드 업데이트
```bash
# 서버에서
cd ~/naver_cafe_crawler
git pull
```

---

## 💰 비용 (평생 무료)

**Always Free 리소스:**
- ✅ VM.Standard.E2.1.Micro: 2개까지
- ✅ Block Volume: 200GB
- ✅ 네트워크: 10TB/월

**주의:**
- Upgrade to paid account 하지 않기
- Always Free 마크 있는 것만 사용

---

## 🎯 최종 체크리스트

### Oracle Cloud
- [ ] 계정 생성 완료
- [ ] VM 인스턴스 생성 (E2.1.Micro)
- [ ] Public IP 확인
- [ ] SSH 키 다운로드

### 서버 설정
- [ ] SSH 접속 성공
- [ ] Python, Chrome, Xvfb 설치
- [ ] Git clone 완료
- [ ] config_secret.py 생성
- [ ] run_scraper.sh 생성 및 권한 부여
- [ ] main.py headless 모드 수정

### 자동 실행
- [ ] Cron 스케줄 등록
- [ ] 수동 테스트 성공
- [ ] 로그 확인

### 텔레그램
- [ ] 알림 테스트 성공

---

## 🚨 주의사항

### 1. SSH 키 관리
- Private Key 절대 공유 금지
- 백업 필수

### 2. 로그인 문제
- 서버에서는 Chrome 프로필 사용 불가
- `USE_PROFILE = False` 유지
- 로그인 필요한 카페는 제한적

### 3. 메모리 관리
- 1GB RAM이므로 너무 많은 페이지 스크래핑 주의
- `MAX_PAGES = 20` 정도 권장

---

## 💡 다음 단계

설정 완료 후:
1. 첫 실행 수동 테스트
2. Cron 로그 확인 (다음날)
3. 텔레그램 알림 확인
4. 안정화 확인 (1주일)

---

## 📞 도움이 필요하면

- Oracle Cloud 공식 문서: https://docs.oracle.com/
- 커뮤니티: https://community.oracle.com/
- 또는 각 단계별로 질문하세요!

---

## 🔄 대안: 로컬 PC + 작업 스케줄러

Oracle Cloud가 복잡하다면:
- Windows 작업 스케줄러 (10분 설정)
- 컴퓨터 절전 모드 + 깨우기 설정
- 전기료: 월 5,000~10,000원

