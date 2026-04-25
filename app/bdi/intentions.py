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


@dataclass
class Plan:
    """Plan concreto seleccionado para satisfacer un deseo."""
    name: str
    context: str   # "generate" | "repair"
    intentions: list[Intention] = field(default_factory=list)


class IntentionPipeline:
    """
    Pipeline de 5 capas del agente HAIA.
    Cada ejecución crea una nueva secuencia de intenciones.
    """

    def plan_for(self, context: str) -> list[Intention]:
        """Despacha el pipeline correcto según el contexto BDI."""
        if context == "repair":
            return self._plan_repair()
        return self._plan_generate()

    def _plan_generate(self) -> list[Intention]:
        return self.build_scheduling_pipeline()

    def _plan_repair(self) -> list[Intention]:
        return self.build_repair_pipeline()

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
