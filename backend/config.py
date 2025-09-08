import os
from typing import Optional  # Optionalを追加

from dotenv import load_dotenv

load_dotenv()

# 基本設定
def get_base_url() -> str:  # 戻り値の型ヒントを追加
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
    except Exception:
        return "http://localhost:8000"

BASE_URL = os.getenv("BASE_URL", "https://your-app-name.railway.app")
DB_PATH = os.getenv("DB_PATH", "url_shortener.db")

# ライブラリ可用性チェック
try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE: bool = True
except ImportError:
    QR_AVAILABLE: bool = False

try:
    import user_agents
    UA_AVAILABLE: bool = True
except ImportError:
    UA_AVAILABLE: bool = False

try:
    import pandas as pd
    PANDAS_AVAILABLE: bool = True
except ImportError:
    PANDAS_AVAILABLE: bool = False