# 🔍 키워드 변경 가이드

네이버 카페 스크래퍼의 알림 키워드를 변경하는 **가장 쉬운 방법**을 설명합니다.

---

## ⭐ 가장 쉬운 방법: keywords.txt 파일 수정

키워드는 `keywords.txt` 파일에서 **한 줄에 하나씩** 관리합니다.

### 📝 현재 키워드 확인
```
기저귀
유산균
바이오가이아
물티슈
```

---

## 🖥️ 로컬 환境에서 변경

### 1. keywords.txt 편집
```bash
# 에디터로 열기
code keywords.txt
```

### 2. 키워드 수정 (한 줄에 하나씩)
```
분유
기저귀
물티슈
유모차
카시트
바이오가이아
```

### 3. Git 커밋 & 푸시
```bash
git add keywords.txt
git commit -m "Update keywords"
git push
```

---

## 🌐 서버에서 변경 (가장 간단!)

### 방법 1: 서버에서 직접 수정 (추천 ⭐)

```bash
# SSH로 서버 접속
ssh -i ssh-key-2025-10-30.key ubuntu@<YOUR_PUBLIC_IP>

# 프로젝트 폴더로 이동
cd ~/naver_cafe_crawler

# keywords.txt 편집
nano keywords.txt

# 키워드 추가/삭제 (한 줄에 하나씩)
# 저장: Ctrl+X → Y → Enter
```

**장점:**
- ✅ main.py 건드릴 필요 없음
- ✅ git pull 필요 없음
- ✅ 바로 적용됨

### 방법 2: Git Pull

로컬에서 변경 후 서버에 반영:

```bash
# SSH로 서버 접속
ssh -i ssh-key-2025-10-30.key ubuntu@<YOUR_PUBLIC_IP>

# 프로젝트 폴더로 이동
cd ~/naver_cafe_crawler

# 최신 코드 가져오기
git pull origin master
```

---

## 💡 키워드 작성 팁

### ✅ 좋은 예
```
분유
기저귀
물티슈
유모차
바이오가이아
페리오
신생아 선물
아기 용품
출산 준비물
```

### ⚠️ 주의사항
```
# 주석도 사용 가능 (#으로 시작하는 줄은 무시됨)

# 너무 일반적인 단어는 피하기
좋아요    # ❌ 너무 많이 매칭됨
추천      # ❌ 너무 많이 매칭됨

# 대소문자 구분 없음 (자동 처리)
iPhone    # OK (iphone, IPHONE 모두 매칭)

# 띄어쓰기 포함 가능
신생아 선물

# 빈 줄은 무시됨
```

---

## 🧪 변경 후 테스트

### 1. 수동 실행으로 확인
```bash
cd ~/naver_cafe_crawler
./run_scraper.sh
```

### 2. 키워드 매칭 확인
```bash
# 데이터베이스에서 키워드 매칭된 글 확인
source venv/bin/activate
python view_keyword_articles.py --pending
```

### 3. 로그 확인
```bash
cat ~/scraper.log
```

---

## 📱 변경 사항 적용

`keywords.txt` 파일을 수정하면 **다음 실행부터** 자동으로 적용됩니다:
- Cron 스케줄에 따라 자동 실행 시
- 수동 실행: `./run_scraper.sh`

### 즉시 확인하고 싶다면
```bash
cd ~/naver_cafe_crawler
./run_scraper.sh
```

---

## ❓ 문제 해결

### 키워드가 매칭되지 않아요
1. 철자 확인 (띄어쓰기 포함)
2. 대소문자는 자동 처리되므로 상관없음
3. 부분 일치로 검색됨 (예: '기저귀' → '신생아기저귀' 매칭됨)

### 변경했는데 반영이 안 돼요
```bash
# 서버에서 keywords.txt 확인
cd ~/naver_cafe_crawler
cat keywords.txt

# 스크립트 다시 실행
./run_scraper.sh
```

### keywords.txt 파일이 없다고 나와요
```bash
# 파일 생성
cd ~/naver_cafe_crawler
nano keywords.txt

# 키워드 입력 (한 줄에 하나씩)
# 저장: Ctrl+X → Y → Enter
```

---

## 🎯 요약

1. **로컬 변경**: `keywords.txt` 수정 → Git 푸시 → 서버에서 `git pull`
2. **서버 변경 (가장 쉬움!)**: SSH 접속 → `nano keywords.txt` → 수정 → 저장
3. **테스트**: `./run_scraper.sh` 실행 후 로그 확인

---

## 📋 예시

**keywords.txt 파일 예시:**
```
# 육아 용품
기저귀
물티슈
분유
젖병

# 브랜드
바이오가이아
페리오
센서티브

# 프로모션
할인
이벤트
무료배송
```

---

**작성일**: 2025-10-30  
**버전**: 1.0

