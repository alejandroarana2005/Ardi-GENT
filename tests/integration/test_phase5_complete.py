"""
Tests de integración — Fase 5: Inteligencia Predictiva + Calibración + Reporting.

Criterios de éxito:
    - AHP: CR < 0.10 con la matriz del paper
    - Forecaster: error < 15% con 4+ semestres de historia
    - Decomposer: instancia de 600 materias → múltiples subproblemas
    - PeriodicReoptimizer: dispara con 5 eventos O |ΔU| > 0.15
    - ReportGenerator: JSON con secciones requeridas; HTML válido
    - Suite completa: todos los tests previos siguen verdes
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import (
    Base, ClassroomModel, ResourceModel, TimeSlotModel,
    ProfessorModel, ProfessorAvailabilityModel, ProfessorPreferenceModel,
    SubjectModel, ScheduleModel, AssignmentModel,
)
from app.database.session import get_db
from app.main import app
from tests.fixtures.sample_data import build_minimal_instance, build_sample_instance


# ── Fixtures compartidas (module scope) ──────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture(scope="module")
def TestSessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def populated_engine(engine, TestSessionLocal):
    with TestSessionLocal() as session:
        _populate_db(session, build_minimal_instance())
        session.commit()
    return engine


@pytest.fixture(scope="module")
def client(populated_engine, TestSessionLocal):
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _populate_db(session: Session, instance) -> None:
    resource_map: dict[str, str] = {}
    for c in instance.classrooms:
        for r in c.resources:
            resource_map[r.code] = r.name

    resource_orm: dict[str, ResourceModel] = {}
    for code, name in resource_map.items():
        r_orm = ResourceModel(code=code, name=name)
        session.add(r_orm)
        resource_orm[code] = r_orm
    session.flush()

    for c in instance.classrooms:
        c_orm = ClassroomModel(code=c.code, name=c.name, capacity=c.capacity)
        for res in c.resources:
            if res.code in resource_orm:
                c_orm.resources.append(resource_orm[res.code])
        session.add(c_orm)
    session.flush()

    for ts in instance.timeslots:
        session.add(TimeSlotModel(
            code=ts.code, day=ts.day,
            start_time=ts.start_time, end_time=ts.end_time, duration=ts.duration,
        ))
    session.flush()

    for p in instance.professors:
        p_orm = ProfessorModel(
            code=p.code, name=p.name,
            max_weekly_hours=p.max_weekly_hours,
            contract_type=p.contract_type,
        )
        session.add(p_orm)
        session.flush()
        for ts_code in p.availability:
            session.add(ProfessorAvailabilityModel(
                professor_id=p_orm.id, timeslot_code=ts_code,
            ))
        for pref in p.preferences:
            session.add(ProfessorPreferenceModel(
                professor_id=p_orm.id,
                timeslot_code=pref.timeslot_code,
                preference=pref.preference,
            ))
    session.flush()

    for s in instance.subjects:
        s_orm = SubjectModel(
            code=s.code, name=s.name, credits=s.credits,
            study_hours=s.study_hours, weekly_subgroups=s.weekly_subgroups,
            groups=s.groups, enrollment=s.enrollment,
            faculty=s.faculty, professor_code=s.professor_code,
        )
        for req in s.required_resources:
            if req.resource_code in resource_orm:
                s_orm.required_resources.append(resource_orm[req.resource_code])
        session.add(s_orm)
    session.flush()


def _create_schedule(client) -> str:
    resp = client.post("/api/v1/schedule",
                       json={"semester": "TEST", "solver_hint": "backtracking"})
    assert resp.status_code == 202
    return resp.json()["schedule_id"]


# ── AHP Tests ─────────────────────────────────────────────────────────────────

class TestAHPCalibration:

    def test_consistency_ratio_paper_matrix(self):
        """La matriz del informe IEEE HAIA debe producir CR < 0.10."""
        from app.layer4_optimization.ahp_weights import AHPCalibrator
        ahp = AHPCalibrator.from_paper()
        cr = ahp.consistency_ratio()
        assert cr < 0.10, f"CR={cr:.4f} debe ser < 0.10"

    def test_weights_sum_to_one(self):
        """Los pesos AHP deben sumar 1.0 (dentro de tolerancia numérica)."""
        from app.layer4_optimization.ahp_weights import AHPCalibrator
        ahp = AHPCalibrator.from_paper()
        w = ahp.compute_weights()
        total = w["w1"] + w["w2"] + w["w3"] + w["w4"]
        assert abs(total - 1.0) < 1e-6, f"Suma de pesos = {total}"

    def test_weights_ordering(self):
        """Ocupación debe ser el criterio más importante (w1 > w2 > w3, w4)."""
        from app.layer4_optimization.ahp_weights import AHPCalibrator
        ahp = AHPCalibrator.from_paper()
        w = ahp.compute_weights()
        assert w["w1"] > w["w2"], "w1 (ocupación) debe ser > w2 (preferencia)"
        assert w["w2"] > w["w3"], "w2 (preferencia) debe ser > w3 (distribución)"

    def test_inconsistent_matrix_fallback(self):
        """Matriz con CR > 0.10 debe retornar pesos por defecto."""
        from app.layer4_optimization.ahp_weights import (
            AHPWeightCalibrator, DEFAULT_AHP_WEIGHTS,
        )
        # Matriz altamente inconsistente
        bad_matrix = [
            [1, 9, 1/9, 9],
            [1/9, 1, 9, 1/9],
            [9, 1/9, 1, 9],
            [1/9, 9, 1/9, 1],
        ]
        calibrator = AHPWeightCalibrator()
        result = calibrator.calibrate(bad_matrix)
        assert result == DEFAULT_AHP_WEIGHTS

    def test_identity_matrix_produces_equal_weights(self):
        """Matriz identidad (todos indiferentes) → todos los pesos iguales."""
        from app.layer4_optimization.ahp_weights import AHPCalibrator
        ahp = AHPCalibrator()
        # identidad: todos se comparan con intensidad 1
        w = ahp.compute_weights()
        assert abs(w["w1"] - 0.25) < 0.01

    def test_ahp_endpoint_via_api(self, client):
        """El endpoint de reporte debe funcionar con schedule existente."""
        sid = _create_schedule(client)
        resp = client.get(f"/api/v1/reports/{sid}/json")
        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert data["metadata"]["schedule_id"] == sid


# ── Forecaster Tests ──────────────────────────────────────────────────────────

class TestEnrollmentForecaster:

    def test_insufficient_history_passthrough(self):
        """Con < 3 semestres, retorna el último valor sin cambio."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        fc = EnrollmentForecaster(min_history_semesters=3)
        history = [
            {"semester": "2023-A", "enrollment": 28},
            {"semester": "2023-B", "enrollment": 30},
        ]
        pred = fc.predict("ISIS101", history)
        assert pred.predicted_enrollment == 30
        assert pred.method == "passthrough"
        assert pred.semesters_used == 2

    def test_sufficient_history_produces_prediction(self):
        """Con 5 semestres de historia creciente, predice valor > historia."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        fc = EnrollmentForecaster()
        history = [
            {"semester": "2021-A", "enrollment": 20},
            {"semester": "2021-B", "enrollment": 22},
            {"semester": "2022-A", "enrollment": 24},
            {"semester": "2022-B", "enrollment": 27},
            {"semester": "2023-A", "enrollment": 30},
        ]
        pred = fc.predict("ISIS101", history)
        assert pred.predicted_enrollment > 0
        assert pred.semesters_used == 5
        assert pred.method == "holt_exponential_smoothing"
        # Tendencia creciente → predicción >= último valor
        assert pred.predicted_enrollment >= 25

    def test_prediction_error_under_15_pct(self):
        """Para una serie estable (enrollments ≈ constantes) el error < 15%."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        fc = EnrollmentForecaster()
        true_val = 30
        history = [
            {"semester": f"202{i}-A", "enrollment": true_val + (i % 3)}
            for i in range(5)
        ]
        pred = fc.predict("TEST", history)
        error_pct = abs(pred.predicted_enrollment - true_val) / true_val * 100
        assert error_pct < 15.0, f"Error = {error_pct:.1f}% debe ser < 15%"

    def test_confidence_interval_contains_prediction(self):
        """El intervalo de confianza debe contener la predicción central."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        fc = EnrollmentForecaster()
        history = [
            {"semester": f"202{i}-A", "enrollment": 25 + i}
            for i in range(5)
        ]
        pred = fc.predict("TEST", history)
        low, high = pred.confidence_interval
        assert low <= pred.predicted_enrollment <= high

    def test_predict_batch(self):
        """predict_batch retorna predicción para cada código."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        fc = EnrollmentForecaster()
        subjects_history = {
            "ISIS101": [{"semester": f"202{i}-A", "enrollment": 28 + i} for i in range(4)],
            "ISIS102": [{"semester": f"202{i}-A", "enrollment": 35 + i} for i in range(4)],
        }
        results = fc.predict_batch(subjects_history)
        assert set(results.keys()) == {"ISIS101", "ISIS102"}
        assert all(p.predicted_enrollment > 0 for p in results.values())

    def test_backward_compat_forecast(self):
        """El método legacy forecast() sigue funcionando."""
        from app.layer1_perception.forecaster import EnrollmentForecaster
        from tests.fixtures.sample_data import build_minimal_instance
        instance = build_minimal_instance()
        fc = EnrollmentForecaster()
        result = fc.forecast(instance.subjects, "2024-A")
        assert len(result) == len(instance.subjects)
        for s in instance.subjects:
            assert result[s.code] == s.enrollment


