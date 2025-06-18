from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from config import settings
from models.database import create_tables
from api.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("🚀 启动RAG聊天服务...")
    
    # 创建数据库表
    try:
        create_tables()
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
    
    # 初始化向量数据库
    try:
        from services.vector_store import vector_store_service
        stats = vector_store_service.get_collection_stats()
        print(f"✅ 向量数据库初始化成功，当前文档数: {stats['total_documents']}")
    except Exception as e:
        print(f"❌ 向量数据库初始化失败: {e}")
    
    yield
    
    # 关闭时执行
    print("🛑 RAG聊天服务关闭")

# 创建FastAPI应用
app = FastAPI(
    title="RAG聊天服务",
    description="基于FastAPI + LangChain + RAG的智能聊天服务，具有记忆能力",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(chat_router)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        from services.vector_store import vector_store_service
        stats = vector_store_service.get_collection_stats()
        
        return {
            "status": "healthy",
            "service": "RAG Chat Service",
            "vector_db_stats": stats,
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务健康检查失败: {str(e)}")

# 根路径
@app.get("/")
async def root():
    return {
        "message": "欢迎使用RAG聊天服务",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    ) 