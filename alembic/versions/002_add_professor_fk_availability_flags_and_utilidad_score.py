"""add_professor_fk_availability_flags_and_utilidad_score

Revision ID: 002
Revises: 001
Create Date: 2026-04-18

Cambios:
  - classrooms: +disponible (bool, default true), +edificio (varchar 100, nullable)
  - timeslots:  +semestre (varchar 10, nullable)
  - professors: +email (varchar 200, nullable), +activo (bool, default true)
  - assignments: +professor_code FK→professors.code (nullable)
                 rename score → utilidad_score
                 +UniqueConstraint(schedule_id, professor_code, timeslot_code)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── classrooms ────────────────────────────────────────────────────────────
    op.add_column("classrooms", sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("classrooms", sa.Column("edificio", sa.String(100), nullable=True))

    # ── timeslots ─────────────────────────────────────────────────────────────
    op.add_column("timeslots", sa.Column("semestre", sa.String(10), nullable=True))

    # ── professors ────────────────────────────────────────────────────────────
    op.add_column("professors", sa.Column("email", sa.String(200), nullable=True))
    op.add_column("professors", sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()))

    # ── assignments: add professor_code ───────────────────────────────────────
    # Añadir como nullable primero para poder hacer backfill en BD con datos existentes.
    # En ambiente fresco (sin filas previas) se puede cambiar a nullable=False directamente.
    op.add_column("assignments", sa.Column("professor_code", sa.String(20), nullable=False, server_default=""))
    op.alter_column("assignments", "professor_code", server_default=None)
    op.create_foreign_key(
        "fk_assignment_professor_code",
        "assignments", "professors",
        ["professor_code"], ["code"],
    )

    # ── assignments: rename score → utilidad_score ────────────────────────────
    op.alter_column("assignments", "score", new_column_name="utilidad_score")

    # ── assignments: add second unique constraint ──────────────────────────────
    op.create_unique_constraint(
        "uq_assignment_professor_slot",
        "assignments",
        ["schedule_id", "professor_code", "timeslot_code"],
    )


def downgrade() -> None:
    # ── assignments ───────────────────────────────────────────────────────────
    op.drop_constraint("uq_assignment_professor_slot", "assignments", type_="unique")
    op.alter_column("assignments", "utilidad_score", new_column_name="score")
    op.drop_constraint("fk_assignment_professor_code", "assignments", type_="foreignkey")
    op.drop_column("assignments", "professor_code")

    # ── professors ────────────────────────────────────────────────────────────
    op.drop_column("professors", "activo")
    op.drop_column("professors", "email")

    # ── timeslots ─────────────────────────────────────────────────────────────
    op.drop_column("timeslots", "semestre")

    # ── classrooms ────────────────────────────────────────────────────────────
    op.drop_column("classrooms", "edificio")
    op.drop_column("classrooms", "disponible")
