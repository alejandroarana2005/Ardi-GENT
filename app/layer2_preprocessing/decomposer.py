"""HAIA Agent — Capa 2: Descomposición jerárquica por facultad. Stub Fase 1."""

import logging

from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA Layer2-Decomposer]")


class HierarchicalDecomposer:
    """Divide la instancia en sub-instancias por facultad para escalar mejor. Fase 2."""

    def decompose(self, instance: SchedulingInstance) -> dict[str, SchedulingInstance]:
        faculties = {s.faculty for s in instance.subjects}
        result = {}
        for faculty in faculties:
            subjects = [s for s in instance.subjects if s.faculty == faculty]
            result[faculty] = SchedulingInstance(
                semester=instance.semester,
                subjects=subjects,
                classrooms=instance.classrooms,
                timeslots=instance.timeslots,
                professors=instance.professors,
                global_constraints=instance.global_constraints,
            )
        logger.info(f"[Layer2-Decomposer] {len(result)} sub-instancias por facultad")
        return result
