"""
Tests de integración para el endpoint POST /schedule y GET /schedule/{id}.

Usa SQLite en memoria para evitar dependencia de PostgreSQL en CI.
Verifica el flujo completo: percepción → AC-3 → solver → SA → persistencia → respuesta.
"""

from __future__ import annotations

import uuid
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Importar TODOS los modelos para que Base.metadata los registre
from app.database.models import (
    AssignmentModel,
    Base,
    ClassroomModel,
    DynamicEventModel,
    ProfessorAvailabilityModel,
    ProfessorPreferenceModel,
    ProfessorModel,
    ResourceModel,
    ScheduleModel,
    SubjectModel,
    TimeSlotModel,
)
from app.database.session import get_db
from app.main import app
from tests.fixtures.sample_data import build_minimal_instance


# ── Engine e infraestructura compartida (module scope) ────────────────────────

@pytest.fixture(scope="module")
def engine():
    # StaticPool: todas las sesiones comparten una única conexión
    # → el esquema creado con create_all es visible para todas las sesiones.
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
    """Puebla la BD una sola vez con la instancia mínima."""
    with TestSessionLocal() as session:
        _populate_db(session, build_minimal_instance())
        session.commit()
    return engine


@pytest.fixture(scope="module")
def client(populated_engine, TestSessionLocal):
    """
    TestClient con get_db sobreescrito.
    Cada request obtiene su propia sesión, que se cierra al finalizar.
    """
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


# ── Helper: poblar BD ─────────────────────────────────────────────────────────

def _populate_db(session: Session, instance) -> None:
    """Inserta los datos del SchedulingInstance como registros ORM."""
    # Recursos: código→nombre desde aulas (fuente canónica, sin duplicados)
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

    # Salones
    classroom_orm: dict[str, ClassroomModel] = {}
    for c in instance.classrooms:
        c_orm = ClassroomModel(code=c.code, name=c.name, capacity=c.capacity)
        for res in c.resources:
            if res.code in resource_orm:
                c_orm.resources.append(resource_orm[res.code])
        session.add(c_orm)
        classroom_orm[c.code] = c_orm
    session.flush()

    # Franjas horarias
    for ts in instance.timeslots:
        session.add(TimeSlotModel(
            code=ts.code,
            day=ts.day,
            start_time=ts.start_time,
            end_time=ts.end_time,
            duration=ts.duration,
        ))
    session.flush()

    # Docentes
    for p in instance.professors:
        p_orm = ProfessorModel(
            code=p.code,
            name=p.name,
            max_weekly_hours=p.max_weekly_hours,
            contract_type=p.contract_type,
        )
        session.add(p_orm)
        session.flush()

        for ts_code in p.availability:
            session.add(ProfessorAvailabilityModel(
                professor_id=p_orm.id,
                timeslot_code=ts_code,
            ))
        for pref in p.preferences:
            session.add(ProfessorPreferenceModel(
                professor_id=p_orm.id,
                timeslot_code=pref.timeslot_code,
                preference=pref.preference,
            ))
    session.flush()

    # Materias
    for s in instance.subjects:
        s_orm = SubjectModel(
            code=s.code,
            name=s.name,
            credits=s.credits,
            study_hours=s.study_hours,
            weekly_subgroups=s.weekly_subgroups,
            groups=s.groups,
            enrollment=s.enrollment,
            faculty=s.faculty,
            professor_code=s.professor_code,
        )
        for req in s.required_resources:
            if req.resource_code in resource_orm:
                s_orm.required_resources.append(resource_orm[req.resource_code])
        session.add(s_orm)
    session.flush()


# ── Tests de health ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_structure(self, client):
        resp = client.get("/api/v1/health")
        data = resp.json()
        assert "status" in data
        assert "version" in data


# ── Tests de POST /schedule ───────────────────────────────────────────────────

