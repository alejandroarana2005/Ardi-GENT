"""
HAIA Agent — Capa 3: CSP Backtracking con Forward Checking + MRV + LCV.

Algoritmo:
  - MRV (Minimum Remaining Values): asignar primero la variable con dominio más pequeño
  - LCV (Least Constraining Value): ordenar valores por el que menos restringe vecinos
  - Forward Checking: tras asignar, propagar y detectar dominios vacíos

Criterio de uso: instancias con ≤ 150 asignaciones totales.
Ref: Russell & Norvig (2020) — Backtracking Search, pág. 220.
"""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from typing import Optional

from app.config import HAIAConfig
from app.domain.entities import Assignment, SchedulingInstance

logger = logging.getLogger("[HAIA Layer3-Backtracking]")


class CSPBacktrackingSolver:
    """
    Backtracking con MRV + LCV + Forward Checking.
    Interface compatible con MILPSolver y TabuSearchSolver.
    """

    name = "backtracking"

    def __init__(self, config: HAIAConfig) -> None:
        self.config = config

    def solve(
        self,
        instance: SchedulingInstance,
        domains: dict[str, list[tuple[str, str]]],
    ) -> list[Assignment]:
        """Retorna lista de Assignment o [] si no encuentra solución."""
        t0 = time.perf_counter()
        variables = list(domains.keys())
        assignment: dict[str, tuple[str, str]] = {}

        result = self._backtrack(assignment, variables, domains, instance)
        elapsed = time.perf_counter() - t0

        if result is None:
            logger.warning(f"[Layer3-BT] No se encontró solución en {elapsed:.2f}s")
            return []

        assignments = self._to_domain_assignments(result, instance)
        logger.info(
            f"[Layer3-BT] Solución encontrada — {len(assignments)} asignaciones en {elapsed:.2f}s"
        )
        return assignments

    def _backtrack(
        self,
        assignment: dict[str, tuple[str, str]],
        unassigned: list[str],
        domains: dict[str, list[tuple[str, str]]],
        instance: SchedulingInstance,
    ) -> Optional[dict[str, tuple[str, str]]]:
        if not unassigned:
            return assignment

        # MRV: seleccionar variable con dominio más pequeño
        var = min(unassigned, key=lambda v: len(domains[v]))
        remaining = [v for v in unassigned if v != var]

        # LCV: ordenar valores por el que menos restringe vecinos
        ordered_values = self._lcv_order(var, domains[var], remaining, domains, instance)

        for value in ordered_values:
            if self._is_consistent(var, value, assignment, instance):
                assignment[var] = value

                # Forward Checking: propagar restricciones
                reduced_domains = self._forward_check(var, value, remaining, domains, instance)

                if reduced_domains is not None:
                    result = self._backtrack(assignment, remaining, reduced_domains, instance)
                    if result is not None:
                        return result

                del assignment[var]

        return None

    def _is_consistent(
        self,
        var: str,
        value: tuple[str, str],
        assignment: dict[str, tuple[str, str]],
        instance: SchedulingInstance,
    ) -> bool:
        """Verifica HC1 y HC2 contra las asignaciones ya realizadas."""
        classroom, timeslot = value
        professor = self._get_professor(var, instance)

        for other_var, other_value in assignment.items():
            other_classroom, other_timeslot = other_value

            # HC1: mismo salón, misma franja
            if classroom == other_classroom and timeslot == other_timeslot:
                return False

            # HC2: mismo docente, misma franja
            if timeslot == other_timeslot and professor:
                other_prof = self._get_professor(other_var, instance)
                if other_prof and other_prof == professor:
                    return False

        return True

    def _forward_check(
        self,
        var: str,
        value: tuple[str, str],
        remaining: list[str],
        domains: dict[str, list[tuple[str, str]]],
        instance: SchedulingInstance,
    ) -> Optional[dict[str, list[tuple[str, str]]]]:
        """
        Propaga la asignación var=value a los dominios de variables no asignadas.
        Retorna None si algún dominio queda vacío (podado).
        """
        classroom, timeslot = value
        professor = self._get_professor(var, instance)
        new_domains = {k: list(v) for k, v in domains.items()}

        for other_var in remaining:
            other_prof = self._get_professor(other_var, instance)
            to_remove = []

            for other_value in new_domains[other_var]:
                other_cls, other_ts = other_value
                # HC1
                if other_cls == classroom and other_ts == timeslot:
                    to_remove.append(other_value)
                # HC2
                elif other_ts == timeslot and professor and other_prof == professor:
                    to_remove.append(other_value)

            for v in to_remove:
                new_domains[other_var].remove(v)

            if not new_domains[other_var]:
                return None  # Dominio vacío — podar

        return new_domains

    def _lcv_order(
        self,
        var: str,
        values: list[tuple[str, str]],
        remaining: list[str],
        domains: dict[str, list[tuple[str, str]]],
        instance: SchedulingInstance,
    ) -> list[tuple[str, str]]:
        """
        Ordena valores por el que menos restringe a las variables restantes.
        Heurística: contar cuántos valores eliminaría cada candidato en los vecinos.
        """
        def constraint_count(val: tuple[str, str]) -> int:
            cls, ts = val
            prof = self._get_professor(var, instance)
            count = 0
            for other_var in remaining:
                other_prof = self._get_professor(other_var, instance)
                for other_val in domains[other_var]:
                    other_cls, other_ts = other_val
                    if (other_cls == cls and other_ts == ts) or (
                        other_ts == ts and prof and other_prof == prof
                    ):
                        count += 1
            return count

        return sorted(values, key=constraint_count)

    def _get_professor(self, key: str, instance: SchedulingInstance) -> str | None:
        subject_code = key.split("__")[0]
        subject = next((s for s in instance.subjects if s.code == subject_code), None)
        return subject.professor_code if subject else None

    def _to_domain_assignments(
        self,
        result: dict[str, tuple[str, str]],
        instance: SchedulingInstance,
    ) -> list[Assignment]:
        assignments = []
        for key, (classroom_code, timeslot_code) in result.items():
            parts = key.split("__")
            subject_code = parts[0]
            group_number = int(parts[1][1:])   # "g1" → 1
            session_number = int(parts[2][1:]) # "s1" → 1
            assignments.append(
                Assignment(
                    subject_code=subject_code,
                    classroom_code=classroom_code,
                    timeslot_code=timeslot_code,
                    group_number=group_number,
                    session_number=session_number,
                )
            )
        return assignments
