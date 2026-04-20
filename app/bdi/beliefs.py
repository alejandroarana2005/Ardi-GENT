"""
HAIA Agent — BDI: Base de Creencias (Beliefs).
Representa el estado actual del mundo percibido por el agente.
Se actualiza en cada ciclo de la Capa 1 y tras cada evento dinámico.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA BDI-Beliefs]")


@dataclass
class BeliefBase:
    """Estado actual del sistema desde la perspectiva del agente HAIA."""

    db_session: Session
    current_instance: SchedulingInstance | None = None
    current_semester: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)
    active_schedule_id: str | None = None

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

    def total_courses_to_assign(self) -> int:
        if not self.current_instance:
            return 0
        return sum(s.total_assignments_needed() for s in self.current_instance.subjects)
