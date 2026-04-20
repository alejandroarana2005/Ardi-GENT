"""HAIA Agent — Endpoints de métricas U(A)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import MetricsResponse
from app.database.models import ScheduleModel
from app.database.session import get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/{schedule_id}", response_model=MetricsResponse, summary="Métricas del horario")
def get_metrics(schedule_id: str, db: Session = Depends(get_db)) -> MetricsResponse:
    schedule = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    from app.reporting.metrics_calculator import MetricsCalculator
    from app.layer1_perception.data_loader import DataLoader

    loader = DataLoader(db)
    instance, _ = loader.load_instance(schedule.semester)

    from app.domain.entities import Assignment
    domain_assignments = [
        Assignment(
            subject_code=a.subject_code,
            classroom_code=a.classroom_code,
            timeslot_code=a.timeslot_code,
            group_number=a.group_number,
            session_number=a.session_number,
            utilidad_score=a.utilidad_score,
        )
        for a in schedule.assignments
    ]

    calc = MetricsCalculator()
    metrics = calc.compute(schedule_id, domain_assignments, instance)
    return metrics
