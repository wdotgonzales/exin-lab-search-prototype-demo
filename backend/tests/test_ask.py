import uuid

import pytest
from sqlalchemy import func, select

from app.chat.llm import Completion, get_llm
from app.core.security import SESSION_COOKIE, create_access_token
from app.ingest.embedder import FakeEmbedder, get_embedder
from app.main import app
from app.models import AiQuery, Chunk, Document, Source, User
from app.models.source import UPLOAD_SOURCE_NAME

EMBEDDER = FakeEmbedder()


class FakeLLM:
    model = "gpt-6-luna"

    def __init__(self, reply: str = "M-045's window cracked [1].") -> None:
        self.reply = reply
        self.calls = 0

    def complete(self, instructions: str, prompt: str) -> Completion:
        self.calls += 1
        return Completion(self.reply, input_tokens=3000, output_tokens=100)


class BrokenLLM(FakeLLM):
    def complete(self, instructions: str, prompt: str) -> Completion:
        raise ConnectionError("OpenAI is down")


@pytest.fixture
def ai(client):
    """Replace OpenAI with fakes. Set ai["llm"] to change the model's behaviour."""
    state = {"llm": FakeLLM()}
    app.dependency_overrides[get_embedder] = lambda: EMBEDDER
    app.dependency_overrides[get_llm] = lambda: state["llm"]
    return state


def sign_in(client, db, role: str = "viewer") -> User:
    user = User(
        email=f"{uuid.uuid4().hex[:8]}@exin.test",
        password_hash="not-used",
        full_name="Test User",
        role=role,
    )
    db.add(user)
    db.commit()
    client.cookies.set(SESSION_COOKIE, create_access_token(user.id))
    return user


def add_document(db, title: str, text: str) -> Document:
    source = db.scalar(select(Source).where(Source.name == UPLOAD_SOURCE_NAME))
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source_id=source.id,
        external_path=f"uploads/{doc_id}/{title.replace(' ', '_')}.md",
        title=title,
        file_type="md",
        size_bytes=len(text),
        content_hash="0" * 64,
        status="indexed",
    )
    db.add(doc)
    db.flush()
    [vector] = EMBEDDER.embed([text])
    db.add(
        Chunk(
            document_id=doc_id,
            chunk_index=0,
            content=text,
            token_count=10,
            embedding=vector,
            embedding_model=EMBEDDER.model,
        )
    )
    db.commit()
    return doc


def logged(db, user: User) -> list[AiQuery]:
    return list(db.scalars(select(AiQuery).where(AiQuery.user_id == user.id)))


def ask(client, question: str):
    return client.post("/api/ask", json={"question": question})


def test_requires_login(client, ai):
    assert ask(client, "anything").status_code == 401


def test_answers_with_sources_and_logs_it(client, db_session, ai):
    user = sign_in(client, db_session)
    doc = add_document(
        db_session, "window incident", "The cranial window on M-045 cracked."
    )

    res = ask(client, "  Which mouse had a cracked window?  ")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "answered"
    assert body["answer"] == "M-045's window cracked [1]."
    assert body["sources"] == [
        {
            "n": 1,
            "document_id": str(doc.id),
            "title": "window incident",
            "filename": "window_incident.md",
            "snippet": "The cranial window on M-045 cracked.",
            "page_number": None,
        }
    ]

    [row] = logged(db_session, user)
    assert row.status == "answered"
    assert row.question == "Which mouse had a cracked window?"  # trimmed
    assert row.cited_document_ids == [doc.id]
    assert len(row.retrieved_chunk_ids) == 1
    assert (row.prompt_tokens, row.completion_tokens) == (3000, 100)
    assert row.cost_usd is not None
    assert row.latency_ms >= 0


def test_nothing_relevant_skips_the_ai_and_is_logged(client, db_session, ai):
    user = sign_in(client, db_session)

    res = ask(client, "zebra quantum pizza")

    assert res.status_code == 200
    assert res.json() == {
        "status": "no_sources",
        "answer": "I couldn't find this in the uploaded documents.",
        "sources": [],
    }
    assert ai["llm"].calls == 0
    [row] = logged(db_session, user)
    assert (row.status, row.cost_usd) == ("no_sources", None)


def test_ai_failure_returns_502_and_is_logged(client, db_session, ai):
    user = sign_in(client, db_session)
    add_document(db_session, "window incident", "The cranial window on M-045 cracked.")
    ai["llm"] = BrokenLLM()

    res = ask(client, "Which mouse had a cracked window?")

    assert res.status_code == 502
    assert "try again" in res.json()["detail"]
    [row] = logged(db_session, user)
    assert row.status == "error"


def test_rate_limit_is_per_user_per_hour(client, db_session, ai):
    other = User(
        email="other@exin.test", password_hash="x", full_name="Other", role="viewer"
    )
    db_session.add(other)
    user = sign_in(client, db_session)
    db_session.add_all(
        AiQuery(user_id=u.id, question="q", model="m", status="answered")
        for u in [user] * 20 + [other] * 5
    )
    db_session.commit()

    res = ask(client, "one more?")

    assert res.status_code == 429
    assert "20 questions this hour" in res.json()["detail"]
    assert int(res.headers["Retry-After"]) > 0
    assert ai["llm"].calls == 0
    count = db_session.scalar(
        select(func.count()).select_from(AiQuery).where(AiQuery.user_id == user.id)
    )
    assert count == 20  # a blocked request is not logged


def test_blank_question_is_rejected(client, db_session, ai):
    sign_in(client, db_session)
    assert ask(client, "   ").status_code == 422
