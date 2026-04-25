"""
Tests de integración para la Capa 5 — Eventos dinámicos y reparación local.

Criterios de éxito (Fase 4):
    - repair_elapsed_seconds < 30
    - hard_violations = 0 en la versión reparada
    - El evento retorna una nueva versión del horario (new_schedule_id != None)
    - Principio de Mínima Perturbación: se mueve solo lo estrictamente necesario

Usa la misma infraestructura SQLite en memoria de test_schedule_endpoint.py.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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


# ── Engine compartido (module scope) ─────────────────────────────────────────

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


# ── Helper: poblar BD (mismo que test_schedule_endpoint) ─────────────────────

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

    classroom_orm: dict[str, ClassroomModel] = {}
    for c in instance.classrooms:
        c_orm = ClassroomModel(code=c.code, name=c.name, capacity=c.capacity)
        for res in c.resources:
            if res.code in resource_orm:
                c_orm.resources.append(resource_orm[res.code])
        session.add(c_orm)
        classroom_orm[c.code] = c_orm
    session.flush()

    for ts in instance.timeslots:
        session.add(TimeSlotModel(
            code=ts.code,
            day=ts.day,
            start_time=ts.start_time,
            end_time=ts.end_time,
            duration=ts.duration,
        ))
    session.flush()

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


# ── Fixture de horario completado ─────────────────────────────────────────────

def _create_completed_schedule(client) -> tuple[str, list]:
    """Crea un horario completado y retorna (schedule_id, assignments)."""
    resp = client.post(
        "/api/v1/schedule",
        json={"semester": "TEST", "solver_hint": "backtracking"},
    )
    assert resp.status_code == 202, f"POST /schedule falló: {resp.text[:200]}"
    sid = resp.json()["schedule_id"]

    detail = client.get(f"/api/v1/schedule/{sid}")
    assert detail.status_code == 200
    assert detail.json()["status"] in ("completed", "failed")

    assignments_resp = client.get(f"/api/v1/schedule/{sid}/assignments")
    assert assignments_resp.status_code == 200
    assignments = assignments_resp.json()
    return sid, assignments


# ── Tests de eventos dinámicos ────────────────────────────────────────────────

class TestDynamicEvents:

    def test_classroom_unavailable_triggers_repair(self, client):
        """
        POST /events con CLASSROOM_UNAVAILABLE debe retornar 200
        y reportar cuántas asignaciones fueron afectadas.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        classroom = assignments[0]["classroom_code"]
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "CLASSROOM_UNAVAILABLE",
            "payload": {"classroom_code": classroom},
        })
        assert resp.status_code == 200, f"Body: {resp.text[:300]}"
        data = resp.json()
        assert "affected_assignments" in data
        assert data["affected_assignments"] >= 1
        assert "repair_elapsed_seconds" in data

    def test_professor_cancelled_triggers_repair(self, client):
        """
        POST /events con PROFESSOR_CANCELLED debe ejecutarse sin error
        y el repair_elapsed_seconds debe estar presente.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        # Get professor from first assignment via subjects endpoint
        subject_code = assignments[0]["subject_code"]
        # Use a known professor from the minimal fixture (prof_P1)
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "PROFESSOR_CANCELLED",
            "payload": {"professor_code": "PROF_P1"},
        })
        # Expect 200 even if no assignments match (affected_assignments = 0)
        assert resp.status_code == 200, f"Body: {resp.text[:300]}"
        data = resp.json()
        assert "repair_elapsed_seconds" in data
        assert data["repair_elapsed_seconds"] >= 0

    def test_slot_blocked_triggers_repair(self, client):
        """
        SLOT_BLOCKED para la primera franja horaria usada en el horario.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        timeslot = assignments[0]["timeslot_code"]
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "SLOT_BLOCKED",
            "payload": {"timeslot_code": timeslot},
        })
        assert resp.status_code == 200, f"Body: {resp.text[:300]}"
        data = resp.json()
        assert data["affected_assignments"] >= 1

    def test_repair_under_30s(self, client):
        """
        Criterio de éxito: reparación en < 30 segundos para instancia mínima.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        classroom = assignments[0]["classroom_code"]
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "CLASSROOM_UNAVAILABLE",
            "payload": {"classroom_code": classroom},
        })
        assert resp.status_code == 200
        elapsed = resp.json()["repair_elapsed_seconds"]
        assert elapsed < 30.0, f"Reparación tardó {elapsed:.2f}s — excede límite de 30s"

    def test_minimum_perturbation_new_schedule_created(self, client):
        """
        Una reparación exitosa debe crear una nueva versión del horario
        (new_schedule_id != None) y el nuevo schedule_id debe ser diferente.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        timeslot = assignments[0]["timeslot_code"]
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "SLOT_BLOCKED",
            "payload": {"timeslot_code": timeslot},
        })
        assert resp.status_code == 200
        data = resp.json()
        # If repair was successful, a new version should be created
        if data["affected_assignments"] > 0:
            assert data["new_schedule_id"] is not None
            assert data["new_schedule_id"] != sid

    def test_get_event_history(self, client):
        """
        GET /events/{schedule_id} retorna la lista de eventos aplicados al horario.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        # Apply one event
        classroom = assignments[0]["classroom_code"]
        client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "CLASSROOM_UNAVAILABLE",
            "payload": {"classroom_code": classroom},
        })

        history = client.get(f"/api/v1/events/{sid}")
        assert history.status_code == 200
        events = history.json()
        assert isinstance(events, list)
        assert len(events) >= 1
        assert events[0]["event_type"] == "CLASSROOM_UNAVAILABLE"

    def test_invalid_event_type_returns_422(self, client):
        """Tipo de evento inválido → Pydantic rechaza con 422."""
        sid, _ = _create_completed_schedule(client)
        resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "INVALID_TYPE",
            "payload": {},
        })
        assert resp.status_code == 422

    def test_event_on_nonexistent_schedule_returns_404(self, client):
        """Evento sobre un schedule_id inexistente → 404."""
        resp = client.post("/api/v1/events", json={
            "schedule_id": "00000000-0000-0000-0000-000000000000",
            "event_type": "CLASSROOM_UNAVAILABLE",
            "payload": {"classroom_code": "CLS_A"},
        })
        assert resp.status_code == 404

    def test_repaired_schedule_has_no_hard_violations(self, client, TestSessionLocal):
        """
        El horario reparado (nueva versión) no debe tener violaciones HC.
        Verifica GET /schedule/{new_schedule_id} → hard_constraint_violations = 0.
        """
        sid, assignments = _create_completed_schedule(client)
        if not assignments:
            pytest.skip("Horario sin asignaciones")

        timeslot = assignments[0]["timeslot_code"]
        repair_resp = client.post("/api/v1/events", json={
            "schedule_id": sid,
            "event_type": "SLOT_BLOCKED",
            "payload": {"timeslot_code": timeslot},
        })
        assert repair_resp.status_code == 200
        new_sid = repair_resp.json().get("new_schedule_id")
        if new_sid is None:
            pytest.skip("No se creó nueva versión (sin asignaciones afectadas)")

        detail = client.get(f"/api/v1/schedule/{new_sid}")
        assert detail.status_code == 200
        data = detail.json()
        assert data["hard_constraint_violations"] == 0, (
            f"Nueva versión {new_sid} tiene {data['hard_constraint_violations']} violaciones HC"
        )
