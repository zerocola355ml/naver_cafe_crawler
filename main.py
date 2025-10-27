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
    """로깅 ?�벨??관리하???�래??""
    VERBOSE = 2  # 모든 ?�버�??�보 출력
    INFO = 1     # ?�용???�보�?출력
    QUIET = 0    # 최소 ?�보�?출력 (?�러/경고)
    
    level = INFO  # 기본 ?�벨
    
    @staticmethod
    def set_level(level):
        """로깅 ?�벨 ?�정"""
        Logger.level = level
    
    @staticmethod
    def debug(msg):
        """?�버�?메시지 (VERBOSE ?�벨?�서�?출력)"""
        if Logger.level >= Logger.VERBOSE:
            print(f"[DEBUG] {msg}")
    
    @staticmethod
    def info(msg):
        """?�반 ?�보 메시지 (INFO ?�벨 ?�상?�서 출력)"""
        if Logger.level >= Logger.INFO:
            print(msg)
    
    @staticmethod
    def success(msg):
        """?�공 메시지 (INFO ?�벨 ?�상?�서 출력)"""
        if Logger.level >= Logger.INFO:
            print(f"??{msg}")
    
    @staticmethod
    def warning(msg):
        """경고 메시지 (??�� 출력)"""
        print(f"?�️ {msg}")
    
    @staticmethod
    def error(msg):
        """?�러 메시지 (??�� 출력)"""
        print(f"??{msg}")
    
    @staticmethod
    def separator(char="=", length=60):
        """구분??(INFO ?�벨 ?�상?�서 출력)"""
        if Logger.level >= Logger.INFO:
            print(char * length)

# ===================== ?�정 ?�래??=====================
class Config:
    """?�크?�핑 ?�정??관리하???�래??""
    
    # URL ?�정
    DEFAULT_URL = "https://cafe.naver.com/f-e/cafes/10094499/menus/599?viewType=L&page=1"
    
    # 로깅 ?�정
    LOG_LEVEL = Logger.INFO  # VERBOSE(?�세), INFO(보통), QUIET(최소)
    
    # 게시글 ?�터 ?�정
    SKIP_NOTICE = True      # 공�??�항 ?�외
    SKIP_RECOMMEND = True   # 추천글 ?�외
    
    # 브라?��? ?�정
    USE_PROFILE = False     # Chrome ?�로???�용 ?��?
CHROME_PROFILE_PATH = "C:\\Users\\tlsgj\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_DIRECTORY = "Default"

    # ?�?�아???�정
    PAGE_LOAD_WAIT = 10     # ?�이지 로딩 ?��??�간 (�?
    ELEMENT_WAIT = 20       # ?�소 ?��??�간 (�?
    SELECTOR_WAIT = 3       # �??�?�터 ?�도 ?�간 (�?
    
    # 출력 ?�일 ?�정
    OUTPUT_FILE = "scraped_articles.txt"
    
    # ?�이?�베?�스 ?�정
    DB_FILE = "naver_cafe_articles.db"  # SQLite ?�이?�베?�스 ?�일�?
    RETENTION_DAYS = 15                  # ?�이??보�? 기간 (??
    
    # ?�크?�핑 범위 ?�정
    SCRAPE_DAYS = 7         # 최근 며칠 ?�안??게시글�??�집 (?�늘부??N???�까지)
    MAX_PAGES = 50          # 최�? ?�이지 ??(무한 루프 방�?)
    
    # CSS Selector ?�의
    SELECTORS = {
        # 게시글 ??tr) 찾기
        'article_rows': [
            "table.article-table > tbody:nth-of-type(3) tr",  # ?�반글�?(3번째 tbody)
            "table.article-table tbody:nth-of-type(3) tr",
            "table.article-table tbody:nth-of-type(n+2) tr",  # 추천글 + ?�반글
            "table.article-table tr",  # ?�체
        ],
        
        # �????��??�서 ?�보 추출
        'article_id': "td.td_normal.type_articleNumber",
        'title': "a.article",
        'comment': "a.cmt",
        'date': "td.td_normal.type_date",
        'read_count': "td.td_normal.type_readCount",
        'like_count': "td.td_normal.type_likeCount",
    }

