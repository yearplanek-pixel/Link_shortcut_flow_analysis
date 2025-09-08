import string
import random
import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional  # Optionalを追加
from config import QR_AVAILABLE, UA_AVAILABLE

def generate_short_code(length: int = 6, conn=None) -> str:

    """短縮コードを生成"""
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM urls WHERE short_code = ?", (code,))
            if not cursor.fetchone():
                return code
        else:
            return code

def generate_qr_code_base64(url: str, size: int = 200) -> Optional[str]:
    """QRコードをBase64で生成"""
    if not QR_AVAILABLE:
        return None
    
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image = qr_image.resize((size, size))
        
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    except Exception:
        return None

def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """User Agentを解析"""
    if not UA_AVAILABLE:
        return {'device_type': 'unknown', 'browser': 'unknown', 'os': 'unknown'}
    
    try:
        from user_agents import parse
        ua = parse(user_agent)
        return {
            'device_type': 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'desktop',
            'browser': f"{ua.browser.family} {ua.browser.version_string}",
            'os': f"{ua.os.family} {ua.os.version_string}"
        }
    except Exception:
        return {'device_type': 'unknown', 'browser': 'unknown', 'os': 'unknown'}

def get_location_info(ip_address: str) -> Dict[str, str]:
    """IPアドレスから位置情報を取得"""
    # 簡易的な実装（実際にはIP情報サービスを使用）
    return {
        'country': 'Unknown',
        'region': 'Unknown', 
        'city': 'Unknown',
        'timezone': 'Unknown'
    }

def parse_utm_parameters(referrer: str) -> Dict[str, str]:
    """UTMパラメータを解析"""
    # 簡易的な実装
    return {}