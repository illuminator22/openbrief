"""SQLAlchemy 2.0 models for all OpenBrief database tables."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(Base):
    """Users table for multi-tenant support."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(255))
    llm_provider: Mapped[str] = mapped_column(String(50), default="anthropic")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Document(Base):
    """Uploaded legal documents."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column()
    page_count: Mapped[int | None] = mapped_column()
    upload_status: Mapped[str] = mapped_column(String(50), default="processing")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    entities: Mapped[list["Entity"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    """Document chunks with embeddings for vector search."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    page_number: Mapped[int | None] = mapped_column()
    section_title: Mapped[str | None] = mapped_column(String(500))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    embedding = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    entities: Mapped[list["Entity"]] = relationship(back_populates="chunk")


class Analysis(Base):
    """Analysis results from agent pipeline runs."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    analysis_type: Mapped[str] = mapped_column(String(100), nullable=False)
    query: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    agent_trace: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="analyses")
    document: Mapped["Document"] = relationship(back_populates="analyses")


class Entity(Base):
    """Extracted legal entities from document chunks."""

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column()
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id")
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="entities")
    chunk: Mapped["Chunk"] = relationship(back_populates="entities")


class EvaluationLog(Base):
    """Evaluation metrics log for RAG pipeline quality tracking."""

    __tablename__ = "evaluation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunks: Mapped[dict | None] = mapped_column(JSONB)
    generated_answer: Mapped[str | None] = mapped_column(Text)
    hallucination_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    retrieval_precision: Mapped[float | None] = mapped_column(Numeric(4, 3))
    citation_accuracy: Mapped[float | None] = mapped_column(Numeric(4, 3))
    answer_relevance: Mapped[float | None] = mapped_column(Numeric(4, 3))
    response_time_ms: Mapped[int | None] = mapped_column()
    model_used: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
