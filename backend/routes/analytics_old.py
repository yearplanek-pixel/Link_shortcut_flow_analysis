from fastapi import APIRouter, HTTPException
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any
from config import DB_PATH, BASE_URL

router = APIRouter()

async def get_detailed_analytics(short_code: str) -> Dict[str, Any]:
    """詳細な分析データを取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 基本情報取得
        cursor.execute('''
            SELECT u.id, u.original_url, u.created_at, u.custom_name, u.campaign_name,
                   COUNT(c.id) as total_clicks,
                   COUNT(DISTINCT c.ip_address) as unique_clicks,
                   COUNT(CASE WHEN c.source = 'qr' THEN 1 END) as qr_clicks
            FROM urls u
            LEFT JOIN clicks c ON u.id = c.url_id
            WHERE u.short_code = ? AND u.is_active = TRUE
            GROUP BY u.id
        ''', (short_code,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Short URL not found")
        
        url_id, original_url, created_at, custom_name, campaign_name, total_clicks, unique_clicks, qr_clicks = result
        
        # 時系列データ
        cursor.execute('''
            SELECT date(created_at) as date, COUNT(*) as clicks,
                   COUNT(CASE WHEN source = 'qr' THEN 1 END) as qr_clicks
            FROM clicks
            WHERE url_id = ? AND created_at >= datetime('now', '-30 days')
            GROUP BY date
            ORDER BY date
        ''', (url_id,))
        
        daily_data = cursor.fetchall()
        
        # デバイス別統計
        cursor.execute('''
            SELECT device_type, COUNT(*) as count
            FROM clicks
            WHERE url_id = ?
            GROUP BY device_type
            ORDER BY count DESC
        ''', (url_id,))
        
        device_data = cursor.fetchall()
        
        # 参照元別統計
        cursor.execute('''
            SELECT source, COUNT(*) as count
            FROM clicks
            WHERE url_id = ?
            GROUP BY source
            ORDER BY count DESC
        ''', (url_id,))
        
        source_data = cursor.fetchall()
        
        # 地域別統計
        cursor.execute('''
            SELECT country, COUNT(*) as count
            FROM clicks
            WHERE url_id = ? AND country != 'Unknown'
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
        ''', (url_id,))
        
        geo_data = cursor.fetchall()
        
        # 時間帯別統計
        cursor.execute('''
            SELECT hour_of_day, COUNT(*) as count
            FROM clicks
            WHERE url_id = ? AND hour_of_day IS NOT NULL
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        ''', (url_id,))
        
        hourly_data = [0] * 24
        for hour, count in cursor.fetchall():
            if 0 <= hour < 24:
                hourly_data[hour] = count
        
        # 曜日別統計
        cursor.execute('''
            SELECT day_of_week, COUNT(*) as count
            FROM clicks
            WHERE url_id = ? AND day_of_week IS NOT NULL
            GROUP BY day_of_week
            ORDER BY day_of_week
        ''', (url_id,))
        
        weekly_data = [0] * 7
        for day, count in cursor.fetchall():
            if 0 <= day < 7:
                weekly_data[day] = count
        
        conn.close()
        
        # チャート用データ整形
        daily_labels = [str(row[0]) for row in daily_data]
        daily_clicks = [row[1] for row in daily_data]
        daily_qr_clicks = [row[2] for row in daily_data]
        
        device_labels = [row[0] for row in device_data]
        device_counts = [row[1] for row in device_data]
        
        source_labels = [row[0] for row in source_data]
        source_counts = [row[1] for row in source_data]
        
        geo_labels = [row[0] for row in geo_data]
        geo_counts = [row[1] for row in geo_data]
        
        # 日別詳細データ
        daily_details = []
        for date, clicks, qr_clicks in daily_data:
            cursor.execute('''
                SELECT device_type, source, COUNT(*) 
                FROM clicks 
                WHERE url_id = ? AND date(created_at) = ?
                GROUP BY device_type, source 
                ORDER BY COUNT(*) DESC 
                LIMIT 1
            ''', (url_id, date))
            
            top_result = cursor.fetchone()
            top_device = top_result[0] if top_result else 'unknown'
            top_source = top_result[1] if top_result else 'direct'
            
            daily_details.append({
                'date': date,
                'clicks': clicks,
                'qr_clicks': qr_clicks,
                'top_device': top_device,
                'top_source': top_source
            })
        
        return {
            'short_code': short_code,
            'original_url': original_url,
            'created_at': created_at,
            'custom_name': custom_name,
            'campaign_name': campaign_name,
            'total_clicks': total_clicks,
            'unique_clicks': unique_clicks,
            'qr_clicks': qr_clicks,
            'click_rate': (qr_clicks / total_clicks * 100) if total_clicks > 0 else 0,
            'short_url': f"{BASE_URL}/{short_code}",
            'daily_labels': daily_labels,
            'daily_clicks': daily_clicks,
            'daily_qr_clicks': daily_qr_clicks,
            'device_labels': device_labels,
            'device_data': device_counts,
            'source_labels': source_labels,
            'source_data': source_counts,
            'geo_labels': geo_labels,
            'geo_data': geo_counts,
            'hourly_data': hourly_data,
            'weekly_data': weekly_data,
            'daily_details': daily_details
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")

@router.get("/stats/{short_code}")
async def get_stats(short_code: str):
    """基本統計情報を取得"""
    return await get_detailed_analytics(short_code)

@router.get("/analytics/campaign/{campaign_name}")
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
        
        # 時系列データ
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
        
        # デバイス別統計
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