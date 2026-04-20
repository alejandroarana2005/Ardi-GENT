"""HAIA Agent — Reporting: Detector de HC violadas en O(n²)."""

import logging

from app.domain.entities import Assignment, SchedulingInstance
from app.domain.constraints import get_active_constraints

logger = logging.getLogger("[HAIA Reporting-ConflictDetector]")


class ConflictDetector:
    """Detecta violaciones de Hard Constraints en un conjunto de asignaciones."""

    def detect(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> list[dict]:
        conflicts = []
        hard_constraints = get_active_constraints("hard")

        for constraint in hard_constraints:
            for a in assignments:
                if not constraint.check(a, assignments, instance):
                    conflicts.append({
                        "constraint_code": constraint.code,
                        "constraint_name": constraint.name,
                        "assignment": str(a),
                    })

        logger.info(f"[Reporting] {len(conflicts)} conflictos HC detectados")
        return conflicts
