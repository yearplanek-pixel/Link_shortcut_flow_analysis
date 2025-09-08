# 統計管理画面（更新版）
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """統計管理画面"""
    return HTMLResponse(content=STATS_HTML)

# リダイレクト処理（UTM・時間データ記録強化版）
@app.get("/{short_code}")
async def redirect_url(short_code: str, request: Request, source: Optional[str] = None):
    print(f"🔍 Looking for short_code: '{short_code}'")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URL取得
        cursor.execute(
            "SELECT id, original_url FROM urls WHERE short_code = ? AND is_active = TRUE",
            (short_code,)
        )
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ URL not found for short_code: '{short_code}'")
            raise HTTPException(status_code=404, detail=f"Short URL '{short_code}' not found")
        
        url_id, original_url = result
        print(f"✅ Found URL: {short_code} -> {original_url}")
        
        # クリック情報を記録（強化版）
        try:
            client_ip = getattr(request.client, 'host', 'unknown')
            user_agent = request.headers.get("user-agent", "")
            referrer = request.headers.get("referer", "")
            
            # 現在時刻の詳細情報
            now = datetime.now()
            hour_of_day = now.hour
            day_of_week = now.weekday()  # 月曜=0, 日曜=6
            
            # ソース判定（強化版）
            click_source = "direct"
            if source == "qr":
                click_source = "qr"
            elif referrer:
                referrer_lower = referrer.lower()
                if any(domain in referrer_lower for domain in ["twitter.com", "t.co", "x.com"]):
                    click_source = "twitter"
                elif "facebook.com" in referrer_lower or "fb.me" in referrer_lower:
                    click_source = "facebook"
                elif "google.com" in referrer_lower:
                    click_source = "google"
                elif "youtube.com" in referrer_lower or "youtu.be" in referrer_lower:
                    click_source = "youtube"
                elif "instagram.com" in referrer_lower:
                    click_source = "instagram"
                elif "linkedin.com" in referrer_lower:
                    click_source = "linkedin"
                elif "tiktok.com" in referrer_lower:
                    click_source = "tiktok"
                else:
                    click_source = "referrer"
            
            # 地理情報取得（タイムゾーン付き）
            location_info = get_location_info(client_ip)
            
            # User Agent解析
            ua_info = parse_user_agent(user_agent)
            
            # UTMパラメータ解析
            utm_info = parse_utm_parameters(referrer)
            
            # クリック情報をデータベースに保存（全フィールド）
            cursor.execute('''
                INSERT INTO clicks (
                    url_id, ip_address, country, region, city, timezone,
                    user_agent, referrer, device_type, browser, os, source,
                    utm_source, utm_medium, utm_campaign,
                    hour_of_day, day_of_week
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url_id, client_ip, location_info['country'], 
                location_info['region'], location_info['city'], location_info['timezone'],
                user_agent, referrer, ua_info['device_type'],
                ua_info['browser'], ua_info['os'], click_source,
                utm_info.get('utm_source'), utm_info.get('utm_medium'), utm_info.get('utm_campaign'),
                hour_of_day, day_of_week
            ))
            conn.commit()
            
            print(f"✅ Enhanced click recorded: {short_code} (source: {click_source}, device: {ua_info['device_type']}, location: {location_info['country']})")
            
        except Exception as e:
            print(f"⚠️  Failed to record click: {e}")
        
        conn.close()
        print(f"🔄 Redirecting to: {original_url}")
        return RedirectResponse(url=original_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in redirect: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

# URL短縮エンドポイント（強化版）
@app.post("/api/shorten", response_model=URLResponse)
async def shorten_url(url_data: URLCreate):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # カスタムスラッグの処理
        if url_data.custom_slug:
            cursor.execute("SELECT id FROM urls WHERE short_code = ?", (url_data.custom_slug,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Custom slug already exists")
            short_code = url_data.custom_slug
        else:
            # ランダムな短縮コード生成（重複チェック付き）
            short_code = generate_short_code(conn=conn)
        
        # URLを保存（強化版）
        cursor.execute('''
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_by) 
            VALUES (?, ?, ?, ?, ?)
        ''', (short_code, url_data.original_url, url_data.custom_name, url_data.campaign_name, 'api'))
        conn.commit()
        
        # 作成時刻取得
        cursor.execute("SELECT created_at FROM urls WHERE short_code = ?", (short_code,))
        created_at = cursor.fetchone()[0]
        
        # URLs作成
        short_url = f"{BASE_URL}/{short_code}"
        qr_url = f"{BASE_URL}/{short_code}?source=qr"
        
        # QRコード生成
        qr_code_base64 = generate_qr_code_base64(qr_url)
        
        response = URLResponse(
            short_code=short_code,
            original_url=url_data.original_url,
            short_url=short_url,
            qr_url=qr_url,
            qr_code_base64=qr_code_base64,
            created_at=created_at,
            custom_name=url_data.custom_name,
            campaign_name=url_data.campaign_name
        )
        
        conn.close()
        print(f"✅ Created enhanced short URL: {short_url}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in shorten_url: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 統計情報取得（強化版）
@app.get("/api/stats/{short_code}")
async def get_stats(short_code: str):
    """基本統計情報を取得"""
    return await get_detailed_analytics(short_code)

# 全URL一覧取得（強化版）
@app.get("/api/urls")
async def get_urls():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.short_code, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as click_count,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks,
                   COUNT(DISTINCT c.ip_address) as unique_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.is_active = TRUE
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''')
        
        results = cursor.fetchall()
        urls = []
        
        for row in results:
            short_url = f"{BASE_URL}/{row[0]}"
            qr_url = f"{BASE_URL}/{row[0]}?source=qr"
            
            urls.append({
                "short_code": row[0],
                "original_url": row[1],
                "created_at": row[2],
                "custom_name": row[3],
                "campaign_name": row[4],
                "click_count": row[5],
                "qr_clicks": row[6],
                "unique_clicks": row[7],
                "other_clicks": row[5] - row[6],
                "short_url": short_url,
                "qr_url": qr_url,
                "analytics_url": f"{BASE_URL}/analytics/{row[0]}",
                "qr_code_base64": generate_qr_code_base64(qr_url, 150)
            })
        
        conn.close()
        return {"urls": urls}
        
    except Exception as e:
        print(f"❌ Error getting URLs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# キャンペーン別分析
@app.get("/api/analytics/campaign/{campaign_name}")
async def get_campaign_analytics(campaign_name: str):
    """キャンペーン別の分析データを取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # キャンペーンのURL一覧と統計
        cursor.execute('''
            SELECT u.short_code, u.original_url, u.custom_name,
                   COUNT(c.id) as clicks,
                   COUNT(DISTINCT c.ip_address) as unique_visitors,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.campaign_name = ? AND u.is_active = TRUE
            GROUP BY u.id
            ORDER BY clicks DESC
        ''', (campaign_name,))
        
        urls_data = cursor.fetchall()
        
        if not urls_data:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # 総計算
        total_clicks = sum(row[3] for row in urls_data)
        total_unique = sum(row[4] for row in urls_data)
        total_qr = sum(row[5] for row in urls_data)
        
        # 時系列データ（キャンペーン全体）
        cursor.execute('''
            SELECT date(c.created_at) as date, COUNT(*) as clicks
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            WHERE u.campaign_name = ?
            AND c.created_at >= datetime('now', '-30 days')
            GROUP BY date
            ORDER BY date
        ''', (campaign_name,))
        
        daily_data = cursor.fetchall()
        
        # デバイス別統計（キャンペーン全体）
        cursor.execute('''
            SELECT c.device_type, COUNT(*) as count
            FROM clicks c
            JOIN urls u ON c.url_id = u.id
            WHERE u.campaign_name = ?
            GROUP BY c.device_type
            ORDER BY count DESC
        ''', (campaign_name,))
        
        device_data = cursor.fetchall()
        
        conn.close()
        
        return {
            "campaign_name": campaign_name,
            "summary": {
                "total_urls": len(urls_data),
                "total_clicks": total_clicks,
                "unique_visitors": total_unique,
                "qr_clicks": total_qr,
                "conversion_rate": f"{(total_qr/max(total_clicks, 1)*100):.1f}%"
            },
            "urls": [{
                "short_code": row[0],
                "original_url": row[1],
                "custom_name": row[2],
                "clicks": row[3],
                "unique_visitors": row[4],
                "qr_clicks": row[5],
                "analytics_url": f"{BASE_URL}/analytics/{row[0]}"
            } for row in urls_data],
            "daily_performance": [{"date": d[0], "clicks": d[1]} for d in daily_data],
            "device_breakdown": [{"device": d[0], "count": d[1]} for d in device_data]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Campaign analytics failed: {str(e)}")

# エクスポート機能
@app.get("/api/export/csv/{short_code}")
async def export_clicks_csv(short_code: str):
    """クリック データをCSVでエクスポート"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URL存在確認
        cursor.execute("SELECT id, original_url FROM urls WHERE short_code = ?", (short_code,))
        url_info = cursor.fetchone()
        if not url_info:
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        url_id = url_info[0]
        
        # クリックデータ取得
        cursor.execute('''
            SELECT created_at, ip_address, country, region, city, 
                   device_type, browser, os, source, referrer,
                   utm_source, utm_medium, utm_campaign
            FROM clicks 
            WHERE url_id = ? 
            ORDER BY created_at DESC
        ''', (url_id,))
        
        clicks_data = cursor.fetchall()
        conn.close()
        
        # CSVデータ作成
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow([
            'DateTime', 'IP_Address', 'Country', 'Region', 'City',
            'Device_Type', 'Browser', 'OS', 'Source', 'Referrer',
            'UTM_Source', 'UTM_Medium', 'UTM_Campaign'
        ])
        
        # データ行
        for row in clicks_data:
            writer.writerow(row)
        
        output.seek(0)
        csv_content = output.getvalue()
        
        # レスポンス作成
        response = Response(
            content=csv_content,
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="clicks_{short_code}_{datetime.now().strftime("%Y%m%d")}.csv"'
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")

# アプリ起動時処理
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Enhanced Link Tracker API...")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"📄 Database path: {os.path.abspath(DB_PATH)}")
    
    success = init_db()
    
    if success:
        print("✅ Enhanced database initialized successfully!")
        print(f"📊 管理画面: {BASE_URL}/admin")
        print(f"🔗 一括生成: {BASE_URL}/bulk")
        print(f"📈 分析例: {BASE_URL}/analytics/test123")
        print(f"📊 API Docs: {BASE_URL}/docs")
        print(f"🔍 Debug: {BASE_URL}/debug/db-status")
    else:
        print("❌ Database initialization failed!")

# QRコード生成エンドポイント
@app.get("/api/qr/{short_code}")
async def generate_qr_code_endpoint(short_code: str, size: int = 200):
    """指定された短縮URLのQRコードを生成"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT short_code FROM urls WHERE short_code = ? AND is_active = TRUE", (short_code,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        qr_url = f"{BASE_URL}/{short_code}?source=qr"
        
        if not QR_AVAILABLE:
            raise HTTPException(status_code=500, detail="QR code generation not available")
            
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        if size != 200:
            qr_image = qr_image.resize((size, size))
        
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return StreamingResponse(img_buffer, media_type="image/png")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"QR code generation error: {e}")
        raise HTTPException(status_code=500, detail="QR code generation failed")
    finally:
        conn.close()

# 既存のエンドポイントも継承（bulk_shorten, import_google_sheets等）
@app.post("/api/bulk-shorten")
async def bulk_shorten_urls(bulk_data: BulkURLCreate):
    """複数URLを一括で短縮（従来互換）"""
    try:
        # 新しいBulkGenerationRequestに変換
        items = [BulkGenerationItem(original_url=url, quantity=1) for url in bulk_data.urls]
        request = BulkGenerationRequest(items=items)
        
        # 新しいエンドポイントを使用
        return await bulk_generate_urls(request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Google Sheets インポート（継承）
@app.post("/api/import/google-sheets")
async def import_from_google_sheets(sheet_url: str):
    """Google SheetsからURLを一括インポート"""
    try:
        if "/edit" in sheet_url:
            csv_url = sheet_url.replace("/edit#gid=", "/export?format=csv&gid=").replace("/edit?gid=", "/export?format=csv&gid=")
            if "export?format=csv" not in csv_url:
                csv_url = sheet_url.replace("/edit", "/export?format=csv")
        else:
            csv_url = sheet_url
        
        print(f"📊 Importing from: {csv_url}")
        
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        rows = list(csv_reader)
        if len(rows) < 2:
            raise HTTPException(status_code=400, detail="スプレッドシートにデータが不足しています")
        
        headers = rows[0]
        print(f"📋 Headers: {headers}")
        
        # オリジナルURLカラムを特定
        original_url_col = None
        for i, header in enumerate(headers):
            if 'オリジナル' in header or 'original' in header.lower() or 'url' in header.lower():
                original_url_col = i
                break
        
        if original_url_col is None:
            original_url_col = 1 if len(headers) > 1 else 0
        
        # 一括生成用データに変換
        items = []
        for row_idx, row in enumerate(rows[1:], start=2):
            if len(row) <= original_url_col:
                continue
                
            original_url = row[original_url_col].strip()
            if not original_url or not original_url.startswith('http'):
                continue
            
            # カスタム名とキャンペーン名を抽出
            custom_name = None
            campaign_name = None
            
            if len(row) > 0 and row[0].strip():
                custom_name = f"import_row_{row[0].strip()}"
            
            # quantity列があるかチェック（C列想定）
            quantity = 1
            if len(row) > 2 and row[2].strip().isdigit():
                quantity = min(int(row[2].strip()), 10)
            
            items.append(BulkGenerationItem(
                original_url=original_url,
                quantity=quantity,
                custom_name=custom_name,
                campaign_name="google_sheets_import"
            ))
        
        if not items:
            raise HTTPException(status_code=400, detail="有効なURLが見つかりませんでした")
        
        # 一括生成実行
        request = BulkGenerationRequest(items=items)
        result = await bulk_generate_urls(request)
        
        # レスポンス形式を調整
        return {
            "source": "google_sheets",
            "sheet_url": sheet_url,
            "csv_url": csv_url,
            "total_rows": len(rows) - 1,
            "success_count": result["success_count"],
            "error_count": result["error_count"],
            "total_generated": result["total_generated"],
            "results": result["results"],
            "errors": result["errors"]
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"スプレッドシートの読み込みに失敗しました: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"インポート処理でエラーが発生しました: {str(e)}")

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "features": {
            "qr_available": QR_AVAILABLE,
            "ua_available": UA_AVAILABLE,
            "pandas_available": PANDAS_AVAILABLE
        },
        "database_path": os.path.abspath(DB_PATH)
    }

# ルートページ（更新版）
@app.get("/")
async def root():
    return {
        "message": "Enhanced Link Tracker API v2.0",
        "new_features": [
            "Bulk generation with custom quantities",
            "Detailed analytics with charts",
            "Campaign tracking",
            "UTM parameter support",
            "Enhanced device & geo tracking"
        ],
        "main_pages": {
            "admin_dashboard": f"{BASE_URL}/admin",
            "bulk_generation": f"{BASE_URL}/bulk",
            "api_docs": f"{BASE_URL}/docs"
        },
        "api_endpoints": {
            "shorten": f"{BASE_URL}/api/shorten",
            "bulk_generate": f"{BASE_URL}/api/bulk-generate",
            "analytics": f"{BASE_URL}/api/stats/{{short_code}}",
            "campaign_analytics": f"{BASE_URL}/api/analytics/campaign/{{campaign_name}}",
            "export_csv": f"{BASE_URL}/api/export/csv/{{short_code}}"
        },
        "examples": {
            "analytics_page": f"{BASE_URL}/analytics/test123",
            "bulk_page": f"{BASE_URL}/bulk"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced FastAPI server...")
    print(f"📍 Server: http://0.0.0.0:8000")
    print(f"📊 管理画面: {BASE_URL}/admin")
    print(f"🔗 一括生成: {BASE_URL}/bulk")
    print(f"📈 分析例: {BASE_URL}/analytics/test123")
    uvicorn.run(app, host="0.0.0.0", port=8000)from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
import sqlite3
import string
import random
import requests
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import base64
from io import BytesIO
import csv
import json
import io

# 必要なライブラリの確認とインポート
try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: qrcode or PIL not installed. Run: pip install qrcode[pil] pillow")
    QR_AVAILABLE = False

try:
    import user_agents
    UA_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: user_agents not installed. Run: pip install user-agents")
    UA_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: pandas not installed. Run: pip install pandas")
    PANDAS_AVAILABLE = False

app = FastAPI(title="Enhanced Link Tracker API", version="2.0.0")

# 簡単なベースURL設定
def get_base_url():
    base_url = os.getenv('BASE_URL')
    if base_url:
        return base_url.rstrip('/')
    
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return f"http://{local_ip}:8000"
    except Exception as e:
        print(f"⚠️  IP auto-detection failed: {e}")
        return "http://localhost:8000"

BASE_URL = get_base_url()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベースファイルのパス
DB_PATH = 'linktracker.db'

# データベース初期化（強化版）
def init_db():
    print(f"🔧 Initializing enhanced database at: {os.path.abspath(DB_PATH)}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # URLsテーブル（強化版）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                custom_name TEXT DEFAULT NULL,
                campaign_name TEXT DEFAULT NULL,
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
                utm_source TEXT DEFAULT NULL,
                utm_medium TEXT DEFAULT NULL,
                utm_campaign TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hour_of_day INTEGER DEFAULT NULL,
                day_of_week INTEGER DEFAULT NULL,
                FOREIGN KEY (url_id) REFERENCES urls (id)
            )
        ''')
        
        # 新しい列を既存テーブルに追加（存在しない場合）
        new_columns = [
            ("urls", "custom_name", "TEXT DEFAULT NULL"),
            ("urls", "campaign_name", "TEXT DEFAULT NULL"),
            ("urls", "created_by", "TEXT DEFAULT 'system'"),
            ("clicks", "timezone", "TEXT DEFAULT 'Unknown'"),
            ("clicks", "utm_source", "TEXT DEFAULT NULL"),
            ("clicks", "utm_medium", "TEXT DEFAULT NULL"),
            ("clicks", "utm_campaign", "TEXT DEFAULT NULL"),
            ("clicks", "hour_of_day", "INTEGER DEFAULT NULL"),
            ("clicks", "day_of_week", "INTEGER DEFAULT NULL")
        ]
        
        for table, column, definition in new_columns:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"✅ Added {column} column to {table} table")
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

# 一括生成管理画面HTML
BULK_GENERATION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>一括リンク生成 - Link Tracker</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        .form-section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .spreadsheet-container { margin: 20px 0; }
        .spreadsheet-table { width: 100%; border-collapse: collapse; }
        .spreadsheet-table th, .spreadsheet-table td { border: 1px solid #ddd; padding: 8px; }
        .spreadsheet-table th { background: #4CAF50; color: white; text-align: center; }
        .spreadsheet-table input { width: 100%; border: none; padding: 5px; }
        .add-row-btn, .generate-btn, .clear-btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
        .add-row-btn { background: #2196F3; color: white; }
        .generate-btn { background: #4CAF50; color: white; font-size: 16px; font-weight: bold; }
        .clear-btn { background: #f44336; color: white; }
        .results-section { margin: 30px 0; }
        .result-item { background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .error-item { background: #ffebee; border-left: 4px solid #f44336; }
        .stats-link { color: #1976d2; text-decoration: none; font-weight: bold; }
        .stats-link:hover { text-decoration: underline; }
        .copy-btn { background: #FF9800; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin-left: 10px; }
        .loading { text-align: center; padding: 20px; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 一括リンク生成システム</h1>
        
        <div class="form-section">
            <h2>📝 リンク生成テーブル</h2>
            <p><strong>使い方:</strong></p>
            <ul>
                <li><strong>B列</strong>: 生成したいオリジナルリンクを入力</li>
                <li><strong>C列</strong>: 生成する数量（空白の場合は1つ）</li>
                <li><strong>D列</strong>: カスタム名（任意、分析用）</li>
                <li><strong>E列</strong>: キャンペーン名（任意、分析用）</li>
            </ul>
            
            <div class="spreadsheet-container">
                <table class="spreadsheet-table" id="spreadsheetTable">
                    <thead>
                        <tr>
                            <th style="width: 5%;">A<br>行番号</th>
                            <th style="width: 40%;">B<br>オリジナルリンク</th>
                            <th style="width: 10%;">C<br>生成数量</th>
                            <th style="width: 20%;">D<br>カスタム名</th>
                            <th style="width: 20%;">E<br>キャンペーン名</th>
                            <th style="width: 5%;">操作</th>
                        </tr>
                    </thead>
                    <tbody id="spreadsheetBody">
                        <tr>
                            <td>1</td>
                            <td><input type="url" placeholder="https://example.com" /></td>
                            <td><input type="number" min="1" max="10" placeholder="1" /></td>
                            <td><input type="text" placeholder="商品A" /></td>
                            <td><input type="text" placeholder="春キャンペーン" /></td>
                            <td><button onclick="removeRow(this)">❌</button></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div style="text-align: center; margin: 20px 0;">
                <button class="add-row-btn" onclick="addRow()">➕ 行を追加</button>
                <button class="clear-btn" onclick="clearAll()">🗑️ 全削除</button>
                <button class="generate-btn" onclick="generateLinks()" id="generateBtn">🚀 一括生成開始</button>
            </div>
        </div>
        
        <div class="results-section" id="resultsSection" style="display: none;">
            <h2>📈 生成結果</h2>
            <div id="resultsContent"></div>
        </div>
    </div>

    <script>
        let rowCounter = 1;
        
        function addRow() {
            rowCounter++;
            const tbody = document.getElementById('spreadsheetBody');
            const newRow = tbody.insertRow();
            newRow.innerHTML = `
                <td>${rowCounter}</td>
                <td><input type="url" placeholder="https://example.com" /></td>
                <td><input type="number" min="1" max="10" placeholder="1" /></td>
                <td><input type="text" placeholder="商品${String.fromCharCode(64 + rowCounter)}" /></td>
                <td><input type="text" placeholder="春キャンペーン" /></td>
                <td><button onclick="removeRow(this)">❌</button></td>
            `;
        }
        
        function removeRow(button) {
            const row = button.closest('tr');
            row.remove();
            updateRowNumbers();
        }
        
        function updateRowNumbers() {
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            rows.forEach((row, index) => {
                row.cells[0].textContent = index + 1;
            });
            rowCounter = rows.length;
        }
        
        function clearAll() {
            if (confirm('全てのデータを削除しますか？')) {
                document.getElementById('spreadsheetBody').innerHTML = `
                    <tr>
                        <td>1</td>
                        <td><input type="url" placeholder="https://example.com" /></td>
                        <td><input type="number" min="1" max="10" placeholder="1" /></td>
                        <td><input type="text" placeholder="商品A" /></td>
                        <td><input type="text" placeholder="春キャンペーン" /></td>
                        <td><button onclick="removeRow(this)">❌</button></td>
                    </tr>
                `;
                rowCounter = 1;
                document.getElementById('resultsSection').style.display = 'none';
            }
        }
        
        async function generateLinks() {
            const btn = document.getElementById('generateBtn');
            const resultsSection = document.getElementById('resultsSection');
            const resultsContent = document.getElementById('resultsContent');
            
            // データ収集
            const rows = document.querySelectorAll('#spreadsheetBody tr');
            const data = [];
            
            for (let row of rows) {
                const inputs = row.querySelectorAll('input');
                const originalUrl = inputs[0].value.trim();
                const quantity = parseInt(inputs[1].value) || 1;
                const customName = inputs[2].value.trim();
                const campaignName = inputs[3].value.trim();
                
                if (originalUrl && originalUrl.startsWith('http')) {
                    data.push({
                        original_url: originalUrl,
                        quantity: Math.min(quantity, 10), // 最大10個まで
                        custom_name: customName || null,
                        campaign_name: campaignName || null
                    });
                }
            }
            
            if (data.length === 0) {
                alert('有効なURLを入力してください');
                return;
            }
            
            // 生成開始
            btn.disabled = true;
            btn.innerHTML = '⏳ 生成中...';
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading"><div class="spinner"></div><p>リンクを生成しています...</p></div>';
            
            try {
                const response = await fetch('/api/bulk-generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ items: data })
                });
                
                const result = await response.json();
                displayResults(result);
                
            } catch (error) {
                resultsContent.innerHTML = `<div class="error-item">エラー: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🚀 一括生成開始';
            }
        }
        
        function displayResults(result) {
            const resultsContent = document.getElementById('resultsContent');
            
            let html = `
                <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3>📊 生成サマリー</h3>
                    <p>総生成数: <strong>${result.total_generated}</strong> | 成功: <strong>${result.success_count}</strong> | エラー: <strong>${result.error_count}</strong></p>
                </div>
            `;
            
            if (result.results && result.results.length > 0) {
                html += '<h3>✅ 生成成功</h3>';
                result.results.forEach((item, index) => {
                    const urls = item.generated_urls;
                    html += `
                        <div class="result-item">
                            <p><strong>元URL:</strong> ${item.original_url}</p>
                            <p><strong>カスタム名:</strong> ${item.custom_name || 'なし'} | <strong>キャンペーン:</strong> ${item.campaign_name || 'なし'}</p>
                            <p><strong>生成されたリンク (${urls.length}個):</strong></p>
                            <ul>
                    `;
                    
                    urls.forEach((url, urlIndex) => {
                        html += `
                            <li>
                                <strong>${url.short_code}</strong>: 
                                <a href="${url.short_url}" target="_blank">${url.short_url}</a>
                                <button class="copy-btn" onclick="copyToClipboard('${url.short_url}')">📋</button>
                                <a href="/analytics/${url.short_code}" target="_blank" class="stats-link">📈 分析</a>
                                <br><small>QR: <a href="${url.qr_url}" target="_blank">${url.qr_url}</a></small>
                            </li>
                        `;
                    });
                    
                    html += '</ul></div>';
                });
            }
            
            if (result.errors && result.errors.length > 0) {
                html += '<h3>❌ エラー</h3>';
                result.errors.forEach(error => {
                    html += `<div class="error-item">URL: ${error.original_url} - エラー: ${error.error}</div>`;
                });
            }
            
            resultsContent.innerHTML = html;
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('クリップボードにコピーしました: ' + text);
            });
        }
    </script>
</body>
</html>
"""

# 詳細分析画面HTML
ANALYTICS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>詳細分析 - {short_code}</title>
    <meta charset="UTF-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #4CAF50; text-align: center; }
        .stat-label { text-align: center; color: #666; margin-top: 10px; font-weight: bold; }
        .chart-container { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .chart-wrapper { position: relative; height: 400px; }
        h1, h2 { color: #333; }
        .info-box { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .refresh-btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #4CAF50; color: white; }
        .trend-indicator { font-weight: bold; }
        .trend-up { color: #4CAF50; }
        .trend-down { color: #f44336; }
        .trend-neutral { color: #FF9800; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 詳細分析: {short_code}</h1>
        
        <div class="info-box">
            <p><strong>元URL:</strong> <a href="{original_url}" target="_blank">{original_url}</a></p>
            <p><strong>短縮URL:</strong> <a href="{short_url}" target="_blank">{short_url}</a></p>
            <p><strong>作成日:</strong> {created_at}</p>
            <div style="text-align: center; margin-top: 15px;">
                <button class="refresh-btn" onclick="location.reload()">🔄 データ更新</button>
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
            <div class="stat-card">
                <div class="stat-number">{click_rate:.1f}%</div>
                <div class="stat-label">QRコード率</div>
            </div>
        </div>

        <div class="chart-container">
            <h2>📊 時系列分析（過去30日間）</h2>
            <div class="chart-wrapper">
                <canvas id="timeChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>📱 デバイス別分析</h2>
            <div class="chart-wrapper">
                <canvas id="deviceChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>🌐 参照元分析</h2>
            <div class="chart-wrapper">
                <canvas id="sourceChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>🌍 地域別分析</h2>
            <div class="chart-wrapper">
                <canvas id="geoChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>🕐 時間帯分析</h2>
            <div class="chart-wrapper">
                <canvas id="hourlyChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>📅 曜日別分析</h2>
            <div class="chart-wrapper">
                <canvas id="weeklyChart"></canvas>
            </div>
        </div>

        <div class="chart-container">
            <h2>📋 詳細データ</h2>
            <table>
                <thead>
                    <tr>
                        <th>日付</th>
                        <th>クリック数</th>
                        <th>QRクリック</th>
                        <th>主要デバイス</th>
                        <th>主要参照元</th>
                    </tr>
                </thead>
                <tbody id="detailTableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // チャートデータの設定
        const analyticsData = {analytics_data};
        
        // 時系列チャート
        const timeCtx = document.getElementById('timeChart').getContext('2d');
        new Chart(timeCtx, {{
            type: 'line',
            data: {{
                labels: analyticsData.daily_labels,
                datasets: [{{
                    label: '総クリック数',
                    data: analyticsData.daily_clicks,
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }}, {{
                    label: 'QRクリック数',
                    data: analyticsData.daily_qr_clicks,
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // デバイス別チャート
        const deviceCtx = document.getElementById('deviceChart').getContext('2d');
        new Chart(deviceCtx, {{
            type: 'doughnut',
            data: {{
                labels: analyticsData.device_labels,
                datasets: [{{
                    data: analyticsData.device_data,
                    backgroundColor: ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#607D8B']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});

        // 参照元チャート
        const sourceCtx = document.getElementById('sourceChart').getContext('2d');
        new Chart(sourceCtx, {{
            type: 'bar',
            data: {{
                labels: analyticsData.source_labels,
                datasets: [{{
                    label: 'クリック数',
                    data: analyticsData.source_data,
                    backgroundColor: '#4CAF50'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 地域別チャート
        const geoCtx = document.getElementById('geoChart').getContext('2d');
        new Chart(geoCtx, {{
            type: 'bar',
            data: {{
                labels: analyticsData.geo_labels,
                datasets: [{{
                    label: 'クリック数',
                    data: analyticsData.geo_data,
                    backgroundColor: '#2196F3'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {{
                    x: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 時間帯チャート
        const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
        new Chart(hourlyCtx, {{
            type: 'bar',
            data: {{
                labels: ['0時', '1時', '2時', '3時', '4時', '5時', '6時', '7時', '8時', '9時', '10時', '11時', 
                        '12時', '13時', '14時', '15時', '16時', '17時', '18時', '19時', '20時', '21時', '22時', '23時'],
                datasets: [{{
                    label: 'クリック数',
                    data: analyticsData.hourly_data,
                    backgroundColor: '#FF9800'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 曜日別チャート
        const weeklyCtx = document.getElementById('weeklyChart').getContext('2d');
        new Chart(weeklyCtx, {{
            type: 'bar',
            data: {{
                labels: ['月曜日', '火曜日', '水曜日', '木曜日', '金曜日', '土曜日', '日曜日'],
                datasets: [{{
                    label: 'クリック数',
                    data: analyticsData.weekly_data,
                    backgroundColor: '#9C27B0'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 詳細テーブルの設定
        function populateDetailTable() {{
            const tbody = document.getElementById('detailTableBody');
            const details = analyticsData.daily_details;
            
            details.forEach(detail => {{
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${{detail.date}}</td>
                    <td>${{detail.clicks}}</td>
                    <td>${{detail.qr_clicks}}</td>
                    <td>${{detail.top_device}}</td>
                    <td>${{detail.top_source}}</td>
                `;
            }});
        }}

        populateDetailTable();
    </script>
</body>
</html>
"""

# Pydanticモデル
class URLCreate(BaseModel):
    original_url: str
    custom_slug: Optional[str] = None
    custom_name: Optional[str]

    if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)