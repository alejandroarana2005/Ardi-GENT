"""
HAIA Agent — Capa 1: Validación de integridad de datos de entrada.
Detecta inconsistencias antes de iniciar la búsqueda, evitando fallas silenciosas
en capas más profundas del pipeline.
"""

import logging
from dataclasses import dataclass, field

from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA Layer1-Validator]")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False
        logger.error(f"[Layer1] Validation error: {msg}")

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning(f"[Layer1] Validation warning: {msg}")


class InstanceValidator:
    """
    Valida la integridad estructural de un SchedulingInstance antes de procesar.
    No verifica factibilidad (eso es responsabilidad de layer2/feasibility.py),
    solo detecta datos corruptos o inconsistentes.
    """

    def validate(self, instance: SchedulingInstance) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        self._check_non_empty(instance, result)
        self._check_professor_references(instance, result)
        self._check_capacity_sanity(instance, result)
        self._check_enrollment_sanity(instance, result)
        self._check_timeslot_consistency(instance, result)
        self._check_availability_references(instance, result)
        self._check_resource_references(instance, result)
        self._check_feasibility_hints(instance, result)

        return result

    def _check_non_empty(self, instance: SchedulingInstance, result: ValidationResult) -> None:
        if not instance.subjects:
            result.add_error("No hay materias en la instancia.")
        if not instance.classrooms:
            result.add_error("No hay salones en la instancia.")
        if not instance.timeslots:
            result.add_error("No hay franjas horarias en la instancia.")

    def _check_professor_references(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        prof_codes = {p.code for p in instance.professors}
        for subject in instance.subjects:
            if subject.professor_code and subject.professor_code not in prof_codes:
                result.add_error(
                    f"Materia {subject.code} referencia docente inexistente: {subject.professor_code}"
                )

    def _check_capacity_sanity(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        for classroom in instance.classrooms:
            if classroom.capacity <= 0:
                result.add_error(
                    f"Salón {classroom.code} tiene capacidad inválida: {classroom.capacity}"
                )

    def _check_enrollment_sanity(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        max_capacity = max((c.capacity for c in instance.classrooms), default=0)
        for subject in instance.subjects:
            if subject.enrollment <= 0:
                result.add_warning(
                    f"Materia {subject.code} tiene enrollment=0, se asignará al salón más pequeño."
                )
            if subject.enrollment > max_capacity:
                result.add_error(
                    f"Materia {subject.code} tiene enrollment={subject.enrollment} "
                    f"mayor que la capacidad máxima disponible ({max_capacity})."
                )

    def _check_timeslot_consistency(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        for ts in instance.timeslots:
            if ts.start_time >= ts.end_time:
                result.add_error(
                    f"Franja {ts.code}: start_time ({ts.start_time}) >= end_time ({ts.end_time})"
                )
            if ts.duration <= 0:
                result.add_error(f"Franja {ts.code}: duración inválida ({ts.duration}h)")

    def _check_availability_references(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        ts_codes = {ts.code for ts in instance.timeslots}
        for professor in instance.professors:
            unknown = [code for code in professor.availability if code not in ts_codes]
            if unknown:
                result.add_warning(
                    f"Docente {professor.code} tiene disponibilidad en franjas no definidas: {unknown}"
                )

    def _check_resource_references(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        all_resource_codes = {
            r.code for c in instance.classrooms for r in c.resources
        }
        for subject in instance.subjects:
            for req in subject.required_resources:
                if req.resource_code not in all_resource_codes:
                    result.add_warning(
                        f"Materia {subject.code} requiere recurso '{req.resource_code}' "
                        "que no existe en ningún salón. El problema puede ser infactible."
                    )

    def _check_feasibility_hints(
        self, instance: SchedulingInstance, result: ValidationResult
    ) -> None:
        """Heurística rápida de factibilidad antes de la búsqueda."""
        total_slots = len(instance.classrooms) * len(instance.timeslots)
        total_needed = sum(s.total_assignments_needed() for s in instance.subjects)

        if total_needed > total_slots:
            result.add_error(
                f"Infactibilidad estructural: se necesitan {total_needed} asignaciones "
                f"pero solo hay {total_slots} combinaciones (salón × franja) disponibles."
            )
        elif total_needed > total_slots * 0.85:
            result.add_warning(
                f"Alta densidad de asignación: {total_needed}/{total_slots} = "
                f"{total_needed/total_slots:.0%}. La búsqueda puede ser lenta."
            )
