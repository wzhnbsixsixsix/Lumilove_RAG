from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import settings

# 创建数据库引擎
engine = create_engine(settings.database_url, echo=settings.debug)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ChatHistory(Base):
    """聊天历史记录表 - 与SpringBoot完全兼容"""
    __tablename__ = "chat_history"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    character_id = Column(BigInteger, index=True, nullable=False)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    msg_type = Column(String(20), nullable=False, default='text')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 新增的RAG字段
    session_id = Column(String(100), index=True, nullable=True)
    message_type = Column(String(20), default='conversation')
    is_deleted = Column(Boolean, default=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class ChatSession(Base):
    """聊天会话表"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(100), index=True, nullable=False)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# 不需要创建表，因为表已经存在
def create_tables():
    # 表已经存在，只需要确保连接正常
    pass

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 