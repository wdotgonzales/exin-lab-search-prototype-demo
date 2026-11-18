import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class AskRequest(BaseModel):
    question: Question


class AskSource(BaseModel):
    n: int
    document_id: uuid.UUID
    title: str
    filename: str
    snippet: str
    page_number: int | None


class AskResponse(BaseModel):
    status: Literal["answered", "no_sources"]
    answer: str
    sources: list[AskSource]
