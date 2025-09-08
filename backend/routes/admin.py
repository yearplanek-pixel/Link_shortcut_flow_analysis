from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import sqlite3
from config import DB_PATH, BASE_URL
from utils import generate_qr_code_base64

router = APIRouter()

# 管理画面HTMLテンプレート
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>リンクトラッカー管理画面</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #4CAF50; }
        .stat-label { color: #666; margin-top: 10px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        tr:hover { background: #f5f5f5; }
        .action-btn { padding: 5px 10px; margin: 2px; border: none; border-radius: 3px; cursor: pointer; text-decoration: none; display: inline-block; }
        .analytics-btn { background: #2196F3; color: white; }
        .qr-btn { background: #FF9800; color: white; }
        .export-btn { background: #4CAF50; color: white; }
        .refresh-btn { background: #9C27B0; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 リンクトラッカー管理画面</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_urls }}</div>
                <div class="stat-label">総URL数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_clicks }}</div>
                <div class="stat-label">総クリック数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ unique_clicks }}</div>
                <div class="stat-label">ユニーク訪問者</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ qr_clicks }}</div>
                <div class="stat-label">QRコードクリック</div>
            </div>
        </div>

        <div style="text-align: center;">
            <button class="refresh-btn" onclick="location.reload()">🔄 データ更新</button>
            <a href="/bulk" class="action-btn" style="background: #607D8B; color: white; padding: 10px 20px;">🚀 一括生成</a>
            <a href="/docs" class="action-btn" style="background: #795548; color: white; padding: 10px 20px;">📚 APIドキュメント</a>
        </div>

        <h2>📋 URL一覧</h2>
        <table>
            <thead>
                <tr>
                    <th>短縮コード</th>
                    <th>元URL</th>
                    <th>カスタム名</th>
                    <th>キャンペーン</th>
                    <th>作成日</th>
                    <th>クリック数</th>
                    <th>ユニーク</th>
                    <th>QRクリック</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {{ table_rows }}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@router.get("/admin")
async def admin_dashboard():
    """統計管理画面"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 総合統計
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT u.id) as total_urls,
                COUNT(c.id) as total_clicks,
                COUNT(DISTINCT c.ip_address) as unique_clicks,
                COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = TRUE
        ''')
        
        stats = cursor.fetchone()
        total_urls, total_clicks, unique_clicks, qr_clicks = stats
        
        # URL一覧
        cursor.execute('''
            SELECT u.short_code, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as click_count,
                   COUNT(DISTINCT c.ip_address) as unique_clicks,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = TRUE
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        # テーブル行を生成
        table_rows = ""
        for row in results:
            short_code, original_url, created_at, custom_name, campaign_name, click_count, unique_count, qr_count = row
            
            table_rows += f"""
                <tr>
                    <td><strong>{short_code}</strong></td>
                    <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">{original_url}</td>
                    <td>{custom_name or '-'}</td>
                    <td>{campaign_name or '-'}</td>
                    <td>{created_at}</td>
                    <td>{click_count}</td>
                    <td>{unique_count}</td>
                    <td>{qr_count}</td>
                    <td>
                        <a href="/analytics/{short_code}" target="_blank" class="action-btn analytics-btn">📈 分析</a>
                        <a href="/{short_code}?source=qr" target="_blank" class="action-btn qr-btn">🔗 QR</a>
                        <a href="/api/export/csv/{short_code}" class="action-btn export-btn">📊 CSV</a>
                    </td>
                </tr>
            """
        
        # HTMLをレンダリング
        html_content = ADMIN_HTML \
            .replace("{{ total_urls }}", str(total_urls)) \
            .replace("{{ total_clicks }}", str(total_clicks)) \
            .replace("{{ unique_clicks }}", str(unique_clicks)) \
            .replace("{{ qr_clicks }}", str(qr_clicks)) \
            .replace("{{ table_rows }}", table_rows)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        error_html = f"<h1>Error</h1><p>{str(e)}</p>"
        return HTMLResponse(content=error_html, status_code=500)

