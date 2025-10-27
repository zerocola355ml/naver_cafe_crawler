import sys
import io

# Windows ì½˜ì†” ?¸ì½”???¤ì • (?œê? ë°??¹ìˆ˜ë¬¸ì ì¶œë ¥???„í•´)
# line_buffering=Trueë¡??¤ì •?˜ì—¬ ?¤ì‹œê°?ì¶œë ¥ ê°€??
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

# ===================== Logger ?´ë˜??=====================
class Logger:
    """ë¡œê¹… ?ˆë²¨??ê´€ë¦¬í•˜???´ë˜??""
    VERBOSE = 2  # ëª¨ë“  ?”ë²„ê·??•ë³´ ì¶œë ¥
    INFO = 1     # ?¬ìš©???•ë³´ë§?ì¶œë ¥
    QUIET = 0    # ìµœì†Œ ?•ë³´ë§?ì¶œë ¥ (?ëŸ¬/ê²½ê³ )
    
    level = INFO  # ê¸°ë³¸ ?ˆë²¨
    
    @staticmethod
    def set_level(level):
        """ë¡œê¹… ?ˆë²¨ ?¤ì •"""
        Logger.level = level
    
    @staticmethod
    def debug(msg):
        """?”ë²„ê·?ë©”ì‹œì§€ (VERBOSE ?ˆë²¨?ì„œë§?ì¶œë ¥)"""
        if Logger.level >= Logger.VERBOSE:
            print(f"[DEBUG] {msg}")
    
    @staticmethod
    def info(msg):
        """?¼ë°˜ ?•ë³´ ë©”ì‹œì§€ (INFO ?ˆë²¨ ?´ìƒ?ì„œ ì¶œë ¥)"""
        if Logger.level >= Logger.INFO:
            print(msg)
    
    @staticmethod
    def success(msg):
        """?±ê³µ ë©”ì‹œì§€ (INFO ?ˆë²¨ ?´ìƒ?ì„œ ì¶œë ¥)"""
        if Logger.level >= Logger.INFO:
            print(f"??{msg}")
    
    @staticmethod
    def warning(msg):
        """ê²½ê³  ë©”ì‹œì§€ (??ƒ ì¶œë ¥)"""
        print(f"? ï¸ {msg}")
    
    @staticmethod
    def error(msg):
        """?ëŸ¬ ë©”ì‹œì§€ (??ƒ ì¶œë ¥)"""
        print(f"??{msg}")
    
    @staticmethod
    def separator(char="=", length=60):
        """êµ¬ë¶„??(INFO ?ˆë²¨ ?´ìƒ?ì„œ ì¶œë ¥)"""
        if Logger.level >= Logger.INFO:
            print(char * length)

# ===================== ?¤ì • ?´ë˜??=====================
class Config:
    """?¤í¬?˜í•‘ ?¤ì •??ê´€ë¦¬í•˜???´ë˜??""
    
    # URL ?¤ì •
    DEFAULT_URL = "https://cafe.naver.com/f-e/cafes/10094499/menus/599?viewType=L&page=1"
    
    # ë¡œê¹… ?¤ì •
    LOG_LEVEL = Logger.INFO  # VERBOSE(?ì„¸), INFO(ë³´í†µ), QUIET(ìµœì†Œ)
    
    # ê²Œì‹œê¸€ ?„í„° ?¤ì •
    SKIP_NOTICE = True      # ê³µì??¬í•­ ?œì™¸
    SKIP_RECOMMEND = True   # ì¶”ì²œê¸€ ?œì™¸
    
    # ë¸Œë¼?°ì? ?¤ì •
    USE_PROFILE = False     # Chrome ?„ë¡œ???¬ìš© ?¬ë?