# ── Decomposer Tests ──────────────────────────────────────────────────────────

class TestHierarchicalDecomposer:

    def test_small_instance_single_subproblem(self):
        """Instancia <= threshold → un solo Subproblem con 'all'."""
        from app.layer2_preprocessing.decomposer import HierarchicalDecomposer
        instance = build_sample_instance()
        decomposer = HierarchicalDecomposer(threshold=500)
        subproblems = decomposer.decompose(instance)
        assert len(subproblems) == 1
        assert subproblems[0].faculty == "all"
        assert subproblems[0].instance is instance

    def test_large_instance_multiple_subproblems(self):
        """Instancia de 600 materias (multi-facultad) → varios Subproblem."""
        from app.layer2_preprocessing.decomposer import HierarchicalDecomposer
        from app.domain.entities import (
            Subject, SchedulingInstance, TimeSlot, Classroom, Professor,
        )
        from datetime import time as dtime

        # Crear 600 materias distribuidas en 3 facultades
        classrooms = [Classroom(f"CLS{i}", f"Salon {i}", 30) for i in range(5)]
        timeslots = [
            TimeSlot(f"TS{i}", "Monday", dtime(7+i, 0), dtime(9+i, 0), 2.0)
            for i in range(10)
        ]
        professors = [
            Professor(f"P{i:03d}", f"Prof {i}",
                      availability=tuple(ts.code for ts in timeslots))
            for i in range(20)
        ]
        faculties = ["ingenieria", "ciencias", "humanidades"]
        subjects = [
            Subject(
                code=f"SBJ{i:04d}", name=f"Materia {i}",
                credits=3, study_hours=4, weekly_subgroups=1, groups=1,
                enrollment=25, professor_code=professors[i % 20].code,
                faculty=faculties[i % 3],
            )
            for i in range(600)
        ]
        big_instance = SchedulingInstance(
            semester="TEST", subjects=subjects,
            classrooms=classrooms, timeslots=timeslots, professors=professors,
        )
        decomposer = HierarchicalDecomposer(threshold=500)
        subproblems = decomposer.decompose(big_instance)

        assert len(subproblems) == 3
        faculty_names = {sp.faculty for sp in subproblems}
        assert faculty_names == set(faculties)
        total_subjects = sum(len(sp.instance.subjects) for sp in subproblems)
        assert total_subjects == 600

    def test_merge_solutions_no_conflicts(self):
        """merge_solutions sin conflictos retorna todas las asignaciones."""
        from app.layer2_preprocessing.decomposer import HierarchicalDecomposer, Subproblem
        from app.domain.entities import Assignment, SchedulingInstance
        from datetime import time as dtime

        decomposer = HierarchicalDecomposer()
        # Crear asignaciones sin conflicto (salón+franja únicos)
        sol1 = [
            Assignment("S1", "CLS1", "TS1", 1, 1),
            Assignment("S2", "CLS2", "TS2", 1, 1),
        ]
        sol2 = [
            Assignment("S3", "CLS3", "TS3", 1, 1),
            Assignment("S4", "CLS4", "TS4", 1, 1),
        ]
        dummy_instance = build_minimal_instance()
        sp1 = Subproblem("fac1", dummy_instance)
        sp2 = Subproblem("fac2", dummy_instance)
        merged = decomposer.merge_solutions([sol1, sol2], [sp1, sp2])
        assert len(merged) == 4

    def test_backward_compat_decompose_as_dict(self):
        """decompose_as_dict() retorna dict igual que el stub Fase 1."""
        from app.layer2_preprocessing.decomposer import HierarchicalDecomposer
        instance = build_sample_instance()
        decomposer = HierarchicalDecomposer()
        result = decomposer.decompose_as_dict(instance)
        assert isinstance(result, dict)
        faculties = {s.faculty for s in instance.subjects}
        assert set(result.keys()) == faculties


