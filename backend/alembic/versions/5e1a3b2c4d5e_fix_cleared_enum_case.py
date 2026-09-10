"""fix_cleared_enum_case

Fix enum value case mismatch: the 'downloadstatus' Postgres enum contains
'cleared' (lowercase, added by c0947aaa7c19) but SQLAlchemy's Enum stores
member names (UPPERCASE). This caused GET /api/downloads/ to 500 with
'InvalidTextRepresentation' on every status != CLEARED query.

Revision ID: 5e1a3b2c4d5e
Revises: c0947aaa7c19
Create Date: 2026-08-03

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5e1a3b2c4d5e'
down_revision: Union[str, None] = 'c0947aaa7c19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE downloadstatus RENAME VALUE 'cleared' TO 'CLEARED'")


def downgrade() -> None:
    op.execute("ALTER TYPE downloadstatus RENAME VALUE 'CLEARED' TO 'cleared'")
