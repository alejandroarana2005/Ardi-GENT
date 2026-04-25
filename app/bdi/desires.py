"""
HAIA Agent — BDI: Conjunto de Deseos (Desires).
Define los objetivos del agente en orden de prioridad.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, Enum


class DesireType(str, Enum):
    """Tipos de deseo formales del agente HAIA."""
    GENERATE_SCHEDULE = "GENERATE_SCHEDULE"
    REPAIR_SCHEDULE = "REPAIR_SCHEDULE"
    OPTIMIZE_SCHEDULE = "OPTIMIZE_SCHEDULE"
    VALIDATE_SCHEDULE = "VALIDATE_SCHEDULE"


class DesirePriority(IntEnum):
    CRITICAL = 1   # Sin esto el agente no cumple su función
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass(frozen=True)
class Desire:
    name: str
    description: str
    priority: DesirePriority
    desire_type: DesireType = DesireType.GENERATE_SCHEDULE
    active: bool = True


class DesireSet:
    """Conjunto de deseos ordenados por prioridad del agente HAIA."""

    DESIRES: list[Desire] = [
        Desire(
            name="FEASIBLE_SCHEDULE",
            description="Producir un horario que no viole ninguna HC",
            priority=DesirePriority.CRITICAL,
            desire_type=DesireType.GENERATE_SCHEDULE,
        ),
        Desire(
            name="MAXIMIZE_UTILITY",
            description="Maximizar U(A) = w1·ocup + w2·pref + w3·dist + w4·rec − λ·Pen",
            priority=DesirePriority.HIGH,
            desire_type=DesireType.OPTIMIZE_SCHEDULE,
        ),
        Desire(
            name="MINIMIZE_PERTURBATION",
            description="Ante eventos dinámicos, minimizar cambios en el horario vigente",
            priority=DesirePriority.HIGH,
            desire_type=DesireType.REPAIR_SCHEDULE,
        ),
        Desire(
            name="EQUITABLE_LOAD",
            description="Distribuir carga docente equitativamente (SC5)",
            priority=DesirePriority.MEDIUM,
            desire_type=DesireType.OPTIMIZE_SCHEDULE,
        ),
        Desire(
            name="PREFER_MORNING_SLOTS",
            description="Asignar en franjas de mañana cuando sea posible (SC3)",
            priority=DesirePriority.LOW,
            desire_type=DesireType.OPTIMIZE_SCHEDULE,
        ),
    ]

    def get_active(self, min_priority: DesirePriority = DesirePriority.LOW) -> list[Desire]:
        return sorted(
            [d for d in self.DESIRES if d.active and d.priority <= min_priority],
            key=lambda d: d.priority,
        )

    def get_by_type(self, desire_type: DesireType) -> list[Desire]:
        return [d for d in self.DESIRES if d.desire_type == desire_type and d.active]

    def is_critical_satisfied(self, has_feasible_solution: bool) -> bool:
        return has_feasible_solution
