import httpx
import json
from typing import List, Dict, Any, Optional
from config import settings

class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.app_name = settings.app_name
        self.app_url = settings.app_url
        
        if not self.api_key:
            raise ValueError("OpenRouter API密钥未配置，请在.env文件中设置OPENROUTER_API_KEY")
    
    async def chat_completion(self, messages: List[Dict[str, str]], 
                            max_tokens: int = 1000, 
                            temperature: float = 0.7) -> str:
        """
        调用OpenRouter API进行聊天补全
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_name
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    raise Exception("OpenRouter API返回格式异常")
                    
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_body = e.response.json()
                    error_detail = error_body.get("error", {}).get("message", str(e))
                except:
                    error_detail = str(e)
                raise Exception(f"OpenRouter API调用失败 ({e.response.status_code}): {error_detail}")
            
            except httpx.TimeoutException:
                raise Exception("OpenRouter API调用超时")
            
            except Exception as e:
                raise Exception(f"OpenRouter API调用异常: {str(e)}")
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], 
                                   max_tokens: int = 1000, 
                                   temperature: float = 0.7):
        """
        流式调用OpenRouter API进行聊天补全
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.app_url,
            "X-Title": self.app_name
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True  # 启用流式处理
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    'POST', 
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data = line[6:]  # 移除 "data: " 前缀
                                
                                if data.strip() == "[DONE]":
                                    break
                                    
                                try:
                                    chunk = json.loads(data)
                                    if "choices" in chunk and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            yield delta["content"]
                                except json.JSONDecodeError:
                                    continue
                                    
            except Exception as e:
                raise Exception(f"OpenRouter流式API调用异常: {str(e)}")
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        获取可用的模型列表
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return result.get("data", [])
                
            except Exception as e:
                print(f"获取模型列表失败: {e}")
                return []
    
    def get_model_info(self) -> Dict[str, str]:
        """
        获取当前使用的模型信息
        """
        return {
            "model": self.model,
            "provider": "OpenRouter",
            "base_url": self.base_url
        }

# 全局客户端实例
openrouter_client = OpenRouterClient()
