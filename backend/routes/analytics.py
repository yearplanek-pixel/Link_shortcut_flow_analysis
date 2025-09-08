from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any
from config import DB_PATH, BASE_URL

router = APIRouter()

# 分析画面HTMLテンプレート - 完全修正版
ANALYTICS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>分析画面 - {short_code}</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 20px; 
            background: #f5f5f5; 
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        h1 {{ 
            color: #333; 
            border-bottom: 3px solid #4CAF50; 
            padding-bottom: 10px; 
        }}
        .info-box {{ 
            background: #e3f2fd; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 20px 0; 
        }}
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        .stat-card {{ 
            background: #f9f9f9; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            text-align: center; 
        }}
        .stat-number {{ 
            font-size: 2em; 
            font-weight: bold; 
            color: #4CAF50; 
        }}
        .stat-label {{ 
            color: #666; 
            margin-top: 10px; 
        }}
        .back-btn {{ 
            background: #4CAF50; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            text-decoration: none; 
            display: inline-block; 
            margin: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 分析画面: {short_code}</h1>
        
        <div class="info-box">
            <p><strong>元URL:</strong> <a href="{original_url}" target="_blank">{original_url}</a></p>
            <p><strong>短縮URL:</strong> <a href="{short_url}" target="_blank">{short_url}</a></p>
            <p><strong>作成日:</strong> {created_at}</p>
            <div style="text-align: center; margin-top: 15px;">
                <a href="/admin" class="back-btn">📊 管理画面に戻る</a>
                <button class="back-btn" onclick="location.reload()">🔄 更新</button>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_clicks}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_clicks}</div>
                <div class="stat-label">ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{qr_clicks}</div>
                <div class="stat-label">QRコードクリック</div>
            </div>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <p>詳細な分析グラフは近日実装予定です。</p>
            <p>現在は基本統計のみ表示しています。</p>
        </div>
    </div>
</body>
</html>"""

@router.get("/analytics/{short_code}")
async def analytics_page(short_code: str):
    """分析画面"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URL情報取得
        cursor.execute('''
            SELECT original_url, created_at, custom_name, campaign_name
            FROM urls WHERE short_code = ? AND is_active = TRUE
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            return HTMLResponse(content="<h1>エラー</h1><p>短縮URLが見つかりません</p>", status_code=404)
        
        original_url, created_at, custom_name, campaign_name = result
        
        # 統計情報取得
        cursor.execute('''
            SELECT 
                COUNT(*) as total_clicks,
                COUNT(DISTINCT ip_address) as unique_clicks,
                COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
            FROM clicks 
            WHERE url_id = (SELECT id FROM urls WHERE short_code = ?)
        ''', (short_code,))
        
        stats = cursor.fetchone()
        total_clicks, unique_clicks, qr_clicks = stats if stats else (0, 0, 0)
        
        conn.close()
        
        # HTMLをレンダリング
        html_content = ANALYTICS_HTML.format(
            short_code=short_code,
            original_url=original_url,
            short_url=f"{BASE_URL}/{short_code}",
            created_at=created_at,
            total_clicks=total_clicks,
            unique_clicks=unique_clicks,
            qr_clicks=qr_clicks
        )
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"<h1>Error</h1><p>{str(e)}</p>"
        return HTMLResponse(content=error_html, status_code=500)

# 既存のAPIエンドポイントはそのまま保持
async def get_detailed_analytics(short_code: str) -> Dict[str, Any]:
    """詳細な分析データを取得（API用）"""
    # ... 既存のコード ...