# ===================== ?�이?�베?�스 ?�수 =====================

def init_database():
    """
    SQLite ?�이?�베?�스�?초기?�합?�다.
    ?�이블이 ?�으�??�성?�고, ?�결??반환?�니??
    
    Returns:
        sqlite3.Connection: ?�이?�베?�스 ?�결
    """
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    # ?�이�??�성 (?��? ?�으�?무시)
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
    Logger.debug(f"?�이?�베?�스 초기???�료: {Config.DB_FILE}")
    return conn


def cleanup_old_data(conn):
    """
    보�? 기간??지???�래???�이?��? ??��?�니??
    
    Args:
        conn: SQLite ?�결
    
    Returns:
        int: ??��???�의 개수
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
        Logger.info(f"{deleted_count}개의 ?�래??게시글 ??��??({Config.RETENTION_DAYS}???�상)")
    
    return deleted_count


def save_or_update_article(conn, article):
    """
    게시글???�이?�베?�스???�?�하거나 ?�데?�트?�니??
    
    Args:
        conn: SQLite ?�결
        article: 게시글 ?�보 ?�셔?�리
    
    Returns:
        str: 'inserted', 'updated', ?�는 'error'
    """
    cursor = conn.cursor()
    
    try:
        # 기존 게시글???�는지 ?�인
        cursor.execute('SELECT article_id FROM articles WHERE article_id = ?', (article['article_id'],))
        exists = cursor.fetchone()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # ?�데?�트
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
            # ?�입
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
        Logger.debug(f"DB ?�???�류 (ID: {article.get('article_id')}): {e}")
        return 'error'


def get_article_stats(conn):
    """
    ?�이?�베?�스???�계 ?�보�?반환?�니??
    
    Args:
        conn: SQLite ?�결
    
    Returns:
        dict: ?�계 ?�보
    """
    cursor = conn.cursor()
    
    # �?게시글 ??
    cursor.execute('SELECT COUNT(*) FROM articles')
    total_count = cursor.fetchone()[0]
    
    # ?�늘 ?�데?�트??게시글 ??
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


# ===================== ?�틸리티 ?�수 =====================

def parse_article_date(date_str):
    """
    게시글 ?�성?�을 ?�싱?�니??
    
    Args:
        date_str: ?�짜 문자??(?? "09:05" ?�는 "2025.10.26.")
    
    Returns:
        datetime: ?�싱???�짜 ?�는 None
    """
    try:
        date_str = date_str.strip()
        
        # ?�간 ?�태 (?�늘 게시글): "09:05"
        if ':' in date_str and '.' not in date_str:
            today = datetime.now()
            time_parts = date_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # ?�짜 ?�태: "2025.10.26." ?�는 "2025.10.26"
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
        Logger.debug(f"?�짜 ?�싱 ?�류: {date_str} - {e}")
        return None


def is_article_too_old(date_str, days_limit):
    """
    게시글???�무 ?�래?�었?��? ?�인?�니??
    
    Args:
        date_str: ?�짜 문자??
        days_limit: 며칠 ?�까지 ?�집?��?
    
    Returns:
        bool: True�??�무 ?�래??(중단?�야 ??
    """
    article_date = parse_article_date(date_str)
    if not article_date:
        return False
    
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    return article_date < cutoff_date


def generate_page_url(base_url, page_number):
    """
    ?�이지 번호�??�함??URL???�성?�니??
    
    Args:
        base_url: 기본 URL
        page_number: ?�이지 번호
    
    Returns:
        str: ?�이지 URL
    """
    # URL?�서 page= 부분을 찾아??교체
    if 'page=' in base_url:
        # 기존 page= ?�라미터 교체
        return re.sub(r'page=\d+', f'page={page_number}', base_url)
    elif '?' in base_url:
        # page ?�라미터 추�?
        return f"{base_url}&page={page_number}"
    else:
        return f"{base_url}?page={page_number}"


def setup_chrome_driver():
    """
    Chrome WebDriver�??�정?�고 반환?�니??
    
    Returns:
        webdriver.Chrome: ?�정??Chrome WebDriver
    """
    options = Options()

    # ?�로???�용 ?�정
    if Config.USE_PROFILE:
        Logger.debug("?�로??모드�??�행?�니??")
        profile_path = os.path.join(Config.CHROME_PROFILE_PATH, Config.PROFILE_DIRECTORY)
        if not os.path.isdir(profile_path):
            Logger.error("?�로??경로가 존재?��? ?�습?�다. USE_PROFILE??False�??�정?�세??")
            return None
        options.add_argument(f"user-data-dir={Config.CHROME_PROFILE_PATH}")
        options.add_argument(f"profile-directory={Config.PROFILE_DIRECTORY}")
    
    # Chrome ?�션 (�?감�? ?�회)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    
    try:
        Logger.info("\n브라?��?�??�작?�는 �?..")
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        Logger.success("브라?��?가 ?�공?�으�??�작?�었?�니??")
        return driver
    except Exception as e:
        Logger.error("WebDriver ?�행 ?�패.")
        Logger.info(f"?�류: {e}")
        Logger.info("\n?�결 방법:")
        Logger.info("1. Chrome 브라?��?가 ?�치?�어 ?�는지 ?�인")
        Logger.info("2. ChromeDriver가 ?�동?�로 ?�치?�는지 ?�인")
        return None


def extract_article_data(row):
    """
    ??tr)?�서 게시글 ?�보�?추출?�니??
    
    Args:
        row: Selenium WebElement (tr ?�그)
    
    Returns:
        dict: 게시글 ?�보 ?�셔?�리 ?�는 None (추출 ?�패 ??
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
        # 게시글 ID 추출 (td?�서 직접)
        try:
            article_id_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['article_id'])
            article_data['article_id'] = article_id_elem.text.strip()
        except:
            pass
        
        # ?�목 추출 (?�수)
        try:
            title_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['title'])
            article_data['title'] = title_link.text.strip()
            article_data['url'] = title_link.get_attribute('href')
            
            # ID가 ?�으�?URL?�서 추출
            if not article_data['article_id']:
                url = article_data['url']
                if 'articleid=' in url.lower():
                    article_data['article_id'] = url.split('articleid=')[1].split('&')[0]
                elif '/articles/' in url:
                    article_data['article_id'] = url.split('/articles/')[1].split('?')[0]
        except:
            return None
        
        # ?��? ??추출
        try:
            comment_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['comment'])
            comment_text = comment_link.text.strip()
            numbers = re.findall(r'\d+', comment_text)
            if numbers:
                article_data['comment_count'] = int(numbers[0])
        except:
            article_data['comment_count'] = 0
        
        # ?�성??추출
        try:
            date_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['date'])
            article_data['date'] = date_elem.text.strip()
        except:
            article_data['date'] = ''
        
        # 조회??추출
        try:
            read_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['read_count'])
            read_count_text = read_count_elem.text.strip()
            numbers = re.findall(r'\d+', read_count_text.replace(',', ''))
            if numbers:
                article_data['read_count'] = int(numbers[0])
        except:
            article_data['read_count'] = 0
        
        # 좋아????추출
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
        Logger.debug(f"?�이??추출 ?�류: {e}")
        return None


