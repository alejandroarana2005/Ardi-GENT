"""
HAIA Agent — Capa 5: Manejador de eventos dinámicos.

5 tipos de evento soportados:
    CLASSROOM_UNAVAILABLE — un salón deja de estar disponible
    PROFESSOR_CANCELLED   — un docente cancela sus clases
    ENROLLMENT_SURGE      — la matrícula de una materia supera la capacidad del salón
    SLOT_BLOCKED          — una franja horaria queda bloqueada (evento institucional)
    NEW_COURSE_ADDED      — se agrega una nueva materia al horario vigente

Principio de Mínima Perturbación (Minimum Perturbation Principle):
    Solo se re-optimizan las asignaciones estrictamente necesarias.
    Target: repair_time < 30s para ≤ 10 cursos afectados.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("[HAIA Layer5-Dynamic]")


class EventType(str, Enum):
    CLASSROOM_UNAVAILABLE = "CLASSROOM_UNAVAILABLE"
    PROFESSOR_CANCELLED = "PROFESSOR_CANCELLED"
    ENROLLMENT_SURGE = "ENROLLMENT_SURGE"
    SLOT_BLOCKED = "SLOT_BLOCKED"
    NEW_COURSE_ADDED = "NEW_COURSE_ADDED"


@dataclass
class DynamicEvent:
    """Evento que dispara re-optimización dinámica."""
    event_type: str
    schedule_id: str
    payload: dict = field(default_factory=dict)

    def validate(self) -> tuple[bool, str]:
        """Retorna (is_valid, error_message)."""
        valid_types = {e.value for e in EventType}
        if self.event_type not in valid_types:
            return False, f"event_type inválido: {self.event_type}"
        if not self.schedule_id:
            return False, "schedule_id requerido"

        required: dict[str, list[str]] = {
            EventType.CLASSROOM_UNAVAILABLE: ["classroom_code"],
            EventType.PROFESSOR_CANCELLED:   ["professor_code"],
            EventType.SLOT_BLOCKED:          ["timeslot_code"],
            EventType.ENROLLMENT_SURGE:      ["subject_code", "new_enrollment"],
            EventType.NEW_COURSE_ADDED:      ["subject_code"],
        }
        for key in required.get(self.event_type, []):
            if key not in self.payload:
                return False, f"payload falta campo requerido: '{key}'"
        return True, ""


@dataclass
class RepairResult:
    """Resultado de una reparación local (Capa 5)."""
    is_successful: bool
    affected_count: int = 0
    repaired_count: int = 0
    elapsed_seconds: float = 0.0
    new_schedule_id: str | None = None
    perturbation_ratio: float = 0.0
    message: str = ""


class EventHandler:
    """
    Gestiona eventos de cambio y dispara reparación local (k-vecindad).
    Principio de Mínima Perturbación: solo re-optimiza lo estrictamente necesario.
    """

    SUPPORTED_EVENTS = {e.value for e in EventType}

    def handle(self, event: DynamicEvent, context: dict) -> RepairResult:
        t0 = time.perf_counter()
        logger.info(
            f"[Layer5] Procesando evento {event.event_type} "
            f"en schedule={event.schedule_id}"
        )

        if event.event_type not in self.SUPPORTED_EVENTS:
            return RepairResult(
                is_successful=False,
                message=f"Tipo de evento no soportado: {event.event_type}",
            )

        is_valid, err = event.validate()
        if not is_valid:
            return RepairResult(is_successful=False, message=err)

        db = context.get("db")
        instance = context.get("instance")
        config = context.get("config")

        if db is None or instance is None:
            return RepairResult(
                is_successful=False,
                message="Contexto incompleto: se requieren 'db' e 'instance'",
            )

        # Load current assignments from DB
        from app.database.models import AssignmentModel, ScheduleModel
        from app.domain.entities import Assignment

        schedule = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == event.schedule_id)
            .first()
        )
        if not schedule:
            return RepairResult(
                is_successful=False,
                message=f"Schedule {event.schedule_id} no encontrado",
            )

        current: list[Assignment] = [
            Assignment(
                subject_code=a.subject_code,
                classroom_code=a.classroom_code,
                timeslot_code=a.timeslot_code,
                group_number=a.group_number,
                session_number=a.session_number,
                utilidad_score=a.utilidad_score,
            )
            for a in schedule.assignments
        ]

        # Identify affected assignments
        affected = self._identify_affected(event, current, instance)
        logger.info(
            f"[Layer5] {len(affected)} asignaciones afectadas por {event.event_type}"
        )

        if not affected and event.event_type != EventType.NEW_COURSE_ADDED:
            return RepairResult(
                is_successful=True,
                affected_count=0,
                repaired_count=len(current),
                elapsed_seconds=time.perf_counter() - t0,
                message="Ninguna asignación afectada por este evento",
            )

        # Run local repair
        from app.layer5_dynamic.repair import RepairModule
        repair_module = RepairModule(config=config)

        repaired = repair_module.repair_local(
            current=current,
            affected=affected,
            event=event,
            context=context,
        )

        if repaired is None:
            return RepairResult(
                is_successful=False,
                affected_count=len(affected),
                elapsed_seconds=time.perf_counter() - t0,
                message="Reparación fallida — no se encontró reasignación factible",
            )

        # Compute perturbation ratio (symmetric difference)
        original_slots = {
            (a.subject_code, a.group_number, a.session_number, a.classroom_code, a.timeslot_code)
            for a in current
        }
        repaired_slots = {
            (a.subject_code, a.group_number, a.session_number, a.classroom_code, a.timeslot_code)
            for a in repaired
        }
        changed = len(original_slots.symmetric_difference(repaired_slots))
        total = max(len(current), 1)
        perturbation_ratio = changed / total

        # Save repaired assignments as a new schedule version
        from app.layer5_dynamic.version_manager import VersionManager
        vm = VersionManager()

        from app.layer4_optimization.utility_function import UtilityCalculator
        calc = UtilityCalculator(config.utility_weights)
        new_score = calc.compute(repaired, instance)

        new_sid = vm.save_version(
            schedule_id=event.schedule_id,
            assignments=repaired,
            reason=f"{event.event_type}: {event.payload}",
            db=db,
            semester=schedule.semester,
            solver_used="repair",
            utility_score=new_score,
        )

        elapsed = time.perf_counter() - t0
        logger.info(
            f"[Layer5] Reparación completada — afectadas={len(affected)}, "
            f"perturbation={perturbation_ratio:.1%}, tiempo={elapsed:.2f}s, "
            f"nueva_versión={new_sid}"
        )

        return RepairResult(
            is_successful=True,
            affected_count=len(affected),
            repaired_count=len(repaired),
            elapsed_seconds=elapsed,
            new_schedule_id=new_sid,
            perturbation_ratio=perturbation_ratio,
            message=f"Reparación exitosa. Nueva versión: {new_sid}",
        )

    # ── Identificación de afectadas ────────────────────────────────────────────

    def _identify_affected(
        self,
        event: DynamicEvent,
        assignments: list,
        instance,
    ) -> list:
        payload = event.payload
        etype = event.event_type

        if etype == EventType.CLASSROOM_UNAVAILABLE:
            code = payload.get("classroom_code", "")
            return [a for a in assignments if a.classroom_code == code]

        if etype == EventType.PROFESSOR_CANCELLED:
            prof_code = payload.get("professor_code", "")
            subjects = {s.code for s in instance.subjects if s.professor_code == prof_code}
            return [a for a in assignments if a.subject_code in subjects]

        if etype == EventType.SLOT_BLOCKED:
            ts_code = payload.get("timeslot_code", "")
            return [a for a in assignments if a.timeslot_code == ts_code]

        if etype == EventType.ENROLLMENT_SURGE:
            subj_code = payload.get("subject_code", "")
            new_enrollment = int(payload.get("new_enrollment", 0))
            cls_map = {c.code: c for c in instance.classrooms}
            return [
                a for a in assignments
                if a.subject_code == subj_code
                and cls_map.get(a.classroom_code) is not None
                and cls_map[a.classroom_code].capacity < new_enrollment
            ]

        # NEW_COURSE_ADDED: no existing assignment is "affected"
        return []
