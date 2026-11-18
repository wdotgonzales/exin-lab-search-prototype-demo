import uuid
from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

FILE_TYPES = ("pdf", "docx", "xlsx", "csv", "md", "txt")
STATUSES = ("pending", "processing", "indexed", "failed")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_id", "external_path"),
        CheckConstraint(
            "file_type IN ('pdf', 'docx', 'xlsx', 'csv', 'md', 'txt')", name="file_type"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'indexed', 'failed')", name="status"
        ),
        CheckConstraint(
            "access_level IN ('general', 'restricted')", name="access_level"
        ),
        Index("idx_documents_source", "source_id"),
        Index("idx_documents_hash", "source_id", "content_hash"),
        Index("idx_documents_filters", "status", "file_type", "document_date"),
        Index("idx_documents_title_tsv", "title_tsv", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE")
    )
    external_path: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    access_level: Mapped[str] = mapped_column(Text, server_default="general")
    document_date: Mapped[date | None] = mapped_column(Date)
    title_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', title)", persisted=True)
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
