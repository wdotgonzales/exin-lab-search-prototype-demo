"""POST /api/ask: the lab assistant (design flow 4.6, v2 agent).

rate limit -> agent (catalogue + history + read-only tools) -> checked answer
-> log in ai_queries -> response
"""

import logging
import math
import time
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.chat.agent import Turn, run_agent
from app.chat.llm import AgentLLM, get_llm
from app.chat.tools import ToolContext
from app.config import get_settings
from app.ingest.embedder import Embedder, get_embedder
from app.models import AiQuery, User
from app.schemas.ask import AskAction, AskRequest, AskResponse, AskSource

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
LLMDep = Annotated[AgentLLM, Depends(get_llm)]

WINDOW = timedelta(hours=1)


@router.post(
    "/ask",
    response_model=AskResponse,
    responses={
        429: {"description": "Too many questions this hour"},
        502: {"description": "The AI service failed; the question was logged"},
    },
)
def ask(
    body: AskRequest,
    user: CurrentUser,
    db: DbSession,
    embedder: EmbedderDep,
    llm: LLMDep,
) -> AskResponse:
    _check_rate_limit(db, user)
    started = time.perf_counter()
    ctx = ToolContext(db=db, embedder=embedder, is_admin=user.role == "admin")
    history = [Turn(t.role, t.content) for t in body.history]

    try:
        answer = run_agent(body.question, history, ctx, llm)
    except Exception:
        log.exception("ask failed for user %s", user.id)
        db.rollback()
        db.add(
            AiQuery(
                user_id=user.id,
                question=body.question,
                model=llm.model,
                latency_ms=_ms_since(started),
                status="error",
            )
        )
        db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The assistant couldn't answer just now. Please try again.",
        ) from None

    db.add(
        AiQuery(
            user_id=user.id,
            question=body.question,
            answer=answer.text,
            model=answer.model,
            retrieved_chunk_ids=answer.retrieved_chunk_ids,
            cited_document_ids=[c.document_id for c in answer.sources],
            tool_calls=answer.tool_calls,
            general_knowledge=answer.general_knowledge,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            cost_usd=answer.cost_usd,
            latency_ms=_ms_since(started),
            status=answer.status,
        )
    )
    db.commit()

    return AskResponse(
        status="answered",
        answer=answer.text,
        sources=[
            AskSource(
                n=c.n,
                document_id=c.document_id,
                title=c.title,
                filename=c.filename,
                snippet=c.snippet,
                page_number=c.page_number,
            )
            for c in answer.sources
        ],
        general_knowledge=answer.general_knowledge,
        actions=[AskAction(**a) for a in answer.actions],
        checked=answer.checked,
    )


def _check_rate_limit(db: DbSession, user: User) -> None:
    limit = get_settings().ask_rate_limit_per_hour
    count, oldest, now = db.execute(
        select(func.count(), func.min(AiQuery.created_at), func.now()).where(
            AiQuery.user_id == user.id, AiQuery.created_at > func.now() - WINDOW
        )
    ).one()
    if count >= limit:
        minutes = max(1, math.ceil((oldest + WINDOW - now).total_seconds() / 60))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"You've reached {limit} questions this hour. "
            f"You can ask again in {minutes} minute{'s' if minutes != 1 else ''}.",
            headers={"Retry-After": str(minutes * 60)},
        )


def _ms_since(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
