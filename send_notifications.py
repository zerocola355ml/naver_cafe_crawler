"""
텔레그램 알림 발송 스크립트
keyword_articles 테이블의 미발송 인기글을 텔레그램으로 알림합니다.
"""

import sys
import io
import sqlite3
import requests
from datetime import datetime

# main.py에서 설정 가져오기 (먼저 import - stdout 설정은 main에서 처리)
try:
    from main import Config, Logger
    DB_FILE = Config.DB_FILE
    TELEGRAM_BOT_TOKEN = Config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID = Config.TELEGRAM_CHAT_ID
    TELEGRAM_ENABLED = Config.TELEGRAM_ENABLED
except ImportError:
    # Standalone 모드 (main.py 없이 실행)
    DB_FILE = "naver_cafe_articles.db"
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
    TELEGRAM_ENABLED = False
    
    # 간단한 Logger (standalone용)
    class Logger:
        @staticmethod
        def info(msg):
            print(msg)
        @staticmethod
        def warning(msg):
            print(f"⚠️ {msg}")
        @staticmethod
        def error(msg):
            print(f"❌ {msg}")
        @staticmethod
        def success(msg):
            print(f"✅ {msg}")
        @staticmethod
        def separator(char="=", length=80):
            print(char * length)


def get_pending_keyword_articles(conn):
    """
    알림 미발송 키워드 인기글을 조회합니다.
    
    Args:
        conn: SQLite 연결
    
    Returns:
        list: 미발송 게시글 리스트
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, article_id, title, comment_count, read_count, like_count, 
               url, date, matched_keywords, detected_at
        FROM keyword_articles 
        WHERE notification_sent = 0
        ORDER BY detected_at DESC
    ''')
    
    columns = ['id', 'article_id', 'title', 'comment_count', 'read_count', 
               'like_count', 'url', 'date', 'matched_keywords', 'detected_at']
    
    articles = []
    for row in cursor.fetchall():
        articles.append(dict(zip(columns, row)))
    
    return articles


def format_telegram_message(article):
    """
    텔레그램 메시지 형식을 생성합니다.
    
    Args:
        article: 게시글 정보 딕셔너리
    
    Returns:
        str: HTML 형식의 텔레그램 메시지
    """
    message = f"""
🌟 <b>키워드 인기글 발견!</b>

📌 <b>{article['title']}</b>

🎯 키워드: {article['matched_keywords']}
💬 댓글: {article['comment_count']}개
👁️ 조회: {article['read_count']}회
❤️ 좋아요: {article['like_count']}개
📅 작성일: {article['date']}

<a href="{article['url']}">▶️ 게시글 보러가기</a>
"""
    return message.strip()


def send_telegram(message, bot_token, chat_id):
    """
    텔레그램으로 메시지를 발송합니다.
    
    Args:
        message: 발송할 메시지
        bot_token: 텔레그램 봇 토큰
        chat_id: 텔레그램 Chat ID
    
    Returns:
        bool: 발송 성공 여부
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            Logger.error(f"텔레그램 API 오류: {response.status_code}")
            Logger.info(f"   응답: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        Logger.error(f"네트워크 오류: {e}")
        return False
    except Exception as e:
        Logger.error(f"알림 발송 오류: {e}")
        return False


def mark_as_sent(conn, article_id, method='telegram'):
    """
    알림 발송 완료로 표시합니다.
    
    Args:
        conn: SQLite 연결
        article_id: 게시글 ID
        method: 알림 방식
    
    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            UPDATE keyword_articles 
            SET notification_sent = 1,
                notification_sent_at = ?,
                notification_method = ?
            WHERE article_id = ?
        ''', (now, method, article_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        Logger.error(f"DB 업데이트 오류: {e}")
        return False


def send_pending_notifications():
    """
    미발송 키워드 인기글을 텔레그램으로 알림합니다.
    """
    Logger.separator()
    Logger.info("📱 텔레그램 알림 발송 시작")
    Logger.separator()
    
    # 설정 확인
    if not TELEGRAM_ENABLED:
        Logger.warning("텔레그램 알림이 비활성화되어 있습니다.")
        Logger.info("main.py의 Config.TELEGRAM_ENABLED = True로 설정하세요.")
        return
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        Logger.error("텔레그램 설정이 완료되지 않았습니다.")
        Logger.info("\nmain.py의 Config에서 다음을 설정하세요:")
        Logger.info("  - TELEGRAM_BOT_TOKEN: 봇 토큰")
        Logger.info("  - TELEGRAM_CHAT_ID: Chat ID")
        Logger.info("\n설정 방법은 TELEGRAM_SETUP.md를 참고하세요.")
        return
    
    try:
        # DB 연결
        conn = sqlite3.connect(DB_FILE)
        
        # 미발송 게시글 조회
        articles = get_pending_keyword_articles(conn)
        
        Logger.info(f"\n📊 알림 대기 중인 키워드 인기글: {len(articles)}개\n")
        
        if len(articles) == 0:
            Logger.success("발송할 알림이 없습니다.")
            conn.close()
            return
        
        # 각 게시글 알림 발송
        success_count = 0
        fail_count = 0
        
        for idx, article in enumerate(articles, 1):
            Logger.info(f"[{idx}/{len(articles)}] 발송 중: {article['title'][:40]}...")
            
            message = format_telegram_message(article)
            
            if send_telegram(message, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID):
                if mark_as_sent(conn, article['article_id']):
                    Logger.success(f"발송 완료 (ID: {article['article_id']})")
                    success_count += 1
                else:
                    Logger.warning(f"발송했으나 DB 업데이트 실패")
                    fail_count += 1
            else:
                Logger.error(f"발송 실패")
                fail_count += 1
            
            # 연속 발송 시 딜레이 (텔레그램 Rate Limit 방지)
            if idx < len(articles):
                import time
                time.sleep(1)
        
        Logger.separator()
        Logger.info("📊 발송 결과:")
        Logger.info(f"   ✅ 성공: {success_count}개")
        Logger.info(f"   ❌ 실패: {fail_count}개")
        Logger.separator()
        
        conn.close()
        
    except sqlite3.Error as e:
        Logger.error(f"데이터베이스 오류: {e}")
    except Exception as e:
        Logger.error(f"예상치 못한 오류: {e}")


if __name__ == "__main__":
    send_pending_notifications()

