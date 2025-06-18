import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import settings
from .vector_store import vector_store_service
import logging

class SpringBootSyncService:
    def __init__(self):
        # 连接到SpringBoot使用的同一个数据库
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    async def sync_chat_history_to_vector_store(self, user_id: str, character_id: str, limit: int = 100):
        """将SpringBoot的聊天历史同步到向量数据库"""
        try:
            with self.SessionLocal() as session:
                # 查询SpringBoot的chat_history表
                query = text("""
                    SELECT id, user_id, character_id, message, response, created_at 
                    FROM chat_history 
                    WHERE user_id = :user_id AND character_id = :character_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """)
                
                result = session.execute(query, {
                    "user_id": int(user_id) if user_id.isdigit() else user_id,
                    "character_id": int(character_id) if character_id.isdigit() else character_id,
                    "limit": limit
                })
                
                chat_histories = [
                    {
                        "id": row.id,
                        "user_id": str(row.user_id),
                        "character_id": str(row.character_id),
                        "message": row.message,
                        "response": row.response,
                        "created_at": row.created_at
                    }
                    for row in result.fetchall()
                ]
                
                # 转换为会话格式并添加到向量存储
                session_id = f"user_{user_id}_character_{character_id}"
                
                conversations = []
                for chat in reversed(chat_histories):  # 按时间顺序处理
                    conversations.append({
                        "user": chat["message"],
                        "assistant": chat["response"]
                    })
                
                if conversations:
                    vector_store_service.add_conversation_to_vector_store(
                        conversations, user_id, session_id
                    )
                    
                    logging.info(f"同步了 {len(conversations)} 条聊天记录到向量数据库")
                
                return len(conversations)
                
        except Exception as e:
            logging.error(f"同步聊天历史失败: {e}")
            return 0
    
    async def auto_sync_new_conversations(self):
        """自动同步新的对话（可以作为定时任务运行）"""
        # 这里可以实现定时检查新对话的逻辑
        pass

# 全局同步服务实例
springboot_sync_service = SpringBootSyncService()