"""HAIA Agent — Capa 5: Historial de versiones del horario. Stub Fase 1."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("[HAIA Layer5-VersionManager]")


@dataclass
class ScheduleVersion:
    version: int
    schedule_id: str
    assignments_snapshot: list
    created_at: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""


class VersionManager:
    """Mantiene un historial de versiones del horario para auditoría y rollback."""

    def __init__(self) -> None:
        self._history: list[ScheduleVersion] = []

    def save(self, schedule_id: str, assignments: list, reason: str = "") -> ScheduleVersion:
        version = ScheduleVersion(
            version=len(self._history) + 1,
            schedule_id=schedule_id,
            assignments_snapshot=list(assignments),
            reason=reason,
        )
        self._history.append(version)
        logger.info(f"[Layer5-VersionManager] Versión {version.version} guardada: {reason}")
        return version

    def get_history(self, schedule_id: str) -> list[ScheduleVersion]:
        return [v for v in self._history if v.schedule_id == schedule_id]
