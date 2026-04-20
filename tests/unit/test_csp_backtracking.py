"""Tests unitarios para CSPBacktrackingSolver — Capa 3."""

from datetime import time

import pytest

from app.config import HAIAConfig
from app.domain.entities import (
    Assignment,
    Classroom,
    Professor,
    Resource,
    ResourceRequirement,
    SchedulingInstance,
    Subject,
    TimeSlot,
)
from app.layer2_preprocessing.ac3 import AC3Preprocessor
from app.layer2_preprocessing.domain_filter import DomainFilter
from app.layer3_solver.csp_backtracking import CSPBacktrackingSolver
from tests.fixtures.sample_data import build_minimal_instance


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def config():
    return HAIAConfig()


def make_timeslots(n: int) -> list[TimeSlot]:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    slots = []
    for i in range(n):
        day = days[i % len(days)]
        hour = 7 + (i % 4) * 2
        slots.append(TimeSlot(
            f"TS_{i}", day,
            time(hour, 0), time(hour + 2, 0), 2.0
        ))
    return slots


def make_instance(subjects, classrooms, timeslots, professors=None) -> SchedulingInstance:
    return SchedulingInstance(
        semester="TEST",
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors or [],
    )


def get_domains(instance: SchedulingInstance) -> dict:
    domains = DomainFilter().filter(instance)
    reduced, feasible = AC3Preprocessor().run(instance, domains)
    return reduced if feasible else domains


# ── Verificadores de restricciones ────────────────────────────────────────────

def check_hc1(assignments: list[Assignment]) -> list[str]:
    """Retorna lista de violaciones HC1 (mismo salón, misma franja)."""
    violations = []
    for i, a in enumerate(assignments):
        for b in assignments[i + 1:]:
            if a.classroom_code == b.classroom_code and a.timeslot_code == b.timeslot_code:
                violations.append(
                    f"HC1: {a.subject_code} y {b.subject_code} comparten {a.classroom_code}@{a.timeslot_code}"
                )
    return violations


def check_hc2(assignments: list[Assignment], instance: SchedulingInstance) -> list[str]:
    """Retorna lista de violaciones HC2 (mismo docente, misma franja)."""
    prof_map = {s.code: s.professor_code for s in instance.subjects}
    violations = []
    for i, a in enumerate(assignments):
        for b in assignments[i + 1:]:
            if a.timeslot_code == b.timeslot_code:
                p1 = prof_map.get(a.subject_code)
                p2 = prof_map.get(b.subject_code)
                if p1 and p2 and p1 == p2:
                    violations.append(
                        f"HC2: {a.subject_code} y {b.subject_code} "
                        f"tienen mismo docente {p1} en {a.timeslot_code}"
                    )
    return violations


# ── Tests de solución ─────────────────────────────────────────────────────────

class TestCSPSolvesMinimalInstance:
    def test_finds_solution(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = CSPBacktrackingSolver(config)
        result = solver.solve(instance, domains)

        assert len(result) > 0, "El solver debe encontrar al menos una asignación"

    def test_assigns_all_variables(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = CSPBacktrackingSolver(config)
        result = solver.solve(instance, domains)

        assigned_keys = {
            f"{a.subject_code}__g{a.group_number}__s{a.session_number}"
            for a in result
        }
        expected_keys = set(domains.keys())
        assert assigned_keys == expected_keys

    def test_no_hc1_violations(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        violations = check_hc1(result)
        assert violations == [], f"Violaciones HC1: {violations}"

    def test_no_hc2_violations(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        violations = check_hc2(result, instance)
        assert violations == [], f"Violaciones HC2: {violations}"

    def test_assignments_within_domain(self, config):
        """Cada asignación debe pertenecer al dominio de su variable."""
        instance = build_minimal_instance()
        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        for a in result:
            key = f"{a.subject_code}__g{a.group_number}__s{a.session_number}"
            assert (a.classroom_code, a.timeslot_code) in domains[key], (
                f"{key} asignado a ({a.classroom_code}, {a.timeslot_code}) "
                f"que no está en su dominio"
            )


class TestCSPWithMultipleGroupsAndSessions:
    def test_multiple_groups_all_assigned(self, config):
        proj = Resource("PROJ", "projector")
        subjects = [Subject("S1", "Mat", 3, 4, weekly_subgroups=1, groups=3, enrollment=20)]
        classrooms = [Classroom(f"A{i}", f"Aula{i}", 30, (proj,)) for i in range(3)]
        timeslots = make_timeslots(6)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        # 3 grupos → 3 asignaciones
        assert len(result) == 3
        assert check_hc1(result) == []

    def test_weekly_subgroups_all_assigned(self, config):
        proj = Resource("PROJ", "projector")
        subjects = [Subject("S1", "Calc", 3, 4, weekly_subgroups=2, groups=2, enrollment=20)]
        classrooms = [Classroom(f"A{i}", f"Aula{i}", 30, (proj,)) for i in range(3)]
        timeslots = make_timeslots(8)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        # 2 grupos × 2 sesiones = 4 asignaciones
        assert len(result) == 4
        assert check_hc1(result) == []


class TestCSPHeuristics:
    def test_mrv_selects_most_constrained(self, config):
        """
        Con un salón de recursos especializados y múltiples materias normales,
        MRV debe asignar primero la materia más restringida (dominio más pequeño).
        Verifica que la solución sea válida independientemente del orden de selección.
        """
        proj = Resource("PROJ", "projector")
        comp = Resource("COMP", "computers")
        subjects = [
            Subject("S_COMP", "Lab", 3, 4, 1, 1, enrollment=15,
                    required_resources=(ResourceRequirement("COMP"),)),
            Subject("S_NORM1", "Mat", 3, 4, 1, 1, enrollment=20),
            Subject("S_NORM2", "Fis", 3, 4, 1, 1, enrollment=20),
        ]
        classrooms = [
            Classroom("LAB", "Laboratorio", 20, (comp,)),   # único válido para S_COMP
            Classroom("A1", "Aula 1", 30, (proj,)),
            Classroom("A2", "Aula 2", 30, (proj,)),
        ]
        timeslots = make_timeslots(6)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = get_domains(instance)
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        assert len(result) == 3
        assert check_hc1(result) == []

        # S_COMP debe estar en LAB (único salón con COMP)
        lab_assignment = next(a for a in result if a.subject_code == "S_COMP")
        assert lab_assignment.classroom_code == "LAB"


class TestCSPReturnEmptyOnInfeasible:
    def test_returns_empty_list_when_no_solution(self, config):
        """Si el dominio es vacío desde el inicio, el solver retorna []."""
        proj = Resource("PROJ", "projector")
        subjects = [Subject("S1", "Mat", 3, 4, 1, 1, enrollment=999)]
        classrooms = [Classroom("A1", "Aula", 30, (proj,))]
        timeslots = make_timeslots(3)
        instance = make_instance(subjects, classrooms, timeslots)

        # Dominio vacío: enrollment >> capacity
        domains = {"S1__g1__s1": []}
        result = CSPBacktrackingSolver(config).solve(instance, domains)

        assert result == []
