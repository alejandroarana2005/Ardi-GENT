"""
Infraestructura compartida para todos los experimentos.
Crea DB in-memory, puebla con instancia sintética y ejecuta HAIA directamente.
No usa HTTP — llama al agente BDI en-proceso para máxima fidelidad.
"""

from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.bdi.agent import HAIAAgent
from app.config import HAIAConfig, settings
from app.database.models import (
    Base,
    ClassroomModel,
    ProfessorAvailabilityModel,
    ProfessorModel,
    ProfessorPreferenceModel,
    ResourceModel,
    ScheduleModel,
    SubjectModel,
    TimeSlotModel,
)
from app.domain.entities import SchedulingInstance, SchedulingResult

logger = logging.getLogger("[experiments]")

# Config with no SA — T0 == T_min so the while-loop never fires
NO_SA_CONFIG = HAIAConfig(
    sa_t0=0.0001,
    sa_t_min=0.0001,
    sa_iters_per_t=1,
    database_url="sqlite:///:memory:",
)


def setup_in_memory_db() -> tuple:
    """Returns (engine, Session factory) backed by a fresh in-memory SQLite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, Session


def populate_db(session: Session, instance: SchedulingInstance) -> None:
    """Insert all domain entities from *instance* into *session*.
    Handles instances with or without resources (synthetic and institutional).
    """
    # 1. Collect + insert unique Resources
    resource_map: dict[str, ResourceModel] = {}
    for c in instance.classrooms:
        for r in c.resources:
            if r.code not in resource_map:
                rm = ResourceModel(code=r.code, name=r.name)
                session.add(rm)
                resource_map[r.code] = rm
    for s in instance.subjects:
        for req in list(s.required_resources) + list(s.optional_resources):
            if req.resource_code not in resource_map:
                rm = ResourceModel(code=req.resource_code, name=req.resource_code)
                session.add(rm)
                resource_map[req.resource_code] = rm
    session.flush()

    # 2. Time slots
    for ts in instance.timeslots:
        session.add(TimeSlotModel(
            code=ts.code,
            day=ts.day,
            start_time=ts.start_time,
            end_time=ts.end_time,
            duration=ts.duration,
        ))
    session.flush()

    # 3. Professors + availability + preferences
    for p in instance.professors:
        prof_model = ProfessorModel(
            code=p.code,
            name=p.name,
            max_weekly_hours=p.max_weekly_hours,
            contract_type=p.contract_type,
        )
        session.add(prof_model)
        session.flush()

        for ts_code in p.availability:
            session.add(ProfessorAvailabilityModel(
                professor_id=prof_model.id,
                timeslot_code=ts_code,
            ))
        for pref in p.preferences:
            session.add(ProfessorPreferenceModel(
                professor_id=prof_model.id,
                timeslot_code=pref.timeslot_code,
                preference=pref.preference,
            ))
    session.flush()

    # 4. Classrooms (with resource links)
    for c in instance.classrooms:
        c_orm = ClassroomModel(code=c.code, name=c.name, capacity=c.capacity)
        for r in c.resources:
            if r.code in resource_map:
                c_orm.resources.append(resource_map[r.code])
        session.add(c_orm)
    session.flush()

    # 5. Subjects (professor FK already in DB, with required resource links)
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
            if req.resource_code in resource_map:
                s_orm.required_resources.append(resource_map[req.resource_code])
        session.add(s_orm)

    session.commit()


def run_haia_on_db(
    db: Session,
    instance: SchedulingInstance,
    solver_hint: Optional[str] = None,
    custom_config: Optional[HAIAConfig] = None,
    sa_seed: Optional[int] = None,
) -> SchedulingResult:
    """Create a ScheduleModel record, run the BDI agent, update the record."""
    config = custom_config or settings
    schedule_id = str(uuid.uuid4())

    record = ScheduleModel(
        schedule_id=schedule_id,
        semester=instance.semester,
        solver_used=solver_hint or "auto",
        status="running",
        is_feasible=False,
        utility_score=0.0,
        elapsed_seconds=0.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    agent = HAIAAgent(db_session=db, config=config)
    result = agent.run_scheduling_cycle(
        semester=instance.semester,
        schedule_id=schedule_id,
        solver_hint=solver_hint,
        sa_seed=sa_seed,
    )

    record.solver_used   = result.solver_used
    record.utility_score = result.utility_score
    record.elapsed_seconds = result.elapsed_seconds
    record.is_feasible   = result.is_feasible
    record.status        = "completed" if result.is_feasible else "failed"
    record.layer1_ms     = result.layer_times.get("layer1_ms")
    record.layer2_ms     = result.layer_times.get("layer2_ms")
    record.layer3_ms     = result.layer_times.get("layer3_ms")
    record.layer4_ms     = result.layer_times.get("layer4_ms")
    record.layer5_ms     = result.layer_times.get("layer5_ms")
    record.updated_at    = datetime.utcnow()
    db.commit()

    return result


def run_haia_cycle(
    instance: SchedulingInstance,
    solver_hint: Optional[str] = None,
    custom_config: Optional[HAIAConfig] = None,
    sa_seed: Optional[int] = None,
) -> SchedulingResult:
    """Full pipeline: fresh in-memory DB → populate → run agent."""
    _, Session = setup_in_memory_db()
    with Session() as db:
        populate_db(db, instance)
        return run_haia_on_db(db, instance, solver_hint, custom_config, sa_seed=sa_seed)


def _run_with_timeout(fn, timeout_s: float) -> tuple:
    """
    Run *fn()* in a thread and return (result, error_msg).
    Returns (None, "timeout") if it exceeds *timeout_s*.
    Windows-compatible (no SIGALRM).
    """
    result_holder: list = [None]
    error_holder:  list = [None]
    done_event = threading.Event()

    def _target():
        try:
            result_holder[0] = fn()
        except Exception as exc:
            error_holder[0] = str(exc)
            logger.exception(f"[experiments] Error en _run_with_timeout: {exc}")
        finally:
            done_event.set()

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    finished = done_event.wait(timeout=timeout_s)

    if not finished:
        return None, f"timeout after {timeout_s}s"
    if error_holder[0]:
        return None, error_holder[0]
    return result_holder[0], None