CHROME_PROFILE_PATH = "C:\\Users\\tlsgj\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_DIRECTORY = "Default"

    # ?€?„ì•„???¤ì •
    PAGE_LOAD_WAIT = 10     # ?˜ì´ì§€ ë¡œë”© ?€ê¸??œê°„ (ì´?
    ELEMENT_WAIT = 20       # ?”ì†Œ ?€ê¸??œê°„ (ì´?
    SELECTOR_WAIT = 3       # ê°??€?‰í„° ?œë„ ?œê°„ (ì´?
    
    # ì¶œë ¥ ?Œì¼ ?¤ì •
    OUTPUT_FILE = "scraped_articles.txt"
    
    # ?°ì´?°ë² ?´ìŠ¤ ?¤ì •
    DB_FILE = "naver_cafe_articles.db"  # SQLite ?°ì´?°ë² ?´ìŠ¤ ?Œì¼ëª?
    RETENTION_DAYS = 15                  # ?°ì´??ë³´ê? ê¸°ê°„ (??
    
    # ?¤í¬?˜í•‘ ë²”ìœ„ ?¤ì •
    SCRAPE_DAYS = 7         # ìµœê·¼ ë©°ì¹  ?™ì•ˆ??ê²Œì‹œê¸€ë§??˜ì§‘ (?¤ëŠ˜ë¶€??N???„ê¹Œì§€)
    MAX_PAGES = 50          # ìµœë? ?˜ì´ì§€ ??(ë¬´í•œ ë£¨í”„ ë°©ì?)
    
    # CSS Selector ?•ì˜
    SELECTORS = {
        # ê²Œì‹œê¸€ ??tr) ì°¾ê¸°
        'article_rows': [
            "table.article-table > tbody:nth-of-type(3) tr",  # ?¼ë°˜ê¸€ë§?(3ë²ˆì§¸ tbody)
            "table.article-table tbody:nth-of-type(3) tr",
            "table.article-table tbody:nth-of-type(n+2) tr",  # ì¶”ì²œê¸€ + ?¼ë°˜ê¸€
            "table.article-table tr",  # ?„ì²´
        ],
        
        # ê°????´ë??ì„œ ?•ë³´ ì¶”ì¶œ
        'article_id': "td.td_normal.type_articleNumber",
        'title': "a.article",
        'comment': "a.cmt",
        'date': "td.td_normal.type_date",
        'read_count': "td.td_normal.type_readCount",
        'like_count': "td.td_normal.type_likeCount",
    }

# ===================== ?°ì´?°ë² ?´ìŠ¤ ?¨ìˆ˜ =====================

def init_database():
    """
    SQLite ?°ì´?°ë² ?´ìŠ¤ë¥?ì´ˆê¸°?”í•©?ˆë‹¤.
    ?Œì´ë¸”ì´ ?†ìœ¼ë©??ì„±?˜ê³ , ?°ê²°??ë°˜í™˜?©ë‹ˆ??
    
    Returns:
        sqlite3.Connection: ?°ì´?°ë² ?´ìŠ¤ ?°ê²°
    """
    conn = sqlite3.connect(Config.DB_FILE)
    cursor = conn.cursor()
    
    # ?Œì´ë¸??ì„± (?´ë? ?ˆìœ¼ë©?ë¬´ì‹œ)
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
    Logger.debug(f"?°ì´?°ë² ?´ìŠ¤ ì´ˆê¸°???„ë£Œ: {Config.DB_FILE}")
    return conn


