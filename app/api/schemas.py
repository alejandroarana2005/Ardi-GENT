"""
HAIA Agent — Pydantic schemas para request/response de la API REST.
Separados de los modelos ORM y las entidades de dominio para respetar
los límites de capa (La Cruz et al., 2024 — patrón API REST).
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────── Recursos ────────────────────────────────────────────

class ResourceCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)


class ResourceResponse(ResourceCreate):
    id: int

    model_config = {"from_attributes": True}


# ─────────────────────── Salones ─────────────────────────────────────────────

class ClassroomCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    capacity: int = Field(..., gt=0)
    resource_codes: list[str] = Field(default_factory=list)


class ClassroomResponse(BaseModel):
    id: int
    code: str
    name: str
    capacity: int
    resources: list[ResourceResponse] = []

    model_config = {"from_attributes": True}


# ─────────────────────── Franjas horarias ────────────────────────────────────

class TimeSlotCreate(BaseModel):
    code: str = Field(..., max_length=20)
    day: str = Field(..., max_length=20)
    start_time: time
    end_time: time
    duration: float = Field(..., gt=0)

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: str) -> str:
        valid = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"}
        if v not in valid:
            raise ValueError(f"day must be one of {valid}")
        return v


class TimeSlotResponse(TimeSlotCreate):
    id: int

    model_config = {"from_attributes": True}


# ─────────────────────── Docentes ────────────────────────────────────────────

class PreferenceSlotSchema(BaseModel):
    timeslot_code: str
    preference: float = Field(..., ge=0.0, le=1.0)


class ProfessorCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    max_weekly_hours: int = Field(default=40, gt=0)
    contract_type: str = Field(default="tiempo_completo")
    availability: list[str] = Field(default_factory=list)  # timeslot codes
    preferences: list[PreferenceSlotSchema] = Field(default_factory=list)

    @field_validator("contract_type")
    @classmethod
    def validate_contract(cls, v: str) -> str:
        valid = {"hora_catedra", "medio_tiempo", "tiempo_completo"}
        if v not in valid:
            raise ValueError(f"contract_type must be one of {valid}")
        return v


class ProfessorResponse(BaseModel):
    id: int
    code: str
    name: str
    max_weekly_hours: int
    contract_type: str

    model_config = {"from_attributes": True}


# ─────────────────────── Materias ────────────────────────────────────────────

class SubjectCreate(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    credits: int = Field(..., gt=0)
    study_hours: int = Field(..., gt=0)
    weekly_subgroups: int = Field(default=1, gt=0)
    groups: int = Field(default=1, gt=0)
    enrollment: int = Field(default=30, gt=0)
    faculty: str = Field(default="ingenieria")
    professor_code: Optional[str] = None
    required_resource_codes: list[str] = Field(default_factory=list)
    optional_resource_codes: list[str] = Field(default_factory=list)


class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    credits: int
    study_hours: int
    weekly_subgroups: int
    groups: int
    enrollment: int
    faculty: str
    professor_code: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────────────── Asignaciones ────────────────────────────────────────

class AssignmentResponse(BaseModel):
    id: int
    subject_code: str
    classroom_code: str
    timeslot_code: str
    group_number: int
    session_number: int
    utilidad_score: float

    model_config = {"from_attributes": True}


# ─────────────────────── Horarios ────────────────────────────────────────────

class ScheduleRequest(BaseModel):
    semester: str = Field(..., max_length=20, examples=["2024-A"])
    solver_hint: Optional[str] = Field(
        default=None,
        description="Forzar solver: 'backtracking' | 'milp' | 'tabu_search'. "
                    "Si None, solver_factory decide automáticamente.",
    )


class ScheduleResponse(BaseModel):
    schedule_id: str
    semester: str
    solver_used: str
    utility_score: float
    elapsed_seconds: float
    is_feasible: bool
    status: str
    assignment_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduleDetailResponse(BaseModel):
    """Respuesta enriquecida para GET /schedule/{id} con métricas de calidad."""
    schedule_id: str
    semester: str
    status: str
    solver_used: str
    utility_score: float
    is_feasible: bool
    total_courses: int
    assigned_courses: int
    hard_constraint_violations: int
    soft_constraint_violations: int
    solve_time_ms: int
    elapsed_seconds: float
    assignments: Optional[list[AssignmentResponse]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────── Eventos dinámicos ───────────────────────────────────

class DynamicEventRequest(BaseModel):
    schedule_id: str
    event_type: str = Field(
        ...,
        description="CLASSROOM_UNAVAILABLE | PROFESSOR_CANCELLED | "
                    "ENROLLMENT_SURGE | SLOT_BLOCKED | NEW_COURSE_ADDED",
    )
    payload: dict = Field(default_factory=dict)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        valid = {
            "CLASSROOM_UNAVAILABLE",
            "PROFESSOR_CANCELLED",
            "ENROLLMENT_SURGE",
            "SLOT_BLOCKED",
            "NEW_COURSE_ADDED",
        }
        if v not in valid:
            raise ValueError(f"event_type must be one of {valid}")
        return v


class DynamicEventResponse(BaseModel):
    id: int
    schedule_id: str
    event_type: str
    affected_assignments: int
    repair_elapsed_seconds: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────── Métricas ────────────────────────────────────────────

class MetricsResponse(BaseModel):
    schedule_id: str
    utility_score: float
    u_occupancy: float
    u_preference: float
    u_distribution: float
    u_resources: float
    penalty: float
    total_assignments: int
    feasible_assignments: int
    hard_constraint_violations: int
    soft_constraint_violations: int
    avg_occupancy_ratio: float
    weights_used: dict = Field(default_factory=dict)
    soft_constraint_counts: dict = Field(default_factory=dict)


# ─────────────────────── Health ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    db_connected: bool
    agent: str = "HAIA — Hybrid Adaptive Intelligent Agent"
