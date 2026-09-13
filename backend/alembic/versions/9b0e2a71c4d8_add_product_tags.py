"""add product tags

Revision ID: 9b0e2a71c4d8
Revises: d748e43f1680
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9b0e2a71c4d8"
down_revision: str | None = "d748e43f1680"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("tags", sa.JSON(), nullable=True))
    op.execute("UPDATE products SET tags = JSON_ARRAY() WHERE tags IS NULL")
    op.alter_column("products", "tags", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column("products", "tags")
