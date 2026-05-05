"""
HAIA Agent — Endpoints de horario.
POST /schedule  inicia el ciclo BDI completo.
GET  /schedule/{id} consulta el resultado.
"""

import logging
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import AssignmentResponse, ScheduleDetailResponse, ScheduleRequest, ScheduleResponse
from app.database.models import ScheduleModel
from app.database.session import SessionLocal, get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter(prefix="/schedule", tags=["Schedule"])


def _run_scheduling_bg(schedule_id: str, semester: str, solver_hint: str | None) -> None:
    """Ejecuta el pipeline BDI en un thread separado con su propia sesión de BD."""
    from app.bdi.agent import HAIAAgent
    from app.config import settings

    with SessionLocal() as db:
        record = db.query(ScheduleModel).filter(ScheduleModel.schedule_id == schedule_id).first()
        if not record:
            return
        try:
            agent = HAIAAgent(db_session=db, config=settings)
            result = agent.run_scheduling_cycle(
                semester=semester,
                schedule_id=schedule_id,
                solver_hint=solver_hint,
            )
            record.solver_used = result.solver_used
            record.utility_score = result.utility_score
            record.elapsed_seconds = result.elapsed_seconds
            record.is_feasible = result.is_feasible
            record.status = "completed" if result.is_feasible else "failed"
        except Exception as exc:
            logger.exception(f"[API] Error en background task {schedule_id}: {exc}")
            record.status = "failed"
        finally:
            db.commit()


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar ciclo de asignación HAIA",
)
def create_schedule(request: ScheduleRequest, db: Session = Depends(get_db)) -> ScheduleResponse:
    """
    Inicia el pipeline BDI en background:
    Percepción → AC-3 → Solver → SA → Persistencia.
    Retorna 202 Accepted de inmediato. Consultar progreso con GET /schedule/{id}.
    """
    schedule_id = str(uuid.uuid4())
    logger.info(f"[API] Nuevo ciclo de asignación — semestre={request.semester}, id={schedule_id}")

    record = ScheduleModel(
        schedule_id=schedule_id,
        semester=request.semester,
        solver_used=request.solver_hint or "auto",
        status="running",
        is_feasible=False,
        utility_score=0.0,
        elapsed_seconds=0.0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    threading.Thread(
        target=_run_scheduling_bg,
        args=(schedule_id, request.semester, request.solver_hint),
        daemon=True,
    ).start()

    return ScheduleResponse(
        schedule_id=record.schedule_id,
        semester=record.semester,
        solver_used=record.solver_used,
        utility_score=record.utility_score,
        elapsed_seconds=record.elapsed_seconds,
        is_feasible=record.is_feasible,
        status=record.status,
        assignment_count=0,
        created_at=record.created_at,
    )


@router.get("/{schedule_id}", response_model=ScheduleDetailResponse, summary="Consultar resultado")
def get_schedule(schedule_id: str, db: Session = Depends(get_db)) -> ScheduleDetailResponse:
    record = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Schedule not found")

    assignments_resp = [
        AssignmentResponse(
            id=a.id,
            subject_code=a.subject_code,
            classroom_code=a.classroom_code,
            timeslot_code=a.timeslot_code,
            group_number=a.group_number,
            session_number=a.session_number,
            utilidad_score=a.utilidad_score,
        )
        for a in record.assignments
    ]

    return ScheduleDetailResponse(
        schedule_id=record.schedule_id,
        semester=record.semester,
        status=record.status,
        solver_used=record.solver_used,
        utility_score=record.utility_score,
        is_feasible=record.is_feasible,
        total_courses=len(record.assignments),
        assigned_courses=len(record.assignments),
        hard_constraint_violations=0 if record.is_feasible else -1,
        soft_constraint_violations=0,
        solve_time_ms=int(record.elapsed_seconds * 1000),
        elapsed_seconds=record.elapsed_seconds,
        assignments=assignments_resp,
        created_at=record.created_at,
    )


@router.get(
    "/{schedule_id}/assignments",
    response_model=list[AssignmentResponse],
    summary="Ver todas las asignaciones",
)
def get_assignments(schedule_id: str, db: Session = Depends(get_db)) -> list[AssignmentResponse]:
    record = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return [
        AssignmentResponse(
            id=a.id,
            subject_code=a.subject_code,
            classroom_code=a.classroom_code,
            timeslot_code=a.timeslot_code,
            group_number=a.group_number,
            session_number=a.session_number,
            utilidad_score=a.utilidad_score,
        )
        for a in record.assignments
    ]


@router.put("/{schedule_id}/accept", summary="Aceptar propuesta de horario")
def accept_schedule(schedule_id: str, db: Session = Depends(get_db)) -> dict:
    record = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if record.status != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot accept schedule in status '{record.status}'")

    record.status = "accepted"
    db.commit()
    return {"schedule_id": schedule_id, "status": "accepted"}


@router.delete("/{schedule_id}", summary="Rechazar y eliminar horario")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)) -> dict:
    record = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(record)
    db.commit()
    return {"schedule_id": schedule_id, "status": "deleted"}
