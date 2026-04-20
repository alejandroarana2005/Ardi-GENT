"""
HAIA Agent — Capa 2: Filtrado inicial de dominios.
Para cada curso, descarta salones con capacidad insuficiente o recursos faltantes
y franjas fuera de la disponibilidad del docente antes de ejecutar AC-3.
Reduce el espacio de búsqueda en O(n·m·p).

Reglas aplicadas:
  HC3 — D(salon): capacity(sj) >= enrollment(ci)
  HC4 — D(salon): recursos_requeridos(ci) ⊆ recursos(sj)
  HC5 — D(franja): franja ∈ disponibilidad(profesor asignado)
"""

import logging

from app.domain.entities import Classroom, Professor, SchedulingInstance, Subject, TimeSlot

logger = logging.getLogger("[HAIA Layer2-DomainFilter]")


class DomainFilter:
    """
    Filtra dominios por capacidad, recursos y disponibilidad docente antes de AC-3.
    Output: dict[subject_assignment_key → list[tuple[classroom_code, timeslot_code]]]
    """

    def filter(
        self, instance: SchedulingInstance
    ) -> dict[str, list[tuple[str, str]]]:
        """
        Para cada (materia, grupo, sesión), retorna las combinaciones
        (salón, franja) que satisfacen HC3, HC4 y HC5.
        Loggea el porcentaje de reducción por variable.
        """
        domains: dict[str, list[tuple[str, str]]] = {}
        prof_map: dict[str, Professor] = {p.code: p for p in instance.professors}
        total_before = 0
        total_after = 0

        for subject in instance.subjects:
            eligible_classrooms = self._eligible_classrooms(subject, instance.classrooms)
            eligible_timeslots = self._eligible_timeslots(
                subject, instance.timeslots, prof_map
            )

            for g in range(1, subject.groups + 1):
                for s in range(1, subject.weekly_subgroups + 1):
                    key = f"{subject.code}__g{g}__s{s}"

                    before = len(instance.classrooms) * len(instance.timeslots)
                    domain = [
                        (c.code, ts.code)
                        for c in eligible_classrooms
                        for ts in eligible_timeslots
                    ]
                    after = len(domain)
                    reduction = (1.0 - after / before) * 100 if before > 0 else 0.0

                    logger.info(
                        f"[Layer2-Filter] {key}: {before} → {after} pares "
                        f"({reduction:.1f}% reducción) "
                        f"[{len(eligible_classrooms)} salones × {len(eligible_timeslots)} franjas]"
                    )
                    domains[key] = domain
                    total_before += before
                    total_after += after

        overall = (1.0 - total_after / total_before) * 100 if total_before > 0 else 0.0
        logger.info(
            f"[Layer2-Filter] Total: {len(domains)} variables, "
            f"{total_after:,}/{total_before:,} pares tras filtro inicial "
            f"({overall:.1f}% reducción global)"
        )
        return domains

    # ── Filtros internos ──────────────────────────────────────────────────────

    def _eligible_classrooms(
        self, subject: Subject, classrooms: list[Classroom]
    ) -> list[Classroom]:
        """HC3 + HC4: capacidad suficiente Y recursos requeridos disponibles."""
        return [
            c for c in classrooms
            if c.capacity >= subject.enrollment
            and c.satisfies_requirements(subject.required_resources)
        ]

    def _eligible_timeslots(
        self,
        subject: Subject,
        timeslots: list[TimeSlot],
        prof_map: dict[str, Professor],
    ) -> list[TimeSlot]:
        """
        HC5: franja dentro de la disponibilidad del docente asignado.
        Si la materia no tiene docente asignado, o el docente no declara
        disponibilidad, se permiten todas las franjas.
        """
        if not subject.professor_code:
            return timeslots

        prof = prof_map.get(subject.professor_code)
        if prof is None or not prof.availability:
            return timeslots

        return [ts for ts in timeslots if ts.code in prof.availability]
