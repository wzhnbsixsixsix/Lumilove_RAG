# RAG聊天服务

基于FastAPI + LangChain + RAG的智能聊天服务，为AI聊天程序提供记忆能力和上下文检索功能。

## 功能特性

- 🧠 **智能记忆**: 使用向量数据库存储和检索历史对话
- 🔍 **上下文检索**: 基于语义相似度检索相关历史对话
- 💬 **多模型支持**: 支持OpenAI GPT-4和DeepSeek模型
- 📊 **会话管理**: 完整的聊天会话创建、管理和删除功能
- 🗄️ **数据持久化**: 支持MySQL/PostgreSQL数据库
- ⚡ **高性能**: 基于FastAPI的异步API服务

## 系统架构

```
[ Java Spring Boot后端 ] ←→ [ FastAPI RAG服务 ]
                                      ↓
                         [ MySQL/PostgreSQL数据库 ]
                                      ↓
                            [ ChromaDB向量数据库 ]
                                      ↓
                            [ LangChain + LLM模型 ]
```

## 快速开始

### 1. 环境配置

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或者
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
# 或者使用DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/chatdb

# 其他配置...
```

### 3. 数据库准备

创建MySQL/PostgreSQL数据库：
```sql
CREATE DATABASE chatdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8001` 启动。

## API使用

### 发送消息
```bash
curl -X POST "http://localhost:8001/api/chat/message" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user123",
       "session_id": "session456",
       "message": "你好，我想了解Python编程"
     }'
```

### 创建会话
```bash
curl -X POST "http://localhost:8001/api/chat/session" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user123",
       "title": "Python学习讨论"
     }'
```

### 获取聊天历史
```bash
curl "http://localhost:8001/api/chat/history/session456"
```

## 与Java后端集成

在你的Java Spring Boot应用中调用RAG服务：

```java
@Service
public class RagChatService {
    
    @Value("${rag.service.url:http://localhost:8001}")
    private String ragServiceUrl;
    
    public ChatResponse sendMessage(String userId, String sessionId, String message) {
        // 构建请求
        ChatRequest request = new ChatRequest(userId, sessionId, message);
        
        // 调用RAG服务
        RestTemplate restTemplate = new RestTemplate();
        ResponseEntity<ChatResponse> response = restTemplate.postForEntity(
            ragServiceUrl + "/api/chat/message",
            request,
            ChatResponse.class
        );
        
        return response.getBody();
    }
}
```

## 项目结构

```
├── main.py                 # FastAPI应用入口
├── config.py              # 配置管理
├── requirements.txt       # Python依赖
├── .env.example          # 环境变量模板
├── models/               # 数据模型
│   ├── __init__.py
│   └── database.py       # 数据库模型
├── schemas/              # Pydantic模式
│   ├── __init__.py
│   └── chat.py          # 聊天相关模式
├── services/             # 业务服务
│   ├── __init__.py
│   ├── chat_service.py   # 聊天服务
│   ├── vector_store.py   # 向量数据库服务
│   └── rag_service.py    # RAG核心服务
└── api/                  # API路由
    ├── __init__.py
    └── chat.py          # 聊天API
```

## 技术栈

- **FastAPI**: 现代、快速的Web框架
- **LangChain**: LLM应用程序开发框架
- **ChromaDB**: 向量数据库
- **SentenceTransformers**: 文本嵌入模型
- **SQLAlchemy**: Python SQL工具包
- **Pydantic**: 数据验证和序列化

## 部署

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8001

CMD ["python", "main.py"]
```

### 生产环境配置

```yaml
# docker-compose.yml
version: '3.8'
services:
  rag-chat:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=mysql+pymysql://user:pass@mysql:3306/chatdb
    depends_on:
      - mysql
      - redis
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: chatdb
      MYSQL_ROOT_PASSWORD: password
    volumes:
      - mysql_data:/var/lib/mysql
  
  redis:
    image: redis:alpine
    
volumes:
  mysql_data:
```

## 监控和日志

- API文档: `http://localhost:8001/docs`
- 健康检查: `http://localhost:8001/health`
- 向量数据库状态: `http://localhost:8001/health`

## 许可证

MIT License # Lumilove_RAG
# Lumilove_RAG
