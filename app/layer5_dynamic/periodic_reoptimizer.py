"""
HAIA Agent — Capa 5: Re-optimización periódica.

Después de N eventos dinámicos consecutivos, la utilidad acumulada puede
degradarse más allá del umbral aceptable. Este módulo dispara un ciclo
SA completo para recuperar la calidad del horario.

Triggers (OR):
    - events_count  >= EVENTS_THRESHOLD  (default 5)
    - |U_actual − U_raíz| > UTILITY_DROP_THRESHOLD (default 0.15)

Acción:
    - Cargar asignaciones del schedule actual.
    - Ejecutar SimulatedAnnealing sobre la instancia completa.
    - Guardar nueva versión etiquetada "periodic_reopt" con version_manager.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("[HAIA Layer5-PeriodicReopt]")

EVENTS_THRESHOLD = 5
UTILITY_DROP_THRESHOLD = 0.15


@dataclass
class ReoptimizationResult:
    """Resultado de una re-optimización periódica."""
    new_schedule_id: Optional[str]
    u_before: float
    u_after: float
    elapsed_seconds: float
    triggered_by: str      # "events_count" | "utility_drop" | "both" | "manual"
    events_count: int
    utility_drop: float


class PeriodicReoptimizer:
    """
    Re-optimización periódica completa de un horario degradado por
    reparaciones locales sucesivas.
    """

    def __init__(
        self,
        events_threshold: int = EVENTS_THRESHOLD,
        utility_drop_threshold: float = UTILITY_DROP_THRESHOLD,
    ) -> None:
        self.events_threshold = events_threshold
        self.utility_drop_threshold = utility_drop_threshold

    # ── API pública ───────────────────────────────────────────────────────────

    def should_trigger(self, schedule_id: str, db) -> tuple[bool, str]:
        """
        Retorna (should_run: bool, reason: str).
        reason puede ser "events_count", "utility_drop", "both" o "no".
        """
        from app.database.models import DynamicEventModel, ScheduleModel

        schedule = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            return False, "schedule_not_found"

        events_count = (
            db.query(DynamicEventModel)
            .filter(DynamicEventModel.schedule_id == schedule.id)
            .count()
        )

        root = self._find_root_schedule(schedule, db)
        utility_drop = root.utility_score - schedule.utility_score

        by_events = events_count >= self.events_threshold
        by_utility = utility_drop > self.utility_drop_threshold

        if by_events and by_utility:
            reason = "both"
        elif by_events:
            reason = "events_count"
        elif by_utility:
            reason = "utility_drop"
        else:
            reason = "no"

        trigger = reason != "no"
        logger.info(
            f"[Layer5-PeriodicReopt] schedule={schedule_id}: "
            f"events={events_count}, drop={utility_drop:.4f}, "
            f"trigger={trigger} ({reason})"
        )
        return trigger, reason

    def reoptimize(
        self,
        schedule_id: str,
        db,
        config,
    ) -> ReoptimizationResult:
        """
        Ejecuta SA completo sobre el schedule indicado y guarda nueva versión.
        Retorna ReoptimizationResult con métricas antes/después.
        """
        from app.database.models import AssignmentModel, ScheduleModel
        from app.domain.entities import Assignment
        from app.layer1_perception.data_loader import DataLoader
        from app.layer4_optimization.simulated_annealing import SimulatedAnnealing
        from app.layer4_optimization.utility_function import UtilityCalculator
        from app.layer5_dynamic.version_manager import VersionManager

        t0 = time.perf_counter()

        schedule = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            logger.error(f"[Layer5-PeriodicReopt] Schedule {schedule_id} no encontrado")
            return ReoptimizationResult(
                new_schedule_id=None, u_before=0.0, u_after=0.0,
                elapsed_seconds=0.0, triggered_by="error",
                events_count=0, utility_drop=0.0,
            )

        # Cargar instancia
        loader = DataLoader(db)
        try:
            instance, _ = loader.load_instance(schedule.semester)
        except Exception as exc:
            logger.error(f"[Layer5-PeriodicReopt] Error cargando instancia: {exc}")
            return ReoptimizationResult(
                new_schedule_id=None, u_before=schedule.utility_score, u_after=0.0,
                elapsed_seconds=0.0, triggered_by="error",
                events_count=0, utility_drop=0.0,
            )

        # Cargar asignaciones actuales
        orm_assignments = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.schedule_id == schedule.id)
            .all()
        )
        current: list[Assignment] = [
            Assignment(
                subject_code=a.subject_code,
                classroom_code=a.classroom_code,
                timeslot_code=a.timeslot_code,
                group_number=a.group_number,
                session_number=a.session_number,
                utilidad_score=a.utilidad_score,
            )
            for a in orm_assignments
        ]

        calc = UtilityCalculator(config.utility_weights)
        u_before = calc.compute(current, instance)

        # SA completo sin restricción de Mínima Perturbación
        sa = SimulatedAnnealing(config=config)
        optimized = sa.optimize(current, instance)

        u_after = calc.compute(optimized, instance)
        elapsed = time.perf_counter() - t0

        # Determinar trigger reason
        _, reason = self.should_trigger(schedule_id, db)
        if reason == "no":
            reason = "manual"

        # Guardar nueva versión
        new_sid = VersionManager().save_version(
            schedule_id=schedule_id,
            assignments=optimized,
            reason=f"periodic_reopt ({reason})",
            db=db,
            semester=schedule.semester,
            solver_used="simulated_annealing_periodic",
            utility_score=u_after,
        )

        logger.info(
            f"[Layer5-PeriodicReopt] Re-optimización completa — "
            f"U: {u_before:.4f} → {u_after:.4f} (+{u_after-u_before:+.4f}), "
            f"tiempo={elapsed:.2f}s, nueva_versión={new_sid}"
        )

        return ReoptimizationResult(
            new_schedule_id=new_sid,
            u_before=u_before,
            u_after=u_after,
            elapsed_seconds=elapsed,
            triggered_by=reason,
            events_count=0,
            utility_drop=u_before - u_after if u_before > u_after else 0.0,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_root_schedule(self, schedule, db):
        """Sube por la cadena parent_schedule_id hasta el schedule raíz."""
        from app.database.models import ScheduleModel

        current = schedule
        visited: set[str] = {current.schedule_id}

        while current.parent_schedule_id:
            parent = (
                db.query(ScheduleModel)
                .filter(ScheduleModel.schedule_id == current.parent_schedule_id)
                .first()
            )
            if parent is None or parent.schedule_id in visited:
                break
            visited.add(parent.schedule_id)
            current = parent

        return current
