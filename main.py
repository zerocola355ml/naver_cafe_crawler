import sys
import io

# Windows 콘솔 ?�코???�정 (?��? �??�수문자 출력???�해)
# line_buffering=True�??�정?�여 ?�시�?출력 가??
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import os
import time
import re
import sqlite3
from datetime import datetime, timedelta

# ===================== Logger ?�래??=====================
class Logger:
    """로깅레벨 관리"""
    VERBOSE = 2  # 모든 디버그 정보 출력
    INFO = 1     # 사용자 정보만 출력
    QUIET = 0    # 최소 정보만 출력 (에러/경고)
    
    level = INFO  # 기본 레벨
    
    @staticmethod
    def set_level(level):
        """로깅 레벨 설정"""
        Logger.level = level
    
    @staticmethod
    def debug(msg):
        """디버그 메시지 (VERBOSE 레벨에서만 출력)"""
        if Logger.level >= Logger.VERBOSE:
            print(f"[DEBUG] {msg}")
    
    @staticmethod
    def info(msg):
        """일반 정보 메시지 (INFO 레벨 이상에서 출력)"""
        if Logger.level >= Logger.INFO:
            print(msg)
    
    @staticmethod
    def success(msg):
        """성공 메시지 (INFO 레벨 이상에서 출력)"""
        if Logger.level >= Logger.INFO:
            print(f"✓ {msg}")
    
    @staticmethod
    def warning(msg):
        """경고 메시지 (항상 출력)"""
        print(f"⚠️ {msg}")
    
    @staticmethod
    def error(msg):
        """에러 메시지 (항상 출력)"""
        print(f"❌ {msg}")
    
    @staticmethod
    def separator(char="=", length=60):
        """구분선 (INFO 레벨 이상에서 출력)"""
        if Logger.level >= Logger.INFO:
            print(char * length)

# ===================== 설정 클래스 =====================
class Config:
    """스크래핑 설정을 관리하는 클래스"""
    
    # URL 설정
    DEFAULT_URL = "https://cafe.naver.com/f-e/cafes/10094499/menus/599?viewType=L&page=1"
    
    # 로깅 설정
    LOG_LEVEL = Logger.VERBOSE  # VERBOSE(자세), INFO(보통), QUIET(최소)
    
    # 게시글 필터 설정
    SKIP_NOTICE = True      # 공지 외
    SKIP_RECOMMEND = True   # 추천글 외
    
    # 브라우저 설정
    USE_PROFILE = False     # Chrome 프로필 사용
    CHROME_PROFILE_PATH = "C:\\Users\\tlsgj\\AppData\\Local\\Google\\Chrome\\User Data"
    PROFILE_DIRECTORY = "Default"

    # 페이지 로딩 설정
    PAGE_LOAD_WAIT = 15     # 페이지 로딩 대기 시간 (초)
    ELEMENT_WAIT = 20       # 요소 대기 시간 (초)
    SELECTOR_WAIT = 5       # 선택자 대기 시간 (초)
    
    # 출력 파일 설정
    OUTPUT_FILE = "scraped_articles.txt"
    
    # 데이터베이스 설정
    DB_FILE = "naver_cafe_articles.db"  # SQLite 데이터베이스 파일
    RETENTION_DAYS = 15                  # 보관 기간 (일)
    
    # 스크래핑 범위 설정
    SCRAPE_DAYS = 7         # 최근 며칠 동안의 게시글만 수집 (오늘부터 N일 전까지)
    MAX_PAGES = 50          # 최대 페이지 수 (무한 루프 방지)
    
    # CSS Selector 설정
    SELECTORS = {
        # 게시글 행(tr) 찾기
        'article_rows': [
            "table.article-table > tbody:nth-of-type(3) tr",  # 일반글(3번째 tbody)
            "table.article-table tbody:nth-of-type(3) tr",
            "table.article-table tbody:nth-of-type(n+2) tr",  # 추천글 + 일반글
            "table.article-table tr",  # 전체
        ],
        
        # 게시글 정보 추출
        'article_id': "td.td_normal.type_articleNumber",
        'title': "a.article",
        'comment': "a.cmt",
        'date': "td.td_normal.type_date",
        'read_count': "td.td_normal.type_readCount",
        'like_count': "td.td_normal.type_likeCount",
    }

# ===================== 데이터베이스 함수 =====================

