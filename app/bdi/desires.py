"""
HAIA Agent — BDI: Conjunto de Deseos (Desires).
Define los objetivos del agente en orden de prioridad.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


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
    active: bool = True


class DesireSet:
    """Conjunto de deseos ordenados por prioridad del agente HAIA."""

    DESIRES: list[Desire] = [
        Desire(
            name="FEASIBLE_SCHEDULE",
            description="Producir un horario que no viole ninguna HC",
            priority=DesirePriority.CRITICAL,
        ),
        Desire(
            name="MAXIMIZE_UTILITY",
            description="Maximizar U(A) = w1·ocup + w2·pref + w3·dist + w4·rec − λ·Pen",
            priority=DesirePriority.HIGH,
        ),
        Desire(
            name="MINIMIZE_PERTURBATION",
            description="Ante eventos dinámicos, minimizar cambios en el horario vigente",
            priority=DesirePriority.HIGH,
        ),
        Desire(
            name="EQUITABLE_LOAD",
            description="Distribuir carga docente equitativamente (SC5)",
            priority=DesirePriority.MEDIUM,
        ),
        Desire(
            name="PREFER_MORNING_SLOTS",
            description="Asignar en franjas de mañana cuando sea posible (SC3)",
            priority=DesirePriority.LOW,
        ),
    ]

    def get_active(self, min_priority: DesirePriority = DesirePriority.LOW) -> list[Desire]:
        return sorted(
            [d for d in self.DESIRES if d.active and d.priority <= min_priority],
            key=lambda d: d.priority,
        )

    def is_critical_satisfied(self, has_feasible_solution: bool) -> bool:
        return has_feasible_solution