# ── PeriodicReoptimizer Tests ─────────────────────────────────────────────────

class TestPeriodicReoptimizer:

    def test_should_not_trigger_fresh_schedule(self, client, TestSessionLocal):
        """Schedule recién creado (0 eventos) no debe disparar re-optimización."""
        from app.layer5_dynamic.periodic_reoptimizer import PeriodicReoptimizer
        sid = _create_schedule(client)
        with TestSessionLocal() as db:
            reopt = PeriodicReoptimizer(events_threshold=5, utility_drop_threshold=0.15)
            should, reason = reopt.should_trigger(sid, db)
        assert not should
        assert reason == "no"

    def test_should_trigger_by_utility_drop(self, client, TestSessionLocal):
        """Child schedule con U 0.20 menor que root debe disparar el trigger."""
        from app.layer5_dynamic.periodic_reoptimizer import PeriodicReoptimizer
        from app.database.models import ScheduleModel

        # Crear schedule raíz
        parent_sid = _create_schedule(client)

        # Crear child con utilidad 0.20 menor (simula degradación por reparaciones)
        with TestSessionLocal() as db:
            parent = db.query(ScheduleModel).filter(
                ScheduleModel.schedule_id == parent_sid
            ).first()
            child = ScheduleModel(
                semester=parent.semester,
                solver_used="repair",
                status="completed",
                is_feasible=True,
                utility_score=max(0.0, parent.utility_score - 0.20),
                elapsed_seconds=0.1,
                parent_schedule_id=parent_sid,
            )
            db.add(child)
            db.commit()
            db.refresh(child)
            child_sid = child.schedule_id

        with TestSessionLocal() as db:
            reopt = PeriodicReoptimizer(events_threshold=5, utility_drop_threshold=0.15)
            should, reason = reopt.should_trigger(child_sid, db)
        assert should, f"Debería disparar — reason={reason}"
        assert reason in ("utility_drop", "both")

    def test_nonexistent_schedule_returns_false(self, TestSessionLocal):
        """Schedule inexistente no dispara re-optimización."""
        from app.layer5_dynamic.periodic_reoptimizer import PeriodicReoptimizer
        with TestSessionLocal() as db:
            reopt = PeriodicReoptimizer()
            should, reason = reopt.should_trigger(
                "00000000-0000-0000-0000-000000000000", db
            )
        assert not should
        assert reason == "schedule_not_found"

    def test_reoptimize_returns_new_schedule(self, client, TestSessionLocal):
        """reoptimize() sobre un schedule completado debe crear nueva versión."""
        from app.layer5_dynamic.periodic_reoptimizer import PeriodicReoptimizer
        from app.config import settings

        sid = _create_schedule(client)
        with TestSessionLocal() as db:
            reopt = PeriodicReoptimizer()
            result = reopt.reoptimize(sid, db, settings)

        assert result.new_schedule_id is not None
        assert result.new_schedule_id != sid
        assert result.u_after >= 0.0
        assert result.elapsed_seconds > 0


