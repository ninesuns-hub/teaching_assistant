import json
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from agent_core.config.settings import settings
from database import conversation_repo, memory_repo
from database import memory_vector_repo

logger = logging.getLogger(__name__)


@dataclass
class BuiltChatContext:
    history_messages: list[dict] = field(default_factory=list)
    summary_text: str = ""
    memories: list[str] = field(default_factory=list)
    recent_image_path: Optional[str] = None
    estimated_tokens: int = 0


def _estimate_tokens(text: str) -> int:
    # Conservative mixed Chinese/English approximation without adding a tokenizer dependency.
    return max(1, (len(text) + 2) // 3)


def _trim_text(text: str, token_budget: int) -> str:
    max_chars = token_budget * 3
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _type_relevance(memory_type: str, question: str) -> float:
    normalized = question.casefold()
    if memory_type in {"communication_preference", "learning_preference"}:
        return 1.0 if any(word in normalized for word in ("讲", "解释", "例", "图", "prove", "explain")) else 0.7
    if memory_type in {"course_learning_state", "unresolved_learning_goal"}:
        return 0.9
    return 0.6


def build_chat_context(
    db: Session,
    *,
    user_id: int,
    conversation_id: int,
    class_id: Optional[int],
    before_message_id: int,
    request_id: str,
    question: str,
) -> BuiltChatContext:
    started_at = time.perf_counter()
    result = BuiltChatContext()
    if not settings.CHAT_CONTEXT_ENABLED:
        return result

    summary = conversation_repo.get_conversation_summary(db, conversation_id)
    if (
        settings.CONVERSATION_SUMMARY_ENABLED
        and summary
        and conversation_repo.is_message_in_ancestry(
            db,
            conversation_id,
            before_message_id,
            summary.summarized_through_message_id,
        )
    ):
        result.summary_text = _trim_text(
            summary.summary_text or "",
            settings.CHAT_SUMMARY_TOKEN_LIMIT,
        )

    candidates = conversation_repo.list_recent_messages(
        db,
        conversation_id,
        limit=settings.CHAT_RECENT_MESSAGE_LIMIT,
        before_message_id=before_message_id,
    )
    remaining = settings.CHAT_RECENT_TOKEN_LIMIT
    selected: list[dict] = []
    for message in reversed(candidates):
        content = message.content or ""
        cost = _estimate_tokens(content)
        if cost > remaining and selected:
            break
        if cost > remaining:
            content = _trim_text(content, remaining)
            cost = _estimate_tokens(content)
        selected.append({"role": message.role, "content": content})
        remaining -= cost
        if result.recent_image_path is None and message.image_path:
            result.recent_image_path = message.image_path
        if remaining <= 0:
            break
    result.history_messages = list(reversed(selected))

    if settings.MEMORY_READ_ENABLED:
        setting = memory_repo.get_or_create_setting(db, user_id)
    else:
        setting = None
    if setting and setting.enabled:
        try:
            vector_results = memory_vector_repo.query_memories(
                question,
                user_id=user_id,
                class_id=class_id,
                limit=settings.MEMORY_RETRIEVAL_LIMIT * 3,
                request_id=request_id,
            )
            ranked_memories = []
            now = datetime.utcnow()
            for vector_item in vector_results:
                item = memory_repo.get_memory(
                    db,
                    user_id,
                    str(vector_item.get("public_id", "")),
                )
                if item and item.status == "active":
                    age_days = max(
                        0.0,
                        (now - (item.updated_at or item.created_at)).total_seconds() / 86400,
                    )
                    recency = max(0.0, 1.0 - age_days / 365.0)
                    score = (
                        0.55 * float(vector_item.get("similarity", 0))
                        + 0.20 * recency
                        + 0.15 * float(item.confidence or 0)
                        + 0.10 * _type_relevance(item.memory_type, question)
                    )
                    ranked_memories.append((score, item.content))
            ranked_memories.sort(key=lambda value: value[0], reverse=True)
            memories = [
                content
                for _, content in ranked_memories[:settings.MEMORY_RETRIEVAL_LIMIT]
            ]
        except Exception:
            logger.warning(
                "Memory vector retrieval failed; using SQL fallback request_id=%s",
                request_id,
            )
            memories = [
                item.content
                for item in memory_repo.recent_relevant_memories(
                    db,
                    user_id,
                    class_id,
                    limit=settings.MEMORY_RETRIEVAL_LIMIT,
                )
            ]
        memory_budget = settings.CHAT_MEMORY_TOKEN_LIMIT
        for memory in memories:
            cost = _estimate_tokens(memory)
            if cost > memory_budget:
                continue
            result.memories.append(memory)
            memory_budget -= cost

    result.estimated_tokens = (
        _estimate_tokens(result.summary_text)
        + sum(_estimate_tokens(item["content"]) for item in result.history_messages)
        + sum(_estimate_tokens(item) for item in result.memories)
    )
    logger.info(json.dumps({
        "event": "chat_timing",
        "request_id": request_id,
        "stage": "context_build",
        "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
        "history_count": len(result.history_messages),
        "memory_count": len(result.memories),
        "estimated_tokens": result.estimated_tokens,
    }, ensure_ascii=False))
    return result
