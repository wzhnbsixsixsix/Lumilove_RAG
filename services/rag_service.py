from typing import List, Dict, Any, Optional
from .vector_store import vector_store_service
from .chat_service import chat_service
from .openrouter_client import openrouter_client
from config import settings
from .character_service import character_service
import tiktoken  # 需要安装: pip install tiktoken

class RAGService:
    def __init__(self):
        self.vector_store_service = vector_store_service
        self.chat_service = chat_service
        self.openrouter_client = openrouter_client
        # 初始化token编码器（使用GPT-4的编码器）
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
    
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
            return "No relevant historical conversation records found."
        
        context_parts = []
        for i, ctx in enumerate(relevant_context, 1):
            similarity_score = ctx.get("similarity_score", 0)
            content = ctx["content"]
            # 添加调试日志
            print(f"📝 上下文 {i}: {content[:100]}... (相似度: {similarity_score:.3f})")
            context_parts.append(f"Relevant conversation {i} (similarity: {similarity_score:.3f}):\n{content}")
        
        result = "\n\n".join(context_parts)
        print(f"🔍 完整上下文:\n{result}")
        return result
    
    def _build_recent_conversation(self, recent_history: List[Dict]) -> str:
        """构建最近的对话历史"""
        if not recent_history:
            return "This is the beginning of the conversation."
        
        conversation_parts = []
        for msg in recent_history:
            role = "User" if msg["message_type"] == "user" else "Assistant"
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
        """完整的RAG响应流程：提示词 + 记忆 + 回复 + 保存"""
        try:
            character_id = self._extract_character_id_from_session(session_id)
            
            # 步骤1：查询角色提示词
            print(f"📝 步骤1: 查询角色{character_id}的提示词...")
            character_prompt = await character_service.get_character_prompt(character_id)
            
            # 步骤2：检索历史记忆
            print(f"🧠 步骤2: 检索用户{user_id}的历史记忆...")
            relevant_context = self.vector_store_service.search_relevant_context(
                query=message,
                user_id=user_id,
                session_id=session_id,
                k=settings.top_k_results
            )
            
            # 步骤3：获取最近对话
            print(f"💬 步骤3: 获取最近对话历史...")
            recent_history = await self.chat_service.get_recent_messages(
                session_id=session_id,
                limit=10
            )
            
            # 步骤4：构建完整上下文
            print(f"🔨 步骤4: 构建AI提示...")
            context_text = self._build_context_from_retrieval(relevant_context)
            recent_conversation = self._build_recent_conversation(recent_history)
            
            # 构建包含角色设定和记忆的完整提示
            messages = self._build_complete_messages(
                user_message=message,
                character_prompt=character_prompt,
                memory_context=context_text,
                recent_conversation=recent_conversation
            )
            
            # 步骤5：生成AI回复（记录输出token）
            print(f"🤖 步骤5: 生成AI回复...")
            complete_response = ""
            output_tokens = 0
            
            async for chunk in self.openrouter_client.chat_completion_stream(
                messages=messages,
                max_tokens=2000,
                temperature=0.7
            ):
                complete_response += chunk
                output_tokens += self._count_tokens(chunk)
                yield {
                    "chunk": chunk,
                    "session_id": session_id,
                    "context_used": [ctx["content"] for ctx in relevant_context],
                    "sources": relevant_context
                }
            
            # 显示输出token统计
            total_input_tokens = self._count_tokens(str(messages))
            print("📤 输出TOKEN统计:")
            print(f"   输出token: {output_tokens} tokens")
            print(f"   预估输出成本: ${output_tokens * 0.000015:.6f} USD")  # 假设$15/1M tokens
            print(f"   总成本: ${(total_input_tokens * 0.000003 + output_tokens * 0.000015):.6f} USD")
            
            # 步骤6：保存到数据库和向量库
            print(f"💾 步骤6: 保存对话到数据库和向量库...")
            
            # 保存到关系数据库
            await self.chat_service.save_message(user_id, character_id, message, complete_response)
            
            # 保存到向量数据库 - 增加调试信息
            conversation_pair = [{"user": message, "assistant": complete_response}]
            print(f"🔧 准备保存到向量库: user_id={user_id}, session_id={session_id}")
            print(f"🔧 对话内容: user='{message}', assistant='{complete_response[:50]}...'")
            
            try:
                self.vector_store_service.add_chat_to_vector_store(
                    user_id, session_id, conversation_pair
                )
                print(f"✅ 向量数据保存成功")
                
                # 立即测试搜索
                test_results = self.vector_store_service.search_relevant_context(
                    query=message,
                    user_id=user_id,
                    session_id=session_id,
                    k=3
                )
                print(f"🔍 保存后立即搜索结果: {len(test_results)} 条")
                
            except Exception as vec_e:
                print(f"❌ 向量数据保存失败: {vec_e}")
                import traceback
                traceback.print_exc()
            
            print(f"✅ 完整RAG流程完成！")
            
        except Exception as e:
            print(f"❌ RAG流程失败: {e}")
            yield {
                "error": f"RAG流程失败: {str(e)}",
                "session_id": session_id
            }

    def _count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        return len(self.token_encoder.encode(text))
    
    def _build_complete_messages(self, user_message: str, character_prompt: str, 
                               memory_context: str, recent_conversation: str) -> List[Dict[str, str]]:
        """构建包含角色设定和记忆的完整AI提示"""
        
        system_prompt = f"""You must fulfill the following requirements simultaneously:

【Character Setting】
{character_prompt}

Please strictly follow the above character setting for role-playing and maintain character consistency and personality.

【Memory Instructions】
- If the user asks about personal information (name, identity, etc.), you MUST find accurate answers from the following historical memories
- Do not say you don't know or don't remember, use specific information from the historical conversations

【Historical Memory】
{memory_context}

【Recent Conversation】
{recent_conversation}

Please maintain your character's personality while accurately using historical memories to answer the user's questions."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 计算并显示token使用情况
        self._log_token_usage(character_prompt, memory_context, recent_conversation, 
                              user_message, system_prompt)
        
        return messages
    
    def _log_token_usage(self, character_prompt: str, memory_context: str, 
                        recent_conversation: str, user_message: str, full_system_prompt: str):
        """详细记录token使用情况"""
        
        # 分别计算各部分token
        character_tokens = self._count_tokens(character_prompt)
        memory_tokens = self._count_tokens(memory_context)
        recent_tokens = self._count_tokens(recent_conversation)
        user_tokens = self._count_tokens(user_message)
        system_tokens = self._count_tokens(full_system_prompt)
        
        total_input_tokens = system_tokens + user_tokens
        
        print("=" * 60)
        print("📊 TOKEN 使用详情")
        print("=" * 60)
        print(f"👤 用户消息: {user_tokens} tokens")
        print(f"🎭 角色设定: {character_tokens} tokens")
        print(f"🧠 历史记忆: {memory_tokens} tokens")
        print(f"💬 最近对话: {recent_tokens} tokens")
        print(f"📋 完整系统提示: {system_tokens} tokens")
        print("-" * 60)
        print(f"📥 总输入token: {total_input_tokens} tokens")
        print(f"💰 预估输入成本: ${total_input_tokens * 0.000003:.6f} USD")  # 假设$3/1M tokens
        print("=" * 60)
        
        # 显示完整prompt内容（可选，用于调试）
        if settings.debug:
            print("📝 完整PROMPT内容:")
            print("-" * 40)
            print(full_system_prompt)
            print("-" * 40)
            print(f"用户: {user_message}")
            print("=" * 60)

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

    def _optimize_context_for_tokens(self, relevant_context: List[Dict[str, Any]], 
                                    max_context_tokens: int = 1000) -> str:
        """优化上下文以控制token使用"""
        
        if not relevant_context:
            return "暂无相关历史对话记录。"
        
        context_parts = []
        current_tokens = 0
        
        for i, ctx in enumerate(relevant_context, 1):
            similarity_score = ctx.get("similarity_score", 0)
            content = ctx["content"]
            
            # 计算这条记录的token
            content_tokens = self._count_tokens(content)
            
            # 如果加上这条记录会超过限制，就停止
            if current_tokens + content_tokens > max_context_tokens:
                print(f"⚠️ 上下文token限制：只使用前{i-1}条记录（{current_tokens} tokens）")
                break
            
            context_parts.append(f"对话{i}(相似度{similarity_score:.2f}): {content}")
            current_tokens += content_tokens
        
        result = "\n".join(context_parts)
        print(f"✅ 最终上下文: {current_tokens} tokens")
        return result

# 全局RAG服务实例
rag_service = RAGService()
