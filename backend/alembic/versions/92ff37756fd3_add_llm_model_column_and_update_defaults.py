"""add llm_model column and update defaults

Revision ID: 92ff37756fd3
Revises: 4f792fd64579
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92ff37756fd3'
down_revision: Union[str, Sequence[str], None] = '4f792fd64579'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add llm_model column, widen encrypted_llm_key to TEXT, update default provider."""
    # Widen encrypted_llm_key from VARCHAR(255) to TEXT for longer encrypted strings
    op.alter_column("users", "encrypted_llm_key", type_=sa.Text)

    # Add llm_model column
    op.add_column("users", sa.Column("llm_model", sa.String(100)))

    # Update default provider from 'anthropic' to 'openai'
    op.alter_column("users", "llm_provider", server_default="openai")
    # Update existing rows that still have the old default
    op.execute("UPDATE users SET llm_provider = 'openai' WHERE llm_provider = 'anthropic'")


def downgrade() -> None:
    """Revert llm_model column, encrypted_llm_key type, and provider default."""
    op.execute("UPDATE users SET llm_provider = 'anthropic' WHERE llm_provider = 'openai'")
    op.alter_column("users", "llm_provider", server_default="anthropic")
    op.drop_column("users", "llm_model")
    op.alter_column("users", "encrypted_llm_key", type_=sa.String(255))
