import sqlite3
from config import DB_PATH

def init_db() -> bool:
    """データベース初期化"""
    print(f"🔧 Initializing enhanced database at: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URLsテーブル（強化版）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                custom_name TEXT,
                campaign_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_by TEXT DEFAULT 'system'
            )
        ''')
        
        # Clicksテーブル（強化版）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER,
                ip_address TEXT,
                country TEXT DEFAULT 'Unknown',
                region TEXT DEFAULT 'Unknown',
                city TEXT DEFAULT 'Unknown',
                timezone TEXT DEFAULT 'Unknown',
                user_agent TEXT,
                referrer TEXT,
                device_type TEXT DEFAULT 'unknown',
                browser TEXT DEFAULT 'unknown',
                os TEXT DEFAULT 'unknown',
                source TEXT DEFAULT 'direct',
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                FOREIGN KEY (url_id) REFERENCES urls (id)
            )
        ''')
        
        # インデックス作成（パフォーマンス向上）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_urls_is_active ON urls(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clicks_created_at ON clicks(created_at)')
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_db_connection() -> sqlite3.Connection:
    """データベース接続を取得"""
    return sqlite3.connect(DB_PATH)