def cleanup_old_data(conn):
    """
    ë³´ê? ê¸°ê°„??ì§€???¤ë˜???°ì´?°ë? ?? œ?©ë‹ˆ??
    
    Args:
        conn: SQLite ?°ê²°
    
    Returns:
        int: ?? œ???‰ì˜ ê°œìˆ˜
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
        Logger.info(f"{deleted_count}ê°œì˜ ?¤ë˜??ê²Œì‹œê¸€ ?? œ??({Config.RETENTION_DAYS}???´ìƒ)")
    
    return deleted_count


def save_or_update_article(conn, article):
    """
    ê²Œì‹œê¸€???°ì´?°ë² ?´ìŠ¤???€?¥í•˜ê±°ë‚˜ ?…ë°?´íŠ¸?©ë‹ˆ??
    
    Args:
        conn: SQLite ?°ê²°
        article: ê²Œì‹œê¸€ ?•ë³´ ?•ì…”?ˆë¦¬
    
    Returns:
        str: 'inserted', 'updated', ?ëŠ” 'error'
    """
    cursor = conn.cursor()
    
    try:
        # ê¸°ì¡´ ê²Œì‹œê¸€???ˆëŠ”ì§€ ?•ì¸
        cursor.execute('SELECT article_id FROM articles WHERE article_id = ?', (article['article_id'],))
        exists = cursor.fetchone()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if exists:
            # ?…ë°?´íŠ¸
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
            # ?½ì…
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
        Logger.debug(f"DB ?€???¤ë¥˜ (ID: {article.get('article_id')}): {e}")
        return 'error'


def get_article_stats(conn):
    """
    ?°ì´?°ë² ?´ìŠ¤???µê³„ ?•ë³´ë¥?ë°˜í™˜?©ë‹ˆ??
    
    Args:
        conn: SQLite ?°ê²°
    
    Returns:
        dict: ?µê³„ ?•ë³´
    """
    cursor = conn.cursor()
    
    # ì´?ê²Œì‹œê¸€ ??
    cursor.execute('SELECT COUNT(*) FROM articles')
    total_count = cursor.fetchone()[0]
    
    # ?¤ëŠ˜ ?…ë°?´íŠ¸??ê²Œì‹œê¸€ ??
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM articles WHERE DATE(last_updated) = ?', (today,))
    today_updated = cursor.fetchone()[0]
    
    # ê°€???¤ë˜??ê²Œì‹œê¸€
    cursor.execute('SELECT MIN(first_scraped) FROM articles')
    oldest = cursor.fetchone()[0]
    
    return {
        'total_count': total_count,
        'today_updated': today_updated,
        'oldest_date': oldest
    }


# ===================== ? í‹¸ë¦¬í‹° ?¨ìˆ˜ =====================

def parse_article_date(date_str):
    """
    ê²Œì‹œê¸€ ?‘ì„±?¼ì„ ?Œì‹±?©ë‹ˆ??
    
    Args:
        date_str: ? ì§œ ë¬¸ì??(?? "09:05" ?ëŠ” "2025.10.26.")
    
    Returns:
        datetime: ?Œì‹±??? ì§œ ?ëŠ” None
    """
    try:
        date_str = date_str.strip()
        
        # ?œê°„ ?•íƒœ (?¤ëŠ˜ ê²Œì‹œê¸€): "09:05"
        if ':' in date_str and '.' not in date_str:
            today = datetime.now()
            time_parts = date_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # ? ì§œ ?•íƒœ: "2025.10.26." ?ëŠ” "2025.10.26"
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
        Logger.debug(f"? ì§œ ?Œì‹± ?¤ë¥˜: {date_str} - {e}")
        return None


def is_article_too_old(date_str, days_limit):
    """
    ê²Œì‹œê¸€???ˆë¬´ ?¤ë˜?˜ì—ˆ?”ì? ?•ì¸?©ë‹ˆ??
    
    Args:
        date_str: ? ì§œ ë¬¸ì??
        days_limit: ë©°ì¹  ?„ê¹Œì§€ ?˜ì§‘? ì?
    
    Returns:
        bool: Trueë©??ˆë¬´ ?¤ë˜??(ì¤‘ë‹¨?´ì•¼ ??
    """
    article_date = parse_article_date(date_str)
    if not article_date:
        return False
    
    cutoff_date = datetime.now() - timedelta(days=days_limit)
    return article_date < cutoff_date


def generate_page_url(base_url, page_number):
    """
    ?˜ì´ì§€ ë²ˆí˜¸ë¥??¬í•¨??URL???ì„±?©ë‹ˆ??
    
    Args:
        base_url: ê¸°ë³¸ URL
        page_number: ?˜ì´ì§€ ë²ˆí˜¸
    
    Returns:
        str: ?˜ì´ì§€ URL
    """
    # URL?ì„œ page= ë¶€ë¶„ì„ ì°¾ì•„??êµì²´
    if 'page=' in base_url:
        # ê¸°ì¡´ page= ?Œë¼ë¯¸í„° êµì²´
        return re.sub(r'page=\d+', f'page={page_number}', base_url)
    elif '?' in base_url:
        # page ?Œë¼ë¯¸í„° ì¶”ê?
        return f"{base_url}&page={page_number}"
    else:
        return f"{base_url}?page={page_number}"


def setup_chrome_driver():
    """
    Chrome WebDriverë¥??¤ì •?˜ê³  ë°˜í™˜?©ë‹ˆ??
    
    Returns:
        webdriver.Chrome: ?¤ì •??Chrome WebDriver
    """
    options = Options()

    # ?„ë¡œ???¬ìš© ?¤ì •
    if Config.USE_PROFILE:
        Logger.debug("?„ë¡œ??ëª¨ë“œë¡??¤í–‰?©ë‹ˆ??")
        profile_path = os.path.join(Config.CHROME_PROFILE_PATH, Config.PROFILE_DIRECTORY)
        if not os.path.isdir(profile_path):
            Logger.error("?„ë¡œ??ê²½ë¡œê°€ ì¡´ì¬?˜ì? ?ŠìŠµ?ˆë‹¤. USE_PROFILE??Falseë¡??¤ì •?˜ì„¸??")
            return None
        options.add_argument(f"user-data-dir={Config.CHROME_PROFILE_PATH}")
        options.add_argument(f"profile-directory={Config.PROFILE_DIRECTORY}")
    
    # Chrome ?µì…˜ (ë´?ê°ì? ?°íšŒ)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    
    try:
        Logger.info("\në¸Œë¼?°ì?ë¥??œì‘?˜ëŠ” ì¤?..")
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        Logger.success("ë¸Œë¼?°ì?ê°€ ?±ê³µ?ìœ¼ë¡??œì‘?˜ì—ˆ?µë‹ˆ??")
        return driver
    except Exception as e:
        Logger.error("WebDriver ?¤í–‰ ?¤íŒ¨.")
        Logger.info(f"?¤ë¥˜: {e}")
        Logger.info("\n?´ê²° ë°©ë²•:")
        Logger.info("1. Chrome ë¸Œë¼?°ì?ê°€ ?¤ì¹˜?˜ì–´ ?ˆëŠ”ì§€ ?•ì¸")
        Logger.info("2. ChromeDriverê°€ ?ë™?¼ë¡œ ?¤ì¹˜?˜ëŠ”ì§€ ?•ì¸")
        return None


def extract_article_data(row):
    """
    ??tr)?ì„œ ê²Œì‹œê¸€ ?•ë³´ë¥?ì¶”ì¶œ?©ë‹ˆ??
    
    Args:
        row: Selenium WebElement (tr ?œê·¸)
    
    Returns:
        dict: ê²Œì‹œê¸€ ?•ë³´ ?•ì…”?ˆë¦¬ ?ëŠ” None (ì¶”ì¶œ ?¤íŒ¨ ??
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
        # ê²Œì‹œê¸€ ID ì¶”ì¶œ (td?ì„œ ì§ì ‘)
        try:
            article_id_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['article_id'])
            article_data['article_id'] = article_id_elem.text.strip()
        except:
            pass
        
        # ?œëª© ì¶”ì¶œ (?„ìˆ˜)
        try:
            title_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['title'])
            article_data['title'] = title_link.text.strip()
            article_data['url'] = title_link.get_attribute('href')
            
            # IDê°€ ?†ìœ¼ë©?URL?ì„œ ì¶”ì¶œ
            if not article_data['article_id']:
                url = article_data['url']
                if 'articleid=' in url.lower():
                    article_data['article_id'] = url.split('articleid=')[1].split('&')[0]
                elif '/articles/' in url:
                    article_data['article_id'] = url.split('/articles/')[1].split('?')[0]
        except:
            return None
        
        # ?“ê? ??ì¶”ì¶œ
        try:
            comment_link = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['comment'])
            comment_text = comment_link.text.strip()
            numbers = re.findall(r'\d+', comment_text)
            if numbers:
                article_data['comment_count'] = int(numbers[0])
        except:
            article_data['comment_count'] = 0
        
        # ?‘ì„±??ì¶”ì¶œ
        try:
            date_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['date'])
            article_data['date'] = date_elem.text.strip()
        except:
            article_data['date'] = ''
        
        # ì¡°íšŒ??ì¶”ì¶œ
        try:
            read_count_elem = row.find_element(By.CSS_SELECTOR, Config.SELECTORS['read_count'])
            read_count_text = read_count_elem.text.strip()
            numbers = re.findall(r'\d+', read_count_text.replace(',', ''))
            if numbers:
                article_data['read_count'] = int(numbers[0])
        except:
            article_data['read_count'] = 0
        
        # ì¢‹ì•„????ì¶”ì¶œ
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
        Logger.debug(f"?°ì´??ì¶”ì¶œ ?¤ë¥˜: {e}")
        return None


