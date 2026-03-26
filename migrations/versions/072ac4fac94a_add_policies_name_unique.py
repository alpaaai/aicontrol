"""add_policies_name_unique

Revision ID: 072ac4fac94a
Revises: 3dae7b8c24cb
Create Date: 2026-03-26 14:49:17.706108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '072ac4fac94a'
down_revision: Union[str, Sequence[str], None] = '3dae7b8c24cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_policies_name', 'policies', ['name'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_policies_name', 'policies', type_='unique')
