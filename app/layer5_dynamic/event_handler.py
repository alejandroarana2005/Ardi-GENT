"""
HAIA Agent — Capa 5: Manejador de eventos dinámicos.
Stub funcional para la Fase 1. Implementación completa en la Fase 4.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("[HAIA Layer5-Dynamic]")


@dataclass
class DynamicEvent:
    """Evento que dispara re-optimización dinámica."""
    event_type: str
    schedule_id: str
    payload: dict = field(default_factory=dict)


@dataclass
class RepairResult:
    """Resultado de una reparación local."""
    is_successful: bool
    affected_count: int = 0
    elapsed_seconds: float = 0.0
    message: str = ""


class EventHandler:
    """
    Gestiona eventos de cambio y dispara reparación local (k-vecindad).
    Principio de Mínima Perturbación: solo re-optimiza lo estrictamente necesario.
    Target: < 30 segundos para eventos que afecten ≤ 10 cursos.
    """

    SUPPORTED_EVENTS = {
        "CLASSROOM_UNAVAILABLE",
        "PROFESSOR_CANCELLED",
        "ENROLLMENT_SURGE",
        "SLOT_BLOCKED",
        "NEW_COURSE_ADDED",
    }

    def handle(self, event: DynamicEvent, context: dict) -> RepairResult:
        logger.info(f"[Layer5] Procesando evento {event.event_type}")
        t0 = time.perf_counter()

        if event.event_type not in self.SUPPORTED_EVENTS:
            return RepairResult(
                is_successful=False,
                message=f"Unsupported event type: {event.event_type}",
            )

        # Stub: en la Fase 4 se implementa la reparación real por tipo de evento
        result = RepairResult(
            is_successful=True,
            affected_count=0,
            elapsed_seconds=time.perf_counter() - t0,
            message=f"[stub] Event {event.event_type} acknowledged, repair pending Phase 4",
        )
        logger.info(f"[Layer5] {result.message}")
        return result
