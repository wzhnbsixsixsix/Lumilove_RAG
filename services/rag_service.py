from typing import List, Dict, Any, Optional
from .vector_store import vector_store_service
from .chat_service import chat_service
from .openrouter_client import openrouter_client
from config import settings

class RAGService:
    def __init__(self):
        self.vector_store_service = vector_store_service
        self.chat_service = chat_service
        self.openrouter_client = openrouter_client
    
    async def generate_response_with_rag(self, user_id: str, session_id: str, 
                                       message: str) -> Dict[str, Any]:
        """使用RAG + OpenRouter生成回复"""
        try:
            # 解析session_id得到character_id
            character_id = self._extract_character_id_from_session(session_id)
            
            # 1. 检索相关的历史上下文
            relevant_context = self.vector_store_service.search_relevant_context(
                query=message,
                user_id=user_id,
                session_id=session_id,
                k=settings.top_k_results
            )
            
            # 2. 获取最近的对话历史
            recent_history = await self.chat_service.get_recent_messages(
                session_id=session_id,
                limit=10
            )
            
            # 3. 构建提示词
            context_text = self._build_context_from_retrieval(relevant_context)
            recent_conversation = self._build_recent_conversation(recent_history)
            
            # 4. 构建消息列表
            messages = self._build_messages(message, context_text, recent_conversation)
            
            # 5. 调用OpenRouter生成回复
            response = await self.openrouter_client.chat_completion(
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            )
            
            # 6. 保存对话到数据库（使用SpringBoot的表结构）
            await self.chat_service.save_message(user_id, character_id, message, response)
            
            # 7. 更新向量数据库 - 修正方法名
            conversation_pair = [{"user": message, "assistant": response}]
            self.vector_store_service.add_chat_to_vector_store(
                user_id, session_id, conversation_pair
            )
            
            return {
                "response": response,
                "context_used": [ctx["content"] for ctx in relevant_context],
                "sources": relevant_context,
                "model_info": self.openrouter_client.get_model_info()
            }
            
        except Exception as e:
            raise Exception(f"RAG响应生成失败: {str(e)}")
    
    def _extract_character_id_from_session(self, session_id: str) -> str:
        """从session_id中提取character_id"""
        # session_id格式: "user_1_character_1"
        try:
            parts = session_id.split('_')
            if len(parts) >= 4 and parts[2] == "character":
                return parts[3]
            return "1"  # 默认character_id
        except:
            return "1"
    
    def _build_messages(self, user_message: str, context: str, recent_conversation: str) -> List[Dict[str, str]]:
        """构建OpenRouter API的消息格式"""
        
        system_prompt = f"""你是一个智能AI助手，具有记忆能力。你可以根据用户的历史对话记录来提供更个性化和连贯的回复。

相关历史对话上下文：
{context}

最近的对话记录：
{recent_conversation}

请基于以上信息，对用户的新消息提供有帮助的回复。如果历史对话中有相关信息，请适当引用。保持回复自然、友好和有用。

当前使用的AI模型: {self.openrouter_client.model}"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    
    def _build_context_from_retrieval(self, relevant_context: List[Dict[str, Any]]) -> str:
        """构建检索到的上下文文本"""
        if not relevant_context:
            return "暂无相关历史对话记录。"
        
        context_parts = []
        for i, ctx in enumerate(relevant_context, 1):
            similarity_score = ctx.get("similarity_score", 0)
            content = ctx["content"]
            context_parts.append(f"相关对话 {i} (相似度: {similarity_score:.3f}):\n{content}")
        
        return "\n\n".join(context_parts)
    
    def _build_recent_conversation(self, recent_history: List[Dict]) -> str:
        """构建最近的对话历史"""
        if not recent_history:
            return "这是对话的开始。"
        
        conversation_parts = []
        for msg in recent_history:
            role = "用户" if msg["message_type"] == "user" else "助手"
            conversation_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(conversation_parts)
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取OpenRouter可用模型"""
        return await self.openrouter_client.get_available_models()
    
    def get_current_model_info(self) -> Dict[str, str]:
        """获取当前模型信息"""
        return self.openrouter_client.get_model_info()

    async def generate_response_with_rag_stream(self, user_id: str, session_id: str, 
                                              message: str):
        """使用RAG + OpenRouter生成流式回复"""
        try:
            character_id = self._extract_character_id_from_session(session_id)
            
            # 1. 检索相关的历史上下文
            relevant_context = self.vector_store_service.search_relevant_context(
                query=message,
                user_id=user_id,
                session_id=session_id,
                k=settings.top_k_results
            )
            
            # 2. 获取最近的对话历史
            recent_history = await self.chat_service.get_recent_messages(
                session_id=session_id,
                limit=10
            )
            
            # 3. 构建提示词
            context_text = self._build_context_from_retrieval(relevant_context)
            recent_conversation = self._build_recent_conversation(recent_history)
            
            # 4. 构建消息列表
            messages = self._build_messages(message, context_text, recent_conversation)
            
            # 5. 流式生成回复
            complete_response = ""
            async for chunk in self.openrouter_client.chat_completion_stream(
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            ):
                complete_response += chunk
                yield {
                    "chunk": chunk,
                    "session_id": session_id,
                    "context_used": [ctx["content"] for ctx in relevant_context],
                    "sources": relevant_context
                }
            
            # 6. 保存完整回复（使用SpringBoot的表结构）
            await self.chat_service.save_message(user_id, character_id, message, complete_response)
            
            # 7. 更新向量数据库 - 修正方法名
            conversation_pair = [{"user": message, "assistant": complete_response}]
            self.vector_store_service.add_chat_to_vector_store(
                user_id, session_id, conversation_pair
            )
            
        except Exception as e:
            yield {
                "error": f"RAG流式处理失败: {str(e)}",
                "session_id": session_id
            }

    async def generate_character_response_stream(self, user_id: str, session_id: str, 
                                               message: str, character_prompt: str = ""):
        """专门为角色扮演优化的流式回复"""
        try:
            character_id = self._extract_character_id_from_session(session_id)
            
            # 1. 检索相关上下文
            relevant_context = self.vector_store_service.search_relevant_context(
                query=message,
                user_id=user_id,
                session_id=session_id,
                k=settings.top_k_results
            )
            
            # 2. 获取最近对话
            recent_history = await self.chat_service.get_recent_messages(
                session_id=session_id,
                limit=10
            )
            
            # 3. 构建角色扮演消息
            messages = self._build_character_messages(
                message, relevant_context, recent_history, character_prompt
            )
            
            # 4. 流式生成
            complete_response = ""
            async for chunk in self.openrouter_client.chat_completion_stream(
                messages=messages,
                max_tokens=2000,
                temperature=0.8  # 角色扮演可以更有创意
            ):
                complete_response += chunk
                yield {"chunk": chunk}
            
            # 5. 保存完整回复
            await self.chat_service.save_message(user_id, character_id, message, complete_response)
            
            # 6. 更新向量数据库
            conversation_pair = [{"user": message, "assistant": complete_response}]
            self.vector_store_service.add_chat_to_vector_store(
                user_id, session_id, conversation_pair
            )
            
        except Exception as e:
            yield {"error": f"角色扮演流式处理失败: {str(e)}"}

    def _build_character_messages(self, user_message: str, context: List, 
                                recent_history: List, character_prompt: str) -> List[Dict]:
        """构建角色扮演的消息"""
        
        context_text = self._build_context_from_retrieval(context)
        recent_conversation = self._build_recent_conversation(recent_history)
        
        system_prompt = f"""角色设定：
{character_prompt}

历史记忆上下文：
{context_text}

最近的对话：
{recent_conversation}

请严格按照角色设定进行扮演，结合历史记忆，对用户的消息做出符合角色的回复。保持角色的一致性和个性。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

# 全局RAG服务实例
rag_service = RAGService()
