"""
HAIA Agent — Capa 5: Historial de versiones del horario.

Cada evento de reparación genera una nueva versión del horario en la BD,
enlazada al horario padre mediante parent_schedule_id.
Permite auditoría completa y rollback a versiones anteriores.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("[HAIA Layer5-VersionManager]")


@dataclass
class ScheduleVersion:
    version_schedule_id: str
    parent_schedule_id: str
    assignments_count: int
    reason: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class VersionManager:
    """
    Persiste versiones reparadas del horario como nuevas filas en 'schedules'.
    El campo parent_schedule_id encadena la historia de reparaciones.
    """

    def save_version(
        self,
        schedule_id: str,
        assignments: list,
        reason: str,
        db,
        semester: str,
        solver_used: str = "repair",
        utility_score: float = 0.0,
    ) -> str:
        """
        Crea una nueva fila en schedules con parent_schedule_id = schedule_id,
        copia todas las asignaciones reparadas y devuelve el nuevo schedule_id.
        """
        from app.database.models import AssignmentModel, ScheduleModel, SubjectModel

        new_sid = str(uuid.uuid4())

        # Preload professor codes for each subject (needed for AssignmentModel.professor_code)
        prof_by_subject: dict[str, str] = {}
        for subj in db.query(SubjectModel).all():
            if subj.professor_code:
                prof_by_subject[subj.code] = subj.professor_code

        new_schedule = ScheduleModel(
            schedule_id=new_sid,
            semester=semester,
            solver_used=solver_used,
            utility_score=utility_score,
            elapsed_seconds=0.0,
            is_feasible=True,
            status="completed",
            parent_schedule_id=schedule_id,
        )
        db.add(new_schedule)
        db.flush()  # get new_schedule.id

        for a in assignments:
            db.add(AssignmentModel(
                schedule_id=new_schedule.id,
                subject_code=a.subject_code,
                classroom_code=a.classroom_code,
                timeslot_code=a.timeslot_code,
                professor_code=prof_by_subject.get(a.subject_code, ""),
                group_number=a.group_number,
                session_number=a.session_number,
                utilidad_score=a.utilidad_score,
            ))

        db.commit()

        logger.info(
            f"[Layer5-VersionManager] Nueva versión creada: {new_sid} "
            f"(padre={schedule_id}, asignaciones={len(assignments)}, motivo={reason!r})"
        )
        return new_sid

    def get_history(self, schedule_id: str, db) -> list[dict]:
        """
        Retorna la cadena de versiones derivadas de schedule_id (todas las hijas directas).
        """
        from app.database.models import ScheduleModel

        children = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.parent_schedule_id == schedule_id)
            .order_by(ScheduleModel.created_at)
            .all()
        )
        return [
            {
                "schedule_id": s.schedule_id,
                "parent_schedule_id": s.parent_schedule_id,
                "created_at": s.created_at,
                "utility_score": s.utility_score,
                "assignments_count": len(s.assignments),
            }
            for s in children
        ]
