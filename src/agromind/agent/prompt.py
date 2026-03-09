"""System prompt builder and context block formatter for AgroMind agent.

build_system_prompt(mandatory_tool_names) → str
    Returns the system prompt that instructs Gemini to always call mandatory tools
    before answering crop/pest/weather questions.

build_context_block(wiki, rag_chunks, geo) → str
    Returns a formatted context section to prepend to the user message, containing
    Wikipedia summary, RAG chunks, and optionally resolved geo context.
"""

from __future__ import annotations

from langchain_core.documents import Document

_SYSTEM_TEMPLATE = """\
You are AgroMind, a precision agriculture copilot for Indian smallholder farmers.
You speak clearly, factually, and in the farmer's preferred language.

## MANDATORY TOOLS — You MUST always call these before answering any farming query:
{mandatory_list}

Never recommend a pesticide, herbicide, or fungicide without first calling
`cibrc_safety_check` to confirm it is legal in India.

Always call `imd_weather_check` when answering questions about sowing timing,
irrigation scheduling, crop stage management, or weather-related risks.

## GUIDELINES
- Give practical, actionable advice suited to Indian smallholder farmers.
- Cite the chemical status from CIBRC and weather thresholds from IMD in your answer.
- If mandatory tools return errors, report the error clearly and advise caution.
- Prefer organic or IPM solutions when equally effective.
- Never recommend chemicals banned in India.
"""

_CONTEXT_TEMPLATE = """\
## BACKGROUND CONTEXT (pre-retrieved, use to inform your answer)

{geo_section}{wiki_section}{rag_section}"""


def build_system_prompt(mandatory_tool_names: list[str]) -> str:
    """Build the system prompt with mandatory tool names listed explicitly."""
    if mandatory_tool_names:
        items = "\n".join(f"  - `{name}`" for name in mandatory_tool_names)
    else:
        items = "  (none)"
    return _SYSTEM_TEMPLATE.format(mandatory_list=items)


def build_context_block(
    wiki: dict,
    rag_chunks: list[Document],
    geo: dict | None = None,
) -> str:
    """Build a formatted context block to prepend to the user message.

    Args:
        wiki: Dict with keys title, summary, url (from WikiLoader.fetch).
        rag_chunks: List of LangChain Documents from ChromaDB retrieval.
        geo: Optional resolved location dict (state, district, block, etc.).

    Returns:
        Formatted string ready to inject before the user query.
    """
    geo_section = ""
    if geo:
        parts = []
        if geo.get("state"):
            parts.append(f"State: {geo['state']}")
        if geo.get("district"):
            parts.append(f"District: {geo['district']}")
        if geo.get("block"):
            parts.append(f"Block: {geo['block']}")
        if parts:
            geo_section = "### Farmer Location\n" + " | ".join(parts) + "\n\n"

    wiki_section = ""
    if wiki.get("summary"):
        wiki_section = (
            f"### Wikipedia: {wiki.get('title', 'Reference')}\n"
            f"{wiki['summary']}\n\n"
        )

    rag_section = ""
    if rag_chunks:
        chunk_texts = "\n---\n".join(
            f"[{i + 1}] {doc.page_content.strip()}"
            for i, doc in enumerate(rag_chunks)
        )
        rag_section = f"### Knowledge Base Excerpts\n{chunk_texts}\n\n"

    return _CONTEXT_TEMPLATE.format(
        geo_section=geo_section,
        wiki_section=wiki_section,
        rag_section=rag_section,
    )
