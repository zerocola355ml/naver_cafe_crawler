# 네이버 카페 게시글 스크래퍼

네이버 카페 게시판에서 게시글 정보를 자동으로 수집하는 도구입니다.

## 기능

- ✅ 게시글 제목, ID, 댓글 수, 조회수, 좋아요 수, 작성일 수집
- ✅ 공지사항/추천글 자동 필터링
- ✅ SQLite 데이터베이스에 누적 저장
- ✅ 중복 데이터 자동 처리 (업데이트 또는 새로 추가)
- ✅ 텍스트 파일로도 저장
- ✅ 설정 가능한 데이터 보관 기간 (기본값: 15일)

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
pip install selenium
```

## 사용 방법

### 1. 스크래퍼 실행

```bash
# 가상환경 활성화 후
python main.py
```

### 2. 데이터베이스 확인

```bash
python view_db.py
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

## 프로젝트 구조

```
naver_cafe_scrapper/
├── main.py              # 메인 스크래퍼 프로그램
├── view_db.py           # 데이터베이스 조회 도구
├── README.md            # 프로젝트 설명
└── .gitignore           # Git 제외 파일 목록
```

