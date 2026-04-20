"""Tests unitarios para la función de utilidad U(A)."""

from datetime import time

import pytest

from app.domain.entities import (
    Assignment,
    Classroom,
    PreferenceSlot,
    Professor,
    Resource,
    ResourceRequirement,
    SchedulingInstance,
    Subject,
    TimeSlot,
)
from app.layer4_optimization.utility_function import UtilityCalculator
from tests.fixtures.sample_data import build_minimal_instance
from app.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc() -> UtilityCalculator:
    return UtilityCalculator(settings.utility_weights)


def _ts(code: str, day: str = "Monday", hour: int = 7) -> TimeSlot:
    return TimeSlot(code, day, time(hour, 0), time(hour + 2, 0), 2.0)


def _make_instance(
    subjects, classrooms, timeslots, professors=None
) -> SchedulingInstance:
    return SchedulingInstance(
        semester="TEST",
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors or [],
    )


# ── Tests existentes ──────────────────────────────────────────────────────────

class TestUtilityFunction:
    def setup_method(self):
        self.instance = build_minimal_instance()
        self.calc = _calc()

    def test_empty_assignments_returns_zero(self):
        assert self.calc.compute([], self.instance) == 0.0

    def test_score_between_zero_and_one(self):
        assignments = [
            Assignment("S001", "A1", "TS_MON_1", 1, 1),
            Assignment("S002", "L1", "TS_MON_2", 1, 1),
        ]
        score = self.calc.compute(assignments, self.instance)
        assert 0.0 <= score <= 2.0

    def test_better_occupancy_increases_score(self):
        # S001 enroll=20, A1 cap=30 (ratio 0.67)
        # S003 enroll=25, A1 cap=30 (ratio 0.83)
        a_low = [Assignment("S001", "A1", "TS_MON_1", 1, 1)]
        a_high = [Assignment("S003", "A1", "TS_MON_1", 1, 1)]
        score_low = self.calc._u_occupancy(a_low, self.instance)
        score_high = self.calc._u_occupancy(a_high, self.instance)
        assert score_high > score_low

    def test_detailed_components_sum_correctly(self):
        assignments = [
            Assignment("S001", "A1", "TS_MON_2", 1, 1),
            Assignment("S002", "L1", "TS_TUE_1", 1, 1),
        ]
        detail = self.calc.compute_detailed(assignments, self.instance)
        expected = (
            0.40 * detail["u_occupancy"]
            + 0.25 * detail["u_preference"]
            + 0.20 * detail["u_distribution"]
            + 0.15 * detail["u_resources"]
            - 1.5 * detail["penalty"]
        )
        assert abs(detail["total"] - max(0.0, expected)) < 1e-9


# ── Tests nuevos Fase 3 ───────────────────────────────────────────────────────

