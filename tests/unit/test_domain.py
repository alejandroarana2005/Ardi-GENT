"""Tests unitarios para entidades de dominio y restricciones."""

import pytest
from datetime import time

from app.domain.entities import (
    Assignment,
    Classroom,
    PreferenceSlot,
    Professor,
    Resource,
    ResourceRequirement,
    Subject,
    TimeSlot,
)
from app.domain.constraints import (
    HC1_NoDoubleBookingClassroom,
    HC3_SufficientCapacity,
    HC4_RequiredResources,
)
from tests.fixtures.sample_data import build_minimal_instance


class TestEntities:
    def test_classroom_has_resource(self):
        proj = Resource("PROJ", "projector")
        c = Classroom("A1", "Aula 1", 30, (proj,))
        assert c.has_resource("PROJ")
        assert not c.has_resource("COMP")

    def test_classroom_satisfies_requirements(self):
        proj = Resource("PROJ", "projector")
        comp = Resource("COMP", "computers")
        c = Classroom("L1", "Lab 1", 30, (proj, comp))
        req_proj = ResourceRequirement("PROJ")
        req_comp = ResourceRequirement("COMP")
        req_lab = ResourceRequirement("LSOFT")
        assert c.satisfies_requirements((req_proj, req_comp))
        assert not c.satisfies_requirements((req_proj, req_lab))

    def test_professor_preference(self):
        p = Professor(
            "P1", "Test Prof",
            preferences=(PreferenceSlot("TS_MON_1", 0.9), PreferenceSlot("TS_MON_2", 0.3)),
        )
        assert p.preference_for("TS_MON_1") == 0.9
        assert p.preference_for("TS_MON_2") == 0.3
        assert p.preference_for("TS_WED_1") == 0.5  # default neutral

    def test_professor_availability(self):
        p = Professor("P1", "Test", availability=("TS_MON_1", "TS_MON_2"))
        assert p.is_available("TS_MON_1")
        assert not p.is_available("TS_FRI_4")

    def test_subject_total_assignments(self):
        s = Subject("S1", "Mat", 3, 4, 2, 3, 30)  # 3 grupos × 2 sesiones = 6
        assert s.total_assignments_needed() == 6

    def test_preference_slot_validation(self):
        with pytest.raises(ValueError):
            PreferenceSlot("TS_1", 1.5)


class TestHardConstraints:
    def test_hc1_no_conflict(self):
        instance = build_minimal_instance()
        a1 = Assignment("S001", "A1", "TS_MON_1", 1, 1)
        a2 = Assignment("S002", "A2", "TS_MON_1", 1, 1)  # distinto salón
        hc1 = HC1_NoDoubleBookingClassroom()
        assert hc1.check(a1, [a1, a2], instance)

    def test_hc1_conflict(self):
        instance = build_minimal_instance()
        a1 = Assignment("S001", "A1", "TS_MON_1", 1, 1)
        a2 = Assignment("S002", "A1", "TS_MON_1", 1, 1)  # mismo salón, misma franja
        hc1 = HC1_NoDoubleBookingClassroom()
        assert not hc1.check(a1, [a1, a2], instance)

    def test_hc3_sufficient_capacity(self):
        instance = build_minimal_instance()
        a_ok = Assignment("S001", "A1", "TS_MON_1", 1, 1)  # enroll=20, cap=30
        a_fail = Assignment("S003", "L1", "TS_MON_1", 1, 1)  # enroll=25, cap=20
        hc3 = HC3_SufficientCapacity()
        assert hc3.check(a_ok, [a_ok], instance)
        assert not hc3.check(a_fail, [a_fail], instance)

    def test_hc4_required_resources(self):
        instance = build_minimal_instance()
        # S001 requiere PROJ, A1 tiene PROJ → ok
        a_ok = Assignment("S001", "A1", "TS_MON_1", 1, 1)
        # S002 requiere COMP, A1 no tiene COMP → falla
        a_fail = Assignment("S002", "A1", "TS_MON_1", 1, 1)
        hc4 = HC4_RequiredResources()
        assert hc4.check(a_ok, [a_ok], instance)
        assert not hc4.check(a_fail, [a_fail], instance)


class TestSchedulingInstance:
    def test_instance_summary(self):
        instance = build_minimal_instance()
        summary = instance.summary()
        assert summary["subjects"] == 3
        assert summary["total_assignments_needed"] == 3  # 3 materias × 1 grupo × 1 sesión
        assert summary["classrooms"] == 3
        assert summary["timeslots"] == 6

    def test_sample_instance(self):
        from tests.fixtures.sample_data import build_sample_instance
        instance = build_sample_instance()
        assert len(instance.subjects) == 30
        assert len(instance.classrooms) == 15
        assert len(instance.timeslots) == 24
        assert len(instance.professors) == 20
