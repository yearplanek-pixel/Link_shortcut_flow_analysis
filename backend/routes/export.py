from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import sqlite3
import csv
import io
from datetime import datetime
from config import DB_PATH

router = APIRouter()

@router.get("/export/csv/{short_code}")
async def export_clicks_csv(short_code: str):
    """クリックデータをCSVでエクスポート"""
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