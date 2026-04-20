"""Tests unitarios para AC3Preprocessor — Capa 2."""

from datetime import time

import pytest

from app.domain.entities import (
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
from tests.fixtures.sample_data import build_minimal_instance, build_sample_instance


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_instance(
    subjects: list[Subject],
    classrooms: list[Classroom],
    timeslots: list[TimeSlot],
    professors: list[Professor] | None = None,
) -> SchedulingInstance:
    return SchedulingInstance(
        semester="TEST",
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors or [],
    )


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


# ── Pruebas básicas ───────────────────────────────────────────────────────────

class TestAC3Basic:
    def test_returns_feasible_for_compatible_instance(self):
        proj = Resource("PROJ", "projector")
        subjects = [
            Subject("S1", "Mat", 3, 4, 1, 1, enrollment=20),
            Subject("S2", "Fis", 3, 4, 1, 1, enrollment=20),
        ]
        classrooms = [
            Classroom("A1", "Aula 1", 30, (proj,)),
            Classroom("A2", "Aula 2", 30, (proj,)),
        ]
        timeslots = make_timeslots(4)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = DomainFilter().filter(instance)
        reduced, feasible = AC3Preprocessor().run(instance, domains)

        assert feasible is True
        assert len(reduced) == 2

    def test_returns_same_number_of_variables(self):
        proj = Resource("PROJ", "projector")
        subjects = [Subject(f"S{i}", f"Mat{i}", 3, 4, 1, 1, enrollment=20) for i in range(5)]
        classrooms = [Classroom(f"A{i}", f"Aula{i}", 30, (proj,)) for i in range(5)]
        timeslots = make_timeslots(8)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = DomainFilter().filter(instance)
        reduced, feasible = AC3Preprocessor().run(instance, domains)

        assert set(reduced.keys()) == set(domains.keys())

    def test_preserves_copy_of_domains(self):
        """AC-3 no debe mutar el dict original de dominios."""
        proj = Resource("PROJ", "projector")
        subjects = [Subject("S1", "Mat", 3, 4, 1, 1, enrollment=20)]
        classrooms = [Classroom("A1", "Aula 1", 30, (proj,))]
        timeslots = make_timeslots(3)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = DomainFilter().filter(instance)
        original_size = len(domains["S1__g1__s1"])

        AC3Preprocessor().run(instance, domains)

        assert len(domains["S1__g1__s1"]) == original_size  # no mutado


# ── Detección de inviabilidad ─────────────────────────────────────────────────

class TestAC3Infeasibility:
    def test_empty_domain_after_filter_returns_infeasible(self):
        """Cuando DomainFilter ya dejó un dominio vacío, AC-3 debe detectarlo."""
        # Materia con enrollment mayor a todos los salones
        subjects = [Subject("S1", "Mat", 3, 4, 1, 1, enrollment=999)]
        classrooms = [Classroom("A1", "Aula", 10, ())]
        timeslots = make_timeslots(2)
        instance = make_instance(subjects, classrooms, timeslots)

        domains = DomainFilter().filter(instance)
        # El dominio ya está vacío tras el filtro
        assert domains["S1__g1__s1"] == []

        reduced, feasible = AC3Preprocessor().run(instance, domains)
        assert feasible is False


# ── Reducción de dominio por HC1 y HC2 ───────────────────────────────────────

class TestAC3Reduction:
    def test_hc1_same_classroom_same_slot_eliminated(self):
        """
        Si dos cursos solo tienen un salón disponible y una franja,
        AC-3 debe detectar que comparten el único valor y uno quedará sin soporte.
        """
        proj = Resource("PROJ", "projector")
        # Dos materias, un solo salón, una sola franja → solo una puede asignarse
        subjects = [
            Subject("S1", "Mat", 3, 4, 1, 1, enrollment=20),
            Subject("S2", "Fis", 3, 4, 1, 1, enrollment=20),
        ]
        classrooms = [Classroom("ONLY", "Único Salón", 30, (proj,))]
        timeslots = [TimeSlot("TS_ONLY", "Monday", time(7, 0), time(9, 0), 2.0)]
        instance = make_instance(subjects, classrooms, timeslots)

        domains = DomainFilter().filter(instance)
        # Ambas variables solo tienen el valor ("ONLY", "TS_ONLY")
        assert domains["S1__g1__s1"] == [("ONLY", "TS_ONLY")]
        assert domains["S2__g1__s1"] == [("ONLY", "TS_ONLY")]

        _, feasible = AC3Preprocessor().run(instance, domains)
        # AC-3 detecta que no pueden ser consistentes: infactible
        assert feasible is False

    def test_hc2_same_professor_same_slot_constrained(self):
        """
        Dos cursos del mismo docente con un solo timeslot deben ser infactibles.
        """
        proj = Resource("PROJ", "projector")
        prof = Professor("P1", "Docente", availability=("TS_MON",))
        subjects = [
            Subject("S1", "Mat", 3, 4, 1, 1, enrollment=20, professor_code="P1"),
            Subject("S2", "Fis", 3, 4, 1, 1, enrollment=20, professor_code="P1"),
        ]
        classrooms = [
            Classroom("A1", "Aula 1", 30, (proj,)),
            Classroom("A2", "Aula 2", 30, (proj,)),
        ]
        timeslots = [TimeSlot("TS_MON", "Monday", time(7, 0), time(9, 0), 2.0)]
        instance = make_instance(subjects, classrooms, timeslots, [prof])

        domains = DomainFilter().filter(instance)
        _, feasible = AC3Preprocessor().run(instance, domains)

        # Mismo profesor, mismo timeslot en todos los valores → infactible
        assert feasible is False

    def test_two_professors_two_slots_remains_feasible(self):
        proj = Resource("PROJ", "projector")
        p1 = Professor("P1", "Docente 1", availability=("TS_1", "TS_2"))
        p2 = Professor("P2", "Docente 2", availability=("TS_1", "TS_2"))
        subjects = [
            Subject("S1", "Mat", 3, 4, 1, 1, enrollment=20, professor_code="P1"),
            Subject("S2", "Fis", 3, 4, 1, 1, enrollment=20, professor_code="P2"),
        ]
        classrooms = [
            Classroom("A1", "Aula 1", 30, (proj,)),
            Classroom("A2", "Aula 2", 30, (proj,)),
        ]
        timeslots = [
            TimeSlot("TS_1", "Monday", time(7, 0), time(9, 0), 2.0),
            TimeSlot("TS_2", "Monday", time(9, 0), time(11, 0), 2.0),
        ]
        instance = make_instance(subjects, classrooms, timeslots, [p1, p2])

        domains = DomainFilter().filter(instance)
        _, feasible = AC3Preprocessor().run(instance, domains)

        assert feasible is True


# ── Integración con instancias reales ────────────────────────────────────────

class TestAC3Integration:
    def test_minimal_instance_feasible(self):
        instance = build_minimal_instance()
        domains = DomainFilter().filter(instance)
        _, feasible = AC3Preprocessor().run(instance, domains)

        assert feasible is True

    def test_sample_instance_feasible(self):
        instance = build_sample_instance()
        domains = DomainFilter().filter(instance)
        _, feasible = AC3Preprocessor().run(instance, domains)

        assert feasible is True

    def test_sample_instance_reduces_domains(self):
        instance = build_sample_instance()
        domains_before = DomainFilter().filter(instance)
        before_total = sum(len(v) for v in domains_before.values())

        reduced, _ = AC3Preprocessor().run(instance, domains_before)
        after_total = sum(len(v) for v in reduced.values())

        # AC-3 debe reducir al menos algo (o mantener — nunca aumentar)
        assert after_total <= before_total
