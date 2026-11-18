import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(max_length=4000)]


class AskRequest(BaseModel):
    question: Question
    # The last few turns of this conversation, so follow-ups work. They are kept
    # in the browser only; the server never stores a conversation.
    history: list[HistoryTurn] = Field(default_factory=list, max_length=12)


class AskSource(BaseModel):
    n: int
    document_id: uuid.UUID
    title: str
    filename: str
    snippet: str
    page_number: int | None


class AskAction(BaseModel):
    type: Literal["open_document", "show_in_list"]
    label: str
    document_id: uuid.UUID | None = None  # open_document
    query: str | None = None  # show_in_list


class AskResponse(BaseModel):
    status: Literal["answered", "no_sources"]
    answer: str
    sources: list[AskSource]
    general_knowledge: bool = False
    actions: list[AskAction] = []
    checked: list[str] = []
