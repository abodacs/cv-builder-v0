from langgraph.prebuilt.chat_agent_executor import AgentState
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)  # Ensures non-empty string
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str = Field(..., min_length=1)  # Ensures non-empty string
    conversation_id: str


class ChatHistory(BaseModel):
    messages: list[dict[str, str]] = Field(
        default_factory=list
    )  # Provides default empty list


class UserState(BaseModel):
    user_token: str
    language: str = Field(default="ar", pattern="^(ar|en)$")


class ChatAppState(AgentState):
    conversation_id: str  # Conversation ID
    user_token: str  # User token


class PersonalInfo(BaseModel):
    name: str = Field(..., min_length=1)
    # Basic email validation
    email: str = Field(..., pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = None
    summary: str | None = None
    country: str | None = None


class WorkExperience(BaseModel):
    company: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Education(BaseModel):
    school: str = Field(..., min_length=1)
    degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    description: str | None = None
    major: str | None = None
