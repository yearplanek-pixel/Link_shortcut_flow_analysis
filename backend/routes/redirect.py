from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import sqlite3
from datetime import datetime
from typing import Optional
from config import DB_PATH
from utils import get_location_info, parse_user_agent, parse_utm_parameters

router = APIRouter()

# 除外するパスのリスト
EXCLUDED_PATHS = {'admin', 'bulk', 'docs', 'health', 'analytics', 'api', 'favicon.ico'}

@router.get("/{short_code}")
async def redirect_url(short_code: str, request: Request, source: Optional[str] = None):
    """リダイレクト処理"""
    
    # 特別なパスは除外（404を返す）
    if short_code in EXCLUDED_PATHS:
        raise HTTPException(status_code=404, detail="Not Found")
    
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
        
        # クリック情報記録
        try:
            client_ip = getattr(request.client, 'host', 'unknown')
            user_agent = request.headers.get("user-agent", "")
            referrer = request.headers.get("referer", "")
            
            now = datetime.now()
            hour_of_day = now.hour
            day_of_week = now.weekday()
            
            # ソース判定
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
            
            location_info = get_location_info(client_ip)
            ua_info = parse_user_agent(user_agent)
            utm_info = parse_utm_parameters(referrer)
            
            # クリック情報をデータベースに保存
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
            
            print(f"✅ Click recorded: {short_code} (source: {click_source})")
            
        except Exception as e:
            print(f"⚠️  Failed to record click: {e}")
            # クリック記録に失敗してもリダイレクトは続行
        
        conn.close()
        return RedirectResponse(url=original_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in redirect: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")