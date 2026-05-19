"""add_layer_times_to_schedule

Revision ID: 004
Revises: 003
Create Date: 2026-05-11

Cambios:
  - schedules: +layer1_ms, layer2_ms, layer3_ms, layer4_ms, layer5_ms (integer, nullable)
    Almacena el tiempo real de ejecución de cada capa BDI en milisegundos.
    nullable=True para compatibilidad con schedules generados antes de esta migración.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("layer1_ms", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("layer2_ms", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("layer3_ms", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("layer4_ms", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("layer5_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("schedules", "layer5_ms")
    op.drop_column("schedules", "layer4_ms")
    op.drop_column("schedules", "layer3_ms")
    op.drop_column("schedules", "layer2_ms")
    op.drop_column("schedules", "layer1_ms")
