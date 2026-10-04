"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

ĐỌC LẠI trước khi commit: autogenerate không nhận ra đổi tên cột (nó sinh DROP + ADD, mất dữ liệu).
Migration nằm trong làn độc quyền `db-migrations` — ticket phải khai làn này.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
${imports if imports else ""}
revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