def should_skip_article(row, driver, skip_notice=True, skip_recommend=True):
    """
    게시글??공�??�항 ?�는 추천글?��? ?�인?�여 ?�터�??��?�?결정?�니??
    
    Args:
        row: Selenium WebElement (tr ?�그)
        driver: Selenium WebDriver
        skip_notice: 공�??�항 ?�외 ?��?
        skip_recommend: 추천글 ?�외 ?��?
    
    Returns:
        tuple: (skip: bool, reason: str) - 건너?��? ?��??� ?�유
    """
    try:
        # ?�이 ?�한 tbody 찾기
        tbody = driver.execute_script("""
            let elem = arguments[0];
            while (elem && elem.tagName !== 'TBODY') {
                elem = elem.parentElement;
            }
            return elem;
        """, row)
        
        if tbody:
            # tbody??부�?table 찾기
            table = driver.execute_script("return arguments[0].parentElement;", tbody)
            if table and 'article-table' in (table.get_attribute('class') or ''):
                # 같�? table??모든 tbody 가?�오�?
                all_tbodies = driver.execute_script(
                    "return arguments[0].querySelectorAll('tbody');", table
                )
                # ?�재 tbody???�덱??찾기
                tbody_index = -1
                for idx, tb in enumerate(all_tbodies):
                    if tb == tbody:
                        tbody_index = idx
                        break
                
                # 0: 공�??�항, 1: 추천글, 2: ?�반글
                if tbody_index == 0 and skip_notice:
                    return (True, 'notice')
                elif tbody_index == 1 and skip_recommend:
                    return (True, 'recommend')
    except Exception as e:
        Logger.debug(f"?�터�??�인 ?�류: {e}")
    
    return (False, None)


