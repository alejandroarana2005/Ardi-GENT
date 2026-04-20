"""
HAIA Agent — Capa 1: Percepción e ingesta de datos.
Lee la BD, construye el SchedulingInstance y lo entrega validado a la Capa 2.
"""

import logging
from sqlalchemy.orm import Session

from app.database.models import (
    ClassroomModel,
    ProfessorModel,
    SubjectModel,
    TimeSlotModel,
)
from app.domain.entities import (
    Assignment,
    Classroom,
    Constraint,
    PreferenceSlot,
    Professor,
    Resource,
    ResourceRequirement,
    SchedulingInstance,
    Subject,
    TimeSlot,
)
from app.layer1_perception.validator import InstanceValidator, ValidationResult

logger = logging.getLogger("[HAIA Layer1-Perception]")


class DataLoader:
    """
    Lee los datos de la BD y los transforma en entidades de dominio inmutables.
    Es el único punto de entrada de datos externos al sistema HAIA.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def load_instance(self, semester: str) -> tuple[SchedulingInstance, ValidationResult]:
        """
        Carga y valida la instancia completa del problema para un semestre.
        Retorna (instance, validation_result) — el agente BDI decide si continuar
        según validation_result.is_valid.
        """
        logger.info(f"[Layer1] Cargando instancia para semestre {semester}")

        classrooms = self._load_classrooms()
        timeslots = self._load_timeslots()
        professors = self._load_professors()
        subjects = self._load_subjects()

        instance = SchedulingInstance(
            semester=semester,
            subjects=subjects,
            classrooms=classrooms,
            timeslots=timeslots,
            professors=professors,
        )

        validator = InstanceValidator()
        result = validator.validate(instance)

        summary = instance.summary()
        logger.info(
            f"[Layer1] Instancia cargada — {summary['subjects']} materias, "
            f"{summary['total_assignments_needed']} asignaciones requeridas, "
            f"espacio de búsqueda ≈ {summary['search_space_size']:,}"
        )

        if not result.is_valid:
            logger.warning(f"[Layer1] Validación fallida: {result.errors}")
        else:
            logger.info("[Layer1] Validación exitosa")

        return instance, result

    def _load_classrooms(self) -> list[Classroom]:
        rows: list[ClassroomModel] = self.db.query(ClassroomModel).all()
        classrooms = []
        for row in rows:
            resources = tuple(
                Resource(code=r.code, name=r.name) for r in row.resources
            )
            classrooms.append(
                Classroom(
                    code=row.code,
                    name=row.name,
                    capacity=row.capacity,
                    resources=resources,
                )
            )
        logger.debug(f"[Layer1] {len(classrooms)} salones cargados")
        return classrooms

    def _load_timeslots(self) -> list[TimeSlot]:
        rows: list[TimeSlotModel] = (
            self.db.query(TimeSlotModel)
            .order_by(TimeSlotModel.day, TimeSlotModel.start_time)
            .all()
        )
        timeslots = [
            TimeSlot(
                code=row.code,
                day=row.day,
                start_time=row.start_time,
                end_time=row.end_time,
                duration=row.duration,
            )
            for row in rows
        ]
        logger.debug(f"[Layer1] {len(timeslots)} franjas horarias cargadas")
        return timeslots

    def _load_professors(self) -> list[Professor]:
        rows: list[ProfessorModel] = self.db.query(ProfessorModel).all()
        professors = []
        for row in rows:
            availability = tuple(a.timeslot_code for a in row.availability)
            preferences = tuple(
                PreferenceSlot(
                    timeslot_code=p.timeslot_code,
                    preference=p.preference,
                )
                for p in row.preferences
            )
            professors.append(
                Professor(
                    code=row.code,
                    name=row.name,
                    availability=availability,
                    preferences=preferences,
                    max_weekly_hours=row.max_weekly_hours,
                    contract_type=row.contract_type,
                )
            )
        logger.debug(f"[Layer1] {len(professors)} docentes cargados")
        return professors

    def _load_subjects(self) -> list[Subject]:
        rows: list[SubjectModel] = self.db.query(SubjectModel).all()
        subjects = []
        for row in rows:
            required = tuple(
                ResourceRequirement(resource_code=r.code) for r in row.required_resources
            )
            optional = tuple(
                ResourceRequirement(resource_code=r.code) for r in row.optional_resources
            )
            subjects.append(
                Subject(
                    code=row.code,
                    name=row.name,
                    credits=row.credits,
                    study_hours=row.study_hours,
                    weekly_subgroups=row.weekly_subgroups,
                    groups=row.groups,
                    enrollment=row.enrollment,
                    professor_code=row.professor_code,
                    required_resources=required,
                    optional_resources=optional,
                    faculty=row.faculty,
                )
            )
        logger.debug(f"[Layer1] {len(subjects)} materias cargadas")
        return subjects
