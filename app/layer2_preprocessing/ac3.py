"""
HAIA Agent — Capa 2: Algoritmo AC-3 (Arc Consistency 3).
Reduce dominios de variables CSP antes de iniciar la búsqueda.

El grafo de restricciones tiene:
  - Nodos: claves de asignación  (subject__gN__sN)
  - Aristas: pares que comparten restricción HC1 (salón) o HC2 (docente) en la misma franja

Complejidad: O(e · d³) donde e = aristas, d = tamaño de dominio más grande.
Ref: Russell & Norvig (2020) — AC-3, pág. 186.
"""

from __future__ import annotations

import logging
from collections import deque

from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA Layer2-AC3]")


class AC3Preprocessor:
    """
    Implementación estándar de AC-3 para el CSP de asignación de salones.

    Input:  instance + dominios iniciales de DomainFilter
    Output: dominios reducidos, is_feasible (False si algún dominio queda vacío)
    """

    def run(
        self,
        instance: SchedulingInstance,
        domains: dict[str, list[tuple[str, str]]],
    ) -> tuple[dict[str, list[tuple[str, str]]], bool]:
        """
        Ejecuta AC-3 sobre el CSP.
        Retorna (reduced_domains, is_feasible).
        """
        domains = {k: list(v) for k, v in domains.items()}  # copia mutable

        # Pre-check: dominio vacío antes de empezar → infactible directo
        for var, dom in domains.items():
            if len(dom) == 0:
                logger.warning(f"[Layer2-AC3] Dominio ya vacío para {var} antes de iniciar")
                return domains, False

        # Construir aristas del grafo de restricciones
        arcs = self._build_arcs(instance, domains)
        queue: deque[tuple[str, str]] = deque(arcs)

        initial_total = sum(len(d) for d in domains.values())
        logger.info(
            f"[Layer2-AC3] Iniciando AC-3 — {len(domains)} variables, "
            f"{len(arcs)} arcos, {initial_total:,} valores iniciales"
        )

        while queue:
            xi, xj = queue.popleft()
            if xi not in domains or xj not in domains:
                continue

            removed = self._revise(xi, xj, domains, instance)
            if removed:
                if len(domains[xi]) == 0:
                    logger.warning(f"[Layer2-AC3] Dominio vacío para {xi} — infactible")
                    return domains, False
                # Añadir arcos vecinos de xi (excepto xj)
                neighbors = [arc[0] for arc in arcs if arc[1] == xi and arc[0] != xj]
                for xk in neighbors:
                    queue.append((xk, xi))

        final_total = sum(len(d) for d in domains.values())
        reduction = (1 - final_total / initial_total) * 100 if initial_total > 0 else 0
        logger.info(
            f"[Layer2-AC3] AC-3 completado — {final_total:,} valores restantes "
            f"({reduction:.1f}% reducción)"
        )
        return domains, True

    def _revise(
        self,
        xi: str,
        xj: str,
        domains: dict[str, list[tuple[str, str]]],
        instance: SchedulingInstance,
    ) -> bool:
        """
        Elimina valores de domain[xi] que no tienen soporte en domain[xj].
        Un valor (c_i, t) de xi tiene soporte en xj si existe (c_j, t') en domain[xj]
        que sea consistente con él según las HC binarias.
        """
        revised = False
        to_remove = []

        for value_i in domains[xi]:
            # Buscar al menos un valor en xj consistente con value_i
            has_support = any(
                self._consistent(xi, value_i, xj, value_j, instance)
                for value_j in domains[xj]
            )
            if not has_support:
                to_remove.append(value_i)
                revised = True

        for v in to_remove:
            domains[xi].remove(v)

        return revised

    def _consistent(
        self,
        xi: str,
        vi: tuple[str, str],
        xj: str,
        vj: tuple[str, str],
        instance: SchedulingInstance,
    ) -> bool:
        """
        Verifica HC1 y HC2 entre dos asignaciones candidatas.
        HC1: no mismo salón en misma franja.
        HC2: no mismo docente en misma franja.
        """
        classroom_i, timeslot_i = vi
        classroom_j, timeslot_j = vj

        # HC1: mismo salón, misma franja → conflicto
        if classroom_i == classroom_j and timeslot_i == timeslot_j:
            return False

        # HC2: mismo docente, misma franja → conflicto
        if timeslot_i == timeslot_j:
            prof_i = self._get_professor(xi, instance)
            prof_j = self._get_professor(xj, instance)
            if prof_i and prof_j and prof_i == prof_j:
                return False

        return True

    def _build_arcs(
        self,
        instance: SchedulingInstance,
        domains: dict[str, list[tuple[str, str]]],
    ) -> list[tuple[str, str]]:
        """
        Construye el conjunto de arcos del grafo de restricciones.
        Dos variables están conectadas si comparten restricción HC1 o HC2.
        """
        keys = list(domains.keys())
        arcs = []
        for i, ki in enumerate(keys):
            for kj in keys[i + 1:]:
                if self._shares_constraint(ki, kj, instance):
                    arcs.append((ki, kj))
                    arcs.append((kj, ki))
        return arcs

    def _shares_constraint(
        self, ki: str, kj: str, instance: SchedulingInstance
    ) -> bool:
        """
        Dos variables comparten restricción si pueden generar HC1 (mismo salón disponible)
        o HC2 (mismo docente). La verificación real se hace en _consistent.
        """
        # Siempre conectar — AC-3 filtrará los valores inconsistentes
        # Optimización futura: conectar solo variables con overlap de dominio
        return True

    def _get_professor(self, key: str, instance: SchedulingInstance) -> str | None:
        subject_code = key.split("__")[0]
        subject = next(
            (s for s in instance.subjects if s.code == subject_code), None
        )
        return subject.professor_code if subject else None
