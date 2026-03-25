"""rename api_key_hash to encrypted_llm_key

Revision ID: 4f792fd64579
Revises: d582570ba747
Create Date: 2026-03-24 22:13:01.583102

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4f792fd64579'
down_revision: Union[str, Sequence[str], None] = 'd582570ba747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename api_key_hash to encrypted_llm_key on users table."""
    op.alter_column("users", "api_key_hash", new_column_name="encrypted_llm_key")


def downgrade() -> None:
    """Revert column name back to api_key_hash."""
    op.alter_column("users", "encrypted_llm_key", new_column_name="api_key_hash")
