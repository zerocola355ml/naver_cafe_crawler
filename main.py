import sys
import io

# Windows 콘솔 인코딩 설정 (한글 및 특수문자 출력을 위해)
# line_buffering=True로 설정하여 실시간 출력 가능
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

# ===================== Logger 클래스 =====================
class Logger:
    """로깅 레벨을 관리하는 클래스"""
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
    LOG_LEVEL = Logger.INFO  # VERBOSE(상세), INFO(보통), QUIET(최소)
    
    # 게시글 필터 설정
    SKIP_NOTICE = True      # 공지사항 제외
    SKIP_RECOMMEND = True   # 추천글 제외
    
    # 브라우저 설정
    USE_PROFILE = False     # Chrome 프로필 사용 여부
CHROME_PROFILE_PATH = "C:\\Users\\tlsgj\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_DIRECTORY = "Default"

    # 타임아웃 설정
    PAGE_LOAD_WAIT = 10     # 페이지 로딩 대기 시간 (초)
    ELEMENT_WAIT = 20       # 요소 대기 시간 (초)
    SELECTOR_WAIT = 3       # 각 셀렉터 시도 시간 (초)
    
    # 출력 파일 설정
    OUTPUT_FILE = "scraped_articles.txt"
    
    # 데이터베이스 설정
    DB_FILE = "naver_cafe_articles.db"  # SQLite 데이터베이스 파일명
    RETENTION_DAYS = 15                  # 데이터 보관 기간 (일)
    
    # 스크래핑 범위 설정
    SCRAPE_DAYS = 7         # 최근 며칠 동안의 게시글만 수집 (오늘부터 N일 전까지)
    MAX_PAGES = 50          # 최대 페이지 수 (무한 루프 방지)
    
    # CSS Selector 정의
    SELECTORS = {
        # 게시글 행(tr) 찾기
        'article_rows': [
            "table.article-table > tbody:nth-of-type(3) tr",  # 일반글만 (3번째 tbody)
            "table.article-table tbody:nth-of-type(3) tr",
            "table.article-table tbody:nth-of-type(n+2) tr",  # 추천글 + 일반글
            "table.article-table tr",  # 전체
        ],
        
        # 각 행 내부에서 정보 추출
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
    SQLite 데이터베이스를 초기화합니다.
    테이블이 없으면 생성하고, 연결을 반환합니다.
    
    Returns:
        sqlite3.Connection: 데이터베이스 연결
    """
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    # 테이블 생성 (이미 있으면 무시)
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
    보관 기간이 지난 오래된 데이터를 삭제합니다.
    
    Args:
        conn: SQLite 연결
    
    Returns:
        int: 삭제된 행의 개수
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
        Logger.info(f"{deleted_count}개의 오래된 게시글 삭제됨 ({Config.RETENTION_DAYS}일 이상)")
    
    return deleted_count


def save_or_update_article(conn, article):
    """
    게시글을 데이터베이스에 저장하거나 업데이트합니다.
    
    Args:
        conn: SQLite 연결
        article: 게시글 정보 딕셔너리
    
    Returns:
        str: 'inserted', 'updated', 또는 'error'
    """
    cursor = conn.cursor()
    
    try:
        # 기존 게시글이 있는지 확인
        cursor.execute('SELECT article_id FROM articles WHERE article_id = ?', (article['article_id'],))
        exists = cursor.fetchone()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # 업데이트
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
            # 삽입
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
        Logger.debug(f"DB 저장 오류 (ID: {article.get('article_id')}): {e}")
        return 'error'


def get_article_stats(conn):
    """
    데이터베이스의 통계 정보를 반환합니다.
    
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
    
    # 가장 오래된 게시글
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
    게시글 작성일을 파싱합니다.
    
    Args:
        date_str: 날짜 문자열 (예: "09:05" 또는 "2025.10.26.")
    
    Returns:
        datetime: 파싱된 날짜 또는 None
    """
    try:
        date_str = date_str.strip()
        
        # 시간 형태 (오늘 게시글): "09:05"
        if ':' in date_str and '.' not in date_str:
            today = datetime.now()
            time_parts = date_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 날짜 형태: "2025.10.26." 또는 "2025.10.26"
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
    게시글이 너무 오래되었는지 확인합니다.
    
    Args:
        date_str: 날짜 문자열
        days_limit: 며칠 전까지 수집할지
    
    Returns:
        bool: True면 너무 오래됨 (중단해야 함)
    """
    article_date = parse_article_date(date_str)
    if not article_date:
        return False
    
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    return article_date < cutoff_date


def setup_chrome_driver():
    """
    Chrome WebDriver를 설정하고 반환합니다.
    
    Returns:
        webdriver.Chrome: 설정된 Chrome WebDriver
    """
    options = Options()

    # 프로필 사용 설정
    if Config.USE_PROFILE:
        Logger.debug("프로필 모드로 실행합니다.")
        profile_path = os.path.join(Config.CHROME_PROFILE_PATH, Config.PROFILE_DIRECTORY)
        if not os.path.isdir(profile_path):
            Logger.error("프로필 경로가 존재하지 않습니다. USE_PROFILE을 False로 설정하세요.")
            return None
        options.add_argument(f"user-data-dir={Config.CHROME_PROFILE_PATH}")
        options.add_argument(f"profile-directory={Config.PROFILE_DIRECTORY}")
    
    # Chrome 옵션 (봇 감지 우회)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    
    try:
        Logger.info("\n브라우저를 시작하는 중...")
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        Logger.success("브라우저가 성공적으로 시작되었습니다.")
        return driver
    except Exception as e:
        Logger.error("WebDriver 실행 실패.")
        Logger.info(f"오류: {e}")
        Logger.info("\n해결 방법:")
        Logger.info("1. Chrome 브라우저가 설치되어 있는지 확인")
        Logger.info("2. ChromeDriver가 자동으로 설치되는지 확인")
        return None


def extract_article_data(row):
    """
    행(tr)에서 게시글 정보를 추출합니다.
    
    Args:
        row: Selenium WebElement (tr 태그)
    
    Returns:
        dict: 게시글 정보 딕셔너리 또는 None (추출 실패 시)
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
        except:
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
        
        # 작성일 추출
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
        Logger.debug(f"데이터 추출 오류: {e}")
        return None


def should_skip_article(row, driver, skip_notice=True, skip_recommend=True):
    """
    게시글이 공지사항 또는 추천글인지 확인하여 필터링 여부를 결정합니다.
    
    Args:
        row: Selenium WebElement (tr 태그)
        driver: Selenium WebDriver
        skip_notice: 공지사항 제외 여부
        skip_recommend: 추천글 제외 여부
    
    Returns:
        tuple: (skip: bool, reason: str) - 건너뛸지 여부와 이유
    """
    try:
        # 행이 속한 tbody 찾기
        tbody = driver.execute_script("""
            let elem = arguments[0];
            while (elem && elem.tagName !== 'TBODY') {
                elem = elem.parentElement;
            }
            return elem;
        """, row)
        
        if tbody:
            # tbody의 부모 table 찾기
            table = driver.execute_script("return arguments[0].parentElement;", tbody)
            if table and 'article-table' in (table.get_attribute('class') or ''):
                # 같은 table의 모든 tbody 가져오기
                all_tbodies = driver.execute_script(
                    "return arguments[0].querySelectorAll('tbody');", table
                )
                # 현재 tbody의 인덱스 찾기
                tbody_index = -1
                for idx, tb in enumerate(all_tbodies):
                    if tb == tbody:
                        tbody_index = idx
                        break
                
                # 0: 공지사항, 1: 추천글, 2: 일반글
                if tbody_index == 0 and skip_notice:
                    return (True, 'notice')
                elif tbody_index == 1 and skip_recommend:
                    return (True, 'recommend')
    except Exception as e:
        Logger.debug(f"필터링 확인 오류: {e}")
    
    return (False, None)


def save_articles_to_file(articles, url, selector, filename="scraped_articles.txt"):
    """
    게시글 정보를 파일로 저장합니다.
    
    Args:
        articles: 게시글 정보 리스트
        url: 스크래핑한 URL
        selector: 사용된 CSS Selector
        filename: 저장할 파일명
    
    Returns:
        bool: 저장 성공 여부
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"네이버 카페 게시글 정보 ({len(articles)}개)\n")
            f.write(f"URL: {url}\n")
            f.write(f"Selector: {selector}\n")
            f.write("="*60 + "\n\n")
            for i, article in enumerate(articles, 1):
                f.write(f"{i}. {article['title']}\n")
                f.write(f"   ID: {article['article_id']}\n")
                f.write(f"   댓글: {article['comment_count']}개\n")
                f.write(f"   조회수: {article['read_count']}\n")
                f.write(f"   좋아요: {article['like_count']}\n")
                f.write(f"   작성일: {article['date']}\n")
                f.write(f"   URL: {article['url']}\n\n")
        Logger.success(f"{filename} 파일로도 저장되었습니다.")
        return True
    except Exception as e:
        Logger.error(f"파일 저장 실패: {e}")
        return False


