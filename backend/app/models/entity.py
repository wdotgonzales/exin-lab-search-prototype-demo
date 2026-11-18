import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

ENTITY_TYPES = ("mouse", "virus_batch", "experiment", "cohort")


class Entity(Base):
    """A lab ID found in documents, e.g. M-042 (mouse) or EXP-007 (experiment)."""

    __tablename__ = "entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('mouse','virus_batch','experiment','cohort')",
            name="entity_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DocumentEntity(Base):
    """Which lab IDs appear in which document, and how often."""

    __tablename__ = "document_entities"
    __table_args__ = (Index("idx_doc_entities_entity", "entity_id"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    mention_count: Mapped[int] = mapped_column(Integer, server_default="1")
