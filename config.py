import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 确保加载.env文件
load_dotenv()

class Settings(BaseSettings):
    # OpenRouter API配置
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # LumiLove应用信息 - 必须设置正确！
    app_name: str = "LumiLove"  # 固定为LumiLove
    app_url: str = "https://main.d3m01u43jjmlec.amplifyapp.com/"  # 您的应用URL
    
    # 数据库配置 - 添加默认值，避免None导致的错误
    database_url: str = os.getenv("DATABASE_URL", "jdbc:postgresql://lumilovedb1.chwuqka62eu2.ap-southeast-2.rds.amazonaws.com:5432/Lumilovedb01")
    
    # 向量数据库配置
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    
    # API设置
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8001"))
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # RAG设置
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # 约22MB
    max_context_length: int = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
    top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))
    
    class Config:
        env_file = ".env"

settings = Settings()

# 添加配置验证
if not settings.database_url:
    raise ValueError("DATABASE_URL 环境变量未设置")

if not settings.openrouter_api_key:
    print("⚠️  警告: OPENROUTER_API_KEY 未设置，某些功能可能无法正常工作")

# 确保LumiLove标识信息正确
print(f"🏷️  应用名称: {settings.app_name}")
print(f"🔗 应用URL: {settings.app_url}")
