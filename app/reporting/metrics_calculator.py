"""HAIA Agent — Reporting: Calculadora de métricas de un horario."""

import logging

from app.api.schemas import MetricsResponse
from app.domain.entities import Assignment, SchedulingInstance
from app.domain.constraints import get_active_constraints
from app.layer4_optimization.utility_function import UtilityCalculator
from app.config import settings

logger = logging.getLogger("[HAIA Reporting-Metrics]")


class MetricsCalculator:
    def compute(
        self,
        schedule_id: str,
        assignments: list[Assignment],
        instance: SchedulingInstance,
    ) -> MetricsResponse:
        calc = UtilityCalculator(settings.utility_weights)
        detail = calc.compute_detailed(assignments, instance)

        hard_violations = 0
        soft_violations = 0
        hard_constraints = get_active_constraints("hard")
        soft_constraints = get_active_constraints("soft")

        for constraint in hard_constraints:
            for a in assignments:
                if not constraint.check(a, assignments, instance):
                    hard_violations += 1

        for constraint in soft_constraints:
            for a in assignments:
                if not constraint.check(a, assignments, instance):
                    soft_violations += 1

        return MetricsResponse(
            schedule_id=schedule_id,
            utility_score=detail["total"],
            u_occupancy=detail["u_occupancy"],
            u_preference=detail["u_preference"],
            u_distribution=detail["u_distribution"],
            u_resources=detail["u_resources"],
            penalty=detail["penalty"],
            total_assignments=len(assignments),
            feasible_assignments=len(assignments) - hard_violations,
            hard_constraint_violations=hard_violations,
            soft_constraint_violations=soft_violations,
            avg_occupancy_ratio=detail["u_occupancy"],
            weights_used=detail.get("weights_used", {}),
            soft_constraint_counts=detail.get("sc_violations", {}),
        )