def should_skip_article(row, driver, skip_notice=True, skip_recommend=True):
    """
    ê²Œì‹œê¸€??ê³µì??¬í•­ ?ëŠ” ì¶”ì²œê¸€?¸ì? ?•ì¸?˜ì—¬ ?„í„°ë§??¬ë?ë¥?ê²°ì •?©ë‹ˆ??
    
    Args:
        row: Selenium WebElement (tr ?œê·¸)
        driver: Selenium WebDriver
        skip_notice: ê³µì??¬í•­ ?œì™¸ ?¬ë?
        skip_recommend: ì¶”ì²œê¸€ ?œì™¸ ?¬ë?
    
    Returns:
        tuple: (skip: bool, reason: str) - ê±´ë„ˆ?¸ì? ?¬ë??€ ?´ìœ 
    """
    try:
        # ?‰ì´ ?í•œ tbody ì°¾ê¸°
        tbody = driver.execute_script("""
            let elem = arguments[0];
            while (elem && elem.tagName !== 'TBODY') {
                elem = elem.parentElement;
            }
            return elem;
        """, row)
        
        if tbody:
            # tbody??ë¶€ëª?table ì°¾ê¸°
            table = driver.execute_script("return arguments[0].parentElement;", tbody)
            if table and 'article-table' in (table.get_attribute('class') or ''):
                # ê°™ì? table??ëª¨ë“  tbody ê°€?¸ì˜¤ê¸?
                all_tbodies = driver.execute_script(
                    "return arguments[0].querySelectorAll('tbody');", table
                )
                # ?„ì¬ tbody???¸ë±??ì°¾ê¸°
                tbody_index = -1
                for idx, tb in enumerate(all_tbodies):
                    if tb == tbody:
                        tbody_index = idx
                        break
                
                # 0: ê³µì??¬í•­, 1: ì¶”ì²œê¸€, 2: ?¼ë°˜ê¸€
                if tbody_index == 0 and skip_notice:
                    return (True, 'notice')
                elif tbody_index == 1 and skip_recommend:
                    return (True, 'recommend')
    except Exception as e:
        Logger.debug(f"?„í„°ë§??•ì¸ ?¤ë¥˜: {e}")
    
    return (False, None)


