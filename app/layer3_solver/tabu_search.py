"""
HAIA Agent — Capa 3: Tabu Search para asignación de salones universitarios.

BASADO EN:
    La Cruz, A., Herrera, L., Cortes, J., García-León, A., y Severeyn, E. (2024).
    "UniSchedApi: A comprehensive solution for university resource scheduling
    and methodology comparison."
    Transactions on Energy Systems and Engineering Applications, 5(2):633.
    DOI: 10.32397/tesea.vol5.n2.633

EXTENSIONES HAIA sobre el algoritmo original:
    1. Memoria de largo plazo: matriz freq[classroom][timeslot] que penaliza
       movimientos sobre slots frecuentemente usados (diversificación).
       La Cruz et al. (2024) usa solo lista tabú de tamaño fijo.
    2. Criterio de aspiración: acepta un movimiento tabú si el vecino supera
       el mejor score global, independientemente del tenure.
    3. Evaluación con U(A) multi-criterio (w1·ocup + w2·pref + w3·dist + w4·rec − λ·Pen)
       en lugar del objetivo mono-criterio del artículo original.
    4. max_iterations=500 (configurable): HAIA usa un límite bajo deliberadamente
       porque el Tabu Search produce una solución inicial de calidad media que
       el SA de la Capa 4 refina en profundidad. No replica los ciclos completos
       del artículo original, que no incluye post-optimización SA.
"""

from __future__ import annotations

import logging
import random
import time
from collections import defaultdict

from app.config import HAIAConfig
from app.domain.entities import Assignment, SchedulingInstance
from app.domain.constraints import get_active_constraints

logger = logging.getLogger("[HAIA Layer3-TabuSearch]")


