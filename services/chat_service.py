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
        """获取最近的聊天消息 - 修复版"""
        print(f"🔍 开始获取 session_id='{session_id}' 的最近消息...")
        
        try:
            with SessionLocal() as db:
                # 1. 测试数据库连接 - 修复text()问题
                try:
                    connection_test = db.execute(text("SELECT 1")).fetchone()
                    print(f"✅ 数据库连接成功: {connection_test}")
                except Exception as conn_e:
                    print(f"❌ 数据库连接失败: {conn_e}")
                    return []
                
                # 2. 检查表是否存在
                try:
                    table_check = db.execute(text("SELECT COUNT(*) FROM chat_history")).fetchone()
                    print(f"✅ chat_history表存在，总记录数: {table_check[0]}")
                except Exception as table_e:
                    print(f"❌ chat_history表不存在或无法访问: {table_e}")
                    return []
                
                # 3. 检查最新的几条记录
                try:
                    latest_records = db.execute(text("""
                        SELECT id, user_id, character_id, session_id, message, response, 
                               created_at, is_deleted, msg_type
                        FROM chat_history 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """)).fetchall()
                    
                    print(f"📋 最新5条记录:")
                    for record in latest_records:
                        print(f"   ID:{record[0]} | user_id:{record[1]} | character_id:{record[2]} | session_id:'{record[3]}' | is_deleted:{record[7]}")
                        print(f"     message: {record[4][:50] if record[4] else 'None'}...")
                        print(f"     response: {record[5][:50] if record[5] else 'None'}...")
                        print("   ---")
                        
                except Exception as latest_e:
                    print(f"❌ 获取最新记录失败: {latest_e}")
                
                # 4. 查找匹配的session_id
                try:
                    session_matches = db.execute(text("""
                        SELECT COUNT(*) FROM chat_history 
                        WHERE session_id = :session_id
                    """), {"session_id": session_id}).fetchone()
                    print(f"🔍 session_id完全匹配的记录数: {session_matches[0]}")
                    
                    # 如果没有完全匹配，检查所有存在的session_id
                    if session_matches[0] == 0:
                        all_sessions = db.execute(text("""
                            SELECT DISTINCT session_id FROM chat_history 
                            WHERE session_id IS NOT NULL 
                            LIMIT 10
                        """)).fetchall()
                        
                        print(f"🔍 数据库中存在的session_id: {[s[0] for s in all_sessions]}")
                        
                        # 尝试按user_id和character_id查找
                        parts = session_id.split('_')
                        if len(parts) >= 4:
                            user_id = parts[1]
                            character_id = parts[3]
                            
                            user_char_records = db.execute(text("""
                                SELECT COUNT(*) FROM chat_history 
                                WHERE user_id = :user_id AND character_id = :character_id
                            """), {"user_id": int(user_id), "character_id": int(character_id)}).fetchone()
                            
                            print(f"🔍 user_id={user_id}, character_id={character_id} 的记录数: {user_char_records[0]}")
                        
                except Exception as match_e:
                    print(f"❌ 匹配session_id失败: {match_e}")
                
                # 5. 使用ORM查询（这里不需要text()）
                try:
                    conversations = db.query(ChatHistory).filter(
                        and_(
                            ChatHistory.session_id == session_id,
                            ChatHistory.is_deleted == False
                        )
                    ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
                    
                    print(f"📥 ORM查询结果: {len(conversations)} 条记录")
                    
                    # 如果ORM查询为空，尝试不使用is_deleted过滤
                    if len(conversations) == 0:
                        print("⚠️ 尝试不使用is_deleted过滤...")
                        all_conversations = db.query(ChatHistory).filter(
                            ChatHistory.session_id == session_id
                        ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
                        print(f"📥 不使用is_deleted过滤的结果: {len(all_conversations)} 条记录")
                        
                        if len(all_conversations) == 0:
                            # 最后尝试：按user_id和character_id查找
                            parts = session_id.split('_')
                            if len(parts) >= 4:
                                user_id = int(parts[1])
                                character_id = int(parts[3])
                                
                                user_char_conversations = db.query(ChatHistory).filter(
                                    and_(
                                        ChatHistory.user_id == user_id,
                                        ChatHistory.character_id == character_id,
                                        ChatHistory.is_deleted == False
                                    )
                                ).order_by(desc(ChatHistory.created_at)).limit(limit).all()
                                
                                print(f"📥 按user_id+character_id查询结果: {len(user_char_conversations)} 条记录")
                                conversations = user_char_conversations
                        else:
                            conversations = all_conversations
                
                except Exception as orm_e:
                    print(f"❌ ORM查询失败: {orm_e}")
                    return []
                
                # 6. 格式化结果
                result = []
                for i, conv in enumerate(reversed(conversations)):
                    print(f"🔄 处理第{i+1}条记录: ID={conv.id}, session_id='{conv.session_id}'")
                    
                    if conv.message and conv.message.strip():
                        result.append({
                            "message_type": "user",
                            "content": conv.message,
                            "timestamp": conv.created_at
                        })
                        print(f"   ✅ 添加用户消息: {conv.message[:30]}...")
                    
                    if conv.response and conv.response.strip() and conv.response != "[流式响应]":
                        result.append({
                            "message_type": "assistant", 
                            "content": conv.response,
                            "timestamp": conv.created_at
                        })
                        print(f"   ✅ 添加AI回复: {conv.response[:30]}...")
                
                print(f"📤 最终返回 {len(result)} 条格式化消息")
                return result
                
        except Exception as e:
            print(f"❌ 获取历史消息异常: {e}")
            import traceback
            traceback.print_exc()
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