"""remove test columns

Revision ID: f66ae96bb1f5
Revises: 36faea8845c7
Create Date: 2025-12-04 14:45:46.631469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f66ae96bb1f5'
down_revision: Union[str, Sequence[str], None] = '36faea8845c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('question', 'test1')


def downgrade() -> None:
        op.add_column(
        'question',
        sa.Column('test1', sa.Text(), nullable=True),
    )
