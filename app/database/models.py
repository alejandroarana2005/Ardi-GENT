"""
HAIA Agent — Modelos ORM SQLAlchemy.
Mapea las entidades de dominio (La Cruz et al., 2024) a tablas relacionales.
Convención de nombres: snake_case para columnas, PascalCase para clases ORM.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Column,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ─────────────────────── Tabla de asociación Resource ↔ Classroom ────────────

classroom_resources = Table(
    "classroom_resources",
    Base.metadata,
    Column("classroom_id", Integer, ForeignKey("classrooms.id"), primary_key=True),
    Column("resource_id", Integer, ForeignKey("resources.id"), primary_key=True),
)

# ─────────────────────── Tabla de asociación Resource ↔ Subject (required) ──

subject_required_resources = Table(
    "subject_required_resources",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
    Column("resource_id", Integer, ForeignKey("resources.id"), primary_key=True),
)

# ─────────────────────── Tabla de asociación Resource ↔ Subject (optional) ──

subject_optional_resources = Table(
    "subject_optional_resources",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
    Column("resource_id", Integer, ForeignKey("resources.id"), primary_key=True),
)


# ─────────────────────── Entidades principales ───────────────────────────────

class ResourceModel(Base):
    """Recurso físico de un aula. Ref: La Cruz et al. (2024) — Resource."""
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    classrooms: Mapped[list[ClassroomModel]] = relationship(
        "ClassroomModel", secondary=classroom_resources, back_populates="resources"
    )


class ClassroomModel(Base):
    """Aula universitaria. Ref: La Cruz et al. (2024) — Classroom."""
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    edificio: Mapped[str | None] = mapped_column(String(100), nullable=True)

    resources: Mapped[list[ResourceModel]] = relationship(
        "ResourceModel", secondary=classroom_resources, back_populates="classrooms"
    )
    assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel", back_populates="classroom"
    )


class TimeSlotModel(Base):
    """Franja horaria. 4 franjas × 6 días = 24 franjas. Ref: La Cruz et al. (2024)."""
    __tablename__ = "timeslots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    day: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    end_time: Mapped[time] = mapped_column(nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    semestre: Mapped[str | None] = mapped_column(String(10), nullable=True)

    assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel", back_populates="timeslot"
    )


class SubjectModel(Base):
    """Materia. Ref: La Cruz et al. (2024) — Subject."""
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    study_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    weekly_subgroups: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    groups: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enrollment: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    faculty: Mapped[str] = mapped_column(String(100), default="ingenieria", nullable=False)
    professor_code: Mapped[str | None] = mapped_column(String(20), ForeignKey("professors.code"), nullable=True)

    professor: Mapped[ProfessorModel | None] = relationship("ProfessorModel", back_populates="subjects")
    required_resources: Mapped[list[ResourceModel]] = relationship(
        "ResourceModel", secondary=subject_required_resources
    )
    optional_resources: Mapped[list[ResourceModel]] = relationship(
        "ResourceModel", secondary=subject_optional_resources
    )
    assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel", back_populates="subject"
    )


class ProfessorModel(Base):
    """Docente con disponibilidad y preferencias."""
    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    max_weekly_hours: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    contract_type: Mapped[str] = mapped_column(
        String(30), default="tiempo_completo", nullable=False
    )
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subjects: Mapped[list[SubjectModel]] = relationship("SubjectModel", back_populates="professor")
    availability: Mapped[list[ProfessorAvailabilityModel]] = relationship(
        "ProfessorAvailabilityModel", back_populates="professor", cascade="all, delete-orphan"
    )
    preferences: Mapped[list[ProfessorPreferenceModel]] = relationship(
        "ProfessorPreferenceModel", back_populates="professor", cascade="all, delete-orphan"
    )


class ProfessorAvailabilityModel(Base):
    """Disponibilidad de un docente en una franja horaria."""
    __tablename__ = "professor_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professor_id: Mapped[int] = mapped_column(Integer, ForeignKey("professors.id"), nullable=False)
    timeslot_code: Mapped[str] = mapped_column(String(20), nullable=False)

    professor: Mapped[ProfessorModel] = relationship("ProfessorModel", back_populates="availability")

    __table_args__ = (
        UniqueConstraint("professor_id", "timeslot_code", name="uq_prof_avail"),
    )


class ProfessorPreferenceModel(Base):
    """Preferencia numérica [0,1] de un docente para una franja."""
    __tablename__ = "professor_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professor_id: Mapped[int] = mapped_column(Integer, ForeignKey("professors.id"), nullable=False)
    timeslot_code: Mapped[str] = mapped_column(String(20), nullable=False)
    preference: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    professor: Mapped[ProfessorModel] = relationship("ProfessorModel", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint("professor_id", "timeslot_code", name="uq_prof_pref"),
    )


# ─────────────────────── Tablas de horario ───────────────────────────────────

class ScheduleModel(Base):
    """Registro de una ejecución del ciclo de asignación de HAIA."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    solver_used: Mapped[str] = mapped_column(String(30), nullable=False)
    utility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elapsed_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_feasible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending | running | completed | accepted | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    assignments: Mapped[list[AssignmentModel]] = relationship(
        "AssignmentModel", back_populates="schedule", cascade="all, delete-orphan"
    )
    events: Mapped[list[DynamicEventModel]] = relationship(
        "DynamicEventModel", back_populates="schedule", cascade="all, delete-orphan"
    )


class AssignmentModel(Base):
    """
    Asignación concreta de materia-grupo a salón-franja.
    Ref: La Cruz et al. (2024) — Assignment extendido con score HAIA.
    """
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id"), nullable=False)
    subject_code: Mapped[str] = mapped_column(String(20), ForeignKey("subjects.code"), nullable=False)
    classroom_code: Mapped[str] = mapped_column(String(20), ForeignKey("classrooms.code"), nullable=False)
    timeslot_code: Mapped[str] = mapped_column(String(20), ForeignKey("timeslots.code"), nullable=False)
    professor_code: Mapped[str] = mapped_column(String(20), ForeignKey("professors.code"), nullable=False)
    group_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    utilidad_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    schedule: Mapped[ScheduleModel] = relationship("ScheduleModel", back_populates="assignments")
    subject: Mapped[SubjectModel] = relationship("SubjectModel", back_populates="assignments")
    classroom: Mapped[ClassroomModel] = relationship("ClassroomModel", back_populates="assignments")
    timeslot: Mapped[TimeSlotModel] = relationship("TimeSlotModel", back_populates="assignments")
    professor: Mapped[ProfessorModel | None] = relationship("ProfessorModel")

    __table_args__ = (
        UniqueConstraint(
            "schedule_id", "classroom_code", "timeslot_code",
            name="uq_assignment_classroom_slot"
        ),
        UniqueConstraint(
            "schedule_id", "professor_code", "timeslot_code",
            name="uq_assignment_professor_slot"
        ),
    )


# ─────────────────────── Eventos dinámicos ───────────────────────────────────

class DynamicEventModel(Base):
    """Evento que dispara re-optimización dinámica (Capa 5)."""
    __tablename__ = "dynamic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedules.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # CLASSROOM_UNAVAILABLE | PROFESSOR_CANCELLED | ENROLLMENT_SURGE | SLOT_BLOCKED | NEW_COURSE_ADDED
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    affected_assignments: Mapped[int] = mapped_column(Integer, default=0)
    repair_elapsed_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    schedule: Mapped[ScheduleModel] = relationship("ScheduleModel", back_populates="events")