class TabuSearchSolver:
    """
    Tabu Search con memoria de largo plazo y criterio de aspiración.
    Interface compatible con CSPBacktrackingSolver y MILPSolver.

    Algoritmo base: La Cruz et al. (2024), DOI: 10.32397/tesea.vol5.n2.633.
    Ver docstring del módulo para la lista completa de extensiones HAIA.
    """

    name = "tabu_search"

    def __init__(
        self,
        config: HAIAConfig,
        tabu_tenure: int = 10,
        max_iterations: int = 500,
        max_no_improve: int = 100,
    ) -> None:
        self.config = config
        self.tabu_tenure = tabu_tenure
        self.max_iterations = max_iterations
        self.max_no_improve = max_no_improve

    def solve(
        self,
        instance: SchedulingInstance,
        domains: dict[str, list[tuple[str, str]]],
    ) -> list[Assignment]:
        """Construye solución inicial con greedy y luego mejora con TS."""
        t0 = time.perf_counter()

        # Solución inicial: asignar al primer valor del dominio
        initial = self._greedy_initial(domains, instance)
        if not initial:
            logger.warning("[Layer3-TS] No se pudo construir solución inicial")
            return []

        current = dict(initial)
        best = dict(current)
        best_score = self._evaluate(best, instance)

        # Lista tabú: conjunto de (var, value) con contador de iteración de expiración
        tabu_list: dict[tuple[str, tuple[str, str]], int] = {}
        # Memoria de largo plazo: frecuencia de uso de (classroom, timeslot)
        frequency: dict[tuple[str, str], int] = defaultdict(int)
        for val in current.values():
            frequency[val] += 1

        no_improve = 0
        iter_count = 0

        logger.info(
            f"[Layer3-TS] Iniciando Tabu Search — {len(domains)} variables, "
            f"score_inicial={best_score:.4f}"
        )

        while iter_count < self.max_iterations and no_improve < self.max_no_improve:
            iter_count += 1

            # Limpiar entradas tabú expiradas
            tabu_list = {k: exp for k, exp in tabu_list.items() if exp > iter_count}

            # Generar vecinos: intercambiar asignación de 2 variables aleatorias
            neighbors = self._generate_neighbors(current, domains, instance, n=20)

            best_neighbor = None
            best_neighbor_score = float("-inf")

            for (var1, val1, var2, val2) in neighbors:
                move_key1 = (var1, val1)
                move_key2 = (var2, val2)

                is_tabu = move_key1 in tabu_list or move_key2 in tabu_list

                # Evaluar vecino
                candidate = dict(current)
                candidate[var1] = val1
                candidate[var2] = val2
                score = self._evaluate(candidate, instance)

                # Penalización por memoria de largo plazo
                freq_penalty = 0.01 * (frequency[val1] + frequency[val2])
                adjusted_score = score - freq_penalty

                # Criterio de aspiración: aceptar tabú si supera el mejor global
                if is_tabu and score <= best_score:
                    continue

                if adjusted_score > best_neighbor_score:
                    best_neighbor_score = adjusted_score
                    best_neighbor = (var1, val1, var2, val2, score)

            if best_neighbor is None:
                no_improve += 1
                continue

            var1, val1, var2, val2, score = best_neighbor
            current[var1] = val1
            current[var2] = val2

            # Actualizar lista tabú y frecuencia
            tabu_list[(var1, current.get(var1))] = iter_count + self.tabu_tenure
            tabu_list[(var2, current.get(var2))] = iter_count + self.tabu_tenure
            frequency[val1] += 1
            frequency[val2] += 1

            if score > best_score:
                best_score = score
                best = dict(current)
                no_improve = 0
                logger.debug(f"[Layer3-TS] iter={iter_count} nuevo mejor: {score:.4f}")
            else:
                no_improve += 1

        elapsed = time.perf_counter() - t0
        logger.info(
            f"[Layer3-TS] Completado — iter={iter_count}, best={best_score:.4f}, "
            f"tiempo={elapsed:.2f}s"
        )

        return self._dict_to_assignments(best)

    def _greedy_initial(
        self, domains: dict[str, list[tuple[str, str]]], instance: SchedulingInstance
    ) -> dict[str, tuple[str, str]] | None:
        """Construye solución inicial greedy respetando HC1 y HC2 (no double-booking)."""
        assignment: dict[str, tuple[str, str]] = {}
        used_classroom_slot: set[tuple[str, str]] = set()
        used_professor_slot: set[tuple[str, str]] = set()

        # Pre-build subject→professor map for fast lookup
        prof_map: dict[str, str | None] = {
            s.code: s.professor_code for s in instance.subjects
        }

        # Ordenar por tamaño de dominio (MRV)
        for var in sorted(domains, key=lambda v: len(domains[v])):
            subject_code = var.split("__")[0]
            prof_code = prof_map.get(subject_code)
            assigned = False
            for cls_code, ts_code in domains[var]:
                # HC1: classroom not double-booked
                if (cls_code, ts_code) in used_classroom_slot:
                    continue
                # HC2: professor not double-booked
                if prof_code and (prof_code, ts_code) in used_professor_slot:
                    continue
                assignment[var] = (cls_code, ts_code)
                used_classroom_slot.add((cls_code, ts_code))
                if prof_code:
                    used_professor_slot.add((prof_code, ts_code))
                assigned = True
                break
            if not assigned:
                return None
        return assignment

    def _evaluate(
        self,
        assignment: dict[str, tuple[str, str]],
        instance: SchedulingInstance,
    ) -> float:
        """Evaluación rápida basada en ocupación y preferencias (proxy de U(A))."""
        if not assignment:
            return 0.0

        w1 = self.config.w1_occupancy
        w2 = self.config.w2_preference
        score = 0.0

        for var, (cls_code, ts_code) in assignment.items():
            subject_code = var.split("__")[0]
            subject = next((s for s in instance.subjects if s.code == subject_code), None)
            classroom = next((c for c in instance.classrooms if c.code == cls_code), None)

            if subject and classroom:
                ocup = subject.enrollment / classroom.capacity
                pref = 0.5
                if subject.professor_code:
                    prof = next(
                        (p for p in instance.professors if p.code == subject.professor_code), None
                    )
                    if prof:
                        pref = prof.preference_for(ts_code)
                score += w1 * ocup + w2 * pref

        return score / len(assignment)

    def _prof_slot_map(
        self,
        current: dict[str, tuple[str, str]],
        instance: SchedulingInstance,
    ) -> dict[str, set[str]]:
        """Retorna {professor_code: {timeslot_codes...}} para el assignment actual."""
        prof_map: dict[str, str | None] = {s.code: s.professor_code for s in instance.subjects}
        result: dict[str, set[str]] = {}
        for var, (_, ts_code) in current.items():
            sub_code = var.split("__")[0]
            prof = prof_map.get(sub_code)
            if prof:
                result.setdefault(prof, set()).add(ts_code)
        return result

    def _generate_neighbors(
        self,
        current: dict[str, tuple[str, str]],
        domains: dict[str, list[tuple[str, str]]],
        instance: SchedulingInstance,
        n: int = 20,
    ) -> list[tuple[str, tuple[str, str], str, tuple[str, str]]]:
        """
        Genera n vecinos por intercambio de asignaciones entre dos variables.
        Respeta HC1 (no double-booking salón) y HC2 (no double-booking docente).
        """
        keys = list(current.keys())
        neighbors = []
        attempts = 0

        prof_map: dict[str, str | None] = {s.code: s.professor_code for s in instance.subjects}
        used_values = set(current.values())

        while len(neighbors) < n and attempts < n * 10:
            attempts += 1
            if len(keys) < 2:
                break

            var1, var2 = random.sample(keys, 2)
            val1 = current[var1]  # (cls, ts) of var1
            val2 = current[var2]  # (cls, ts) of var2
            sub1 = var1.split("__")[0]
            sub2 = var2.split("__")[0]
            prof1 = prof_map.get(sub1)
            prof2 = prof_map.get(sub2)

            # Pure swap: var1←val2, var2←val1
            if val2 in domains.get(var1, []) and val1 in domains.get(var2, []):
                # HC2 check: after swap, prof1 uses ts of val2, prof2 uses ts of val1
                ts1, ts2 = val1[1], val2[1]
                ps = self._prof_slot_map(current, instance)
                ok = True
                # prof1 moves from ts1 to ts2: check no OTHER var of prof1 already at ts2
                if prof1 and ts2 != ts1:
                    others = ps.get(prof1, set()) - {ts1}
                    if ts2 in others:
                        ok = False
                # prof2 moves from ts2 to ts1: check no OTHER var of prof2 already at ts1
                if ok and prof2 and ts1 != ts2:
                    others = ps.get(prof2, set()) - {ts2}
                    if ts1 in others:
                        ok = False
                if ok:
                    neighbors.append((var1, val2, var2, val1))
            else:
                # Free-slot move for var1 only (var2 unchanged)
                dom1 = domains.get(var1, [])
                if dom1:
                    free = [v for v in dom1 if v not in used_values or v == val1]
                    if free:
                        new_val1 = random.choice(free)
                        if new_val1 != val1:
                            # HC2 check for prof1
                            ts_new = new_val1[1]
                            ps = self._prof_slot_map(current, instance)
                            ok = True
                            if prof1:
                                others = ps.get(prof1, set()) - {val1[1]}
                                if ts_new in others:
                                    ok = False
                            if ok:
                                neighbors.append((var1, new_val1, var2, val2))

        return neighbors

    def _dict_to_assignments(
        self, assignment: dict[str, tuple[str, str]]
    ) -> list[Assignment]:
        result = []
        for key, (cls_code, ts_code) in assignment.items():
            parts = key.split("__")
            result.append(
                Assignment(
                    subject_code=parts[0],
                    classroom_code=cls_code,
                    timeslot_code=ts_code,
                    group_number=int(parts[1][1:]),
                    session_number=int(parts[2][1:]),
                )
            )
        return result
