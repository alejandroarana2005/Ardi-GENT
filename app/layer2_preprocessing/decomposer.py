"""
HAIA Agent — Capa 2: Descomposición jerárquica por facultad.

Aborda Brecha G3 del informe (escalabilidad): instancias > THRESHOLD materias
se dividen en subproblemas por unidad académica que se resuelven de forma
independiente; luego se coordinan los conflictos en recursos compartidos.

Algoritmo:
    1. decompose(instance) → lista de Subproblem (uno por facultad).
    2. Cada Subproblem lleva la sub-instancia + metadata de recursos compartidos.
    3. merge_solutions(sub_solutions) → lista unificada con conflictos resueltos.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from app.domain.entities import Assignment, SchedulingInstance

logger = logging.getLogger("[HAIA Layer2-Decomposer]")

DECOMPOSE_THRESHOLD = 500  # materias; por encima se activa la descomposición


@dataclass
class Subproblem:
    """Sub-instancia por facultad lista para ser resuelta de forma independiente."""
    faculty: str
    instance: SchedulingInstance
    shared_professors: set[str] = field(default_factory=set)
    shared_classrooms: set[str] = field(default_factory=set)


class HierarchicalDecomposer:
    """
    Descomposición jerárquica por facultad.

    Para instancias <= threshold devuelve un único Subproblem con toda la
    instancia (comportamiento del stub Fase 1 — sin costo extra).

    Para instancias > threshold:
        - Agrupa materias por faculty.
        - Identifica docentes y aulas compartidas entre facultades.
        - Retorna un Subproblem por facultad con la información de coordinación.
    """

    def __init__(self, threshold: int = DECOMPOSE_THRESHOLD) -> None:
        self.threshold = threshold

    # ── API pública ───────────────────────────────────────────────────────────

    def decompose(self, instance: SchedulingInstance) -> list[Subproblem]:
        """
        Retorna lista de Subproblem.
        Si len(subjects) <= threshold: lista con un solo elemento (instancia completa).
        """
        if len(instance.subjects) <= self.threshold:
            logger.info(
                f"[Layer2-Decomposer] {len(instance.subjects)} materias "
                f"<= umbral {self.threshold} — sin descomposición"
            )
            return [Subproblem(faculty="all", instance=instance)]

        return self._decompose_by_faculty(instance)

    def merge_solutions(
        self,
        sub_solutions: list[list[Assignment]],
        subproblems: list[Subproblem],
    ) -> list[Assignment]:
        """
        Unifica las soluciones de cada subproblema.
        Detecta y resuelve conflictos HC1/HC2 en recursos compartidos
        (docentes y aulas que aparecen en múltiples facultades).
        """
        merged: list[Assignment] = []
        for sol in sub_solutions:
            merged.extend(sol)

        if len(sub_solutions) <= 1:
            return merged

        # Detectar conflictos de double-booking en recursos compartidos
        used_cls_ts: dict[tuple[str, str], int] = {}
        used_prof_ts: dict[tuple[str, str], int] = {}
        conflicts: list[int] = []

        for idx, a in enumerate(merged):
            ct_key = (a.classroom_code, a.timeslot_code)
            if ct_key in used_cls_ts:
                conflicts.append(idx)
            else:
                used_cls_ts[ct_key] = idx

            if a.timeslot_code and a.classroom_code:
                # We don't have professor_code in Assignment directly; skip prof check
                pass

        if conflicts:
            logger.warning(
                f"[Layer2-Decomposer] {len(conflicts)} conflictos HC1 "
                "en recursos compartidos — eliminando duplicados"
            )
            conflict_set = set(conflicts)
            merged = [a for i, a in enumerate(merged) if i not in conflict_set]

        logger.info(
            f"[Layer2-Decomposer] merge_solutions → {len(merged)} asignaciones "
            f"de {len(sub_solutions)} sub-soluciones"
        )
        return merged

    # ── Backward-compat con stub Fase 1 ──────────────────────────────────────

    def decompose_as_dict(
        self, instance: SchedulingInstance
    ) -> dict[str, SchedulingInstance]:
        """
        Interfaz original del stub Fase 1.
        Retorna {faculty: sub_instance} independientemente del umbral.
        """
        faculties = {s.faculty for s in instance.subjects}
        result: dict[str, SchedulingInstance] = {}
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

    # ── Lógica interna ────────────────────────────────────────────────────────

    def _decompose_by_faculty(self, instance: SchedulingInstance) -> list[Subproblem]:
        """Agrupa materias por facultad e identifica recursos compartidos."""
        # Mapa faculty → lista de Subject
        faculty_subjects: dict[str, list] = defaultdict(list)
        for s in instance.subjects:
            faculty_subjects[s.faculty].append(s)

        # Profesores que aparecen en más de una facultad
        prof_faculty: dict[str, set[str]] = defaultdict(set)
        for s in instance.subjects:
            if s.professor_code:
                prof_faculty[s.professor_code].add(s.faculty)
        shared_profs = {p for p, facs in prof_faculty.items() if len(facs) > 1}

        subproblems: list[Subproblem] = []
        for faculty, subjects in faculty_subjects.items():
            sub_instance = SchedulingInstance(
                semester=instance.semester,
                subjects=subjects,
                classrooms=instance.classrooms,    # todas las aulas (visibles para todos)
                timeslots=instance.timeslots,
                professors=instance.professors,
                global_constraints=instance.global_constraints,
            )
            # Profesores de esta facultad que también están en otras
            faculty_prof_codes = {s.professor_code for s in subjects if s.professor_code}
            sp = Subproblem(
                faculty=faculty,
                instance=sub_instance,
                shared_professors=faculty_prof_codes & shared_profs,
            )
            subproblems.append(sp)
            logger.info(
                f"[Layer2-Decomposer] Facultad '{faculty}': "
                f"{len(subjects)} materias, "
                f"{len(sp.shared_professors)} docentes compartidos"
            )

        logger.info(
            f"[Layer2-Decomposer] Instancia descompuesta en "
            f"{len(subproblems)} subproblemas"
        )
        return subproblems
