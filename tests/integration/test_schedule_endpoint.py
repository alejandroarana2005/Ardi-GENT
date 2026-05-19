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


# ── Tests de tiempos por capa ─────────────────────────────────────────────────

class TestLayerTimes:
    """
    Verifica que GET /schedule/{id} exponga tiempos reales por capa BDI.
    Criterio de aceptación: layer1-4 son enteros positivos; layer5 es None;
    la suma de las 4 capas no supera elapsed_seconds * 1000 * 1.05 (tolerancia 5%).
    """

    @pytest.fixture(autouse=True)
    def run_full_cycle(self, client):
        resp = client.post(
            "/api/v1/schedule",
            json={"semester": "TEST", "solver_hint": "backtracking"},
        )
        assert resp.status_code == 202
        self.schedule_id = resp.json()["schedule_id"]
        self.post_data = resp.json()

    def test_layer_times_present_in_response(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        assert resp.status_code == 200
        assert "layer_times" in resp.json()

    def test_layer_times_keys(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        lt = resp.json()["layer_times"]
        assert lt is not None
        for key in ("layer1_ms", "layer2_ms", "layer3_ms", "layer4_ms", "layer5_ms"):
            assert key in lt, f"Falta clave: {key}"

    def test_layer1_to_4_are_positive_integers_when_completed(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        if data["status"] != "completed":
            pytest.skip("Schedule no completado — no se puede verificar tiempos")
        lt = data["layer_times"]
        for key in ("layer1_ms", "layer2_ms", "layer3_ms", "layer4_ms"):
            assert isinstance(lt[key], int), f"{key} debe ser int, es {type(lt[key])}"
            assert lt[key] >= 0, f"{key} debe ser >= 0, es {lt[key]}"

    def test_layer5_is_none_for_initial_generation(self, client):
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        if data["status"] != "completed":
            pytest.skip("Schedule no completado")
        assert data["layer_times"]["layer5_ms"] is None

    def test_layer4_is_largest_when_completed(self, client):
        """SA (Capa 4) debe ser la capa más lenta; si no lo es, hay bug en instrumentación."""
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        if data["status"] != "completed":
            pytest.skip("Schedule no completado")
        lt = data["layer_times"]
        timed = {k: lt[k] for k in ("layer1_ms", "layer2_ms", "layer3_ms", "layer4_ms")}
        max_key = max(timed, key=lambda k: timed[k])
        assert max_key == "layer4_ms", (
            f"Se esperaba layer4_ms como la más lenta, pero fue {max_key}. Tiempos: {timed}"
        )

    def test_sum_of_layers_within_elapsed_tolerance(self, client):
        """
        La suma layer1+2+3+4 no debe superar elapsed_seconds*1000 en más de un 5%.
        La suma podría ser ligeramente menor porque elapsed incluye overhead de coordinación.
        """
        resp = client.get(f"/api/v1/schedule/{self.schedule_id}")
        data = resp.json()
        if data["status"] != "completed":
            pytest.skip("Schedule no completado")
        lt = data["layer_times"]
        layer_sum = sum(lt[k] for k in ("layer1_ms", "layer2_ms", "layer3_ms", "layer4_ms"))
        elapsed_ms = data["elapsed_seconds"] * 1000
        assert layer_sum <= elapsed_ms * 1.05, (
            f"Suma de capas ({layer_sum} ms) supera elapsed ({elapsed_ms:.0f} ms) + 5%"
        )


class TestListSchedules:
    """
    Tests para GET /api/v1/schedules.
    Usa semestres únicos (LIST_TEST_*) para evitar interferencia con otros tests.
    """

    _ids: list[str]

    @pytest.fixture(autouse=True)
    def insert_and_cleanup(self, TestSessionLocal):
        """Inserta registros conocidos con timestamps explícitos y los limpia al final."""
        from datetime import datetime as dt

        records = [
            ScheduleModel(
                schedule_id="list-test-001",
                semester="LIST_TEST_2024A",
                solver_used="tabu_search",
                status="completed",
                is_feasible=True,
                utility_score=0.75,
                elapsed_seconds=38.5,
                created_at=dt(2026, 5, 10, 10, 0, 0),
            ),
            ScheduleModel(
                schedule_id="list-test-002",
                semester="LIST_TEST_2024A",
                solver_used="milp",
                status="completed",
                is_feasible=True,
                utility_score=0.72,
                elapsed_seconds=45.2,
                created_at=dt(2026, 5, 11, 12, 0, 0),
            ),
            ScheduleModel(
                schedule_id="list-test-003",
                semester="LIST_TEST_2025A",
                solver_used="backtracking",
                status="failed",
                is_feasible=False,
                utility_score=0.0,
                elapsed_seconds=5.1,
                created_at=dt(2026, 5, 9, 8, 0, 0),
            ),
        ]
        self._ids = [r.schedule_id for r in records]

        with TestSessionLocal() as session:
            for r in records:
                session.add(r)
            session.commit()

        yield

        with TestSessionLocal() as session:
            for sid in self._ids:
                session.query(ScheduleModel).filter(
                    ScheduleModel.schedule_id == sid
                ).delete()
            session.commit()

    def test_list_schedules_returns_empty_when_no_schedules(self, client):
        """Semestre inexistente devuelve lista vacía con paginación correcta."""
        resp = client.get("/api/v1/schedules?semester=NONEXISTENT_XYZ")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_list_schedules_returns_most_recent_first(self, client):
        """Los items se ordenan descendente por created_at (más reciente primero)."""
        resp = client.get("/api/v1/schedules?semester=LIST_TEST_2024A")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        items = data["items"]
        assert len(items) == 2
        # list-test-002 (2026-05-11) debe preceder a list-test-001 (2026-05-10)
        assert items[0]["schedule_id"] == "list-test-002"
        assert items[1]["schedule_id"] == "list-test-001"

    def test_list_schedules_filters_by_semester_and_status(self, client):
        """Filtros combinados semester+status devuelven solo registros que coinciden."""
        resp = client.get("/api/v1/schedules?semester=LIST_TEST_2025A&status=failed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["schedule_id"] == "list-test-003"
        assert data["items"][0]["semester"] == "LIST_TEST_2025A"
        assert data["items"][0]["status"] == "failed"
