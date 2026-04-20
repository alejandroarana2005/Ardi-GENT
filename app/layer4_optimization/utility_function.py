"""
HAIA Agent — Capa 4: Función de utilidad U(A) multi-criterio.

U(A) = w1·U_ocup(A) + w2·U_pref(A) + w3·U_dist(A) + w4·U_rec(A) − λ·Pen(A)

Componentes:
    U_ocup: (1/n) · Σ [enrollment(ci) / capacity(salon(ci))]
    U_pref: (1/n) · Σ pref(professor(ci), franja(ci))  donde pref ∈ [0,1]
    U_dist: 1 - variance(clases_por_franja) / max_variance
    U_rec:  (1/n) · Σ [|recursos_requeridos(ci)| / |recursos_disponibles(salon(ci))|]
    Pen:    Σ δ_k · violaciones_blanda_k(A)

Ref: Informe IEEE HAIA — función objetivo con w1=0.40, w2=0.25, w3=0.20, w4=0.15.
"""

from __future__ import annotations

import logging
from statistics import variance as stat_variance

from app.domain.entities import Assignment, SchedulingInstance
from app.domain.constraints import get_active_constraints

logger = logging.getLogger("[HAIA Layer4-UtilityFunction]")


class UtilityCalculator:
    """Calcula U(A) para un conjunto de asignaciones dada la instancia del problema."""

    def __init__(self, weights: dict[str, float]) -> None:
        self.w1 = weights.get("w1", 0.40)
        self.w2 = weights.get("w2", 0.25)
        self.w3 = weights.get("w3", 0.20)
        self.w4 = weights.get("w4", 0.15)
        self.lam = weights.get("lambda", 1.5)

    def compute(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> float:
        if not assignments:
            return 0.0

        u_ocup = self._u_occupancy(assignments, instance)
        u_pref = self._u_preference(assignments, instance)
        u_dist = self._u_distribution(assignments, instance)
        u_rec = self._u_resources(assignments, instance)
        penalty = self._penalty(assignments, instance)

        score = (
            self.w1 * u_ocup
            + self.w2 * u_pref
            + self.w3 * u_dist
            + self.w4 * u_rec
            - self.lam * penalty
        )

        logger.debug(
            f"[Layer4-U(A)] ocup={u_ocup:.3f} pref={u_pref:.3f} "
            f"dist={u_dist:.3f} rec={u_rec:.3f} pen={penalty:.3f} → U={score:.4f}"
        )
        return max(0.0, score)

    def compute_detailed(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> dict:
        if not assignments:
            return {
                "u_occupancy": 0.0, "u_preference": 0.0,
                "u_distribution": 0.0, "u_resources": 0.0,
                "penalty": 0.0, "total": 0.0,
                "sc_violations": {}, "weights_used": self._weights_dict(),
            }

        u_ocup = self._u_occupancy(assignments, instance)
        u_pref = self._u_preference(assignments, instance)
        u_dist = self._u_distribution(assignments, instance)
        u_rec = self._u_resources(assignments, instance)
        penalty, sc_violations = self._penalty_detailed(assignments, instance)
        total = max(0.0, self.w1*u_ocup + self.w2*u_pref + self.w3*u_dist + self.w4*u_rec - self.lam*penalty)

        return {
            "u_occupancy": u_ocup,
            "u_preference": u_pref,
            "u_distribution": u_dist,
            "u_resources": u_rec,
            "penalty": penalty,
            "total": total,
            "sc_violations": sc_violations,
            "weights_used": self._weights_dict(),
        }

    def _weights_dict(self) -> dict:
        return {"w1": self.w1, "w2": self.w2, "w3": self.w3, "w4": self.w4, "lambda": self.lam}

    def _u_occupancy(self, assignments: list[Assignment], instance: SchedulingInstance) -> float:
        """U_ocup = (1/n) · Σ enrollment(ci) / capacity(salon(ci))"""
        scores = []
        for a in assignments:
            subject = next((s for s in instance.subjects if s.code == a.subject_code), None)
            classroom = next((c for c in instance.classrooms if c.code == a.classroom_code), None)
            if subject and classroom and classroom.capacity > 0:
                scores.append(min(1.0, subject.enrollment / classroom.capacity))
        return sum(scores) / len(scores) if scores else 0.0

    def _u_preference(self, assignments: list[Assignment], instance: SchedulingInstance) -> float:
        """U_pref = (1/n) · Σ pref(professor(ci), franja(ci))"""
        scores = []
        for a in assignments:
            subject = next((s for s in instance.subjects if s.code == a.subject_code), None)
            if subject and subject.professor_code:
                prof = next(
                    (p for p in instance.professors if p.code == subject.professor_code), None
                )
                if prof:
                    scores.append(prof.preference_for(a.timeslot_code))
                else:
                    scores.append(0.5)
            else:
                scores.append(0.5)
        return sum(scores) / len(scores) if scores else 0.5

    def _u_distribution(self, assignments: list[Assignment], instance: SchedulingInstance) -> float:
        """U_dist = 1 - variance(clases_por_franja) / max_variance"""
        from collections import Counter
        counts = Counter(a.timeslot_code for a in assignments)

        # Asegurar que todas las franjas existan (con 0 si no hay clase)
        all_counts = [counts.get(ts.code, 0) for ts in instance.timeslots]

        if len(all_counts) < 2:
            return 1.0

        var = stat_variance(all_counts)
        # Máxima varianza teórica: todos en una franja
        n = len(assignments)
        m = len(instance.timeslots)
        max_var = (n * (1 - 1/m) ** 2 + (m - 1) * (n/m) ** 2) if m > 1 else 0
        if max_var == 0:
            return 1.0
        return max(0.0, 1.0 - var / max_var)

    def _u_resources(self, assignments: list[Assignment], instance: SchedulingInstance) -> float:
        """U_rec = (1/n) · Σ |req ∩ available| / |req|  (1.0 si materia sin recursos)"""
        scores = []
        for a in assignments:
            subject = next((s for s in instance.subjects if s.code == a.subject_code), None)
            classroom = next((c for c in instance.classrooms if c.code == a.classroom_code), None)
            if subject is None or classroom is None:
                scores.append(0.0)
                continue
            required = {r.resource_code for r in subject.required_resources}
            if not required:
                scores.append(1.0)
                continue
            available = {r.code for r in classroom.resources}
            scores.append(len(required & available) / len(required))
        return sum(scores) / len(scores) if scores else 0.0

    def _penalty(self, assignments: list[Assignment], instance: SchedulingInstance) -> float:
        """Pen = Σ δ_k · violaciones_blanda_k(A), normalizada a [0,1]."""
        penalty, _ = self._penalty_detailed(assignments, instance)
        return penalty

    def _penalty_detailed(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> tuple[float, dict[str, int]]:
        """Retorna (penalty_normalizada ∈ [0,1], dict conteos binarios por SC)."""
        soft_constraints = get_active_constraints("soft")
        n = len(assignments)
        if n == 0:
            return 0.0, {}

        total_weight = sum(getattr(c, "penalty_weight", 1.0) for c in soft_constraints)
        sc_counts: dict[str, int] = {}
        raw_penalty = 0.0

        for constraint in soft_constraints:
            violations = 0
            for a in assignments:
                p = constraint.penalty(a, assignments, instance)
                raw_penalty += p
                # Contar violación sólo si check() falla, no si penalty > 0.
                # SC1 devuelve penalty fraccional incluso cuando pref ≥ 0.5.
                if not constraint.check(a, assignments, instance):
                    violations += 1
            sc_counts[constraint.code] = violations

        # Normalizar: Pen ∈ [0, 1]  (raw ≤ n × total_weight por construcción)
        denom = n * total_weight
        penalty_norm = min(1.0, raw_penalty / denom) if denom > 0 else 0.0
        return penalty_norm, sc_counts
