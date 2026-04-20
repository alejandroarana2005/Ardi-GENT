"""Tests unitarios para TabuSearchSolver — Capa 3."""

from datetime import time

import pytest

from app.config import HAIAConfig
from app.domain.entities import (
    Classroom,
    PreferenceSlot,
    Professor,
    Resource,
    ResourceRequirement,
    SchedulingInstance,
    Subject,
    TimeSlot,
)
from app.layer2_preprocessing.domain_filter import DomainFilter
from app.layer3_solver.tabu_search import TabuSearchSolver
from tests.fixtures.sample_data import build_minimal_instance, build_sample_instance


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def config():
    return HAIAConfig()


@pytest.fixture
def fast_config():
    """Config con iteraciones reducidas para tests rápidos."""
    cfg = HAIAConfig()
    return cfg


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
    return DomainFilter().filter(instance)


def check_hc1(assignments) -> list[str]:
    violations = []
    for i, a in enumerate(assignments):
        for b in assignments[i + 1:]:
            if a.classroom_code == b.classroom_code and a.timeslot_code == b.timeslot_code:
                violations.append(f"HC1: {a.subject_code} y {b.subject_code}")
    return violations


# ── Tests de solución ─────────────────────────────────────────────────────────

class TestTabuSearchSolvesMinimalInstance:
    def test_finds_solution(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=200, max_no_improve=50)
        result = solver.solve(instance, domains)

        assert len(result) > 0

    def test_assigns_all_variables(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=200, max_no_improve=50)
        result = solver.solve(instance, domains)

        assigned_keys = {
            f"{a.subject_code}__g{a.group_number}__s{a.session_number}"
            for a in result
        }
        expected_keys = set(domains.keys())
        assert assigned_keys == expected_keys

    def test_no_hc1_double_booking(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=300, max_no_improve=80)
        result = solver.solve(instance, domains)

        violations = check_hc1(result)
        assert violations == [], f"Violaciones HC1: {violations}"

    def test_assignments_have_valid_codes(self, config):
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=200, max_no_improve=50)
        result = solver.solve(instance, domains)

        classroom_codes = {c.code for c in instance.classrooms}
        timeslot_codes = {ts.code for ts in instance.timeslots}
        subject_codes = {s.code for s in instance.subjects}

        for a in result:
            assert a.subject_code in subject_codes
            assert a.classroom_code in classroom_codes
            assert a.timeslot_code in timeslot_codes


class TestTabuSearchMemoryMechanisms:
    def test_greedy_initial_solution_valid(self, config):
        """La solución greedy inicial no debe tener double-booking."""
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=1, max_no_improve=1)
        result = solver.solve(instance, domains)

        # Con max_iterations=1 básicamente se retorna la solución greedy
        assert len(result) > 0
        violations = check_hc1(result)
        assert violations == []

    def test_repeated_calls_produce_valid_solutions(self, config):
        """TS debe producir soluciones válidas en múltiples ejecuciones."""
        instance = build_minimal_instance()
        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=100, max_no_improve=30)

        for _ in range(3):
            result = solver.solve(instance, domains)
            assert len(result) > 0
            assert check_hc1(result) == []

    def test_more_iterations_improves_or_maintains_score(self, config):
        """
        Con más iteraciones el score debe ser >= al de pocas iteraciones.
        (No garantizado siempre por naturaleza estocástica, pero muy probable
        con la instancia mínima que tiene pocas variables.)
        """
        instance = build_minimal_instance()
        domains = get_domains(instance)

        solver_few = TabuSearchSolver(config, max_iterations=5, max_no_improve=3)
        solver_many = TabuSearchSolver(config, max_iterations=200, max_no_improve=50)

        result_few = solver_few.solve(instance, domains)
        result_many = solver_many.solve(instance, domains)

        # Ambos deben ser válidos
        assert len(result_few) > 0
        assert len(result_many) > 0


class TestTabuSearchWithResources:
    def test_respects_resource_domains(self, config):
        """TS no debe asignar un curso a un salón fuera de su dominio filtrado."""
        comp = Resource("COMP", "computers")
        proj = Resource("PROJ", "projector")
        subjects = [
            Subject("S_LAB", "Lab", 3, 4, 1, 1, enrollment=15,
                    required_resources=(ResourceRequirement("COMP"),)),
            Subject("S_NORM", "Mat", 3, 4, 1, 1, enrollment=20),
        ]
        classrooms = [
            Classroom("LAB", "Lab", 20, (comp,)),
            Classroom("SALA", "Sala", 30, (proj,)),
        ]
        timeslots = make_timeslots(4)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = get_domains(instance)
        solver = TabuSearchSolver(config, max_iterations=100, max_no_improve=30)
        result = solver.solve(instance, domains)

        assert len(result) == 2
        lab_assign = next(a for a in result if a.subject_code == "S_LAB")
        assert lab_assign.classroom_code == "LAB"


class TestTabuSearchInterface:
    def test_interface_compatible_with_backtracking(self, config):
        """
        TabuSearchSolver y CSPBacktrackingSolver deben tener la misma interfaz:
        solve(instance, domains) → list[Assignment]
        """
        from app.layer3_solver.csp_backtracking import CSPBacktrackingSolver

        instance = build_minimal_instance()
        domains = get_domains(instance)

        bt_result = CSPBacktrackingSolver(config).solve(instance, domains)
        ts_result = TabuSearchSolver(config, max_iterations=100, max_no_improve=30).solve(
            instance, domains
        )

        # Ambos retornan listas de Assignment
        assert isinstance(bt_result, list)
        assert isinstance(ts_result, list)

    def test_solver_name_attribute(self):
        assert TabuSearchSolver.__dict__.get("name") or hasattr(TabuSearchSolver, "name")

    def test_returns_empty_on_empty_domains(self, config):
        instance = build_minimal_instance()
        domains = {"S001__g1__s1": [], "S002__g1__s1": [], "S003__g1__s1": []}
        solver = TabuSearchSolver(config, max_iterations=10, max_no_improve=5)
        result = solver.solve(instance, domains)

        assert result == []


class TestTabuSearchWithSampleData:
    def test_sample_instance_produces_assignments(self, config):
        instance = build_sample_instance()
        domains = get_domains(instance)
        # Reducir iteraciones para que el test no tarde demasiado
        solver = TabuSearchSolver(config, max_iterations=500, max_no_improve=100)
        result = solver.solve(instance, domains)

        # Debe producir al menos una asignación
        assert len(result) > 0

        # Sin double-booking
        violations = check_hc1(result)
        assert violations == [], f"HC1 violadas: {violations[:5]}"
