"""
HAIA Agent — Capa 4: Post-optimización con Recocido Simulado (SA).

Parámetros por defecto (configurables en .env):
    T0 = 1.0    — calibrado para deltas U(A) de 0.01-0.05
    T_min = 0.001
    α = 0.98    — enfriamiento lento para exploración en T medias
    iteraciones_por_T = 100

Operadores de vecindad:
    70%  _swap_two_assignments        — intercambio aleatorio de sala+franja
    30%  _move_to_spread_professor_hours — ataca SC4 (>3h/día por docente)

Mecanismos de control:
    - Contadores separados: invalid_neighbors vs thermodynamic_accepted
    - Partial HC check: solo verifica indices modificados — O(k·n) vs O(n²)
    - Early stopping: iter_since_best > 5,000 AND T < 0.1
    - Reheating:      iter_since_best > 3,000 AND reheating_count < 2 → T = T0/2
"""

from __future__ import annotations

import logging
import math
import random
import time
from collections import defaultdict

from app.config import HAIAConfig
from app.domain.constraints import get_active_constraints
from app.domain.entities import Assignment, SchedulingInstance

logger = logging.getLogger("[HAIA Layer4-SA]")


class SimulatedAnnealing:
    """Recocido Simulado sobre solución factible de la Capa 3."""

    def __init__(self, config: HAIAConfig) -> None:
        self.T0 = config.sa_t0
        self.T_min = config.sa_t_min
        self.alpha = config.sa_alpha
        self.iters_per_T = config.sa_iters_per_t
        self.weights = config.utility_weights

    def optimize(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> list[Assignment]:
        if not assignments:
            return assignments

        from app.layer4_optimization.utility_function import UtilityCalculator
        calc = UtilityCalculator(self.weights)

        current = list(assignments)
        current_score = calc.compute(current, instance)
        best = list(current)
        best_score = current_score
        initial_score = current_score

        T = self.T0

        # ── Contadores separados ─────────────────────────────────────────────
        total_iters = 0
        invalid_neighbors = 0        # rechazados por HC antes de Boltzmann
        valid_evaluated = 0          # pasaron HC, evaluados termodinámicamente
        thermodynamic_accepted = 0   # de valid_evaluated, cuántos aceptados

        # ── Control de estancamiento y reheating ─────────────────────────────
        iter_since_best = 0
        max_stagnation = 0
        reheating_count = 0

        t0 = time.perf_counter()
        hard_constraints = get_active_constraints("hard")

        logger.info(
            f"[Layer4-SA] Iniciando SA — T0={self.T0}, α={self.alpha}, "
            f"iters_per_T={self.iters_per_T}, score_inicial={current_score:.4f}"
        )

        while T > self.T_min:
            for _ in range(self.iters_per_T):
                total_iters += 1
                iter_since_best += 1
                max_stagnation = max(max_stagnation, iter_since_best)

                result = self._generate_neighbor(current, instance)
                if result is None:
                    invalid_neighbors += 1
                    continue

                neighbor, modified_indices = result

                # Partial HC check: sólo los assignments modificados
                if not self._hard_check_modified(
                    modified_indices, neighbor, instance, hard_constraints
                ):
                    invalid_neighbors += 1
                    continue

                valid_evaluated += 1
                neighbor_score = calc.compute(neighbor, instance)
                delta = neighbor_score - current_score

                if delta > 0 or random.random() < math.exp(delta / T):
                    current = neighbor
                    current_score = neighbor_score
                    thermodynamic_accepted += 1

                    if current_score > best_score:
                        best = list(current)
                        best_score = current_score
                        iter_since_best = 0

            T *= self.alpha

            # Reheating: escapar de óptimos locales (máx 2 veces).
            # T = T0/5: lleva la temperatura a zona de búsqueda semi-dirigida,
            # sin volver al random walk de T0 completo.
            if iter_since_best > 2000 and reheating_count < 2:
                T = self.T0 / 5
                iter_since_best = 0
                reheating_count += 1
                logger.info(
                    f"[Layer4-SA] Reheating #{reheating_count}: "
                    f"T={T:.5f}, score_actual={current_score:.4f}"
                )

            # Early stopping: zona muy fría donde la aceptación es < 5%
            # y el estancamiento lleva más de 1,500 iteraciones sin mejora.
            if iter_since_best > 1500 and T < self.T_min * 5:
                logger.info(
                    f"[Layer4-SA] Early stopping: {iter_since_best:,} iter sin mejora, "
                    f"T={T:.5f}"
                )
                break

        elapsed = time.perf_counter() - t0

        # ── Métricas finales ─────────────────────────────────────────────────
        thermo_rate = (
            thermodynamic_accepted / valid_evaluated * 100
            if valid_evaluated > 0 else 0.0
        )
        hc_rejection_rate = (
            invalid_neighbors / total_iters * 100
            if total_iters > 0 else 0.0
        )
        delta_abs = best_score - initial_score
        delta_pct = delta_abs / initial_score * 100 if initial_score > 0 else 0.0

        logger.info("[Layer4-SA] === Resumen de Post-Optimización ===")
        logger.info(
            f"[Layer4-SA] U_inicial: {initial_score:.4f} → U_final: {best_score:.4f} "
            f"(Δ: {delta_abs:+.4f} / {delta_pct:+.1f}%)"
        )
        logger.info(
            f"[Layer4-SA] Iteraciones: {total_iters:,} | "
            f"HC-inválidos: {invalid_neighbors:,} ({hc_rejection_rate:.1f}%) | "
            f"Evaluados: {valid_evaluated:,}"
        )
        logger.info(
            f"[Layer4-SA] acceptance_rate (termodinámico): "
            f"{thermodynamic_accepted:,} / {valid_evaluated:,} = {thermo_rate:.1f}%"
        )
        logger.info(
            f"[Layer4-SA] T final: {T:.4f} | Reheatings: {reheating_count} | "
            f"Max estancamiento: {max_stagnation:,} iter"
        )
        logger.info(f"[Layer4-SA] Tiempo total: {elapsed:.2f}s")

        for a in best:
            a.utilidad_score = best_score

        return best

    # ── Operadores de vecindad ─────────────────────────────────────────────────

    def _generate_neighbor(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> tuple[list[Assignment], list[int]] | None:
        """30% SC4-spread, 70% swap aleatorio."""
        if random.random() < 0.3:
            return self._move_to_spread_professor_hours(assignments, instance)
        return self._swap_two_assignments(assignments, instance)

    def _swap_two_assignments(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> tuple[list[Assignment], list[int]] | None:
        """Intercambia sala+franja entre dos asignaciones aleatorias."""
        if len(assignments) < 2:
            return None

        idx1, idx2 = random.sample(range(len(assignments)), 2)
        a1, a2 = assignments[idx1], assignments[idx2]

        neighbor = list(assignments)
        neighbor[idx1] = Assignment(
            subject_code=a1.subject_code,
            classroom_code=a2.classroom_code,
            timeslot_code=a2.timeslot_code,
            group_number=a1.group_number,
            session_number=a1.session_number,
        )
        neighbor[idx2] = Assignment(
            subject_code=a2.subject_code,
            classroom_code=a1.classroom_code,
            timeslot_code=a1.timeslot_code,
            group_number=a2.group_number,
            session_number=a2.session_number,
        )
        return neighbor, [idx1, idx2]

    def _move_to_spread_professor_hours(
        self, assignments: list[Assignment], instance: SchedulingInstance
    ) -> tuple[list[Assignment], list[int]] | None:
        """
        Operador SC4: detecta un docente con >3h en un mismo día y mueve
        una de sus asignaciones a un día distinto, manteniendo el salón.
        """
        prof_map = {s.code: s.professor_code for s in instance.subjects}
        ts_map = {ts.code: ts for ts in instance.timeslots}

        # Agrupar índices por (profesor, día)
        prof_day: dict[tuple[str, str], list[int]] = defaultdict(list)
        for i, a in enumerate(assignments):
            prof = prof_map.get(a.subject_code)
            ts = ts_map.get(a.timeslot_code)
            if prof and ts:
                prof_day[(prof, ts.day)].append(i)

        # Candidatos: grupos donde el docente supera 3h ese día
        candidates: list[int] = []
        for (_, _), indices in prof_day.items():
            total_hours = sum(
                ts_map[assignments[i].timeslot_code].duration
                for i in indices
                if assignments[i].timeslot_code in ts_map
            )
            if total_hours > 3:
                candidates.extend(indices)

        if not candidates:
            return self._swap_two_assignments(assignments, instance)

        idx = random.choice(candidates)
        a = assignments[idx]
        current_ts = ts_map.get(a.timeslot_code)
        if not current_ts:
            return None

        prof_code = prof_map.get(a.subject_code)

        # Franjas ya ocupadas por este profesor (HC2)
        used_prof_slots = {
            assignments[i].timeslot_code
            for i in range(len(assignments))
            if i != idx and prof_map.get(assignments[i].subject_code) == prof_code
        }
        # Pares (sala, franja) ya usados por otros (HC1)
        used_cls_ts = {
            (assignments[i].classroom_code, assignments[i].timeslot_code)
            for i in range(len(assignments))
            if i != idx
        }

        # HC5: disponibilidad real del docente en la nueva franja
        prof_entity = next(
            (p for p in instance.professors if p.code == prof_code), None
        ) if prof_code else None

        # Franja libre en un día distinto al actual, respetando HC1, HC2 y HC5
        candidate_ts = [
            ts for ts in instance.timeslots
            if ts.day != current_ts.day
            and ts.code not in used_prof_slots
            and (a.classroom_code, ts.code) not in used_cls_ts
            and (prof_entity is None or prof_entity.is_available(ts.code))
        ]

        if not candidate_ts:
            return self._swap_two_assignments(assignments, instance)

        new_ts = random.choice(candidate_ts)
        neighbor = list(assignments)
        neighbor[idx] = Assignment(
            subject_code=a.subject_code,
            classroom_code=a.classroom_code,
            timeslot_code=new_ts.code,
            group_number=a.group_number,
            session_number=a.session_number,
        )
        return neighbor, [idx]

    # ── Verificación HC ────────────────────────────────────────────────────────

    def _hard_check_modified(
        self,
        modified_indices: list[int],
        assignments: list[Assignment],
        instance: SchedulingInstance,
        hard_constraints,
    ) -> bool:
        """
        Verifica HC sólo en los assignments modificados.
        O(k·n) en lugar de O(k·n²) — k = |modified_indices| (1 o 2).
        """
        for idx in modified_indices:
            a = assignments[idx]
            for constraint in hard_constraints:
                if not constraint.check(a, assignments, instance):
                    return False
        return True

    def _all_hard_satisfied(
        self,
        assignments: list[Assignment],
        instance: SchedulingInstance,
        hard_constraints,
    ) -> bool:
        """Verificación completa (usado en validación final si se necesita)."""
        for constraint in hard_constraints:
            for a in assignments:
                if not constraint.check(a, assignments, instance):
                    return False
        return True
