"""
HAIA Agent — BDI: Pipeline de Intenciones (Intentions).
Define el plan de ejecución concreto para el ciclo de asignación.
Cada intención es un paso del pipeline de 5 capas de HAIA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("[HAIA BDI-Intentions]")


class IntentionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Intention:
    name: str
    layer: int
    status: IntentionStatus = IntentionStatus.PENDING
    result: object = None
    error: str | None = None


class IntentionPipeline:
    """
    Pipeline de 5 capas del agente HAIA.
    Cada ejecución crea una nueva secuencia de intenciones.
    """

    def build_scheduling_pipeline(self) -> list[Intention]:
        return [
            Intention(name="PERCEIVE_DATA", layer=1),
            Intention(name="PREPROCESS_AC3", layer=2),
            Intention(name="SOLVE_CSP_OR_MILP", layer=3),
            Intention(name="OPTIMIZE_SA", layer=4),
            Intention(name="PERSIST_AND_REPORT", layer=5),
        ]

    def build_repair_pipeline(self) -> list[Intention]:
        return [
            Intention(name="PERCEIVE_EVENT", layer=1),
            Intention(name="IDENTIFY_AFFECTED", layer=5),
            Intention(name="LOCAL_REPAIR", layer=5),
            Intention(name="REOPTIMIZE_NEIGHBORHOOD", layer=4),
            Intention(name="PERSIST_REPAIR", layer=5),
        ]

    def next_pending(self, intentions: list[Intention]) -> Intention | None:
        return next((i for i in intentions if i.status == IntentionStatus.PENDING), None)

    def all_completed(self, intentions: list[Intention]) -> bool:
        return all(
            i.status in (IntentionStatus.COMPLETED, IntentionStatus.SKIPPED)
            for i in intentions
        )

    def has_failure(self, intentions: list[Intention]) -> bool:
        return any(i.status == IntentionStatus.FAILED for i in intentions)
