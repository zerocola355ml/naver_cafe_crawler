"""
SQLite 데이터베이스 뷰어
naver_cafe_articles.db 파일의 내용을 확인합니다.
"""

import sqlite3
import sys
import io

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

DB_FILE = "naver_cafe_articles.db"

def view_database():
    """데이터베이스 내용을 보기 좋게 출력합니다."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 총 게시글 수
        cursor.execute('SELECT COUNT(*) FROM articles')
        total = cursor.fetchone()[0]
        
        print("=" * 80)
        print(f"📊 데이터베이스: {DB_FILE}")
        print("=" * 80)
        print(f"\n총 게시글 수: {total}개\n")
        
        if total == 0:
            print("저장된 게시글이 없습니다.")
            return
        
        # 최근 게시글 10개 조회
        print("📝 최근 업데이트된 게시글 (10개):")
        print("-" * 80)
        
        cursor.execute('''
            SELECT article_id, title, comment_count, read_count, like_count, 
                   date, last_updated
            FROM articles 
            ORDER BY last_updated DESC 
            LIMIT 10
        ''')
        
        for idx, row in enumerate(cursor.fetchall(), 1):
            article_id, title, comments, reads, likes, date, updated = row
            print(f"\n{idx}. {title}")
            print(f"   ID: {article_id} | 댓글: {comments} | 조회: {reads} | 좋아요: {likes}")
            print(f"   작성일: {date} | 업데이트: {updated}")
        
        print("\n" + "-" * 80)
        
        # 통계 정보
        print("\n📈 통계 정보:")
        cursor.execute('SELECT AVG(comment_count), AVG(read_count), AVG(like_count) FROM articles')
        avg_comments, avg_reads, avg_likes = cursor.fetchone()
        print(f"   평균 댓글 수: {avg_comments:.1f}")
        print(f"   평균 조회수: {avg_reads:.1f}")
        print(f"   평균 좋아요: {avg_likes:.1f}")
        
        # 가장 인기있는 게시글
        print("\n🔥 조회수 TOP 5:")
        cursor.execute('''
            SELECT title, read_count, comment_count, like_count
            FROM articles 
            ORDER BY read_count DESC 
            LIMIT 5
        ''')
        for idx, (title, reads, comments, likes) in enumerate(cursor.fetchall(), 1):
            print(f"   {idx}. {title[:60]}...")
            print(f"      조회: {reads} | 댓글: {comments} | 좋아요: {likes}")
        
        print("\n" + "=" * 80)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {DB_FILE}")
        print("먼저 main.py를 실행하여 데이터를 수집하세요.")

if __name__ == "__main__":
    view_database()

