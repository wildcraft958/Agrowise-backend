"""POST /agromind/chat — main agent chat endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agromind.agent.chain import AgroMindAgent

router = APIRouter()

# Singleton agent — instantiated once at import time.
# Patched in tests via `patch("agromind.api.chat._agent")`.
_agent = AgroMindAgent()


class ChatRequest(BaseModel):
    message: str
    user_id: str
    language: str = "en"
    context_block: str = ""


class ChatResponse(BaseModel):
    answer: str
    tool_trace: list[str]
    safety_violation: bool
    violations: list[str]


@router.post("/agromind/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """Run the AgroMind agent pipeline for a user message."""
    context = {"context_block": body.context_block} if body.context_block else None
    result = _agent.invoke(body.message, context=context)
    return ChatResponse(**result)
