"""add_cleared_status_to_downloads

Revision ID: c0947aaa7c19
Revises: 528f8ed4833e
Create Date: 2026-07-17 11:05:04.063263

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c0947aaa7c19'
down_revision: Union[str, None] = '528f8ed4833e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE downloadstatus ADD VALUE 'cleared'")


def downgrade() -> None:
    pass
