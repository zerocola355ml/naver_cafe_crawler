"""
키워드 인기글 전용 뷰어
keyword_articles 테이블의 내용을 상세히 확인합니다.
(인기글 중 관심 키워드를 포함하는 게시글만)
"""

import sqlite3
import sys
import io

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

DB_FILE = "naver_cafe_articles.db"

def view_keyword_articles(show_all=True):
    """
    키워드 인기글 목록을 보기 좋게 출력합니다.
    
    Args:
        show_all: True면 전체, False면 알림 미발송 글만
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        print("=" * 100)
        print(f"⭐ 키워드 인기글 목록 - {DB_FILE}")
        print("=" * 100)
        
        # 통계 정보
        cursor.execute('SELECT COUNT(*) FROM keyword_articles')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM keyword_articles WHERE notification_sent = 0')
        pending = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM keyword_articles WHERE notification_sent = 1')
        sent = cursor.fetchone()[0]
        
        print(f"\n📊 통계:")
        print(f"   총 키워드 인기글: {total}개")
        print(f"   ✅ 알림 발송 완료: {sent}개")
        print(f"   ⏳ 알림 대기 중: {pending}개")
        
        if total == 0:
            print("\n키워드 인기글이 없습니다.")
            print("스크래핑을 실행하면 조건을 만족하는 게시글이 자동으로 수집됩니다.")
            return
        
        # 키워드별 분포
        cursor.execute('''
            SELECT matched_keywords, COUNT(*) 
            FROM keyword_articles 
            GROUP BY matched_keywords
            ORDER BY COUNT(*) DESC
        ''')
        keyword_distribution = cursor.fetchall()
        
        print(f"\n🔍 키워드별 분포:")
        for keywords, count in keyword_distribution:
            print(f"   {keywords}: {count}개")
        
        # 필터 설정
        if show_all:
            print(f"\n📋 모든 키워드 인기글 ({total}개):")
            query = '''
                SELECT id, article_id, title, comment_count, read_count, like_count, 
                       url, date, matched_keywords, detected_at, notification_sent, notification_sent_at
                FROM keyword_articles 
                ORDER BY detected_at DESC
            '''
            cursor.execute(query)
        else:
            print(f"\n⏳ 알림 대기 중인 키워드 인기글 ({pending}개):")
            query = '''
                SELECT id, article_id, title, comment_count, read_count, like_count, 
                       url, date, matched_keywords, detected_at, notification_sent, notification_sent_at
                FROM keyword_articles 
                WHERE notification_sent = 0
                ORDER BY detected_at DESC
            '''
            cursor.execute(query)
        
        print("=" * 100)
        
        articles = cursor.fetchall()
        
        for idx, article in enumerate(articles, 1):
            (id, article_id, title, comments, reads, likes, 
             url, date, keywords, detected, notified, notified_at) = article
            
            print(f"\n[{idx}] {title}")
            print(f"    📌 ID: {article_id}")
            print(f"    🎯 매칭 키워드: {keywords}")
            print(f"    💬 댓글: {comments}개 | 👁️ 조회: {reads}회 | ❤️ 좋아요: {likes}개")
            print(f"    📅 작성일: {date}")
            print(f"    🔍 발견: {detected}")
            
            if notified:
                print(f"    ✅ 알림 완료: {notified_at}")
            else:
                print(f"    ⏳ 알림 대기 중")
            
            print(f"    🔗 {url}")
            print("-" * 100)
        
        # 통계 분석
        if total > 0:
            cursor.execute('''
                SELECT AVG(comment_count), AVG(read_count), AVG(like_count),
                       MAX(comment_count), MAX(read_count), MAX(like_count)
                FROM keyword_articles
            ''')
            avg_c, avg_r, avg_l, max_c, max_r, max_l = cursor.fetchone()
            
            print(f"\n📈 키워드 인기글 통계:")
            print(f"   평균 - 댓글: {avg_c:.1f}개 | 조회: {avg_r:.1f}회 | 좋아요: {avg_l:.1f}개")
            print(f"   최대 - 댓글: {max_c}개 | 조회: {max_r}회 | 좋아요: {max_l}개")
        
        print("\n" + "=" * 100)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {DB_FILE}")
        print("먼저 main.py를 실행하여 데이터를 수집하세요.")


def show_menu():
    """메뉴를 표시하고 사용자 선택을 받습니다."""
    print("\n" + "=" * 100)
    print("⭐ 키워드 인기글 뷰어")
    print("=" * 100)
    print("\n1. 모든 키워드 인기글 보기")
    print("2. 알림 대기 중인 키워드 인기글만 보기")
    print("3. 종료")
    print("\n" + "-" * 100)
    
    choice = input("\n선택 (1-3): ").strip()
    return choice


if __name__ == "__main__":
    # 명령줄 인자가 있으면 바로 실행
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            view_keyword_articles(show_all=True)
        elif sys.argv[1] == "--pending":
            view_keyword_articles(show_all=False)
        else:
            print("사용법:")
            print("  python view_keyword_articles.py           # 메뉴 모드")
            print("  python view_keyword_articles.py --all     # 모든 키워드 인기글")
            print("  python view_keyword_articles.py --pending # 알림 대기 중만")
    else:
        # 메뉴 모드
        while True:
            choice = show_menu()
            
            if choice == '1':
                view_keyword_articles(show_all=True)
                input("\n계속하려면 Enter를 누르세요...")
            elif choice == '2':
                view_keyword_articles(show_all=False)
                input("\n계속하려면 Enter를 누르세요...")
            elif choice == '3':
                print("\n종료합니다.")
                break
            else:
                print("\n❌ 잘못된 선택입니다. 1-3 중 선택하세요.")

