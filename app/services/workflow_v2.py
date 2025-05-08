import uuid
from http import HTTPStatus
from typing import Annotated, TypedDict

from fastapi import HTTPException
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableConfig,
    RunnableLambda,
    RunnableWithFallbacks,
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.redis.aio import AsyncRedisStore
from pydantic import SecretStr

from app.core.config import Config
from app.core.constants import PROMPT, RESUME_SECTIONS
from app.core.schemas import ChatResponse
from app.tools.resume_tools import resume_tools

REDIS_URI = f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}"


def handle_tool_error(state: dict) -> dict[str, list[ToolMessage]]:
    """Handle tool error by returning a message with the error details."""
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls

    return {
        "messages": [
            ToolMessage(
                content=f"Error: {error!r}\nPlease fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ],
    }


def create_tool_node_with_fallback(tools: list[BaseTool]) -> "RunnableWithFallbacks":
    """Create a tool node with a fallback mechanism."""

    return ToolNode(
        tools,
    ).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_token: str | None


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    async def __call__(
        self, state: State, config: RunnableConfig
    ) -> dict[str, list[ToolMessage]]:
        """Invoke the assistant with the given state and config."""
        while True:
            configuration = config.get("configurable", {})
            user_token = configuration.get("user_token", None)
            state = {**state, "user_token": user_token}
            # Call the runnable with the state and config
            result = await self.runnable.ainvoke(state, config)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or (
                    isinstance(result.content, list)
                    and not result.content[0].get("text")
                )
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break

        return {"messages": result}


class ChatService:
    def __init__(self) -> None:
        # Initialize the LLM and tools
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=SecretStr(Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None,
            base_url=Config.OPENAI_API_BASE_URL,
        )
        self.tools: list[BaseTool] = resume_tools

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    PROMPT
                    + "\n\n"
                    + "Sections are "
                    + ", ".join(section for section in RESUME_SECTIONS)
                    + ".\n",
                ),
                ("placeholder", "{messages}"),
            ]
        )
        # Create the assistant runnable
        assistant_runnable = self.prompt | self.llm.bind_tools(self.tools)

        # Build the graph
        self.builder = StateGraph(State)
        self.builder.add_node("assistant", Assistant(assistant_runnable))
        self.builder.add_node("tools", create_tool_node_with_fallback(self.tools))

        # Define edges
        self.builder.add_edge(START, "assistant")
        self.builder.add_conditional_edges(
            "assistant",
            tools_condition,
        )
        self.builder.add_edge("tools", "assistant")

    async def process_message(
        self, message: str, user_token: str, conversation_id: str | None = None
    ) -> ChatResponse:
        """Process a message and return the response."""

        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
        # Validate the message
        if not isinstance(message, str) or not message.strip():
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Message must be a non-empty string.",
            )
        try:
            # Create config for this invocation
            config: RunnableConfig = {
                "configurable": {
                    "thread_id": conversation_id,
                    "user_token": user_token,
                },
                "recursion_limit": 25,
            }
            ttl_config = {
                "default_ttl": 60,  # Default TTL in minutes
                "refresh_on_read": True,  # Refresh TTL when store entries are read
            }
            # Create a Redis store with the specified TTL configuration
            async with AsyncRedisSaver.from_conn_string(REDIS_URI) as checkpointer:
                await checkpointer.asetup()

                async with AsyncRedisStore.from_conn_string(
                    REDIS_URI, ttl=ttl_config
                ) as store:
                    await store.setup()
                    # Add the conversation ID to the checkpointer
                    graph = self.builder.compile(checkpointer=checkpointer)
                    # Get response from agent
                    response = await graph.ainvoke(
                        {"messages": [("user", str(message))]}, config
                    )

                    # Extract the final answer from the response
                    # LangGraph agents return the last message in the messages list
                    final_response = response["messages"][-1].content
                    print("final_response", final_response)
                    # Check if the response is empty
                    if not final_response:
                        raise HTTPException(
                            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                            detail="Empty response from the assistant.",
                        )
                    # Check if the response is a list
                    if isinstance(final_response, list):
                        # If it's a list, extract the first element
                        final_response = final_response[0].get("text", "")

                    return ChatResponse(
                        response=final_response,
                        conversation_id=conversation_id,
                    )

        except Exception as e:
            print(e)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e
