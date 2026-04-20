"""Tests unitarios para DomainFilter — Capa 2."""

from datetime import time

import pytest

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


# ── Fixtures básicas ──────────────────────────────────────────────────────────

@pytest.fixture
def proj():
    return Resource("PROJ", "projector")


@pytest.fixture
def comp():
    return Resource("COMP", "computers")


@pytest.fixture
def timeslots_3():
    return [
        TimeSlot("TS_MON_1", "Monday", time(7, 0), time(9, 0), 2.0),
        TimeSlot("TS_MON_2", "Monday", time(9, 0), time(11, 0), 2.0),
        TimeSlot("TS_TUE_1", "Tuesday", time(7, 0), time(9, 0), 2.0),
    ]


# ── HC3: Filtro por capacidad ─────────────────────────────────────────────────

class TestCapacityFilter:
    def test_excludes_classroom_with_insufficient_capacity(self, proj, timeslots_3):
        subject = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=35)
        small = Classroom("SMALL", "Small", 20, (proj,))
        big = Classroom("BIG", "Big", 40, (proj,))

        instance = make_instance([subject], [small, big], timeslots_3)
        domains = DomainFilter().filter(instance)

        key = "S1__g1__s1"
        classroom_codes = {cls for cls, _ in domains[key]}
        assert "SMALL" not in classroom_codes
        assert "BIG" in classroom_codes

    def test_includes_classroom_with_exact_capacity(self, proj, timeslots_3):
        subject = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=30)
        exact = Classroom("EXACT", "Exact", 30, (proj,))

        instance = make_instance([subject], [exact], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert len(domains["S1__g1__s1"]) == 3  # 1 salón × 3 franjas

    def test_all_classrooms_excluded_gives_empty_domain(self, proj, timeslots_3):
        subject = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=100)
        small = Classroom("SMALL", "Small", 20, (proj,))

        instance = make_instance([subject], [small], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert domains["S1__g1__s1"] == []


# ── HC4: Filtro por recursos ──────────────────────────────────────────────────

class TestResourceFilter:
    def test_excludes_classroom_without_required_resource(self, proj, comp, timeslots_3):
        subject = Subject(
            "S2", "Lab", 3, 4, 1, 1, enrollment=20,
            required_resources=(ResourceRequirement("COMP"),),
        )
        no_comp = Classroom("A1", "Aula 1", 30, (proj,))
        with_comp = Classroom("L1", "Lab 1", 30, (comp,))

        instance = make_instance([subject], [no_comp, with_comp], timeslots_3)
        domains = DomainFilter().filter(instance)

        key = "S2__g1__s1"
        classroom_codes = {cls for cls, _ in domains[key]}
        assert "A1" not in classroom_codes
        assert "L1" in classroom_codes

    def test_no_required_resources_allows_all(self, proj, timeslots_3):
        subject = Subject("S3", "Calc", 3, 4, 1, 1, enrollment=10)
        c1 = Classroom("A1", "Aula 1", 30, (proj,))
        c2 = Classroom("A2", "Aula 2", 40, ())

        instance = make_instance([subject], [c1, c2], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert len(domains["S3__g1__s1"]) == 2 * 3  # 2 salones × 3 franjas


# ── HC5: Filtro por disponibilidad del docente ────────────────────────────────

class TestProfessorAvailabilityFilter:
    def test_excludes_timeslots_outside_professor_availability(self, proj, timeslots_3):
        prof = Professor(
            "P1", "Docente 1",
            availability=("TS_MON_1", "TS_MON_2"),  # solo lunes
        )
        subject = Subject("S4", "Redes", 3, 4, 1, 1, enrollment=20, professor_code="P1")
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3, [prof])
        domains = DomainFilter().filter(instance)

        key = "S4__g1__s1"
        timeslot_codes = {ts for _, ts in domains[key]}
        assert "TS_MON_1" in timeslot_codes
        assert "TS_MON_2" in timeslot_codes
        assert "TS_TUE_1" not in timeslot_codes  # profesor no disponible

    def test_no_professor_allows_all_timeslots(self, proj, timeslots_3):
        subject = Subject("S5", "Prog", 3, 4, 1, 1, enrollment=20)  # sin profesor
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert len(domains["S5__g1__s1"]) == 3  # todos los timeslots

    def test_professor_with_empty_availability_allows_all(self, proj, timeslots_3):
        prof = Professor("P2", "Docente 2", availability=())  # sin restricciones
        subject = Subject("S6", "BD", 3, 4, 1, 1, enrollment=20, professor_code="P2")
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3, [prof])
        domains = DomainFilter().filter(instance)

        assert len(domains["S6__g1__s1"]) == 3

    def test_professor_not_found_in_map_allows_all(self, proj, timeslots_3):
        """Si el professor_code no existe en la lista, no se filtra."""
        subject = Subject("S7", "OS", 3, 4, 1, 1, enrollment=20, professor_code="UNKNOWN")
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert len(domains["S7__g1__s1"]) == 3


# ── Grupos y sesiones múltiples ───────────────────────────────────────────────

class TestMultipleGroupsAndSessions:
    def test_generates_key_per_group_and_session(self, proj, timeslots_3):
        subject = Subject("S8", "Calc", 3, 4, weekly_subgroups=2, groups=3, enrollment=20)
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3)
        domains = DomainFilter().filter(instance)

        # 3 grupos × 2 sesiones = 6 variables
        expected_keys = {
            f"S8__g{g}__s{s}" for g in range(1, 4) for s in range(1, 3)
        }
        assert expected_keys == set(domains.keys())

    def test_all_groups_have_identical_domain(self, proj, timeslots_3):
        subject = Subject("S9", "Disc", 3, 4, 1, 2, enrollment=20)
        classroom = Classroom("A1", "Aula", 30, (proj,))

        instance = make_instance([subject], [classroom], timeslots_3)
        domains = DomainFilter().filter(instance)

        assert domains["S9__g1__s1"] == domains["S9__g2__s1"]


# ── Integración con instancia de muestra ─────────────────────────────────────

class TestIntegrationWithSampleData:
    def test_sample_instance_produces_non_empty_domains(self):
        instance = build_sample_instance()
        domains = DomainFilter().filter(instance)

        assert len(domains) > 0
        empty = [k for k, v in domains.items() if len(v) == 0]
        # Con los fixtures de U. Ibagué no debería haber dominios vacíos
        assert len(empty) == 0, f"Dominios vacíos: {empty}"

    def test_minimal_instance_domains_correct(self):
        instance = build_minimal_instance()
        domains = DomainFilter().filter(instance)

        # La instancia mínima tiene 3 materias × 1 grupo × 1 sesión = 3 variables
        assert len(domains) == 3
