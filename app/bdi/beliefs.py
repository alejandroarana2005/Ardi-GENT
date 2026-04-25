"""
HAIA Agent — BDI: Base de Creencias (Beliefs).
Representa el estado actual del mundo percibido por el agente.
Se actualiza en cada ciclo de la Capa 1 y tras cada evento dinámico.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.domain.entities import Assignment, SchedulingInstance

if TYPE_CHECKING:
    from app.layer5_dynamic.event_handler import DynamicEvent

logger = logging.getLogger("[HAIA BDI-Beliefs]")


@dataclass
class BeliefBase:
    """Estado actual del sistema desde la perspectiva del agente HAIA."""

    db_session: Session
    current_instance: SchedulingInstance | None = None
    current_semester: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)
    active_schedule_id: str | None = None
    assignments: list[Assignment] = field(default_factory=list)

    # Creencias derivadas del análisis de la instancia
    is_instance_feasible: bool = True
    estimated_difficulty: str = "unknown"  # "easy" | "medium" | "hard"

    def update_from_instance(self, instance: SchedulingInstance, semester: str) -> None:
        self.current_instance = instance
        self.current_semester = semester
        self.last_updated = datetime.utcnow()

        summary = instance.summary()
        search_space = summary["search_space_size"]

        if search_space < 10_000:
            self.estimated_difficulty = "easy"
        elif search_space < 1_000_000:
            self.estimated_difficulty = "medium"
        else:
            self.estimated_difficulty = "hard"

        logger.info(
            f"[BDI-Beliefs] Instancia actualizada — semestre={semester}, "
            f"dificultad={self.estimated_difficulty}, "
            f"espacio={search_space:,}"
        )

    def update_from_event(self, event: "DynamicEvent") -> None:
        """Invalida creencias afectadas por un evento dinámico."""
        self.last_updated = datetime.utcnow()
        logger.info(
            f"[BDI-Beliefs] Creencias actualizadas por evento: "
            f"{event.event_type} en schedule={event.schedule_id}"
        )

    def get_affected_assignments(self, event: "DynamicEvent") -> list[Assignment]:
        """Retorna las asignaciones que el evento hace inválidas o necesitan reparación."""
        if not self.assignments or not self.current_instance:
            return []

        payload = event.payload
        event_type = event.event_type

        if event_type == "CLASSROOM_UNAVAILABLE":
            classroom_code = payload.get("classroom_code", "")
            return [a for a in self.assignments if a.classroom_code == classroom_code]

        if event_type == "PROFESSOR_CANCELLED":
            professor_code = payload.get("professor_code", "")
            subjects_for_prof = {
                s.code for s in self.current_instance.subjects
                if s.professor_code == professor_code
            }
            return [a for a in self.assignments if a.subject_code in subjects_for_prof]

        if event_type == "SLOT_BLOCKED":
            timeslot_code = payload.get("timeslot_code", "")
            return [a for a in self.assignments if a.timeslot_code == timeslot_code]

        if event_type == "ENROLLMENT_SURGE":
            subject_code = payload.get("subject_code", "")
            new_enrollment = int(payload.get("new_enrollment", 0))
            affected = []
            cls_map = {c.code: c for c in self.current_instance.classrooms}
            for a in self.assignments:
                if a.subject_code != subject_code:
                    continue
                cls = cls_map.get(a.classroom_code)
                if cls and cls.capacity < new_enrollment:
                    affected.append(a)
            return affected

        # NEW_COURSE_ADDED: no existing assignments invalidated
        return []

    def load_from_schedule(self, schedule_id: str, db: Session) -> None:
        """Carga las asignaciones activas desde la BD para el schedule dado."""
        from app.database.models import AssignmentModel, ScheduleModel

        schedule = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            logger.warning(f"[BDI-Beliefs] Schedule {schedule_id} no encontrado en BD")
            return

        self.active_schedule_id = schedule_id
        self.assignments = [
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
        logger.info(
            f"[BDI-Beliefs] {len(self.assignments)} asignaciones cargadas "
            f"desde schedule={schedule_id}"
        )

    def total_courses_to_assign(self) -> int:
        if not self.current_instance:
            return 0
        return sum(s.total_assignments_needed() for s in self.current_instance.subjects)