# ===================== 메인 함수 =====================

def scrape_naver_cafe_titles(url):
    """
    네이버 카페 게시글을 스크래핑하고 데이터베이스에 저장합니다.
    
    Args:
        url: 스크래핑할 네이버 카페 URL
    """
    # 로깅 레벨 설정
    Logger.set_level(Config.LOG_LEVEL)
    
    # 데이터베이스 초기화
    Logger.info("\n데이터베이스 초기화 중...")
    db_conn = init_database()
    
    # 오래된 데이터 정리
    cleanup_old_data(db_conn)

    # 브라우저 설정 및 시작
    driver = setup_chrome_driver()
    if not driver:
        db_conn.close()
        return

    # 2. URL로 이동
    try:
        Logger.info(f"\n대상 URL로 이동 중: {url}")
        driver.get(url)
        Logger.success("URL 로딩 시작...")
        
        # 페이지 초기 로딩 대기
        Logger.info(f"페이지 로딩 대기 중... ({Config.PAGE_LOAD_WAIT}초)")
        time.sleep(Config.PAGE_LOAD_WAIT)
        Logger.success("로딩 완료, 계속 진행합니다...")

    except Exception as e:
        Logger.error(f"URL 이동 실패: {e}")
        driver.quit()
        return

    # 3. 요소 대기 설정
    wait = WebDriverWait(driver, Config.ELEMENT_WAIT)

    try:
        # 3. 페이지 완전 로딩 대기 (새로운 네이버 카페 UI는 iframe 없음)
        Logger.info("\n페이지가 완전히 로드될 때까지 대기 중...")
        try:
            # article-table이 로드될 때까지 기다림
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.article-table")))
            Logger.success("페이지 로드 완료!")
            time.sleep(2)  # 추가 안정화 대기
        except TimeoutException:
            Logger.warning("article-table을 찾을 수 없습니다. 계속 시도합니다...")
            time.sleep(3)

        # 4. 게시글 행(tr) 찾기
        Logger.info("\n게시글 행을 찾는 중...")
        article_rows = []
        successful_selector = None
        
        for i, selector in enumerate(Config.SELECTORS['article_rows'], 1):
            try:
                Logger.debug(f"[{i}/{len(Config.SELECTORS['article_rows'])}] 시도 중: {selector}")
                temp_wait = WebDriverWait(driver, Config.SELECTOR_WAIT)
                temp_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                article_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if article_rows and len(article_rows) > 0:
                    successful_selector = selector
                    Logger.success(f"셀렉터 [{i}/{len(Config.SELECTORS['article_rows'])}] 성공!")
                    break
                else:
                    Logger.debug("(요소 없음)")
            except TimeoutException:
                Logger.debug("(타임아웃)")
                continue
            except Exception as e:
                Logger.debug(f"(오류: {e})")
                continue

        # 5. 각 행에서 게시글 정보 추출
        if not article_rows or len(article_rows) == 0:
            Logger.separator()
            Logger.error("게시글을 찾지 못했습니다.")
            Logger.separator()
            Logger.info(f"\n현재 URL: {driver.current_url}")
            
            # 디버깅용 파일 저장
            Logger.info("\n디버깅용 파일을 저장합니다...")
            try:
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                Logger.success("debug_page_source.html 저장 완료")
                
                driver.save_screenshot("debug_screenshot.png")
                Logger.success("debug_screenshot.png 저장 완료")
                
                # 페이지에서 'article' 포함 요소 찾기
                Logger.info("\n💡 페이지 분석 중...")
                all_links = driver.find_elements(By.TAG_NAME, "a")
                article_links = [link for link in all_links if 'article' in link.get_attribute('href').lower() if link.get_attribute('href')]
                
                Logger.info(f"  - 전체 링크 개수: {len(all_links)}")
                Logger.info(f"  - 'article' 포함 링크: {len(article_links)}")
                
                if article_links:
                    Logger.info("\n  샘플 링크 (처음 3개):")
                    for i, link in enumerate(article_links[:3], 1):
                        Logger.info(f"    {i}. href: {link.get_attribute('href')}")
                        Logger.info(f"       class: {link.get_attribute('class')}")
                        Logger.info(f"       text: {link.text[:50] if link.text else '(없음)'}")
                        
                Logger.info("\n💡 debug_page_source.html 파일을 열어 정확한 셀렉터를 찾아보세요.")
            except Exception as e:
                Logger.error(f"파일 저장 실패: {e}")
                
        else:
            Logger.separator()
            Logger.success(f"성공! 총 {len(article_rows)}개의 행을 찾았습니다!")
            Logger.separator()
            
            # VERBOSE 모드: 처음 3개 행의 HTML 구조 출력
            if Logger.level >= Logger.VERBOSE:
                print("\n🔍 디버그: 처음 3개 행의 HTML 구조 분석")
                print("-" * 60)
                for i, row in enumerate(article_rows[:3], 1):
                    try:
                        print(f"\n[행 {i}]")
                        
                        # 게시글 ID
                        try:
                            article_id_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['article_id'])
                            print(f"  게시글 ID: {article_id_elem.text.strip()}")
                        except:
                            print(f"  게시글 ID: 찾을 수 없음")
                        
                        # 제목 찾기
                        try:
                            title_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['title'])
                            print(f"  제목: {title_link.text.strip()}")
                        except:
                            print(f"  제목: 찾을 수 없음")
                        
                        # 댓글 수
                        try:
                            comment_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['comment'])
                            print(f"  댓글 수: {comment_link.text.strip()}")
                        except:
                            print(f"  댓글 수: 0")
                        
                        # 작성일
                        try:
                            date_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['date'])
                            print(f"  작성일: {date_elem.text.strip()}")
                        except:
                            print(f"  작성일: 찾을 수 없음")
                        
                        # 조회수
                        try:
                            read_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['read_count'])
                            print(f"  조회수: {read_count_elem.text.strip()}")
                        except:
                            print(f"  조회수: 0")
                        
                        # 좋아요 수
                        try:
                            like_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['like_count'])
                            print(f"  좋아요 수: {like_count_elem.text.strip()}")
                        except:
                            print(f"  좋아요 수: 0")
                        
                        # tbody 인덱스 확인
                        tbody = driver.execute_script("""
                            let elem = arguments[0];
                            while (elem && elem.tagName !== 'TBODY') {
                                elem = elem.parentElement;
                            }
                            return elem;
                        """, row)
                        
                        if tbody:
                            table = driver.execute_script("return arguments[0].parentElement;", tbody)
                            if table:
                                all_tbodies = driver.execute_script(
                                    "return arguments[0].querySelectorAll('tbody');", table
                                )
                                tbody_index = -1
                                for idx, tb in enumerate(all_tbodies):
                                    if tb == tbody:
                                        tbody_index = idx
                                        break
                                
                                tbody_type = "알 수 없음"
                                if tbody_index == 0:
                                    tbody_type = "공지사항"
                                elif tbody_index == 1:
                                    tbody_type = "추천글"
                                elif tbody_index == 2:
                                    tbody_type = "일반글"
                                
                                print(f"  🎯 tbody 인덱스: {tbody_index} ({tbody_type})")
                        
                        # 행(tr) 태그 정보
                        print(f"  행 태그: {row.tag_name}")
                        print(f"  행 class: {row.get_attribute('class')}")
                    except Exception as e:
                        print(f"  분석 오류: {e}")
                print("-" * 60)
                
                print("\n⏸ 분석 결과 확인을 위해 15초 대기합니다... (스킵하려면 Ctrl+C)")
                try:
                    for i in range(15, 0, -1):
                        print(f"\r남은 시간: {i}초...    ", end="")
                        time.sleep(1)
                    print("\n✓ 계속 진행합니다...")
                except KeyboardInterrupt:
                    print("\n✓ 대기 스킵, 계속 진행합니다...")
            
            # 각 행에서 게시글 정보 추출
            articles = []
            skipped_notice = 0
            skipped_recommend = 0
            
            Logger.info("\n게시글 정보를 추출하는 중...")
            for row in article_rows:
                # 필터링 확인
                skip, reason = should_skip_article(row, driver, Config.SKIP_NOTICE, Config.SKIP_RECOMMEND)
                if skip:
                    if reason == 'notice':
                        skipped_notice += 1
                    elif reason == 'recommend':
                        skipped_recommend += 1
                    continue
                
                # 데이터 추출
                article_data = extract_article_data(row)
                if article_data:
                    articles.append(article_data)
            
            # 데이터베이스에 저장/업데이트
            Logger.info(f"\n데이터베이스에 저장 중...")
            inserted_count = 0
            updated_count = 0
            error_count = 0
            
            for article in articles:
                result = save_or_update_article(db_conn, article)
                if result == 'inserted':
                    inserted_count += 1
                elif result == 'updated':
                    updated_count += 1
                elif result == 'error':
                    error_count += 1
            
            Logger.success(f"DB 저장 완료 - 새 게시글: {inserted_count}개, 업데이트: {updated_count}개")
            if error_count > 0:
                Logger.warning(f"저장 실패: {error_count}개")
            
            # 데이터베이스 통계
            stats = get_article_stats(db_conn)
            Logger.info(f"\n📊 데이터베이스 통계:")
            Logger.info(f"  총 게시글: {stats['total_count']}개")
            Logger.info(f"  오늘 업데이트: {stats['today_updated']}개")
            if stats['oldest_date']:
                Logger.info(f"  가장 오래된 데이터: {stats['oldest_date']}")
            
            Logger.separator()
            Logger.info(f"사용된 CSS Selector: {successful_selector}")
            Logger.info(f"이번 스크래핑 발견: {len(article_rows)}개")
            if Config.SKIP_NOTICE:
                Logger.info(f"공지사항 제외: {skipped_notice}개")
            if Config.SKIP_RECOMMEND:
                Logger.info(f"추천글 제외: {skipped_recommend}개")
            Logger.info(f"최종 게시글 개수: {len(articles)}개\n")
            
            for i, article in enumerate(articles, 1):
                Logger.info(f"{i:3d}. {article['title']}")
                Logger.info(f"      ID: {article['article_id']} | 댓글: {article['comment_count']} | 조회: {article['read_count']} | 좋아요: {article['like_count']} | 날짜: {article['date']}")
            
            Logger.separator()
            
            # 결과를 파일로도 저장
            save_articles_to_file(articles, url, successful_selector, Config.OUTPUT_FILE)

    except TimeoutException:
        Logger.separator()
        Logger.error("페이지 요소 로드 시간 초과")
        Logger.separator()
        Logger.info("\n▶ 가능한 원인:")
        Logger.info("  1. 로그인이 필요한데 로그인하지 않음")
        Logger.info("  2. 네이버 카페에 가입하지 않았거나 접근 권한이 없음")
        Logger.info("  3. 카페 구조가 변경됨")
        Logger.info(f"\n현재 URL: {driver.current_url}")
        
        # 디버깅용 스크린샷
        try:
            driver.save_screenshot("debug_screenshot.png")
            Logger.success("디버깅용 스크린샷이 debug_screenshot.png로 저장되었습니다.")
        except:
            pass
            
    except Exception as e:
        Logger.separator()
        Logger.error("예상치 못한 오류 발생")
        Logger.separator()
        Logger.info(f"\n오류 메시지: {e}")
        import traceback
        Logger.info("\n상세 오류:")
        traceback.print_exc()
    finally:
        # 데이터베이스 연결 종료
        try:
            db_conn.close()
            Logger.debug("데이터베이스 연결 종료")
        except:
            pass
        
        Logger.separator()
        Logger.info("10초 후 브라우저가 자동으로 종료됩니다... (바로 종료하려면 Ctrl+C)")
        try:
            for i in range(10, 0, -1):
                Logger.info(f"\r남은 시간: {i}초...    ")
                time.sleep(1)
            Logger.info("\n")
        except KeyboardInterrupt:
            Logger.info("\n")
        
        Logger.info("브라우저를 종료하는 중...")
        driver.quit()
        Logger.success("브라우저가 종료되었습니다.")
        Logger.separator()


if __name__ == "__main__":
    Logger.separator()
    Logger.info("    네이버 카페 게시글 스크래퍼")
    Logger.separator()
    scrape_naver_cafe_titles(Config.DEFAULT_URL)
