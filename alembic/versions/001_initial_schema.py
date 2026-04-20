"""Initial schema — todas las tablas HAIA.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.create_table(
        "classrooms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False),
    )
    op.create_table(
        "classroom_resources",
        sa.Column("classroom_id", sa.Integer, sa.ForeignKey("classrooms.id"), primary_key=True),
        sa.Column("resource_id", sa.Integer, sa.ForeignKey("resources.id"), primary_key=True),
    )
    op.create_table(
        "timeslots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("day", sa.String(20), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("duration", sa.Float, nullable=False),
    )
    op.create_table(
        "professors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("max_weekly_hours", sa.Integer, default=40, nullable=False),
        sa.Column("contract_type", sa.String(30), default="tiempo_completo", nullable=False),
    )
    op.create_table(
        "professor_availability",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("professor_id", sa.Integer, sa.ForeignKey("professors.id"), nullable=False),
        sa.Column("timeslot_code", sa.String(20), nullable=False),
        sa.UniqueConstraint("professor_id", "timeslot_code", name="uq_prof_avail"),
    )
    op.create_table(
        "professor_preferences",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("professor_id", sa.Integer, sa.ForeignKey("professors.id"), nullable=False),
        sa.Column("timeslot_code", sa.String(20), nullable=False),
        sa.Column("preference", sa.Float, nullable=False, default=0.5),
        sa.UniqueConstraint("professor_id", "timeslot_code", name="uq_prof_pref"),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("credits", sa.Integer, nullable=False),
        sa.Column("study_hours", sa.Integer, nullable=False),
        sa.Column("weekly_subgroups", sa.Integer, default=1, nullable=False),
        sa.Column("groups", sa.Integer, default=1, nullable=False),
        sa.Column("enrollment", sa.Integer, default=30, nullable=False),
        sa.Column("faculty", sa.String(100), default="ingenieria", nullable=False),
        sa.Column("professor_code", sa.String(20), sa.ForeignKey("professors.code"), nullable=True),
    )
    op.create_table(
        "subject_required_resources",
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id"), primary_key=True),
        sa.Column("resource_id", sa.Integer, sa.ForeignKey("resources.id"), primary_key=True),
    )
    op.create_table(
        "subject_optional_resources",
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id"), primary_key=True),
        sa.Column("resource_id", sa.Integer, sa.ForeignKey("resources.id"), primary_key=True),
    )
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("schedule_id", sa.String(36), unique=True, nullable=False),
        sa.Column("semester", sa.String(20), nullable=False),
        sa.Column("solver_used", sa.String(30), nullable=False),
        sa.Column("utility_score", sa.Float, nullable=False, default=0.0),
        sa.Column("elapsed_seconds", sa.Float, nullable=False, default=0.0),
        sa.Column("is_feasible", sa.Boolean, nullable=False, default=False),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("schedule_id", sa.Integer, sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("subject_code", sa.String(20), sa.ForeignKey("subjects.code"), nullable=False),
        sa.Column("classroom_code", sa.String(20), sa.ForeignKey("classrooms.code"), nullable=False),
        sa.Column("timeslot_code", sa.String(20), sa.ForeignKey("timeslots.code"), nullable=False),
        sa.Column("group_number", sa.Integer, nullable=False, default=1),
        sa.Column("session_number", sa.Integer, nullable=False, default=1),
        sa.Column("score", sa.Float, nullable=False, default=0.0),
        sa.UniqueConstraint("schedule_id", "classroom_code", "timeslot_code",
                           name="uq_assignment_classroom_slot"),
    )
    op.create_table(
        "dynamic_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("schedule_id", sa.Integer, sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.Text, nullable=False, default="{}"),
        sa.Column("affected_assignments", sa.Integer, default=0),
        sa.Column("repair_elapsed_seconds", sa.Float, default=0.0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("dynamic_events")
    op.drop_table("assignments")
    op.drop_table("schedules")
    op.drop_table("subject_optional_resources")
    op.drop_table("subject_required_resources")
    op.drop_table("subjects")
    op.drop_table("professor_preferences")
    op.drop_table("professor_availability")
    op.drop_table("professors")
    op.drop_table("timeslots")
    op.drop_table("classroom_resources")
    op.drop_table("classrooms")
    op.drop_table("resources")
