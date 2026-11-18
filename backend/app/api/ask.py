"""POST /api/ask: the chat assistant (design flow 4.6).

rate limit -> hybrid retrieval -> cited answer -> log in ai_queries -> response
"""

import logging
import math
import time
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.chat.answer import answer_question
from app.chat.llm import LLM, get_llm
from app.chat.retrieval import retrieve
from app.config import get_settings
from app.ingest.embedder import Embedder, get_embedder
from app.models import AiQuery, User
from app.schemas.ask import AskRequest, AskResponse, AskSource

log = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
LLMDep = Annotated[LLM, Depends(get_llm)]

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

    try:
        retrieval = retrieve(db, body.question, embedder, is_admin=user.role == "admin")
        answer = answer_question(body.question, retrieval, llm)
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
            retrieved_chunk_ids=[c.chunk_id for c in retrieval.chunks],
            cited_document_ids=[s.document_id for s in answer.sources],
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            cost_usd=answer.cost_usd,
            latency_ms=_ms_since(started),
            status=answer.status,
        )
    )
    db.commit()

    return AskResponse(
        status=answer.status,
        answer=answer.text,
        sources=[
            AskSource(
                n=s.n,
                document_id=s.document_id,
                title=s.title,
                filename=s.filename,
                snippet=s.snippet,
                page_number=s.page_number,
            )
            for s in answer.sources
        ],
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