def save_articles_to_file(articles, url, selector, filename="scraped_articles.txt"):
    """
    ê²Œì‹œê¸€ ?•ë³´ë¥??Œì¼ë¡??€?¥í•©?ˆë‹¤.
    
    Args:
        articles: ê²Œì‹œê¸€ ?•ë³´ ë¦¬ìŠ¤??
        url: ?¤í¬?˜í•‘??URL
        selector: ?¬ìš©??CSS Selector
        filename: ?€?¥í•  ?Œì¼ëª?
    
    Returns:
        bool: ?€???±ê³µ ?¬ë?
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"?¤ì´ë²?ì¹´í˜ ê²Œì‹œê¸€ ?•ë³´ ({len(articles)}ê°?\n")
            f.write(f"URL: {url}\n")
            f.write(f"Selector: {selector}\n")
            f.write("="*60 + "\n\n")
            for i, article in enumerate(articles, 1):
                f.write(f"{i}. {article['title']}\n")
                f.write(f"   ID: {article['article_id']}\n")
                f.write(f"   ?“ê?: {article['comment_count']}ê°?n")
                f.write(f"   ì¡°íšŒ?? {article['read_count']}\n")
                f.write(f"   ì¢‹ì•„?? {article['like_count']}\n")
                f.write(f"   ?‘ì„±?? {article['date']}\n")
                f.write(f"   URL: {article['url']}\n\n")
        Logger.success(f"{filename} ?Œì¼ë¡œë„ ?€?¥ë˜?ˆìŠµ?ˆë‹¤.")
        return True
    except Exception as e:
        Logger.error(f"?Œì¼ ?€???¤íŒ¨: {e}")
        return False


# ===================== ë©”ì¸ ?¨ìˆ˜ =====================

def scrape_single_page(driver, wait):
    """
    ?„ì¬ ?˜ì´ì§€??ê²Œì‹œê¸€???¤í¬?˜í•‘?©ë‹ˆ??
    
    Args:
        driver: Selenium WebDriver
        wait: WebDriverWait ê°ì²´
    
    Returns:
        tuple: (articles: list, should_stop: bool)
               - articles: ì¶”ì¶œ??ê²Œì‹œê¸€ ë¦¬ìŠ¤??
               - should_stop: ?¤ë˜??ê²Œì‹œê¸€??ë§Œë‚˜ ì¤‘ë‹¨?´ì•¼ ?˜ëŠ”ì§€ ?¬ë?
    """
    articles = []
    should_stop = False
    
    try:
        # ?˜ì´ì§€ ?„ì „ ë¡œë”© ?€ê¸?
        Logger.debug("?˜ì´ì§€ê°€ ?„ì „??ë¡œë“œ???Œê¹Œì§€ ?€ê¸?ì¤?..")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.article-table")))
            Logger.debug("?˜ì´ì§€ ë¡œë“œ ?„ë£Œ!")
            time.sleep(2)
        except TimeoutException:
            Logger.warning("article-table??ì°¾ì„ ???†ìŠµ?ˆë‹¤.")
            return articles, True  # ì¤‘ë‹¨
        
        # ê²Œì‹œê¸€ ??tr) ì°¾ê¸°
        Logger.debug("ê²Œì‹œê¸€ ?‰ì„ ì°¾ëŠ” ì¤?..")
        article_rows = []
        successful_selector = None
        
        for i, selector in enumerate(Config.SELECTORS['article_rows'], 1):
            try:
                Logger.debug(f"[{i}/{len(Config.SELECTORS['article_rows'])}] ?œë„ ì¤? {selector}")
                temp_wait = WebDriverWait(driver, Config.SELECTOR_WAIT)
                temp_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                article_rows = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if article_rows and len(article_rows) > 0:
                    successful_selector = selector
                    Logger.debug(f"?€?‰í„° ?±ê³µ!")
                    break
            except TimeoutException:
                continue
            except Exception as e:
                Logger.debug(f"?¤ë¥˜: {e}")
                continue
        
        if not article_rows:
            Logger.warning("ê²Œì‹œê¸€??ì°¾ì? ëª»í–ˆ?µë‹ˆ??")
            return articles, True
        
        Logger.debug(f"ì´?{len(article_rows)}ê°œì˜ ??ë°œê²¬")
        
        # ê°??‰ì—??ê²Œì‹œê¸€ ?•ë³´ ì¶”ì¶œ
        for row in article_rows:
            # ?„í„°ë§??•ì¸
            skip, reason = should_skip_article(row, driver, Config.SKIP_NOTICE, Config.SKIP_RECOMMEND)
            if skip:
                continue
            
            # ?°ì´??ì¶”ì¶œ
            article_data = extract_article_data(row)
            if not article_data:
                continue
            
            # ? ì§œ ?•ì¸ - ?ˆë¬´ ?¤ë˜??ê²Œì‹œê¸€?´ë©´ ì¤‘ë‹¨
            if article_data['date']:
                if is_article_too_old(article_data['date'], Config.SCRAPE_DAYS):
                    Logger.info(f"?“… {Config.SCRAPE_DAYS}???´ì „ ê²Œì‹œê¸€ ë°œê²¬ (? ì§œ: {article_data['date']}) - ?¤í¬?˜í•‘ ì¤‘ë‹¨")
                    should_stop = True
                    break
            
            articles.append(article_data)
        
        Logger.debug(f"ì¶”ì¶œ??ê²Œì‹œê¸€: {len(articles)}ê°?)

    except Exception as e:
        Logger.error(f"?˜ì´ì§€ ?¤í¬?˜í•‘ ?¤ë¥˜: {e}")
    
    return articles, should_stop


def scrape_naver_cafe_titles(url):
    """
    ?¤ì´ë²?ì¹´í˜ ê²Œì‹œê¸€???¤í¬?˜í•‘?˜ê³  ?°ì´?°ë² ?´ìŠ¤???€?¥í•©?ˆë‹¤.
    
    Args:
        url: ?¤í¬?˜í•‘???¤ì´ë²?ì¹´í˜ URL
    """
    # ë¡œê¹… ?ˆë²¨ ?¤ì •
    Logger.set_level(Config.LOG_LEVEL)
    
    # ?°ì´?°ë² ?´ìŠ¤ ì´ˆê¸°??
    Logger.info("\n?°ì´?°ë² ?´ìŠ¤ ì´ˆê¸°??ì¤?..")
    db_conn = init_database()
    
    # ?¤ë˜???°ì´???•ë¦¬
    cleanup_old_data(db_conn)

    # ë¸Œë¼?°ì? ?¤ì • ë°??œì‘
    driver = setup_chrome_driver()
    if not driver:
        db_conn.close()
        return

    # ?”ì†Œ ?€ê¸??¤ì •
    wait = WebDriverWait(driver, Config.ELEMENT_WAIT)
    
    # ?µê³„ ë³€??
    total_articles = []
    total_inserted = 0
    total_updated = 0
    
    try:
        # ?˜ì´ì§€ë³„ë¡œ ?¤í¬?˜í•‘
        for page_num in range(1, Config.MAX_PAGES + 1):
            Logger.separator()
            Logger.info(f"\n?“„ ?˜ì´ì§€ {page_num} ?¤í¬?˜í•‘ ì¤?..")
            Logger.separator()
            
            # ?˜ì´ì§€ URL ?ì„± ë°??´ë™
            page_url = generate_page_url(url, page_num)
            Logger.info(f"URL: {page_url}")
            
            try:
                driver.get(page_url)
                Logger.success("URL ë¡œë”© ?œì‘...")
                
                # ?˜ì´ì§€ ë¡œë”© ?€ê¸?
                Logger.debug(f"?˜ì´ì§€ ë¡œë”© ?€ê¸?ì¤?.. ({Config.PAGE_LOAD_WAIT}ì´?")
                time.sleep(Config.PAGE_LOAD_WAIT)
                
            except Exception as e:
                Logger.error(f"URL ?´ë™ ?¤íŒ¨: {e}")
                break
            
            # ?¨ì¼ ?˜ì´ì§€ ?¤í¬?˜í•‘
            page_articles, should_stop = scrape_single_page(driver, wait)
            
            if not page_articles and page_num == 1:
                Logger.error("ì²??˜ì´ì§€?ì„œ ê²Œì‹œê¸€??ì°¾ì? ëª»í–ˆ?µë‹ˆ??")
                break
            
            # ?°ì´?°ë² ?´ìŠ¤???€??
            if page_articles:
                Logger.info(f"\n?’¾ ?˜ì´ì§€ {page_num} ?°ì´?°ë² ?´ìŠ¤ ?€??ì¤?.. ({len(page_articles)}ê°?")
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
                
                Logger.success(f"?˜ì´ì§€ {page_num} ?€???„ë£Œ - ?? {inserted}ê°? ?…ë°?´íŠ¸: {updated}ê°?)
            
            # ì¤‘ë‹¨ ì¡°ê±´ ?•ì¸
            if should_stop:
                Logger.info(f"\n?›‘ ?˜ì´ì§€ {page_num}?ì„œ ?¤í¬?˜í•‘ ì¤‘ë‹¨ ({Config.SCRAPE_DAYS}???´ì „ ê²Œì‹œê¸€ ë°œê²¬)")
                break
            
            # ë§ˆì?ë§??˜ì´ì§€ ?•ì¸
            if len(page_articles) == 0:
                Logger.info(f"\n?›‘ ?˜ì´ì§€ {page_num}??ê²Œì‹œê¸€???†ìŒ - ?¤í¬?˜í•‘ ì¢…ë£Œ")
                break
            
            # ?¤ìŒ ?˜ì´ì§€ë¡?(?ˆë¬´ ë¹ ë¥´ê²??”ì²­?˜ì? ?Šë„ë¡??€ê¸?
            if page_num < Config.MAX_PAGES:
                Logger.debug(f"?¤ìŒ ?˜ì´ì§€ë¡??´ë™... (2ì´??€ê¸?")
        time.sleep(2)

        # ìµœì¢… ?µê³„ ì¶œë ¥
        Logger.separator()
        Logger.success(f"\n???¤í¬?˜í•‘ ?„ë£Œ!")
        Logger.separator()
        Logger.info(f"\n?“Š ìµœì¢… ?µê³„:")
        Logger.info(f"  ì´??˜ì§‘ ê²Œì‹œê¸€: {len(total_articles)}ê°?)
        Logger.info(f"  ?ˆë¡œ ì¶”ê?: {total_inserted}ê°?)
        Logger.info(f"  ?…ë°?´íŠ¸: {total_updated}ê°?)
        
        # ?°ì´?°ë² ?´ìŠ¤ ?µê³„
        stats = get_article_stats(db_conn)
        Logger.info(f"\n?“Š ?°ì´?°ë² ?´ìŠ¤ ?µê³„:")
        Logger.info(f"  ì´??€?¥ëœ ê²Œì‹œê¸€: {stats['total_count']}ê°?)
        Logger.info(f"  ?¤ëŠ˜ ?…ë°?´íŠ¸: {stats['today_updated']}ê°?)
        if stats['oldest_date']:
            Logger.info(f"  ê°€???¤ë˜???°ì´?? {stats['oldest_date']}")
        
        # ?ìŠ¤???Œì¼ë¡œë„ ?€??
        if total_articles:
            Logger.separator()
            save_articles_to_file(total_articles, url, "multi-page", Config.OUTPUT_FILE)
    
    except KeyboardInterrupt:
        Logger.separator()
        Logger.warning("?¬ìš©?ê? ì¤‘ë‹¨?ˆìŠµ?ˆë‹¤.")
        Logger.separator()

    except Exception as e:
        Logger.separator()
        Logger.error("?ˆìƒì¹?ëª»í•œ ?¤ë¥˜ ë°œìƒ")
        Logger.separator()
        Logger.info(f"\n?¤ë¥˜ ë©”ì‹œì§€: {e}")
        import traceback
        Logger.info("\n?ì„¸ ?¤ë¥˜:")
        traceback.print_exc()
    
    finally:
        # ?°ì´?°ë² ?´ìŠ¤ ?°ê²° ì¢…ë£Œ
        try:
            db_conn.close()
            Logger.debug("?°ì´?°ë² ?´ìŠ¤ ?°ê²° ì¢…ë£Œ")
        except:
            pass
        
        Logger.separator()
        Logger.info("10ì´???ë¸Œë¼?°ì?ê°€ ?ë™?¼ë¡œ ì¢…ë£Œ?©ë‹ˆ??.. (ë°”ë¡œ ì¢…ë£Œ?˜ë ¤ë©?Ctrl+C)")
        try:
            for i in range(10, 0, -1):
                Logger.info(f"\r?¨ì? ?œê°„: {i}ì´?..    ")
                time.sleep(1)
            Logger.info("\n")
        except KeyboardInterrupt:
            Logger.info("\n")
        
        Logger.info("ë¸Œë¼?°ì?ë¥?ì¢…ë£Œ?˜ëŠ” ì¤?..")
        driver.quit()
        Logger.success("ë¸Œë¼?°ì?ê°€ ì¢…ë£Œ?˜ì—ˆ?µë‹ˆ??")
        Logger.separator()


if __name__ == "__main__":
    Logger.separator()
    Logger.info("    ?¤ì´ë²?ì¹´í˜ ê²Œì‹œê¸€ ?¤í¬?˜í¼")
    Logger.info(f"    ìµœê·¼ {Config.SCRAPE_DAYS}?¼ê°„??ê²Œì‹œê¸€ ?˜ì§‘")
    Logger.separator()
    scrape_naver_cafe_titles(Config.DEFAULT_URL)
