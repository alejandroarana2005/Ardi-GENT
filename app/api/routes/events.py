"""HAIA Agent — Endpoints de eventos dinámicos (Capa 5)."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import DynamicEventRequest, DynamicEventResponse
from app.database.models import DynamicEventModel, ScheduleModel
from app.database.session import get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=DynamicEventResponse, summary="Reportar evento dinámico")
def post_event(request: DynamicEventRequest, db: Session = Depends(get_db)) -> DynamicEventResponse:
    """Dispara re-optimización dinámica según el tipo de evento (Principio de Mínima Perturbación)."""
    from app.bdi.agent import HAIAAgent
    from app.config import settings

    schedule = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == request.schedule_id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.status not in ("completed", "accepted"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply event to schedule in status '{schedule.status}'",
        )

    logger.info(
        f"[API] Evento {request.event_type} en schedule {request.schedule_id}: {request.payload}"
    )

    from app.domain.entities import SchedulingResult
    from app.layer5_dynamic.event_handler import DynamicEvent

    event = DynamicEvent(
        event_type=request.event_type,
        schedule_id=request.schedule_id,
        payload=request.payload,
    )

    agent = HAIAAgent(db_session=db, config=settings)
    repair_result = agent.handle_dynamic_event(event)

    record = DynamicEventModel(
        schedule_id=schedule.id,
        event_type=request.event_type,
        payload=json.dumps(request.payload),
        affected_assignments=repair_result.affected_count,
        repair_elapsed_seconds=repair_result.elapsed_seconds,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return DynamicEventResponse(
        id=record.id,
        schedule_id=request.schedule_id,
        event_type=record.event_type,
        affected_assignments=record.affected_assignments,
        repair_elapsed_seconds=record.repair_elapsed_seconds,
        new_schedule_id=repair_result.new_schedule_id,
        created_at=record.created_at,
    )


@router.get("/{schedule_id}", response_model=list[DynamicEventResponse], summary="Historial de eventos")
def get_events(schedule_id: str, db: Session = Depends(get_db)) -> list[DynamicEventResponse]:
    schedule = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return [
        DynamicEventResponse(
            id=e.id,
            schedule_id=schedule_id,
            event_type=e.event_type,
            affected_assignments=e.affected_assignments,
            repair_elapsed_seconds=e.repair_elapsed_seconds,
            created_at=e.created_at,
        )
        for e in schedule.events
    ]
