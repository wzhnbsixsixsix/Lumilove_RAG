from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatMessage(BaseModel):
    user_id: str
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    context_used: List[str]
    sources: Optional[List[dict]] = None

class HistoryMessage(BaseModel):
    id: int
    message_type: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]

class SessionCreate(BaseModel):
    user_id: str
    title: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime 