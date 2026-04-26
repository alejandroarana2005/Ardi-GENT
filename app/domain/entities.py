"""
HAIA Agent — Entidades de dominio puras.

Modelo de datos de:
    La Cruz, A., Herrera, L., Cortes, J., García-León, A., y Severeyn, E. (2024).
    "UniSchedApi: A comprehensive solution for university resource scheduling
    and methodology comparison."
    Transactions on Energy Systems and Engineering Applications, 5(2):633.
    DOI: 10.32397/tesea.vol5.n2.633

Extensiones HAIA sobre el modelo original: campos BDI en Subject/Assignment
(faculty, utilidad_score), entidades SchedulingResult y SchedulingInstance
con métricas del agente.

Todas las entidades son dataclasses inmutables para facilitar hashing y comparación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Optional


@dataclass(frozen=True)
class Resource:
    """Recurso físico disponible en un aula o requerido por una materia."""
    code: str
    name: str  # computers | projector | tv | software_lab | electronics_lab | specialized_equipment

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ResourceRequirement:
    """Requerimiento de recurso asociado a una materia (obligatorio u opcional)."""
    resource_code: str
    quantity: int = 1


@dataclass(frozen=True)
class Constraint:
    """
    Restricción asociada a una materia, docente o instancia global.
    HC (Hard Constraint) = type 'hard'  — nunca se puede violar.
    SC (Soft Constraint) = type 'soft'  — penaliza U(A) si se viola.
    """
    code: str
    name: str
    description: str  # Descripción alfanumérica del filtro (La Cruz et al., 2024)
    type: str         # "hard" | "soft"
    active: bool = True

    def is_hard(self) -> bool:
        return self.type == "hard"

    def is_soft(self) -> bool:
        return self.type == "soft"


@dataclass(frozen=True)
class TimeSlot:
    """
    Franja horaria. El modelo UniSchedApi usa 4 franjas × 6 días = 24 franjas.
    Ref: La Cruz et al. (2024) — modelo de datos Universidad de Ibagué.
    """
    code: str
    day: str        # Monday | Tuesday | Wednesday | Thursday | Friday | Saturday
    start_time: time
    end_time: time
    duration: float  # horas

    def __str__(self) -> str:
        return f"{self.day} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


@dataclass(frozen=True)
class Classroom:
    """
    Aula universitaria con su capacidad y recursos disponibles.
    Ref: La Cruz et al. (2024) — entidad Classroom.
    """
    code: str
    name: str
    capacity: int
    resources: tuple[Resource, ...] = field(default_factory=tuple)

    def has_resource(self, resource_code: str) -> bool:
        return any(r.code == resource_code for r in self.resources)

    def satisfies_requirements(self, requirements: tuple[ResourceRequirement, ...]) -> bool:
        return all(self.has_resource(req.resource_code) for req in requirements)

    def __str__(self) -> str:
        return f"{self.name} (cap={self.capacity})"


@dataclass(frozen=True)
class PreferenceSlot:
    """Preferencia de un docente por una franja horaria. pref ∈ [0,1]."""
    timeslot_code: str
    preference: float  # 0.0 = no deseable, 1.0 = muy deseable

    def __post_init__(self) -> None:
        if not 0.0 <= self.preference <= 1.0:
            raise ValueError(f"preference must be in [0,1], got {self.preference}")


@dataclass(frozen=True)
class Professor:
    """
    Docente con disponibilidad y preferencias horarias.
    contract_type define la carga máxima semanal permitida.
    """
    code: str
    name: str
    availability: tuple[str, ...] = field(default_factory=tuple)   # timeslot codes
    preferences: tuple[PreferenceSlot, ...] = field(default_factory=tuple)
    max_weekly_hours: int = 40
    contract_type: str = "tiempo_completo"  # hora_catedra | medio_tiempo | tiempo_completo

    def preference_for(self, timeslot_code: str) -> float:
        for p in self.preferences:
            if p.timeslot_code == timeslot_code:
                return p.preference
        return 0.5  # neutral si no hay preferencia explícita

    def is_available(self, timeslot_code: str) -> bool:
        return timeslot_code in self.availability

    def __str__(self) -> str:
        return f"{self.name} ({self.contract_type})"


@dataclass(frozen=True)
class Subject:
    """
    Materia a programar. Puede tener múltiples grupos que generan asignaciones independientes.
    Ref: La Cruz et al. (2024) — entidad Subject con todos sus campos.
    """
    code: str
    name: str
    credits: int
    study_hours: int
    weekly_subgroups: int          # sesiones por semana (normalmente 1 o 2)
    groups: int                    # número de grupos paralelos a programar
    enrollment: int = 30           # estudiantes matriculados (promedio por grupo)
    professor_code: Optional[str] = None
    required_resources: tuple[ResourceRequirement, ...] = field(default_factory=tuple)
    optional_resources: tuple[ResourceRequirement, ...] = field(default_factory=tuple)
    constraints: tuple[Constraint, ...] = field(default_factory=tuple)
    faculty: str = "ingenieria"    # facultad para descomposición jerárquica

    def total_assignments_needed(self) -> int:
        """Total de tuplas (materia, grupo, sesión) a asignar."""
        return self.groups * self.weekly_subgroups

    def __str__(self) -> str:
        return f"{self.code} — {self.name} ({self.groups}g × {self.weekly_subgroups}s/sem)"


@dataclass
class Assignment:
    """
    Asignación concreta: materia-grupo en salón-franja.
    La puntuación U(A) se calcula por la Capa 4.
    Ref: La Cruz et al. (2024) — entidad Assignment extendida con score HAIA.
    """
    subject_code: str
    classroom_code: str
    timeslot_code: str
    group_number: int
    session_number: int = 1      # para materias con weekly_subgroups > 1
    utilidad_score: float = 0.0  # U(A) calculado por utility_function.py

    def key(self) -> tuple:
        return (self.subject_code, self.group_number, self.session_number)

    def __str__(self) -> str:
        return (
            f"{self.subject_code} G{self.group_number}S{self.session_number} "
            f"→ {self.classroom_code} @ {self.timeslot_code}"
        )


@dataclass
class SchedulingInstance:
    """
    Instancia completa del problema de asignación para un semestre.
    Es la entrada principal al pipeline de HAIA.
    """
    semester: str
    subjects: list[Subject]
    classrooms: list[Classroom]
    timeslots: list[TimeSlot]
    professors: list[Professor]
    global_constraints: list[Constraint] = field(default_factory=list)

    def summary(self) -> dict:
        total_assignments = sum(s.total_assignments_needed() for s in self.subjects)
        return {
            "semester": self.semester,
            "subjects": len(self.subjects),
            "total_assignments_needed": total_assignments,
            "classrooms": len(self.classrooms),
            "timeslots": len(self.timeslots),
            "professors": len(self.professors),
            "search_space_size": total_assignments * len(self.classrooms) * len(self.timeslots),
        }


@dataclass
class SchedulingResult:
    """Resultado completo del ciclo de asignación de HAIA."""
    schedule_id: str
    semester: str
    assignments: list[Assignment]
    utility_score: float
    solver_used: str          # "backtracking" | "milp" | "tabu_search"
    elapsed_seconds: float
    is_feasible: bool
    violations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
