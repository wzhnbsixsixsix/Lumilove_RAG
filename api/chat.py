from fastapi import APIRouter, HTTPException, Depends, Form, Header
from sqlalchemy.orm import Session
from schemas.chat import (
    ChatMessage, ChatResponse, ChatHistoryResponse, 
    SessionCreate, SessionResponse
)
from services import rag_service, chat_service
from models.database import get_db
from typing import List
from fastapi.responses import StreamingResponse
import json
import httpx

router = APIRouter(prefix="/api/chat", tags=["聊天"])

@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """发送消息并获取AI回复（带RAG功能）"""
    try:
        # 检查会话是否存在
        session = await chat_service.get_session_by_id(message.session_id)
        if not session:
            # 如果会话不存在，创建新会话
            await chat_service.create_session(message.user_id, "新对话")
        
        # 使用RAG服务生成回复
        result = await rag_service.generate_response_with_rag(
            user_id=message.user_id,
            session_id=message.session_id,
            message=message.message
        )
        
        return ChatResponse(
            response=result["response"],
            session_id=message.session_id,
            context_used=result["context_used"],
            sources=result.get("sources")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 50):
    """获取聊天历史记录"""
    try:
        messages = await chat_service.get_chat_history(session_id, limit)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")

@router.post("/session", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """创建新的聊天会话"""
    try:
        session = await chat_service.create_session(
            user_id=session_data.user_id,
            title=session_data.title
        )
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@router.get("/sessions/{user_id}", response_model=List[SessionResponse])
async def get_user_sessions(user_id: str):
    """获取用户的所有会话"""
    try:
        sessions = await chat_service.get_user_sessions(user_id)
        return [
            SessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
            for session in sessions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        success = await chat_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 同时删除向量数据库中的相关数据
        from services.vector_store import vector_store_service
        vector_store_service.delete_session_vectors(session_id)
        
        return {"message": "会话删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@router.get("/context/{session_id}")
async def get_relevant_context(session_id: str, query: str, k: int = 5):
    """获取相关上下文（用于调试）"""
    try:
        from services.vector_store import vector_store_service
        
        # 先获取会话信息
        session = await chat_service.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 搜索相关上下文
        context = vector_store_service.search_relevant_context(
            query=query,
            user_id=session.user_id,
            session_id=session_id,
            k=k
        )
        
        return {"context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")

@router.get("/models")
async def get_available_models():
    """获取OpenRouter可用模型列表"""
    try:
        models = await rag_service.get_available_models()
        current_model = rag_service.get_current_model_info()
        
        return {
            "current_model": current_model,
            "available_models": models[:20],  # 只返回前20个模型
            "total_count": len(models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

@router.get("/model/current")
async def get_current_model():
    """获取当前使用的模型信息"""
    return rag_service.get_current_model_info()

@router.post("/message/stream")
async def send_message_stream(message: ChatMessage):
    """发送消息并获取AI流式回复（带RAG功能）"""
    try:
        # 检查会话是否存在
        session = await chat_service.get_session_by_id(message.session_id)
        if not session:
            await chat_service.create_session(message.user_id, "新对话")
        
        async def generate():
            async for chunk_data in rag_service.generate_response_with_rag_stream(
                user_id=message.user_id,
                session_id=message.session_id,
                message=message.message
            ):
                # 发送 SSE 格式的数据
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式处理消息失败: {str(e)}")

@router.post("/springboot/stream")
async def springboot_stream_proxy(
    user_id: str = Form(...),
    character_id: int = Form(...), 
    message: str = Form(...),
    character_prompt: str = Form(default=""),
    chat_id: str = Form(default="")
):
    """专门为SpringBoot设计的流式代理接口"""
    try:
        # 构建session_id
        session_id = f"user_{user_id}_character_{character_id}"
        
        # 检查会话
        session = await chat_service.get_session_by_id(session_id)
        if not session:
            await chat_service.create_session(user_id, f"角色{character_id}对话")
        
        async def generate():
            try:
                # 流式生成，简化输出格式
                async for chunk_data in rag_service.generate_response_with_rag_stream(
                    user_id=user_id,
                    session_id=session_id,
                    message=message
                ):
                    if 'chunk' in chunk_data:
                        chunk_content = chunk_data['chunk']
                        if chunk_content:  # 只发送非空内容
                            yield f"data: {chunk_content}\n\n"
                
                # 完成标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式处理失败: {str(e)}")

async def verify_jwt_token(authorization: str):
    """验证SpringBoot的JWT token"""
    try:
        # 调用SpringBoot的验证接口
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://54.206.37.109:8443/api/auth/verify",
                headers={"Authorization": authorization},
                verify=False  # 跳过SSL验证
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data["id"]  # 返回用户ID
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token验证失败")

@router.post("/message/stream/authenticated")
async def send_message_stream_with_auth(
    message: ChatMessage,
    authorization: str = Header(None)
):
    """带认证的流式聊天接口"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证token")
    
    # 验证token并获取用户ID
    user_id = await verify_jwt_token(authorization)
    
    # 使用验证后的用户ID
    message.user_id = str(user_id)
    
    # 检查会话
    session = await chat_service.get_session_by_id(message.session_id)
    if not session:
        await chat_service.create_session(message.user_id, "新对话")
    
    async def generate():
        async for chunk_data in rag_service.generate_response_with_rag_stream(
            user_id=message.user_id,
            session_id=message.session_id,
            message=message.message
        ):
            if 'chunk' in chunk_data:
                chunk_content = chunk_data['chunk']
                if chunk_content:
                    yield f"data: {chunk_content}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "https://main.d3m01u43jjmlec.amplifyapp.com",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        }
    ) 