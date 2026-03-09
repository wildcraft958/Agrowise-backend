"""AgroMind agent chain.

Architecture:
    1. Build system prompt (mandatory tool instructions).
    2. Bind all 16 tools to ChatGoogleGenerativeAI.
    3. Invoke with [SystemMessage, HumanMessage(context + user_query)].
    4. Post-validate: check mandatory tools were called; retry once if not.
    5. Post-filter: scan answer for banned chemicals (CIBRC safety).

Returns:
    {
        "answer": str,
        "tool_trace": list[str],   # tools called
        "safety_violation": bool,  # True if banned chemical in answer
        "violations": list[str],   # banned chemicals found
    }
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agromind.agent.mandatory import get_called_tool_names, missing_mandatory_tools
from agromind.agent.prompt import build_context_block, build_system_prompt
from agromind.agent.tools import ALL_TOOLS
from agromind.config import settings
from agromind.rag.retriever import RAGRetriever
from agromind.rag.wiki_loader import WikiLoader
from agromind.safety.validator import SafetyValidator

# Build banned chemical set from CIBRC client at startup
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.cibrc_tool import CIBRCClient  # noqa: E402

logger = logging.getLogger(__name__)

# Tool name → callable lookup for execution
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

_MANDATORY_NAMES = settings.tools.mandatory
_MAX_RETRIES = int(settings.tools.enforcement.get("max_retries", 2))

# Pre-load banned chemical set for the safety validator
try:
    _cibrc = CIBRCClient(db_path=settings.safety.cibrc_csv_path)
    _BANNED_CHEMICALS = set(_cibrc.list_banned())
except Exception:
    _BANNED_CHEMICALS = set()

# RAG components — instantiated at module level, gracefully disabled if unavailable
try:
    _embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.models.embedding,
        project=settings.gcp.project_id,
        location=settings.gcp.location,
    )
    _icar_retriever = RAGRetriever(
        settings.rag.collections["icar"],
        _embeddings,
        settings.rag.chroma_persist_dir,
    )
    _kcc_retriever = RAGRetriever(
        settings.rag.collections["kcc"],
        _embeddings,
        settings.rag.chroma_persist_dir,
    )
    _wiki = WikiLoader()
    _rag_enabled = True
except Exception:
    _rag_enabled = False


_MAX_LOOP = 6  # max tool-call rounds per invoke


def _execute_tool_calls(response: AIMessage) -> list[ToolMessage]:
    """Execute all tool calls in an AIMessage, return ToolMessages with results."""
    results: list[ToolMessage] = []
    for tc in response.tool_calls:
        tool_fn = _TOOL_MAP.get(tc["name"])
        if tool_fn is None:
            content = json.dumps({"error": f"unknown tool: {tc['name']}"})
        else:
            try:
                content = tool_fn.invoke(tc["args"])
            except Exception as exc:
                content = json.dumps({"error": str(exc)})
        results.append(ToolMessage(content=content, tool_call_id=tc["id"]))
    return results


class AgroMindAgent:
    """Gemini-powered agricultural copilot with mandatory tool enforcement."""

    def __init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=settings.models.chat,
            vertexai=True,
            project=settings.gcp.project_id,
            location=settings.gcp.location,
            temperature=settings.models.temperature,
            max_output_tokens=settings.models.max_output_tokens,
        )
        self._bound = self._llm.bind_tools(ALL_TOOLS)
        self._system_prompt = build_system_prompt(_MANDATORY_NAMES)
        self._validator = SafetyValidator(
            banned_chemicals=_BANNED_CHEMICALS,
            strict_mode=settings.safety.strict_mode,
        )

    def invoke(self, user_message: str, context: dict | None = None) -> dict:
        """Run the agent pipeline for a single user message.

        Args:
            user_message: The farmer's question.
            context: Optional pre-built context string to prepend.

        Returns:
            Dict with answer, tool_trace, safety_violation, violations.
        """
        # Auto-build RAG context if not pre-supplied and RAG is available
        if not (context and context.get("context_block")) and _rag_enabled:
            try:
                icar_chunks = _icar_retriever.search(user_message, k=settings.rag.top_k)
                kcc_chunks = _kcc_retriever.search(user_message, k=3)
                keyword = user_message.split()[0] if user_message.split() else user_message
                wiki = _wiki.fetch(keyword)
                context_block = build_context_block(
                    wiki=wiki,
                    rag_chunks=icar_chunks + kcc_chunks,
                )
                if context_block:
                    context = {"context_block": context_block}
            except Exception as exc:
                logger.debug("RAG context build failed (degraded mode): %s", exc)

        human_content = user_message
        if context and context.get("context_block"):
            human_content = context["context_block"] + "\n\n## Question\n" + user_message

        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=human_content),
        ]

        # Agentic loop: LLM → execute tools → LLM → … until final text answer
        response = self._bound.invoke(messages)
        messages.append(response)
        for _ in range(_MAX_LOOP):
            if not getattr(response, "tool_calls", None):
                break
            messages.extend(_execute_tool_calls(response))
            response = self._bound.invoke(messages)
            messages.append(response)

        # Enforce mandatory tools — retry once if missing
        missing = missing_mandatory_tools(messages, _MANDATORY_NAMES)
        if missing and _MAX_RETRIES > 0:
            retry_msg = HumanMessage(
                content=(
                    f"You forgot to call mandatory tools: {missing}. "
                    "Please call them now and provide your final answer."
                )
            )
            messages.append(retry_msg)
            response = self._bound.invoke(messages)
            messages.append(response)
            for _ in range(_MAX_LOOP):
                if not getattr(response, "tool_calls", None):
                    break
                messages.extend(_execute_tool_calls(response))
                response = self._bound.invoke(messages)
                messages.append(response)

        raw = response.content if isinstance(response, AIMessage) else str(response)
        if isinstance(raw, list):
            answer = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw
            ).strip()
        else:
            answer = str(raw)
        tool_trace = get_called_tool_names(messages)

        # CIBRC safety post-filter
        safety_result = self._validator.validate(answer)

        if not safety_result["safe"] and settings.safety.strict_mode:
            answer = (
                "⚠️ This response mentioned a banned chemical and has been blocked. "
                f"Banned substances detected: {', '.join(safety_result['violations'])}. "
                "Please consult a licensed agronomist for safe alternatives."
            )

        return {
            "answer": answer,
            "tool_trace": tool_trace,
            "safety_violation": not safety_result["safe"],
            "violations": safety_result["violations"],
        }
