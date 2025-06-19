import asyncio
from services.chat_service import chat_service
from services.vector_store import vector_store_service
from models.database import SessionLocal, ChatHistory
from sqlalchemy import desc, and_

async def migrate_session_to_vector(session_id: str):
    """将特定session的历史对话迁移到向量库"""
    print(f"🚀 开始迁移session {session_id} 的历史数据...")
    
    try:
        with SessionLocal() as db:
            # 获取该session的所有历史对话
            conversations = db.query(ChatHistory).filter(
                and_(
                    ChatHistory.session_id == session_id,
                    ChatHistory.is_deleted == False
                )
            ).order_by(ChatHistory.created_at).all()
            
            print(f"📋 找到 {len(conversations)} 条历史对话")
            
            # 转换为对话对格式
            conversation_pairs = []
            for conv in conversations:
                if conv.message and conv.response and conv.response != "[流式响应]":
                    conversation_pairs.append({
                        "user": conv.message,
                        "assistant": conv.response
                    })
            
            print(f"💬 转换为 {len(conversation_pairs)} 个对话对")
            
            # 批量添加到向量库
            if conversation_pairs:
                # 解析session_id获取user_id
                user_id = session_id.split('_')[1] if '_' in session_id else "1"
                
                vector_store_service.add_chat_to_vector_store(
                    user_id=user_id,
                    session_id=session_id,
                    conversation_context=conversation_pairs
                )
                
                print(f"✅ 成功迁移 {len(conversation_pairs)} 个对话对到向量库")
                
                # 测试搜索
                test_results = vector_store_service.search_relevant_context(
                    query="what's my name",
                    user_id=user_id,
                    session_id=session_id,
                    k=3
                )
                print(f"🔍 迁移后测试搜索: 找到 {len(test_results)} 条结果")
                for i, result in enumerate(test_results):
                    print(f"  结果{i+1}: {result['content'][:100]}... (相似度: {result.get('similarity_score', 0):.3f})")
            else:
                print("❌ 没有有效的对话对可以迁移")
                
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    # 迁移当前用户的历史数据
    await migrate_session_to_vector("user_1_character_2")
    
    # 也可以迁移其他session
    # await migrate_session_to_vector("user_1_character_1")

if __name__ == "__main__":
    asyncio.run(main())