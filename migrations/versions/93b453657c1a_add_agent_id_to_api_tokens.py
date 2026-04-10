"""add_agent_id_to_api_tokens

Revision ID: 93b453657c1a
Revises: 82970211fc77
Create Date: 2026-04-10 11:39:37.727245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '93b453657c1a'
down_revision: Union[str, Sequence[str], None] = '82970211fc77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agent_id FK column to api_tokens."""
    op.add_column('api_tokens', sa.Column('agent_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_api_tokens_agent_id',
        'api_tokens', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Remove agent_id FK column from api_tokens."""
    op.drop_constraint('fk_api_tokens_agent_id', 'api_tokens', type_='foreignkey')
    op.drop_column('api_tokens', 'agent_id')
