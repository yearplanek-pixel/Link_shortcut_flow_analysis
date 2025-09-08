from fastapi import APIRouter, HTTPException
import sqlite3
from models import URLCreate, URLResponse
from config import DB_PATH, BASE_URL
from utils import generate_short_code, generate_qr_code_base64

router = APIRouter()

@router.post("/api/shorten", response_model=URLResponse)
async def shorten_url(url_data: URLCreate):
    """URL短縮エンドポイント"""
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
            short_code = generate_short_code(conn=conn)
        
        # URLを保存
        cursor.execute('''
            INSERT INTO urls (short_code, original_url, custom_name, campaign_name, created_by) 
            VALUES (?, ?, ?, ?, ?)
        ''', (short_code, url_data.original_url, url_data.custom_name, url_data.campaign_name, 'api'))
        conn.commit()
        
        # 作成時刻取得
        cursor.execute("SELECT created_at FROM urls WHERE short_code = ?", (short_code,))
        created_at = cursor.fetchone()[0]
        
        # URL生成
        short_url = f"{BASE_URL}/{short_code}"
        qr_url = f"{BASE_URL}/{short_code}?source=qr"
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
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")