def save_articles_to_file(articles, url, selector, filename="scraped_articles.txt"):
    """
    게시글 ?�보�??�일�??�?�합?�다.
    
    Args:
        articles: 게시글 ?�보 리스??
        url: ?�크?�핑??URL
        selector: ?�용??CSS Selector
        filename: ?�?�할 ?�일�?
    
    Returns:
        bool: ?�???�공 ?��?
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"?�이�?카페 게시글 ?�보 ({len(articles)}�?\n")
            f.write(f"URL: {url}\n")
            f.write(f"Selector: {selector}\n")
            f.write("="*60 + "\n\n")
            for i, article in enumerate(articles, 1):
                f.write(f"{i}. {article['title']}\n")
                f.write(f"   ID: {article['article_id']}\n")
                f.write(f"   ?��?: {article['comment_count']}�?n")
                f.write(f"   조회?? {article['read_count']}\n")
                f.write(f"   좋아?? {article['like_count']}\n")
                f.write(f"   ?�성?? {article['date']}\n")
                f.write(f"   URL: {article['url']}\n\n")
        Logger.success(f"{filename} ?�일로도 ?�?�되?�습?�다.")
        return True
    except Exception as e:
        Logger.error(f"?�일 ?�???�패: {e}")
        return False


# ===================== 메인 ?�수 =====================

def scrape_single_page(driver, wait):
    """
    ?�재 ?�이지??게시글???�크?�핑?�니??
    
    Args:
        driver: Selenium WebDriver
        wait: WebDriverWait 객체
    
    Returns:
        tuple: (articles: list, should_stop: bool)
               - articles: 추출??게시글 리스??
               - should_stop: ?�래??게시글??만나 중단?�야 ?�는지 ?��?
    """
    articles = []
    should_stop = False
    
    try:
        # ?�이지 ?�전 로딩 ?��?
        Logger.debug("?�이지가 ?�전??로드???�까지 ?��?�?..")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.article-table")))
            Logger.debug("?�이지 로드 ?�료!")
            time.sleep(2)
        except TimeoutException:
            Logger.warning("article-table??찾을 ???�습?�다.")
            return articles, True  # 중단
        
        # 게시글 ??tr) 찾기
        Logger.debug("게시글 ?�을 찾는 �?..")
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
        
        Logger.debug(f"�?{len(article_rows)}개의 ??발견")
        
        # �??�에??게시글 ?�보 추출
        for row in article_rows:
            # ?�터�??�인
            skip, reason = should_skip_article(row, driver, Config.SKIP_NOTICE, Config.SKIP_RECOMMEND)
            if skip:
                continue
            
            # ?�이??추출
            article_data = extract_article_data(row)
            if not article_data:
                continue
            
            # ?�짜 ?�인 - ?�무 ?�래??게시글?�면 중단
            if article_data['date']:
                if is_article_too_old(article_data['date'], Config.SCRAPE_DAYS):
                    Logger.info(f"?�� {Config.SCRAPE_DAYS}???�전 게시글 발견 (?�짜: {article_data['date']}) - ?�크?�핑 중단")
                    should_stop = True
                    break
            
            articles.append(article_data)
        
        Logger.debug(f"추출??게시글: {len(articles)}�?)

    except Exception as e:
        Logger.error(f"?�이지 ?�크?�핑 ?�류: {e}")
    
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
                Logger.success("URL 로딩 ?�작...")
                
                # ?�이지 로딩 ?��?
                Logger.debug(f"?�이지 로딩 ?��?�?.. ({Config.PAGE_LOAD_WAIT}�?")
                time.sleep(Config.PAGE_LOAD_WAIT)
                
            except Exception as e:
                Logger.error(f"URL ?�동 ?�패: {e}")
                break
            
            # ?�일 ?�이지 ?�크?�핑
            page_articles, should_stop = scrape_single_page(driver, wait)
            
            if not page_articles and page_num == 1:
                Logger.error("�??�이지?�서 게시글??찾�? 못했?�니??")
                break
            
            # ?�이?�베?�스???�??
            if page_articles:
                Logger.info(f"\n?�� ?�이지 {page_num} ?�이?�베?�스 ?�??�?.. ({len(page_articles)}�?")
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
                
                Logger.success(f"?�이지 {page_num} ?�???�료 - ?? {inserted}�? ?�데?�트: {updated}�?)
            
            # 중단 조건 ?�인
            if should_stop:
                Logger.info(f"\n?�� ?�이지 {page_num}?�서 ?�크?�핑 중단 ({Config.SCRAPE_DAYS}???�전 게시글 발견)")
                break
            
            # 마�?�??�이지 ?�인
            if len(page_articles) == 0:
                Logger.info(f"\n?�� ?�이지 {page_num}??게시글???�음 - ?�크?�핑 종료")
                break
            
            # ?�음 ?�이지�?(?�무 빠르�??�청?��? ?�도�??��?
            if page_num < Config.MAX_PAGES:
                Logger.debug(f"?�음 ?�이지�??�동... (2�??��?")
        time.sleep(2)

        # 최종 ?�계 출력
        Logger.separator()
        Logger.success(f"\n???�크?�핑 ?�료!")
        Logger.separator()
        Logger.info(f"\n?�� 최종 ?�계:")
        Logger.info(f"  �??�집 게시글: {len(total_articles)}�?)
        Logger.info(f"  ?�로 추�?: {total_inserted}�?)
        Logger.info(f"  ?�데?�트: {total_updated}�?)
        
        # ?�이?�베?�스 ?�계
        stats = get_article_stats(db_conn)
        Logger.info(f"\n?�� ?�이?�베?�스 ?�계:")
        Logger.info(f"  �??�?�된 게시글: {stats['total_count']}�?)
        Logger.info(f"  ?�늘 ?�데?�트: {stats['today_updated']}�?)
        if stats['oldest_date']:
            Logger.info(f"  가???�래???�이?? {stats['oldest_date']}")
        
        # ?�스???�일로도 ?�??
        if total_articles:
            Logger.separator()
            save_articles_to_file(total_articles, url, "multi-page", Config.OUTPUT_FILE)
    
    except KeyboardInterrupt:
        Logger.separator()
        Logger.warning("?�용?��? 중단?�습?�다.")
        Logger.separator()

    except Exception as e:
        Logger.separator()
        Logger.error("?�상�?못한 ?�류 발생")
        Logger.separator()
        Logger.info(f"\n?�류 메시지: {e}")
        import traceback
        Logger.info("\n?�세 ?�류:")
        traceback.print_exc()
    
    finally:
        # ?�이?�베?�스 ?�결 종료
        try:
            db_conn.close()
            Logger.debug("?�이?�베?�스 ?�결 종료")
        except:
            pass
        
        Logger.separator()
        Logger.info("10�???브라?��?가 ?�동?�로 종료?�니??.. (바로 종료?�려�?Ctrl+C)")
        try:
            for i in range(10, 0, -1):
                Logger.info(f"\r?��? ?�간: {i}�?..    ")
                time.sleep(1)
            Logger.info("\n")
        except KeyboardInterrupt:
            Logger.info("\n")
        
        Logger.info("브라?��?�?종료?�는 �?..")
        driver.quit()
        Logger.success("브라?��?가 종료?�었?�니??")
        Logger.separator()


if __name__ == "__main__":
    Logger.separator()
    Logger.info("    ?�이�?카페 게시글 ?�크?�퍼")
    Logger.info(f"    최근 {Config.SCRAPE_DAYS}?�간??게시글 ?�집")
    Logger.separator()
    scrape_naver_cafe_titles(Config.DEFAULT_URL)
