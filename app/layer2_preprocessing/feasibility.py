"""HAIA Agent — Capa 2: Detector de inviabilidad estructural antes de buscar."""

import logging

from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA Layer2-Feasibility]")


class FeasibilityDetector:
    """Detecta inviabilidad antes de iniciar la búsqueda exhaustiva."""

    def check(self, instance: SchedulingInstance) -> tuple[bool, list[str]]:
        issues: list[str] = []

        total_slots = len(instance.classrooms) * len(instance.timeslots)
        total_needed = sum(s.total_assignments_needed() for s in instance.subjects)

        if total_needed > total_slots:
            issues.append(
                f"Infactible: {total_needed} asignaciones > {total_slots} slots disponibles"
            )

        for s in instance.subjects:
            eligible = [
                c for c in instance.classrooms
                if c.capacity >= s.enrollment and c.satisfies_requirements(s.required_resources)
            ]
            if not eligible:
                issues.append(
                    f"Materia {s.code} no tiene salón elegible (enrollment={s.enrollment}, recursos={s.required_resources})"
                )

        if issues:
            logger.warning(f"[Layer2-Feasibility] {len(issues)} problemas detectados")
        return len(issues) == 0, issues
