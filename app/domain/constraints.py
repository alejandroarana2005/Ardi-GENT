"""
HAIA Agent — Definición formal de restricciones HC y SC.
Cada restricción es una clase configurable que expone un método check() y penalty().

Hard Constraints (HC) — nunca se pueden violar en una solución factible:
    HC1: No double-booking de salones (mismo salón, misma franja → máx 1 clase)
    HC2: No double-booking de docentes (mismo docente, misma franja → máx 1 clase)
    HC3: Capacidad suficiente (enrollment ≤ capacity del salón)
    HC4: Recursos requeridos disponibles en el salón
    HC5: Docente disponible en la franja asignada

Soft Constraints (SC) — penalizan U(A) pero no invalidan la solución:
    SC1: Preferencia horaria del docente (pref ∈ [0,1])
    SC2: No asignar lunes primera franja (restricción institucional U. Ibagué)
    SC3: Preferir bloques de mañana
    SC4: No más de 3 horas consecutivas para un docente
    SC5: Distribución equitativa de carga entre docentes
    SC6: Minimizar salones subutilizados (ocupación < 50%)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.entities import Assignment, SchedulingInstance


class BaseConstraint(ABC):
    """Interfaz común para todas las restricciones del sistema HAIA."""

    code: str
    name: str
    constraint_type: str  # "hard" | "soft"
    active: bool = True

    @abstractmethod
    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        """Retorna True si la restricción se satisface."""
        ...

    def penalty(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> float:
        """Penalización numérica si se viola (solo relevante para SC). Default 0."""
        return 0.0 if self.check(assignment, all_assignments, instance) else 1.0


# ─────────────────────────── HARD CONSTRAINTS ────────────────────────────────

@dataclass
class HC1_NoDoubleBookingClassroom(BaseConstraint):
    """HC1: Un salón no puede tener dos clases en la misma franja."""
    code: str = "HC1"
    name: str = "No Double Booking Classroom"
    constraint_type: str = "hard"

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        conflicts = [
            a for a in all_assignments
            if a is not assignment
            and a.classroom_code == assignment.classroom_code
            and a.timeslot_code == assignment.timeslot_code
        ]
        return len(conflicts) == 0


@dataclass
class HC2_NoDoubleBookingProfessor(BaseConstraint):
    """HC2: Un docente no puede tener dos clases en la misma franja."""
    code: str = "HC2"
    name: str = "No Double Booking Professor"
    constraint_type: str = "hard"

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        if subject is None or subject.professor_code is None:
            return True

        same_prof_same_slot = [
            a for a in all_assignments
            if a is not assignment
            and a.timeslot_code == assignment.timeslot_code
        ]
        for a in same_prof_same_slot:
            other_subject = next(
                (s for s in instance.subjects if s.code == a.subject_code), None
            )
            if other_subject and other_subject.professor_code == subject.professor_code:
                return False
        return True


@dataclass
class HC3_SufficientCapacity(BaseConstraint):
    """HC3: El salón debe tener capacidad suficiente para el grupo."""
    code: str = "HC3"
    name: str = "Sufficient Capacity"
    constraint_type: str = "hard"

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        classroom = next(
            (c for c in instance.classrooms if c.code == assignment.classroom_code), None
        )
        if subject is None or classroom is None:
            return False
        return classroom.capacity >= subject.enrollment


@dataclass
class HC4_RequiredResources(BaseConstraint):
    """HC4: El salón debe tener todos los recursos requeridos por la materia."""
    code: str = "HC4"
    name: str = "Required Resources Available"
    constraint_type: str = "hard"

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        classroom = next(
            (c for c in instance.classrooms if c.code == assignment.classroom_code), None
        )
        if subject is None or classroom is None:
            return False
        return classroom.satisfies_requirements(subject.required_resources)


@dataclass
class HC5_ProfessorAvailability(BaseConstraint):
    """HC5: La franja asignada debe estar en la disponibilidad del docente."""
    code: str = "HC5"
    name: str = "Professor Availability"
    constraint_type: str = "hard"

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        if subject is None or subject.professor_code is None:
            return True  # sin docente asignado, no aplica
        professor = next(
            (p for p in instance.professors if p.code == subject.professor_code), None
        )
        if professor is None:
            return True
        return professor.is_available(assignment.timeslot_code)


# ─────────────────────────── SOFT CONSTRAINTS ────────────────────────────────

@dataclass
class SC1_ProfessorPreference(BaseConstraint):
    """SC1: Preferir franjas de alta preferencia para cada docente."""
    code: str = "SC1"
    name: str = "Professor Time Preference"
    constraint_type: str = "soft"
    penalty_weight: float = 0.5

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        if subject is None or subject.professor_code is None:
            return True
        professor = next(
            (p for p in instance.professors if p.code == subject.professor_code), None
        )
        if professor is None:
            return True
        return professor.preference_for(assignment.timeslot_code) >= 0.5

    def penalty(self, assignment, all_assignments, instance) -> float:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        if subject is None or subject.professor_code is None:
            return 0.0
        professor = next(
            (p for p in instance.professors if p.code == subject.professor_code), None
        )
        if professor is None:
            return 0.0
        pref = professor.preference_for(assignment.timeslot_code)
        return self.penalty_weight * (1.0 - pref)


@dataclass
class SC2_NoMondayFirstSlot(BaseConstraint):
    """
    SC2: No asignar lunes primera franja (restricción institucional U. Ibagué).
    Ref: La Cruz et al. (2024) — restricciones institucionales del semestre 2023-A/B.
    """
    code: str = "SC2"
    name: str = "No Monday First Slot"
    constraint_type: str = "soft"
    forbidden_slot_code: str = "TS_MON_1"  # configurable
    penalty_weight: float = 0.25

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        return assignment.timeslot_code != self.forbidden_slot_code

    def penalty(self, assignment, all_assignments, instance) -> float:
        return self.penalty_weight if not self.check(assignment, all_assignments, instance) else 0.0


@dataclass
class SC3_PreferMorningSlots(BaseConstraint):
    """SC3: Preferir bloques de mañana (mejor asistencia estudiantil)."""
    code: str = "SC3"
    name: str = "Prefer Morning Slots"
    constraint_type: str = "soft"
    morning_slot_codes: tuple[str, ...] = ("TS_MON_1", "TS_MON_2",
                                            "TS_TUE_1", "TS_TUE_2",
                                            "TS_WED_1", "TS_WED_2",
                                            "TS_THU_1", "TS_THU_2",
                                            "TS_FRI_1", "TS_FRI_2",
                                            "TS_SAT_1", "TS_SAT_2")
    penalty_weight: float = 0.3

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        return assignment.timeslot_code in self.morning_slot_codes

    def penalty(self, assignment, all_assignments, instance) -> float:
        return self.penalty_weight if not self.check(assignment, all_assignments, instance) else 0.0


@dataclass
class SC4_MaxConsecutiveHours(BaseConstraint):
    """SC4: Un docente no debe tener más de 3 horas consecutivas."""
    code: str = "SC4"
    name: str = "Max Consecutive Hours"
    constraint_type: str = "soft"
    max_consecutive: int = 3
    penalty_weight: float = 0.15

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        if subject is None or subject.professor_code is None:
            return True

        # Obtener todas las asignaciones del mismo docente
        prof_assignments = []
        for a in all_assignments:
            s = next((sub for sub in instance.subjects if sub.code == a.subject_code), None)
            if s and s.professor_code == subject.professor_code:
                ts = next((t for t in instance.timeslots if t.code == a.timeslot_code), None)
                if ts:
                    prof_assignments.append((ts.day, ts.start_time, ts.duration))

        # Verificar franjas del mismo día ordenadas
        ts_current = next(
            (t for t in instance.timeslots if t.code == assignment.timeslot_code), None
        )
        if ts_current is None:
            return True

        same_day = sorted(
            [(st, dur) for day, st, dur in prof_assignments if day == ts_current.day],
            key=lambda x: x[0],
        )
        consecutive_hours = sum(dur for _, dur in same_day)
        return consecutive_hours <= self.max_consecutive

    def penalty(self, assignment, all_assignments, instance) -> float:
        return self.penalty_weight if not self.check(assignment, all_assignments, instance) else 0.0


@dataclass
class SC5_EquitableLoadDistribution(BaseConstraint):
    """SC5: Distribuir la carga equitativamente entre docentes de la misma categoría."""
    code: str = "SC5"
    name: str = "Equitable Load Distribution"
    constraint_type: str = "soft"
    penalty_weight: float = 0.4

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        return True  # la verificación real se hace a nivel de conjunto en metrics

    def penalty(self, assignment, all_assignments, instance) -> float:
        return 0.0


@dataclass
class SC6_MinimizeUnderutilization(BaseConstraint):
    """SC6: Penalizar aulas con ocupación menor al 50%."""
    code: str = "SC6"
    name: str = "Minimize Underutilization"
    constraint_type: str = "soft"
    min_occupancy_ratio: float = 0.5
    penalty_weight: float = 0.3

    def check(
        self,
        assignment: "Assignment",
        all_assignments: list["Assignment"],
        instance: "SchedulingInstance",
    ) -> bool:
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        classroom = next(
            (c for c in instance.classrooms if c.code == assignment.classroom_code), None
        )
        if subject is None or classroom is None:
            return True
        return (subject.enrollment / classroom.capacity) >= self.min_occupancy_ratio

    def penalty(self, assignment, all_assignments, instance) -> float:
        if self.check(assignment, all_assignments, instance):
            return 0.0
        subject = next(
            (s for s in instance.subjects if s.code == assignment.subject_code), None
        )
        classroom = next(
            (c for c in instance.classrooms if c.code == assignment.classroom_code), None
        )
        if subject is None or classroom is None:
            return 0.0
        ratio = subject.enrollment / classroom.capacity
        return self.penalty_weight * (self.min_occupancy_ratio - ratio)


# ─────────────────────────── REGISTRO GLOBAL ─────────────────────────────────

ALL_HARD_CONSTRAINTS: list[BaseConstraint] = [
    HC1_NoDoubleBookingClassroom(),
    HC2_NoDoubleBookingProfessor(),
    HC3_SufficientCapacity(),
    HC4_RequiredResources(),
    HC5_ProfessorAvailability(),
]

ALL_SOFT_CONSTRAINTS: list[BaseConstraint] = [
    SC1_ProfessorPreference(),
    SC2_NoMondayFirstSlot(),
    SC3_PreferMorningSlots(),
    SC4_MaxConsecutiveHours(),
    SC5_EquitableLoadDistribution(),
    SC6_MinimizeUnderutilization(),
]

ALL_CONSTRAINTS: list[BaseConstraint] = ALL_HARD_CONSTRAINTS + ALL_SOFT_CONSTRAINTS


def get_active_constraints(constraint_type: str | None = None) -> list[BaseConstraint]:
    """Retorna solo las restricciones activas, opcionalmente filtradas por tipo."""
    constraints = ALL_CONSTRAINTS
    if constraint_type:
        constraints = [c for c in constraints if c.constraint_type == constraint_type]
    return [c for c in constraints if c.active]
