"""add_tenant_id_to_all_tables

Revision ID: 82970211fc77
Revises: 8577cda44002
Create Date: 2026-03-29 14:36:26.259501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82970211fc77'
down_revision: Union[str, Sequence[str], None] = '8577cda44002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = [
        "agents", "sessions", "policies",
        "audit_events", "hitl_reviews", "api_tokens",
    ]
    for table in tables:
        op.add_column(
            table,
            sa.Column("tenant_id", sa.UUID(), nullable=True)
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    tables = [
        "agents", "sessions", "policies",
        "audit_events", "hitl_reviews", "api_tokens",
    ]
    for table in reversed(tables):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
