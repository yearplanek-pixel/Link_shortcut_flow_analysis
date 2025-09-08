from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
from contextlib import asynccontextmanager
import config
from routes import redirect_router, shorten_router, analytics_router, bulk_router, export_router, admin_router
from database import init_db

# ライフスパンハンドラーを使用
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時処理
    print("🚀 Starting Enhanced Link Tracker API...")
    print(f"🌐 Base URL: {config.BASE_URL}")
    
    success = init_db()
    if success:
        print("✅ Enhanced database initialized successfully!")
        print(f"📊 管理画面: {config.BASE_URL}/admin")
        print(f"🔗 一括生成: {config.BASE_URL}/bulk")
        print(f"📈 分析例: {config.BASE_URL}/analytics/test123")
        print(f"📊 API Docs: {config.BASE_URL}/docs")
    else:
        print("❌ Database initialization failed!")
    
    yield  # アプリケーション実行中
    
    # シャットダウン時処理
    print("🛑 Shutting down...")

app = FastAPI(
    title="Enhanced Link Tracker API", 
    version="2.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録 - 順序が重要！
app.include_router(admin_router)      # /admin, /bulk など
app.include_router(analytics_router)  # /analytics/{short_code}
app.include_router(bulk_router)       # /bulk と /api/bulk-generate
app.include_router(shorten_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(redirect_router)   # 最後に動的なルート {short_code}

# ルートページ
@app.get("/")
async def root():
    return {
        "message": "Enhanced Link Tracker API v2.0",
        "endpoints": {
            "admin_dashboard": f"{config.BASE_URL}/admin",
            "bulk_generation": f"{config.BASE_URL}/bulk",
            "api_docs": f"{config.BASE_URL}/docs",
            "health_check": f"{config.BASE_URL}/health"
        }
    }

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "base_url": config.BASE_URL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)