def init_database():
    """
    SQLite 데이터베이스 초기화
    테이블이 존재하면 생성하고, 연결을 반환합니다.
    
    Returns:
        sqlite3.Connection: 데이터베이스 연결
    """
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    # 테이블 생성 (존재하지 않으면 생성)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            article_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            comment_count INTEGER DEFAULT 0,
            date TEXT,
            read_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            url TEXT,
            first_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    Logger.debug(f"데이터베이스 초기화 완료: {Config.DB_FILE}")
    return conn


def cleanup_old_data(conn):
    """
    보관 기간 이전의 데이터를 삭제합니다.
    
    Args:
        conn: SQLite 연결
    
    Returns:
        int: 삭제된 데이터의 개수
    """
    cursor = conn.cursor()
    cutoff_date = datetime.now() - timedelta(days=Config.RETENTION_DAYS)
    
    cursor.execute('''
        DELETE FROM articles 
        WHERE last_updated < ?
    ''', (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),))
    
    deleted_count = cursor.rowcount
    conn.commit()
    
    if deleted_count > 0:
        Logger.info(f"{deleted_count}개의 오래된 게시글 삭제 ({Config.RETENTION_DAYS}일 이상)")
    
    return deleted_count


def save_or_update_article(conn, article):
    """
    게시글을 데이터베이스에 저장하거나 업데이트합니다.
    
    Args:
        conn: SQLite 연결
        article: 게시글 정보 사전
    
    Returns:
        str: 'inserted', 'updated', 또는 'error'
    """
    cursor = conn.cursor()
    
    try:
        # 기존 게시글이 존재하는지 확인
        cursor.execute('SELECT article_id FROM articles WHERE article_id = ?', (article['article_id'],))
        exists = cursor.fetchone()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # 데이터 업데이트
            cursor.execute('''
                UPDATE articles 
                SET title = ?, comment_count = ?, date = ?, 
                    read_count = ?, like_count = ?, url = ?, last_updated = ?
                WHERE article_id = ?
            ''', (
                article['title'], article['comment_count'], article['date'],
                article['read_count'], article['like_count'], article['url'], 
                now, article['article_id']
            ))
            conn.commit()
            return 'updated'
        else:
            # 새 게시글 삽입
            cursor.execute('''
                INSERT INTO articles 
                (article_id, title, comment_count, date, read_count, like_count, url, first_scraped, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['article_id'], article['title'], article['comment_count'],
                article['date'], article['read_count'], article['like_count'],
                article['url'], now, now
            ))
            conn.commit()
            return 'inserted'
    except Exception as e:
        Logger.debug(f"DB 오류 (ID: {article.get('article_id')}): {e}")
        return 'error'


def get_article_stats(conn):
    """
    ?�이?�베?�스 통계 정보를 반환합니다.
    
    Args:
        conn: SQLite 연결
    
    Returns:
        dict: 통계 정보
    """
    cursor = conn.cursor()
    
    # 총 게시글 수
    cursor.execute('SELECT COUNT(*) FROM articles')
    total_count = cursor.fetchone()[0]
    
    # 오늘 업데이트된 게시글 수
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM articles WHERE DATE(last_updated) = ?', (today,))
    today_updated = cursor.fetchone()[0]
    
    # 가???�래??게시글
    cursor.execute('SELECT MIN(first_scraped) FROM articles')
    oldest = cursor.fetchone()[0]
    
    return {
        'total_count': total_count,
        'today_updated': today_updated,
        'oldest_date': oldest
    }


# ===================== 유틸리티 함수 =====================

def parse_article_date(date_str):
    """
    게시글 생성일을 파싱합니다.
    
    Args:
        date_str: 날짜 문자열("09:05" 또는 "2025.10.26.")
    
    Returns:
        datetime: 파싱된 날짜 또는 None
    """
    try:
        date_str = date_str.strip()
        
        # 시간 형식 (오늘 게시글): "09:05"
        if ':' in date_str and '.' not in date_str:
            today = datetime.now()
            time_parts = date_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 날짜 형식: "2025.10.26." 또는 "2025.10.26"
        elif '.' in date_str:
            date_str = date_str.rstrip('.')
            parts = date_str.split('.')
            if len(parts) >= 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return datetime(year, month, day)
        
        return None
    except Exception as e:
        Logger.debug(f"날짜 파싱 오류: {date_str} - {e}")
        return None


def is_article_too_old(date_str, days_limit):
    """
    게시글이 오래되었는지 확인합니다.
    
    Args:
        date_str: 날짜 문자열
        days_limit: 며칠 이전까지 수집할지
    
    Returns:
        bool: True(중단해야 함)
    """
    article_date = parse_article_date(date_str)
    if not article_date:
        return False
    
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    return article_date < cutoff_date


def generate_page_url(base_url, page_number):
    """
    페이지 번호를 사용하여 URL을 생성합니다.
    
    Args:
        base_url: 기본 URL
        page_number: 페이지 번호
    
    Returns:
        str: 페이지 URL
    """
    # URL에서 page= 부분을 찾아 교체
    if 'page=' in base_url:
        # 기존 page= 파라미터 교체
        return re.sub(r'page=\d+', f'page={page_number}', base_url)
    elif '?' in base_url:
        # page 파라미터 추가
        return f"{base_url}&page={page_number}"
    else:
        return f"{base_url}?page={page_number}"


def setup_chrome_driver():
    """
    Chrome WebDriver를 설정하고 반환합니다.
    
    Returns:
        webdriver.Chrome: 설정된 Chrome WebDriver
    """
    options = Options()

    # 프로필 사용 설정
    if Config.USE_PROFILE:
        Logger.debug("프로필 모드 실행")
        profile_path = os.path.join(Config.CHROME_PROFILE_PATH, Config.PROFILE_DIRECTORY)
        if not os.path.isdir(profile_path):
            Logger.error("프로필 경로가 존재하지 않습니다. USE_PROFILE를 False로 설정하세요.")
            return None
        options.add_argument(f"user-data-dir={Config.CHROME_PROFILE_PATH}")
        options.add_argument(f"profile-directory={Config.PROFILE_DIRECTORY}")
    
    # Chrome 옵션 (자동화 제어 비활성화)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    
    try:
        Logger.info("\n브라우저 작업 시작...")
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        Logger.success("브라우저 작업 완료")
        return driver
    except Exception as e:
        Logger.error("WebDriver 실행 실패.")
        Logger.info(f"오류: {e}")
        Logger.info("\n?�결 방법:")
        Logger.info("1. Chrome 브라우저가 설치되어 있는지 확인")
        Logger.info("2. ChromeDriver가 자동으로 설치되어 있는지 확인")
        return None


def extract_article_data(row):
    """
    tr)에서 게시글 정보를 추출합니다.
    
    Args:
        row: Selenium WebElement (tr 그래)
    
    Returns:
        dict: 게시글 정보 사전 또는 None (추출 실패)
    """
    article_data = {
        'article_id': '',
        'title': '',
        'comment_count': 0,
        'date': '',
        'read_count': 0,
        'like_count': 0,
        'url': ''
    }
    
    try:
        # 게시글 ID 추출 (td에서 직접)
        try:
            article_id_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['article_id'])
            article_data['article_id'] = article_id_elem.text.strip()
        except:
            pass
        
        # 제목 추출 (필수)
        try:
            title_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['title'])
            article_data['title'] = title_link.text.strip()
            article_data['url'] = title_link.get_attribute('href')
            
            # ID가 없으면 URL에서 추출
            if not article_data['article_id']:
                url = article_data['url']
                if 'articleid=' in url.lower():
                    article_data['article_id'] = url.split('articleid=')[1].split('&')[0]
                elif '/articles/' in url:
                    article_data['article_id'] = url.split('/articles/')[1].split('?')[0]
        except Exception as e:
            Logger.debug(f"제목 추출 실패: {e}")
            return None
        
        # 댓글 수 추출
        try:
            comment_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['comment'])
            comment_text = comment_link.text.strip()
            numbers = re.findall(r'\d+', comment_text)
            if numbers:
                article_data['comment_count'] = int(numbers[0])
        except:
            article_data['comment_count'] = 0
        
        # 생성일 추출
        try:
            date_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['date'])
            article_data['date'] = date_elem.text.strip()
        except:
            article_data['date'] = ''
        
        # 조회수 추출
        try:
            read_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['read_count'])
            read_count_text = read_count_elem.text.strip()
            numbers = re.findall(r'\d+', read_count_text.replace(',', ''))
            if numbers:
                article_data['read_count'] = int(numbers[0])
        except:
            article_data['read_count'] = 0
        
        # 좋아요 수 추출
        try:
            like_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['like_count'])
            like_count_text = like_count_elem.text.strip()
            numbers = re.findall(r'\d+', like_count_text.replace(',', ''))
            if numbers:
                article_data['like_count'] = int(numbers[0])
        except:
            article_data['like_count'] = 0
        
        return article_data
        
    except Exception as e:
        Logger.debug(f"게시글 정보 추출 오류: {e}")
        return None


def should_skip_article(row, driver, skip_notice=True, skip_recommend=True):
    """
    게시글 공지 항목 외는 추천글 외인 여부에 따라 결정합니다.
    
    Args:
        row: Selenium WebElement (tr 그래)
        driver: Selenium WebDriver
        skip_notice: 공지 항목 외 여부
        skip_recommend: 추천글 외 여부
    
    Returns:
        tuple: (skip: bool, reason: str) - 건너뛰어야 하는 이유
    """
    try:
        # 이에 해당하는 tbody 찾기
        tbody = driver.execute_script("""
            let elem = arguments[0];
            while (elem && elem.tagName !== 'TBODY') {
                elem = elem.parentElement;
            }
            return elem;
        """, row)
        
        if tbody:
            # tbody 부분에 table 찾기
            table = driver.execute_script("return arguments[0].parentElement;", tbody)
            if table and 'article-table' in (table.get_attribute('class') or ''):
                # 같은 table에 모든 tbody 가져오기
                all_tbodies = driver.execute_script(
                    "return arguments[0].querySelectorAll('tbody');", table
                )
                # 현재 tbody 인덱스 찾기
                tbody_index = -1
                for idx, tb in enumerate(all_tbodies):
                    if tb == tbody:
                        tbody_index = idx
                        break
                
                # tbody 개수에 따라 구분
                # - 3개: 0=공지, 1=추천, 2=일반
                # - 1개: 전부 일반글 (페이지 2 이후)
                Logger.debug(f"tbody 인덱스: {tbody_index} (총 {len(all_tbodies)}개 tbody)")
                
                # tbody가 3개 이상일 때만 인덱스로 구분
                if len(all_tbodies) >= 3:
                    if tbody_index == 0 and skip_notice:
                        Logger.debug(f"공지사항으로 스킵")
                        return (True, 'notice')
                    elif tbody_index == 1 and skip_recommend:
                        Logger.debug(f"추천글로 스킵")
                        return (True, 'recommend')
                    elif tbody_index >= 2:
                        Logger.debug(f"일반글로 인식 (tbody_index={tbody_index})")
                        return (False, None)
                else:
                    # tbody가 1-2개면 전부 일반글
                    Logger.debug(f"일반글로 인식 (tbody 개수: {len(all_tbodies)})")
                    return (False, None)
    except Exception as e:
        Logger.debug(f"필터링 확인 오류: {e}")
    
    return (False, None)


def save_articles_to_file(articles, url, selector, filename="scraped_articles.txt"):
    """
    게시글 정보를 파일에 저장합니다.
    
    Args:
        articles: 게시글 정보 리스트
        url: 스크래핑 URL
        selector: 사용 CSS Selector
        filename: 저장할 파일명
    
    Returns:
        bool: 성공 여부
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"이카페 게시글 정보 ({len(articles)}개)\n")
            f.write(f"URL: {url}\n")
            f.write(f"Selector: {selector}\n")
            f.write("="*60 + "\n\n")
            for i, article in enumerate(articles, 1):
                f.write(f"{i}. {article['title']}\n")
                f.write(f"   ID: {article['article_id']}\n")
                f.write(f"   댓글글: {article['comment_count']}개\n")
                f.write(f"   조회수: {article['read_count']}회\n")
                f.write(f"   좋아요: {article['like_count']}개\n")
                f.write(f"   생성일: {article['date']}\n")
                f.write(f"   URL: {article['url']}\n\n")
        Logger.success(f"{filename} 저장 완료")
        return True
    except Exception as e:
        Logger.error(f"파일 저장 오류: {e}")
        return False


# ===================== 메인 함수 =====================

def scrape_single_page(driver, wait):
    """
    현재 페이지의 게시글을 스크래핑합니다.
    
    Args:
        driver: Selenium WebDriver
        wait: WebDriverWait 객체
    
    Returns:
        tuple: (articles: list, should_stop: bool)
               - articles: 추출된 게시글 리스트
               - should_stop: 스크래핑 중단 여부
    """
    articles = []
    should_stop = False
    
    try:
        # 페이지 완전 로딩 대기
        Logger.debug("페이지가 완전히 로드될 때까지 대기 중...")
        
        # 재시도 로직 추가 (최대 3번)
        table_found = False
        for attempt in range(3):
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.article-table")))
                Logger.debug(f"페이지 로드 완료! (시도 {attempt + 1}/3)")
                table_found = True
                time.sleep(2)  # 추가 안정화
                break
            except TimeoutException:
                if attempt < 2:
                    Logger.debug(f"article-table 로딩 재시도 중... ({attempt + 1}/3)")
                    time.sleep(3)
                else:
                    Logger.warning("article-table을 찾을 수 없습니다.")
        
        if not table_found:
            return articles, True  # 중단
        
        # 게시글 tr) 찾기
        Logger.debug("게시글 tr을 찾는 중...")
        article_rows = []
        successful_selector = None
        
        for i, selector in enumerate(Config.SELECTORS['article_rows'], 1):
            try:
                Logger.debug(f"[{i}/{len(Config.SELECTORS['article_rows'])}] ?�도 �? {selector}")
                temp_wait = WebDriverWait(driver, Config.SELECTOR_WAIT)
                temp_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                article_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if article_rows and len(article_rows) > 0:
                    successful_selector = selector
                    Logger.debug(f"?�?�터 ?�공!")
                    break
            except TimeoutException:
                continue
            except Exception as e:
                Logger.debug(f"?�류: {e}")
                continue
        
        if not article_rows:
            Logger.warning("게시글??찾�? 못했?�니??")
            return articles, True
        
        Logger.debug(f"총 {len(article_rows)}개의 행 발견")
        
        # 각 행에서 게시글 정보 추출
        skipped_count = 0
        for idx, row in enumerate(article_rows, 1):
            Logger.debug(f"\n--- 행 {idx}/{len(article_rows)} 처리 중 ---")
            
            # 필터링 확인
            skip, reason = should_skip_article(row, driver, Config.SKIP_NOTICE, Config.SKIP_RECOMMEND)
            if skip:
                Logger.debug(f"행 {idx}: {reason}으로 스킵됨")
                skipped_count += 1
                continue
            
            # 데이터 추출
            article_data = extract_article_data(row)
            if not article_data:
                Logger.debug(f"행 {idx}: 데이터 추출 실패")
                continue
            
            Logger.debug(f"행 {idx}: 추출 성공 - 제목: {article_data['title'][:30] if article_data['title'] else '(제목없음)'}...")
            
            # 날짜 확인 - 너무 오래된 게시글이면 중단
            if article_data['date']:
                if is_article_too_old(article_data['date'], Config.SCRAPE_DAYS):
                    Logger.info(f"?�� {Config.SCRAPE_DAYS}???�전 게시글 발견 (?�짜: {article_data['date']}) - ?�크?�핑 중단")
                    should_stop = True
                    break
            
            articles.append(article_data)
        
        Logger.debug(f"\n=== 페이지 처리 결과 ===")
        Logger.debug(f"총 행 수: {len(article_rows)}개")
        Logger.debug(f"스킵됨: {skipped_count}개")
        Logger.debug(f"추출 성공: {len(articles)}개")

    except Exception as e:
        Logger.error(f"페이지 스크래핑 오류: {e}")
    
    return articles, should_stop


def scrape_naver_cafe_titles(url):
    """
    ?�이�?카페 게시글???�크?�핑?�고 ?�이?�베?�스???�?�합?�다.
    
    Args:
        url: ?�크?�핑???�이�?카페 URL
    """
    # 로깅 ?�벨 ?�정
    Logger.set_level(Config.LOG_LEVEL)
    
    # ?�이?�베?�스 초기??
    Logger.info("\n?�이?�베?�스 초기??�?..")
    db_conn = init_database()
    
    # ?�래???�이???�리
    cleanup_old_data(db_conn)

    # 브라?��? ?�정 �??�작
    driver = setup_chrome_driver()
    if not driver:
        db_conn.close()
        return

    # ?�소 ?��??�정
    wait = WebDriverWait(driver, Config.ELEMENT_WAIT)
    
    # ?�계 변??
    total_articles = []
    total_inserted = 0
    total_updated = 0
    
    try:
        # ?�이지별로 ?�크?�핑
        for page_num in range(1, Config.MAX_PAGES + 1):
            Logger.separator()
            Logger.info(f"\n?�� ?�이지 {page_num} ?�크?�핑 �?..")
            Logger.separator()
            
            # ?�이지 URL ?�성 �??�동
            page_url = generate_page_url(url, page_num)
            Logger.info(f"URL: {page_url}")
            
            try:
                driver.get(page_url)
                Logger.success("URL 로딩 시작...")
                
                # 페이지 로딩 대기
                Logger.debug(f"페이지 로딩 대기 중... ({Config.PAGE_LOAD_WAIT}초)")
                time.sleep(Config.PAGE_LOAD_WAIT)
                
                # 실제 로드된 URL 확인
                current_url = driver.current_url
                Logger.debug(f"현재 URL: {current_url}")
                
            except Exception as e:
                Logger.error(f"URL 로딩 실패: {e}")
                break
            
            # 현재 페이지의 게시글을 스크래핑
            page_articles, should_stop = scrape_single_page(driver, wait)
            
            if not page_articles and page_num == 1:
                Logger.error("첫 페이지에서 게시글을 찾을 수 없습니다.")
                break
            
            # 데이터베이스에 저장
            if page_articles:
                Logger.info(f"\n페이지 {page_num}의 게시글을 데이터베이스에 저장... ({len(page_articles)}개)")
                inserted = 0
                updated = 0
                
                for article in page_articles:
                    result = save_or_update_article(db_conn, article)
                    if result == 'inserted':
                        inserted += 1
                    elif result == 'updated':
                        updated += 1
                
                total_inserted += inserted
                total_updated += updated
                total_articles.extend(page_articles)
                
                Logger.success(f"페이지 {page_num} 스크래핑 완료 - 삽입: {inserted}개, 업데이트: {updated}개")
            
            # 중단 조건 ?�인
            if should_stop:
                Logger.info(f"\n페이지 {page_num}에서 스크래핑 중단 ({Config.SCRAPE_DAYS}일 이전 게시글 발견)")
                break
            
            # 마지막 페이지인지 확인
            if len(page_articles) == 0:
                Logger.info(f"\n페이지 {page_num}에서 게시글을 찾을 수 없습니다. 스크래핑 종료")
                break
            
            # 다음 페이지로 이동 (서버 부하 방지)
            if page_num < Config.MAX_PAGES:
                Logger.debug(f"다음 페이지로 이동... (3초 대기)")
                time.sleep(3)

        # 최종 결과 출력
        Logger.separator()
        Logger.success(f"\n스크래핑 완료!")
        Logger.separator()
        Logger.info(f"\n최종 결과:")
        Logger.info(f"  수집된 게시글: {len(total_articles)}개")
        Logger.info(f"  삽입된 데이터: {total_inserted}개")
        Logger.info(f"  업데이트된 데이터: {total_updated}개")
        
        # 데이터베이스 통계
        stats = get_article_stats(db_conn)
        Logger.info(f"\n데이터베이스 통계:")
        Logger.info(f"  총 게시글: {stats['total_count']}개")
        Logger.info(f"  오늘 업데이트된 게시글: {stats['today_updated']}개")
        if stats['oldest_date']:
            Logger.info(f"  가장 오래된 게시글: {stats['oldest_date']}")
        
        # 스크래핑 결과를 파일에 저장
        if total_articles:
            Logger.separator()
            save_articles_to_file(total_articles, url, "multi-page", Config.OUTPUT_FILE)
    
    except KeyboardInterrupt:
        Logger.separator()
        Logger.warning("사용자 중단 요청")
        Logger.separator()

    except Exception as e:
        Logger.separator()
        Logger.error("예상치 못한 오류 발생")
        Logger.separator()
        Logger.info(f"\n오류 메시지: {e}")
        import traceback
        Logger.info("\n세부 오류:")
        traceback.print_exc()
    
    finally:
        # 데이터베이스 연결 종료
        try:
            db_conn.close()
            Logger.debug("데이터베이스 연결 종료")
        except:
            pass
        
        Logger.separator()
        Logger.info("10초 후에 브라우저가 자동으로 종료됩니다. (바로 종료하려면 Ctrl+C)")
        try:
            for i in range(10, 0, -1):
                Logger.info(f"\r남은 시간: {i}초..    ")
                time.sleep(1)
            Logger.info("\n")
        except KeyboardInterrupt:
            Logger.info("\n")
        
        Logger.info("브라우저가 종료됩니다...")
        driver.quit()
        Logger.success("브라우저가 종료되었습니다.")
        Logger.separator()


if __name__ == "__main__":
    Logger.separator()
    Logger.info("    네이버 카페 게시글 스크래퍼")
    Logger.info(f"    최근 {Config.SCRAPE_DAYS}일 간의 게시글 수집")
    Logger.separator()
    scrape_naver_cafe_titles(Config.DEFAULT_URL)
