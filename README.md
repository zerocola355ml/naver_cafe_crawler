# 네이버 카페 게시글 스크래퍼

네이버 카페 게시판에서 게시글 정보를 자동으로 수집하는 도구입니다.

## 기능

### 기본 기능
- ✅ 다중 페이지 자동 스크래핑 (page=1, 2, 3...)
- ✅ 날짜 기반 자동 중단 (최근 N일 게시글만 수집)
- ✅ 게시글 제목, ID, 댓글 수, 조회수, 좋아요 수, 작성일 수집
- ✅ 공지사항/추천글 자동 필터링
- ✅ SQLite 데이터베이스에 누적 저장
- ✅ 중복 데이터 자동 처리 (업데이트 또는 새로 추가)

### 인기글 필터링
- ✅ 조건 기반 인기글 자동 감지 (좋아요 + 조회수 + 댓글)
- ✅ 키워드 기반 인기글 필터링
- ✅ 별도 테이블로 관리 (알림용)

### 알림 기능
- ✅ 텔레그램 봇 알림
- ✅ 키워드 인기글 자동 알림
- ✅ 중복 알림 방지

## 설치

```bash
# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.\venv\Scripts\activate.bat

# 3. 필요한 패키지 설치
pip install selenium requests
```

## 사용 방법

### 1. 기본 스크래핑

```bash
# 가상환경 활성화 후
python main.py
```

### 2. 데이터베이스 확인

```bash
python view_db.py                      # 전체 게시글
python view_hot_articles.py            # 인기글만
python view_keyword_articles.py        # 키워드 인기글만
```

### 3. 텔레그램 알림 (선택)

```bash
# 1. 텔레그램 봇 설정 (최초 1회)
# TELEGRAM_SETUP.md 파일 참고

# 2. 알림 발송
python send_notifications.py
```

## 설정 (`main.py`의 `Config` 클래스)

```python
# URL 설정
DEFAULT_URL = "https://cafe.naver.com/f-e/cafes/10094499/menus/599?viewType=L&page=1"

# 로깅 설정
LOG_LEVEL = Logger.INFO  # VERBOSE(상세), INFO(보통), QUIET(최소)

# 게시글 필터 설정
SKIP_NOTICE = True      # 공지사항 제외
SKIP_RECOMMEND = True   # 추천글 제외

# 브라우저 설정
USE_PROFILE = False     # Chrome 프로필 사용 여부

# 데이터베이스 설정
DB_FILE = "naver_cafe_articles.db"
RETENTION_DAYS = 15     # 데이터 보관 기간 (일)

# 스크래핑 범위
SCRAPE_DAYS = 7         # 최근 7일간의 게시글만 수집
MAX_PAGES = 50          # 최대 페이지 수

# 인기글 기준 (AND 조건)
HOT_ARTICLE_MIN_LIKE = 10       # 좋아요 10개 이상
HOT_ARTICLE_MIN_READ = 100      # 조회수 100회 이상
HOT_ARTICLE_MIN_COMMENT = 5     # 댓글 5개 이상

# 키워드 필터
KEYWORDS = ['기저귀', '유산균', '바이오가이아', '물티슈']

# 텔레그램 알림 (선택)
TELEGRAM_ENABLED = False  # True로 변경 후 아래 설정
TELEGRAM_BOT_TOKEN = ""   # 봇 토큰
TELEGRAM_CHAT_ID = ""     # Chat ID
```

## 수집되는 데이터

- **게시글 ID**: 고유 식별자
- **제목**: 게시글 제목
- **댓글 수**: 댓글 개수
- **작성일**: 게시 날짜/시간
- **조회수**: 게시글 조회 수
- **좋아요 수**: 좋아요 개수
- **URL**: 게시글 링크

## 주의사항

- 네이버 카페에 로그인된 상태여야 접근 가능한 게시판을 스크래핑할 수 있습니다
- 과도한 요청으로 인한 IP 차단을 주의하세요
- 스크래핑은 해당 카페의 이용 규칙을 준수해야 합니다

## 데이터베이스 구조

### 테이블
1. **articles** - 모든 게시글 저장
2. **hot_articles** - 인기글 (조건 만족)
3. **keyword_articles** - 키워드 인기글 (인기글 + 키워드)

### 관계
```
전체 게시글 (articles)
    ↓ (좋아요 10+ AND 조회 100+ AND 댓글 5+)
인기글 (hot_articles)
    ↓ (키워드 포함)
키워드 인기글 (keyword_articles) ← 텔레그램 알림 대상
```

## 프로젝트 구조

```
naver_cafe_scrapper/
├── main.py                    # 메인 스크래퍼
├── send_notifications.py      # 텔레그램 알림 발송
├── view_db.py                 # 전체 DB 조회
├── view_hot_articles.py       # 인기글 조회
├── view_keyword_articles.py   # 키워드 인기글 조회
├── TELEGRAM_SETUP.md          # 텔레그램 설정 가이드
├── README.md                  # 프로젝트 설명
└── .gitignore                 # Git 제외 파일
```

## 텔레그램 알림 설정

자세한 설정 방법은 `TELEGRAM_SETUP.md` 파일을 참고하세요.

간단 요약:
1. @BotFather에서 봇 생성 → 토큰 받기
2. 봇과 대화 시작 → Chat ID 얻기
3. `main.py`의 Config 설정
4. `python send_notifications.py` 실행

