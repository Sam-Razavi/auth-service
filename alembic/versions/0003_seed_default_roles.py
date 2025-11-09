"""seed default roles

Revision ID: 0003
Revises: 0002
Create Date: 2025-11-09 10:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_roles_table = sa.table(
    "roles",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
)

_DEFAULT_ROLES = [
    {"id": "10000000-0000-0000-0000-000000000001", "name": "admin"},
    {"id": "10000000-0000-0000-0000-000000000002", "name": "user"},
    {"id": "10000000-0000-0000-0000-000000000003", "name": "moderator"},
]


def upgrade() -> None:
    op.bulk_insert(_roles_table, _DEFAULT_ROLES)


def downgrade() -> None:
    op.execute(
        _roles_table.delete().where(
            _roles_table.c.name.in_(["admin", "user", "moderator"])
        )
    )
