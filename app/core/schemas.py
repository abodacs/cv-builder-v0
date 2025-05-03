from langgraph.prebuilt.chat_agent_executor import AgentState
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


class ChatHistory(BaseModel):
    messages: list[dict[str, str]]


class UserState(BaseModel):
    """User-specific state information"""

    user_token: str
    language: str = "ar"  # Default to Arabic


class ChatAppState(AgentState):
    conversation_id: str
    user_token: str


class PersonalInfo(BaseModel):
    name: str
    email: str
    phone: str
    summary: str
    country: str


class WorkExperience(BaseModel):
    company: str
    title: str
    location: str
    start_date: str
    end_date: str


class Education(BaseModel):
    school: str
    degree: str
    start_date: str
    end_date: str