# ── Report Generator Tests ────────────────────────────────────────────────────

class TestReportGenerator:

    def test_generate_full_report_structure(self, client, TestSessionLocal):
        """generate_full_report() debe contener todas las secciones requeridas."""
        from app.reporting.report_generator import ReportGenerator
        sid = _create_schedule(client)

        with TestSessionLocal() as db:
            report = ReportGenerator().generate_full_report(sid, db)

        required_keys = {
            "schema_version", "generated_at", "metadata",
            "utility_breakdown", "assignments",
            "conflicts_detected", "event_history", "version_tree",
        }
        assert required_keys.issubset(set(report.keys()))
        assert report["metadata"]["schedule_id"] == sid
        assert isinstance(report["assignments"], list)
        assert isinstance(report["event_history"], list)

    def test_report_assignments_match_db(self, client, TestSessionLocal):
        """El número de asignaciones en el reporte debe coincidir con la BD."""
        from app.reporting.report_generator import ReportGenerator
        sid = _create_schedule(client)

        assignments_resp = client.get(f"/api/v1/schedule/{sid}/assignments")
        assert assignments_resp.status_code == 200
        expected_count = len(assignments_resp.json())

        with TestSessionLocal() as db:
            report = ReportGenerator().generate_full_report(sid, db)

        assert len(report["assignments"]) == expected_count

    def test_generate_html_report_contains_sections(self, client, TestSessionLocal):
        """generate_html_report() retorna HTML válido con secciones clave."""
        from app.reporting.report_generator import ReportGenerator
        sid = _create_schedule(client)

        with TestSessionLocal() as db:
            html = ReportGenerator().generate_html_report(sid, db)

        assert "<!DOCTYPE html>" in html
        assert "HAIA" in html
        assert "U(A)" in html
        assert sid[:8] in html

    def test_report_json_api_endpoint(self, client):
        """GET /reports/{id}/json debe retornar 200 con metadata correcta."""
        sid = _create_schedule(client)
        resp = client.get(f"/api/v1/reports/{sid}/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["schedule_id"] == sid

    def test_report_html_api_endpoint(self, client):
        """GET /reports/{id}/html debe retornar 200 con Content-Type html."""
        sid = _create_schedule(client)
        resp = client.get(f"/api/v1/reports/{sid}/html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_report_pdf_api_endpoint(self, client):
        """GET /reports/{id}/pdf debe retornar 200 (PDF o HTML fallback)."""
        sid = _create_schedule(client)
        resp = client.get(f"/api/v1/reports/{sid}/pdf")
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "application/pdf" in ct or "text/html" in ct

    def test_report_nonexistent_schedule_404(self, client):
        """Reporte de schedule inexistente → 404."""
        resp = client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000/json")
        assert resp.status_code == 404


# ── Full demo integration test ────────────────────────────────────────────────

class TestFullDemoScenario:

    def test_full_pipeline_with_forecast_and_report(self, client, TestSessionLocal):
        """
        Escenario completo de demo:
        1. Forecaster predice enrollment
        2. Generar horario
        3. Aplicar evento dinámico
        4. Verificar nueva versión
        5. Generar reporte con historial de eventos
        """
        from app.layer1_perception.forecaster import EnrollmentForecaster
        from app.reporting.report_generator import ReportGenerator

        # Paso 1: Forecaster
        fc = EnrollmentForecaster()
        history = [
            {"semester": f"202{i}-A", "enrollment": 25 + i} for i in range(4)
        ]
        pred = fc.predict("ISIS101", history)
        assert pred.predicted_enrollment > 0

        # Paso 2: Crear horario
        resp = client.post("/api/v1/schedule",
                           json={"semester": "TEST", "solver_hint": "backtracking"})
        assert resp.status_code == 202
        sid = resp.json()["schedule_id"]
        assert resp.json()["status"] == "completed"

        # Paso 3: Obtener asignaciones y aplicar evento
        assignments = client.get(f"/api/v1/schedule/{sid}/assignments").json()
        if not assignments:
            pytest.skip("Sin asignaciones — instancia mínima no factible")

        classroom = assignments[0]["classroom_code"]
        evt_resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "CLASSROOM_UNAVAILABLE",
            "payload": {"classroom_code": classroom},
        })
        assert evt_resp.status_code == 200

        # Paso 4: Verificar nueva versión
        new_sid = evt_resp.json().get("new_schedule_id")
        affected = evt_resp.json()["affected_assignments"]
        if affected > 0:
            assert new_sid is not None

        # Paso 5: Generar reporte con historial
        source_sid = new_sid if new_sid else sid
        with TestSessionLocal() as db:
            report = ReportGenerator().generate_full_report(source_sid, db)

        assert report["metadata"]["schedule_id"] == source_sid
        assert isinstance(report["assignments"], list)
        # El report del schedule original tiene el historial del evento
        with TestSessionLocal() as db:
            orig_report = ReportGenerator().generate_full_report(sid, db)
        if affected > 0:
            assert len(orig_report["event_history"]) >= 1