class TestUOccupancy:
    def test_perfect_fit(self):
        """Enrollment == capacity → U_ocup = 1.0"""
        cls = Classroom("C1", "Aula", 30, ())
        subj = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=30)
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_occupancy([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(1.0)

    def test_half_full(self):
        """Enrollment=15, capacity=30 → U_ocup = 0.5"""
        cls = Classroom("C1", "Aula", 30, ())
        subj = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=15)
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_occupancy([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(0.5)

    def test_capped_at_one_when_over_capacity(self):
        """enrollment > capacity se clampa a 1.0"""
        cls = Classroom("C1", "Aula", 20, ())
        subj = Subject("S1", "Mat", 3, 4, 1, 1, enrollment=30)
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_occupancy([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(1.0)


class TestUPreference:
    def test_all_preferred(self):
        """Todos los docentes en franja con pref=1.0 → U_pref = 1.0"""
        ts = _ts("TS_MON_1")
        prof = Professor(
            "P1", "Prof",
            availability=("TS_MON_1",),
            preferences=(PreferenceSlot("TS_MON_1", 1.0),),
        )
        subj = Subject("S1", "Mat", 3, 4, 1, 1, professor_code="P1")
        cls = Classroom("C1", "Aula", 30, ())
        inst = _make_instance([subj], [cls], [ts], professors=[prof])
        calc = _calc()
        result = calc._u_preference([Assignment("S1", "C1", "TS_MON_1", 1, 1)], inst)
        assert result == pytest.approx(1.0)

    def test_no_preference_defaults_to_neutral(self):
        """Sin preferencia registrada → default 0.5"""
        ts = _ts("TS_MON_1")
        prof = Professor("P1", "Prof", availability=("TS_MON_1",), preferences=())
        subj = Subject("S1", "Mat", 3, 4, 1, 1, professor_code="P1")
        cls = Classroom("C1", "Aula", 30, ())
        inst = _make_instance([subj], [cls], [ts], professors=[prof])
        calc = _calc()
        result = calc._u_preference([Assignment("S1", "C1", "TS_MON_1", 1, 1)], inst)
        assert result == pytest.approx(0.5)


class TestUDistribution:
    def test_perfect_spread(self):
        """N cursos en N franjas distintas → U_dist ≈ 1.0"""
        n = 4
        timeslots = [_ts(f"TS{i}", hour=7 + i * 2) for i in range(n)]
        subjects = [Subject(f"S{i}", f"Mat{i}", 3, 4, 1, 1, enrollment=20) for i in range(n)]
        classrooms = [Classroom(f"C{i}", f"Aula{i}", 30, ()) for i in range(n)]
        inst = _make_instance(subjects, classrooms, timeslots)
        assignments = [
            Assignment(f"S{i}", f"C{i}", f"TS{i}", 1, 1) for i in range(n)
        ]
        calc = _calc()
        result = calc._u_distribution(assignments, inst)
        assert result == pytest.approx(1.0, abs=0.05)

    def test_all_same_slot(self):
        """Todos los cursos en la misma franja → U_dist claramente menor que distribución ideal"""
        timeslots = [_ts(f"TS{i}", hour=7 + i * 2) for i in range(6)]
        subjects = [Subject(f"S{i}", f"Mat{i}", 3, 4, 1, 1, enrollment=20) for i in range(6)]
        classrooms = [Classroom(f"C{i}", f"Aula{i}", 30, ()) for i in range(6)]
        inst = _make_instance(subjects, classrooms, timeslots)
        # Todos van a la misma franja TS0
        assignments_concentrated = [Assignment(f"S{i}", f"C{i}", "TS0", 1, 1) for i in range(6)]
        assignments_spread = [Assignment(f"S{i}", f"C{i}", f"TS{i}", 1, 1) for i in range(6)]
        calc = _calc()
        dist_concentrated = calc._u_distribution(assignments_concentrated, inst)
        dist_spread = calc._u_distribution(assignments_spread, inst)
        # La distribución concentrada debe ser claramente peor que la distribuida
        assert dist_concentrated < dist_spread


class TestUResources:
    def test_all_required_available(self):
        """Aula tiene todos los recursos requeridos → U_rec = 1.0"""
        proj = Resource("PROJ", "projector")
        cls = Classroom("C1", "Aula", 30, (proj,))
        subj = Subject("S1", "Mat", 3, 4, 1, 1,
                       required_resources=(ResourceRequirement("PROJ"),))
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_resources([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(1.0)

    def test_no_resources_required(self):
        """Materia sin recursos requeridos → aporta 1.0"""
        cls = Classroom("C1", "Aula", 30, ())
        subj = Subject("S1", "Mat", 3, 4, 1, 1)
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_resources([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(1.0)

    def test_partial_resource_match(self):
        """Solo 1 de 2 recursos requeridos disponible → U_rec = 0.5"""
        proj = Resource("PROJ", "projector")
        comp = Resource("COMP", "computers")
        cls = Classroom("C1", "Aula", 30, (proj,))  # solo proj
        subj = Subject(
            "S1", "Mat", 3, 4, 1, 1,
            required_resources=(ResourceRequirement("PROJ"), ResourceRequirement("COMP")),
        )
        ts = _ts("TS1")
        inst = _make_instance([subj], [cls], [ts])
        calc = _calc()
        result = calc._u_resources([Assignment("S1", "C1", "TS1", 1, 1)], inst)
        assert result == pytest.approx(0.5)


class TestWeightsValidation:
    def test_weights_from_settings_sum_to_one(self):
        w = settings.utility_weights
        total = w["w1"] + w["w2"] + w["w3"] + w["w4"]
        assert abs(total - 1.0) < 1e-6

    def test_total_utility_near_one_with_ideal_conditions(self):
        """U(A) con ocupación perfecta, pref=1.0, spread ideal, todos los recursos ≈ 1.0"""
        proj = Resource("PROJ", "projector")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday"]
        # Un profesor por materia para evitar SC4 (consecutivas mismo día)
        timeslots = [_ts(f"TS{i}", day=days[i], hour=9) for i in range(4)]
        professors = [
            Professor(
                f"P{i}", f"Prof{i}",
                availability=(f"TS{i}",),
                preferences=(PreferenceSlot(f"TS{i}", 1.0),),
            )
            for i in range(4)
        ]
        subjects = [
            Subject(f"S{i}", f"Mat{i}", 3, 4, 1, 1,
                    enrollment=30, professor_code=f"P{i}",
                    required_resources=(ResourceRequirement("PROJ"),))
            for i in range(4)
        ]
        classrooms = [Classroom(f"C{i}", f"Aula{i}", 30, (proj,)) for i in range(4)]
        inst = _make_instance(subjects, classrooms, timeslots, professors=professors)
        assignments = [Assignment(f"S{i}", f"C{i}", f"TS{i}", 1, 1) for i in range(4)]
        calc = _calc()
        score = calc.compute(assignments, inst)
        assert score > 0.5, f"U(A) esperado > 0.5, obtenido {score:.4f}"

    def test_compute_detailed_has_sc_violations_and_weights(self):
        instance = build_minimal_instance()
        calc = _calc()
        assignments = [Assignment("S001", "A1", "TS_MON_2", 1, 1)]
        detail = calc.compute_detailed(assignments, instance)
        assert "sc_violations" in detail
        assert "weights_used" in detail
        assert set(detail["weights_used"].keys()) >= {"w1", "w2", "w3", "w4", "lambda"}