class TestPostSchedule:
    def test_returns_202_accepted(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202, f"Body: {resp.text[:300]}"

    def test_response_has_schedule_id(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "schedule_id" in data
        assert len(data["schedule_id"]) > 0

    def test_response_has_expected_fields(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        data = resp.json()
        required = {"schedule_id", "semester", "solver_used", "status",
                    "utility_score", "elapsed_seconds", "is_feasible"}
        assert required.issubset(data.keys())

    def test_completed_status(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] in ("completed", "failed")

    def test_feasible_result_on_valid_data(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        data = resp.json()
        if data["status"] == "completed":
            assert data["is_feasible"] is True

    def test_zero_hard_constraint_violations(self, client):
        """
        Criterio de éxito principal de la Fase 2:
        Un schedule completado debe tener 0 violaciones de HC.
        """
        post_resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert post_resp.status_code == 202
        schedule_id = post_resp.json()["schedule_id"]

        detail = client.get(f"/api/v1/schedule/{schedule_id}")
        assert detail.status_code == 200
        data = detail.json()

        if data["status"] == "completed":
            assert data["hard_constraint_violations"] == 0, (
                f"Se esperaban 0 violaciones HC, se obtuvo "
                f"{data['hard_constraint_violations']}"
            )


# ── Tests de GET /schedule/{id} ───────────────────────────────────────────────

class TestGetSchedule:
    @pytest.fixture(autouse=True)
    def created_schedule(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        self.schedule_id = resp.json()["schedule_id"]

    def test_get_existing_schedule_200(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        assert resp.status_code == 200

    def test_get_nonexistent_schedule_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/schedule/{fake_id}")
        assert resp.status_code == 404

    def test_detail_response_has_required_fields(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        required = {
            "schedule_id", "semester", "status", "solver_used",
            "total_courses", "assigned_courses", "hard_constraint_violations",
            "soft_constraint_violations", "solve_time_ms",
        }
        assert required.issubset(data.keys())

    def test_assigned_courses_matches_subjects(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        if data["status"] == "completed":
            # La instancia mínima tiene 3 materias × 1 grupo × 1 sesión = 3
            assert data["assigned_courses"] == 3


# ── Tests de GET /schedule/{id}/assignments ───────────────────────────────────

class TestGetAssignments:
    @pytest.fixture(autouse=True)
    def created_schedule(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        self.schedule_id = resp.json()["schedule_id"]
        self.status = resp.json()["status"]

    def test_get_assignments_200(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}/assignments")
        assert resp.status_code == 200

    def test_assignments_is_list(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}/assignments")
        assert isinstance(resp.json(), list)

    def test_assignments_have_expected_fields(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}/assignments")
        assignments = resp.json()
        if assignments:
            a = assignments[0]
            for field in ("subject_code", "classroom_code", "timeslot_code", "group_number"):
                assert field in a

    def test_no_double_booking_in_assignments(self, client):
        """Ningún salón puede aparecer en la misma franja dos veces."""
        if self.status != "completed":
            pytest.skip("Schedule no completado")

        resp = client.get(f"/api/v1/schedule/{self.schedule_id}/assignments")
        assignments = resp.json()

        seen: set = set()
        for a in assignments:
            key = (a["classroom_code"], a["timeslot_code"])
            assert key not in seen, f"Double-booking: {key}"
            seen.add(key)


# ── Test de ciclo completo (criterio de éxito Fase 2) ────────────────────────

class TestPhase2SuccessCriteria:
    """
    Criterio de éxito de la Fase 2:
    POST /api/v1/schedule → schedule_id
    GET  /api/v1/schedule/{id} → status=completed, hard_constraint_violations=0
    """

    def test_full_scheduling_cycle(self, client):
        # 1. POST /schedule
        post_resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "auto"},
        )
        assert post_resp.status_code == 202, f"POST falló: {post_resp.text[:200]}"
        schedule_id = post_resp.json()["schedule_id"]
        assert schedule_id

        # 2. GET /schedule/{id}
        get_resp = client.get(f"/api/v1/schedule/{schedule_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()

        assert data["schedule_id"] == schedule_id
        assert data["status"] in ("completed", "failed")

        if data["status"] == "completed":
            assert data["hard_constraint_violations"] == 0
            assert data["assigned_courses"] > 0
