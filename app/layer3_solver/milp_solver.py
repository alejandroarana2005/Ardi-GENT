"""
HAIA Agent — Capa 3: Solver MILP con OR-Tools CP-SAT.

Variables de decisión:
    x[i][j][k] = 1 si el curso i va al salón j en la franja k

Restricciones:
    R1: Σ_j Σ_k x[i][j][k] = 1  ∀ curso i  (asignado exactamente una vez)
    R2: Σ_i x[i][j][k] ≤ 1      ∀ j, k     (no double-booking salón)
    R3: x[i][j][k] = 0 si capacity(j) < enrollment(i)
    R4: x[i][j][k] = 0 si resources(i) ⊄ resources(j)
    R5: Σ_i x[i][j][k] ≤ 1 ∀ docente p, franja k  (no double-booking docente)

Función objetivo: maximizar Σ x[i][j][k] · [w1·ocup(i,j) + w2·pref(i,k)]
"""

from __future__ import annotations

import logging
import time

from app.config import HAIAConfig
from app.domain.entities import Assignment, SchedulingInstance

logger = logging.getLogger("[HAIA Layer3-MILP]")


class MILPSolver:
    """
    Solver MILP usando OR-Tools CP-SAT.
    Interface compatible con CSPBacktrackingSolver.
    """

    name = "milp"

    def __init__(self, config: HAIAConfig) -> None:
        self.config = config

    def solve(
        self,
        instance: SchedulingInstance,
        domains: dict[str, list[tuple[str, str]]],
    ) -> list[Assignment]:
        try:
            from ortools.sat.python import cp_model
        except ImportError:
            logger.error("[Layer3-MILP] ortools no instalado — fallback a Backtracking")
            from app.layer3_solver.csp_backtracking import CSPBacktrackingSolver
            return CSPBacktrackingSolver(self.config).solve(instance, domains)

        t0 = time.perf_counter()
        model = cp_model.CpModel()

        classrooms = instance.classrooms
        timeslots = instance.timeslots

        # Índices
        cls_idx = {c.code: i for i, c in enumerate(classrooms)}
        ts_idx = {t.code: i for i, t in enumerate(timeslots)}

        # Construir lista de variables: (key, classroom_code, timeslot_code)
        variables: dict[tuple[str, str, str], cp_model.IntVar] = {}
        var_keys = list(domains.keys())

        for key in var_keys:
            subject_code = key.split("__")[0]
            subject = next(s for s in instance.subjects if s.code == subject_code)
            for (cls_code, ts_code) in domains[key]:
                var = model.NewBoolVar(f"x_{key}_{cls_code}_{ts_code}")
                variables[(key, cls_code, ts_code)] = var

        # R1: Cada curso asignado exactamente una vez
        for key in var_keys:
            course_vars = [v for (k, c, t), v in variables.items() if k == key]
            if course_vars:
                model.Add(sum(course_vars) == 1)

        # R2: No double-booking de salones
        for cls in classrooms:
            for ts in timeslots:
                slot_vars = [
                    v for (k, c, t), v in variables.items()
                    if c == cls.code and t == ts.code
                ]
                if slot_vars:
                    model.Add(sum(slot_vars) <= 1)

        # R5: No double-booking de docentes
        prof_map: dict[str, list[str]] = {}
        for s in instance.subjects:
            if s.professor_code:
                for g in range(1, s.groups + 1):
                    for sess in range(1, s.weekly_subgroups + 1):
                        key = f"{s.code}__g{g}__s{sess}"
                        prof_map.setdefault(s.professor_code, []).append(key)

        for prof_code, keys in prof_map.items():
            for ts in timeslots:
                prof_slot_vars = [
                    v for (k, c, t), v in variables.items()
                    if k in keys and t == ts.code
                ]
                if prof_slot_vars:
                    model.Add(sum(prof_slot_vars) <= 1)

        # R3: capacidad de aula (informe IEEE sección II.C)
        # Redundante si domain_filter ya filtró dominios, pero lo afirmamos
        # explícitamente para documentar las 5 HC y como fail-safe.
        for (key, cls_code, ts_code), var in variables.items():
            subject_code = key.split("__")[0]
            subject = next(s for s in instance.subjects if s.code == subject_code)
            classroom = next(c for c in classrooms if c.code == cls_code)
            if classroom.capacity < subject.enrollment:
                model.Add(var == 0)

        # R4: recursos requeridos disponibles (informe IEEE sección II.C)
        for (key, cls_code, ts_code), var in variables.items():
            subject_code = key.split("__")[0]
            subject = next(s for s in instance.subjects if s.code == subject_code)
            classroom = next(c for c in classrooms if c.code == cls_code)
            required = {r.resource_code for r in subject.required_resources}
            available = {r.code for r in classroom.resources}
            if not required.issubset(available):
                model.Add(var == 0)

        # Función objetivo: maximizar ocupación + preferencia docente
        w1 = self.config.w1_occupancy
        w2 = self.config.w2_preference
        objective_terms = []

        for (key, cls_code, ts_code), var in variables.items():
            subject_code = key.split("__")[0]
            subject = next((s for s in instance.subjects if s.code == subject_code), None)
            classroom = next((c for c in classrooms if c.code == cls_code), None)

            if subject and classroom:
                ocup = subject.enrollment / classroom.capacity
                pref = 0.5
                if subject.professor_code:
                    prof = next(
                        (p for p in instance.professors if p.code == subject.professor_code), None
                    )
                    if prof:
                        pref = prof.preference_for(ts_code)

                score = int((w1 * ocup + w2 * pref) * 1000)
                objective_terms.append(score * var)

        if objective_terms:
            model.Maximize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        status = solver.Solve(model)

        elapsed = time.perf_counter() - t0

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.warning(f"[Layer3-MILP] Sin solución en {elapsed:.2f}s (status={status})")
            return []

        assignments = []
        for (key, cls_code, ts_code), var in variables.items():
            if solver.Value(var) == 1:
                parts = key.split("__")
                assignments.append(
                    Assignment(
                        subject_code=parts[0],
                        classroom_code=cls_code,
                        timeslot_code=ts_code,
                        group_number=int(parts[1][1:]),
                        session_number=int(parts[2][1:]),
                    )
                )

        logger.info(
            f"[Layer3-MILP] {len(assignments)} asignaciones en {elapsed:.2f}s "
            f"(obj={solver.ObjectiveValue():.2f})"
        )
        return assignments
