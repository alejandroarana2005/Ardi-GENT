"""
HAIA Agent — Capa 5: Reparación local con k-vecindad.

Principio de Mínima Perturbación:
    U_repair(A') = U(A') − w_stab × |A' △ A_original| / |A_original|

Algoritmo:
    1. Aislar asignaciones afectadas → to_reassign
    2. Congelar el resto → frozen
    3. Construir dominios válidos para to_reassign (HC1-HC5 + restricción de evento)
    4. Backtracking sobre el subproblema
    5. Si falla: expandir con k-vecindad y reintentar
    6. Si sigue fallando: fallback a re-optimización completa
"""

from __future__ import annotations

import copy
import logging
import time
from collections import defaultdict

logger = logging.getLogger("[HAIA Layer5-Repair]")

W_STABILITY = 0.30  # penalización por cambio en U_repair


class RepairModule:
    """Reparación local de asignaciones afectadas por un evento dinámico."""

    def __init__(self, config) -> None:
        self.config = config
        self.k = getattr(config, "repair_neighborhood_k", 2)
        self.max_seconds = getattr(config, "repair_max_seconds", 30)

    # ── Entrada pública ────────────────────────────────────────────────────────

    def repair_local(
        self,
        current: list,
        affected: list,
        event,
        context: dict,
    ) -> list | None:
        """
        Repara las asignaciones afectadas manteniendo las demás congeladas.
        Retorna la lista completa de asignaciones reparadas, o None si falla.
        """
        t0 = time.perf_counter()
        instance = context["instance"]

        if not affected:
            # NEW_COURSE_ADDED: nothing to reassign from current
            return self._handle_new_course(current, event, context)

        affected_keys = {
            (a.subject_code, a.group_number, a.session_number) for a in affected
        }
        frozen = [
            a for a in current
            if (a.subject_code, a.group_number, a.session_number) not in affected_keys
        ]

        # ── Intento 1: solo reasignar las afectadas ────────────────────────────
        domains = self._build_constrained_domains(affected, event, instance, frozen)
        solution = self._solve_subproblem(affected, domains, frozen, instance, t0)
        if solution is not None:
            logger.info(
                f"[Layer5-Repair] Solución encontrada reasignando "
                f"{len(affected)} afectadas"
            )
            return self._score_and_return(frozen + solution, current, instance)

        # ── Intento 2: expandir con k-vecindad ────────────────────────────────
        if time.perf_counter() - t0 < self.max_seconds:
            k_neighbors = self._compute_k_neighborhood(affected, current, context)
            if k_neighbors:
                extended = list(affected) + k_neighbors
                ext_keys = {
                    (a.subject_code, a.group_number, a.session_number)
                    for a in extended
                }
                frozen_ext = [
                    a for a in current
                    if (a.subject_code, a.group_number, a.session_number) not in ext_keys
                ]
                domains_ext = self._build_constrained_domains(
                    extended, event, instance, frozen_ext
                )
                solution_ext = self._solve_subproblem(
                    extended, domains_ext, frozen_ext, instance, t0
                )
                if solution_ext is not None:
                    logger.info(
                        f"[Layer5-Repair] Solución con k-vecindad "
                        f"({len(extended)} reasignadas)"
                    )
                    return self._score_and_return(
                        frozen_ext + solution_ext, current, instance
                    )

        # ── Intento 3: fallback completo ──────────────────────────────────────
        logger.warning("[Layer5-Repair] Fallback: re-optimización completa")
        return self._fallback_full_reoptimize(current, event, context)

    # ── Construcción de dominios ───────────────────────────────────────────────

    def _build_constrained_domains(
        self,
        to_reassign: list,
        event,
        instance,
        frozen: list,
    ) -> dict:
        """
        Calcula (classroom, timeslot) válidos para cada asignación a reasignar.
        Aplica HC1 (no double-booking aula), HC2 (no double-booking docente),
        HC3 (capacidad), HC4 (recursos), HC5 (disponibilidad docente),
        más la restricción del evento.
        """
        prof_map = {s.code: s.professor_code for s in instance.subjects}
        subj_map = {s.code: s for s in instance.subjects}
        prof_entity_map = {p.code: p for p in instance.professors}

        # Conflictos ya fijados por los asignaciones congeladas
        used_cls_ts: set[tuple[str, str]] = {
            (a.classroom_code, a.timeslot_code) for a in frozen
        }
        used_prof_ts: dict[str, set[str]] = defaultdict(set)
        for a in frozen:
            prof = prof_map.get(a.subject_code)
            if prof:
                used_prof_ts[prof].add(a.timeslot_code)

        # Restricciones de evento
        blocked_classrooms: set[str] = set()
        blocked_timeslots: set[str] = set()
        blocked_professor: str | None = None

        etype = event.event_type
        payload = event.payload

        if etype == "CLASSROOM_UNAVAILABLE":
            blocked_classrooms.add(payload.get("classroom_code", ""))
        elif etype == "SLOT_BLOCKED":
            blocked_timeslots.add(payload.get("timeslot_code", ""))
        elif etype == "PROFESSOR_CANCELLED":
            blocked_professor = payload.get("professor_code")

        domains: dict[tuple, list[tuple[str, str]]] = {}

        for a in to_reassign:
            key = (a.subject_code, a.group_number, a.session_number)
            subject = subj_map.get(a.subject_code)
            if not subject:
                domains[key] = []
                continue

            prof_code = prof_map.get(a.subject_code)
            # If this professor is cancelled, we cannot reassign their courses
            # without removing the professor constraint — skip valid domain (empty)
            if blocked_professor and prof_code == blocked_professor:
                domains[key] = []
                continue

            prof_entity = prof_entity_map.get(prof_code) if prof_code else None

            valid: list[tuple[str, str]] = []
            for cls in instance.classrooms:
                if cls.code in blocked_classrooms:
                    continue
                if cls.capacity < subject.enrollment:
                    continue
                if not cls.satisfies_requirements(subject.required_resources):
                    continue

                for ts in instance.timeslots:
                    if ts.code in blocked_timeslots:
                        continue
                    if (cls.code, ts.code) in used_cls_ts:
                        continue
                    if prof_code and ts.code in used_prof_ts.get(prof_code, set()):
                        continue
                    if prof_entity and not prof_entity.is_available(ts.code):
                        continue
                    valid.append((cls.code, ts.code))

            domains[key] = valid

        return domains

    # ── Backtracking sobre el subproblema ─────────────────────────────────────

    def _solve_subproblem(
        self,
        to_reassign: list,
        domains: dict,
        frozen: list,
        instance,
        t0: float,
    ) -> list | None:
        """Backtracking simple sobre las asignaciones a reasignar."""
        from app.domain.entities import Assignment

        prof_map = {s.code: s.professor_code for s in instance.subjects}

        used_cls_ts: set[tuple[str, str]] = {
            (a.classroom_code, a.timeslot_code) for a in frozen
        }
        used_prof_ts: dict[str, set[str]] = defaultdict(set)
        for a in frozen:
            prof = prof_map.get(a.subject_code)
            if prof:
                used_prof_ts[prof].add(a.timeslot_code)

        assignments_list = list(to_reassign)
        solution: list[Assignment] = []

        def backtrack(idx: int) -> bool:
            if time.perf_counter() - t0 > self.max_seconds * 0.8:
                return False
            if idx == len(assignments_list):
                return True

            a = assignments_list[idx]
            key = (a.subject_code, a.group_number, a.session_number)
            prof_code = prof_map.get(a.subject_code)

            for cls_code, ts_code in domains.get(key, []):
                if (cls_code, ts_code) in used_cls_ts:
                    continue
                if prof_code and ts_code in used_prof_ts.get(prof_code, set()):
                    continue

                new_a = Assignment(
                    subject_code=a.subject_code,
                    classroom_code=cls_code,
                    timeslot_code=ts_code,
                    group_number=a.group_number,
                    session_number=a.session_number,
                )
                solution.append(new_a)
                used_cls_ts.add((cls_code, ts_code))
                if prof_code:
                    used_prof_ts[prof_code].add(ts_code)

                if backtrack(idx + 1):
                    return True

                solution.pop()
                used_cls_ts.discard((cls_code, ts_code))
                if prof_code:
                    used_prof_ts[prof_code].discard(ts_code)

            return False

        return solution if backtrack(0) else None

    # ── K-vecindad ────────────────────────────────────────────────────────────

    def _compute_k_neighborhood(
        self,
        affected: list,
        current: list,
        context: dict,
    ) -> list:
        """
        Retorna asignaciones de current que comparten salón, franja o docente
        con alguna de las afectadas (1-hop). Excluye las propias afectadas.
        """
        instance = context["instance"]
        prof_map = {s.code: s.professor_code for s in instance.subjects}

        affected_keys = {(a.subject_code, a.group_number, a.session_number) for a in affected}
        affected_classrooms = {a.classroom_code for a in affected}
        affected_timeslots = {a.timeslot_code for a in affected}
        affected_profs = {prof_map.get(a.subject_code) for a in affected} - {None}

        neighbors = []
        for a in current:
            key = (a.subject_code, a.group_number, a.session_number)
            if key in affected_keys:
                continue
            prof = prof_map.get(a.subject_code)
            if (
                a.classroom_code in affected_classrooms
                or a.timeslot_code in affected_timeslots
                or (prof and prof in affected_profs)
            ):
                neighbors.append(a)

        return neighbors

    # ── Caso especial: nuevo curso ─────────────────────────────────────────────

    def _handle_new_course(
        self,
        current: list,
        event,
        context: dict,
    ) -> list | None:
        """Asigna un nuevo curso al horario existente."""
        instance = context["instance"]
        subject_code = event.payload.get("subject_code", "")
        subject = next((s for s in instance.subjects if s.code == subject_code), None)
        if not subject:
            logger.warning(f"[Layer5-Repair] Materia {subject_code} no encontrada")
            return None

        from app.domain.entities import Assignment
        placeholder = Assignment(
            subject_code=subject.code,
            classroom_code="",
            timeslot_code="",
            group_number=1,
            session_number=1,
        )
        domains = self._build_constrained_domains([placeholder], event, instance, current)
        solution = self._solve_subproblem([placeholder], domains, current, instance, time.perf_counter())
        if solution is None:
            return None
        return self._score_and_return(current + solution, current, instance)

    # ── Fallback: re-optimización completa ────────────────────────────────────

    def _fallback_full_reoptimize(
        self,
        current: list,
        event,
        context: dict,
    ) -> list | None:
        instance = context.get("instance")
        config = context.get("config")
        if not instance or not config:
            return None
        try:
            from app.layer2_preprocessing.domain_filter import DomainFilter
            from app.layer2_preprocessing.ac3 import AC3Preprocessor
            from app.layer3_solver.solver_factory import SolverFactory

            reduced = DomainFilter().filter(instance)
            domains, feasible = AC3Preprocessor().run(instance, reduced)
            if not feasible:
                return None

            solver = SolverFactory(config=config).select(instance)
            assignments = solver.solve(instance, domains)
            if not assignments:
                return None
            return self._score_and_return(assignments, current, instance)
        except Exception as exc:
            logger.error(f"[Layer5-Repair] Fallback falló: {exc}")
            return None

    # ── Puntuación y estabilidad ───────────────────────────────────────────────

    def _score_and_return(
        self,
        repaired: list,
        original: list,
        instance,
    ) -> list:
        """Calcula U_repair = U(A') - w_stab × perturbation y lo asigna a los scores."""
        from app.layer4_optimization.utility_function import UtilityCalculator

        calc = UtilityCalculator(self.config.utility_weights)
        u_repaired = calc.compute(repaired, instance)

        orig_map = {
            (a.subject_code, a.group_number, a.session_number): (
                a.classroom_code, a.timeslot_code
            )
            for a in original
        }
        changed = sum(
            1 for a in repaired
            if orig_map.get((a.subject_code, a.group_number, a.session_number))
            != (a.classroom_code, a.timeslot_code)
        )
        n = max(len(original), 1)
        perturbation = changed / n
        u_repair = u_repaired - W_STABILITY * perturbation

        logger.info(
            f"[Layer5-Repair] U(A')={u_repaired:.4f}, "
            f"perturbación={perturbation:.1%}, "
            f"U_repair={u_repair:.4f}"
        )

        for a in repaired:
            a.utilidad_score = u_repair
        return repaired

    # ── Verificación HC completa (para validación post-repair) ─────────────────

    def _are_related(self, a, b, context: dict) -> bool:
        """True si dos asignaciones comparten salón, franja o docente."""
        instance = context["instance"]
        prof_map = {s.code: s.professor_code for s in instance.subjects}
        return (
            a.classroom_code == b.classroom_code
            or a.timeslot_code == b.timeslot_code
            or (
                prof_map.get(a.subject_code) is not None
                and prof_map.get(a.subject_code) == prof_map.get(b.subject_code)
            )
        )
