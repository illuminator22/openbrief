"""create initial tables

Revision ID: d582570ba747
Revises:
Create Date: 2026-03-23 08:17:21.681489

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'd582570ba747'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables and enable pgvector extension."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("api_key_hash", sa.String(255)),
        sa.Column("llm_provider", sa.String(50), server_default="anthropic"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer),
        sa.Column("page_count", sa.Integer),
        sa.Column("upload_status", sa.String(50), server_default="processing"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # Chunks
    op.create_table(
        "chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer),
        sa.Column("section_title", sa.String(500)),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("embedding", Vector(384)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    # NOTE: IVFFlat index on chunks.embedding is NOT created here.
    # IVFFlat requires existing data to build the index effectively.
    # Create the index in a later migration after data has been ingested:
    #   CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

    # Analyses
    op.create_table(
        "analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_type", sa.String(100), nullable=False),
        sa.Column("query", sa.Text),
        sa.Column("result", JSONB, nullable=False),
        sa.Column("agent_trace", JSONB),
        sa.Column("confidence_score", sa.Numeric(4, 3)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # Entities
    op.create_table(
        "entities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_value", sa.Text, nullable=False),
        sa.Column("page_number", sa.Integer),
        sa.Column("chunk_id", UUID(as_uuid=True), sa.ForeignKey("chunks.id")),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # Evaluation Logs
    op.create_table(
        "evaluation_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("retrieved_chunks", JSONB),
        sa.Column("generated_answer", sa.Text),
        sa.Column("hallucination_score", sa.Numeric(4, 3)),
        sa.Column("retrieval_precision", sa.Numeric(4, 3)),
        sa.Column("citation_accuracy", sa.Numeric(4, 3)),
        sa.Column("answer_relevance", sa.Numeric(4, 3)),
        sa.Column("response_time_ms", sa.Integer),
        sa.Column("model_used", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    """Drop all tables and pgvector extension."""
    op.drop_table("evaluation_logs")
    op.drop_table("entities")
    op.drop_table("analyses")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
