from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, text
from models.database import ChatHistory, ChatSession, get_db, SessionLocal
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import logging

class ChatService:
    
    async def save_message(self, user_id: str, character_id: str, 
                          user_message: str, ai_response: str) -> ChatHistory:
        """保存聊天消息到SpringBoot的表结构"""
        try:
            with SessionLocal() as db:
                # 生成session_id
                session_id = f"user_{user_id}_character_{character_id}"
                
                chat_history = ChatHistory(
                    user_id=int(user_id),
                    character_id=int(character_id),
                    message=user_message,          # SpringBoot字段名
                    response=ai_response,          # SpringBoot字段名
                    msg_type='text',
                    session_id=session_id,
                    message_type='conversation',
                    is_deleted=False
                )
                db.add(chat_history)
                db.commit()
                db.refresh(chat_history)
                return chat_history
        except Exception as e:
            logging.error(f"保存聊天记录失败: {e}")
            raise
    
    async def get_chat_history(self, session_id: str, 
                              limit: Optional[int] = None) -> List[Dict]:
        """获取聊天历史记录"""
        db = next(get_db())
        try:
            query = db.query(ChatHistory).filter(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.is_deleted == False
                )
            ).order_by(ChatHistory.timestamp)
            
            if limit:
                query = query.limit(limit)
            
            messages = query.all()
            
            return [
                {
                    "id": msg.id,
                    "message_type": msg.message_type,
                    "content": msg.message,
                    "timestamp": msg.timestamp
                }
                for msg in messages
            ]
        finally:
            db.close()
    
    async def get_recent_messages(self, session_id: str, 
                                 limit: int = 10) -> List[Dict]:
        """获取最近的聊天消息 - 确保使用正确的sessionId过滤"""
        print(f"🔍 获取最近消息: session_id='{session_id}', limit={limit}")
        
        try:
            with SessionLocal() as db:
                # 解析session_id获取user_id（用于验证）
                parts = session_id.split('_')
                if len(parts) >= 4:
                    expected_user_id = int(parts[1])
                    expected_character_id = int(parts[3])
                    print(f"🔍 从session_id解析: user_id={expected_user_id}, character_id={expected_character_id}")
                
                # 使用session_id过滤（包含了user和character信息）
                conversations = db.query(ChatHistory).filter(
                    and_(
                        ChatHistory.session_id == session_id,  # 这已经包含了userId+characterId
                        ChatHistory.is_deleted == False
                    )
                ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
                
                print(f"📥 从数据库获取到 {len(conversations)} 条历史记录")
                
                # 验证所有记录都匹配正确的user_id
                if conversations and len(parts) >= 4:
                    for conv in conversations[:3]:  # 检查前几条
                        if conv.user_id != expected_user_id:
                            print(f"⚠️ 警告: 记录的user_id({conv.user_id})与session_id不匹配({expected_user_id})")
                
                # 格式化结果...
                result = []
                for conv in reversed(conversations):
                    if conv.message and conv.message.strip():
                        result.append({
                            "message_type": "user",
                            "content": conv.message,
                            "timestamp": conv.created_at
                        })
                    
                    if conv.response and conv.response.strip() and conv.response != "[流式响应]":
                        result.append({
                            "message_type": "assistant", 
                            "content": conv.response,
                            "timestamp": conv.created_at
                        })
                
                print(f"📤 格式化后返回 {len(result)} 条消息")
                return result
                
        except Exception as e:
            print(f"❌ 获取历史消息失败: {e}")
            return []
    
    async def create_session(self, user_id: str, character_id: str, title: str = "新对话"):
        """创建会话（对于SpringBoot集成，这主要是确保session_id格式正确）"""
        session_id = f"user_{user_id}_character_{character_id}"
        return type('Session', (), {
            'session_id': session_id,
            'user_id': user_id,
            'character_id': character_id,
            'title': title
        })()
    
    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """获取用户的所有会话"""
        db = next(get_db())
        try:
            sessions = db.query(ChatSession).filter(
                and_(
                    ChatSession.user_id == user_id,
                    ChatSession.is_active == True
                )
            ).order_by(desc(ChatSession.updated_at)).all()
            
            return sessions
        finally:
            db.close()
    
    async def get_session_by_id(self, session_id: str) -> bool:
        """检查会话是否存在（简化版本）"""
        # 对于SpringBoot集成，session_id格式是固定的
        return session_id.startswith("user_") and "_character_" in session_id
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话（软删除）"""
        db = next(get_db())
        try:
            # 删除会话
            session = db.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if session:
                session.is_active = False
                
                # 删除相关消息
                db.query(ChatHistory).filter(
                    ChatHistory.session_id == session_id
                ).update({"is_deleted": True})
                
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    async def get_conversation_pairs(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话对，用于向量化存储"""
        messages = await self.get_chat_history(session_id)
        
        pairs = []
        current_pair = {}
        
        for msg in messages:
            if msg["message_type"] == "user":
                current_pair = {"user": msg["content"]}
            elif msg["message_type"] == "assistant" and "user" in current_pair:
                current_pair["assistant"] = msg["content"]
                pairs.append(current_pair.copy())
                current_pair = {}
        
        return pairs

# 全局聊天服务实例
chat_service = ChatService() 