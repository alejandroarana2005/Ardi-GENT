"""add_parent_schedule_id_to_schedules

Revision ID: 003
Revises: 002
Create Date: 2026-04-24

Cambios:
  - schedules: +parent_schedule_id (varchar 36, nullable)
    Permite encadenar versiones de horario creadas por reparación dinámica (Capa 5).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column("parent_schedule_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("schedules", "parent_schedule_id")
