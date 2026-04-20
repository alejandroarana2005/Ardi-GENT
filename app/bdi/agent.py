"""
HAIA Agent — Agente BDI principal.
Orquesta las 5 capas del pipeline de asignación.

Clasificación: Agente Basado en Utilidad con arquitectura BDI
Ref: Russell & Norvig (2020) — Artificial Intelligence: A Modern Approach, 4th ed.
     La Cruz et al. (2024) — UniSchedApi (modelo de datos y algoritmos base)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.bdi.beliefs import BeliefBase
from app.bdi.desires import DesireSet
from app.bdi.intentions import IntentionPipeline, IntentionStatus
from app.config import HAIAConfig
from app.domain.entities import Assignment, SchedulingResult
from app.layer1_perception.data_loader import DataLoader
from app.layer5_dynamic.event_handler import DynamicEvent, EventHandler, RepairResult

logger = logging.getLogger("[HAIA BDI-Agent]")


class HAIAAgent:
    """
    Hybrid Adaptive Intelligent Agent — Arquitectura BDI.
    Clasificación: Agente Basado en Utilidad (Russell & Norvig, 2020).
    """

    def __init__(self, db_session: Session, config: HAIAConfig) -> None:
        self.beliefs = BeliefBase(db_session=db_session)
        self.desires = DesireSet()
        self.intentions = IntentionPipeline()
        self.config = config
        self.db = db_session

    def run_scheduling_cycle(
        self,
        semester: str,
        schedule_id: Optional[str] = None,
        solver_hint: Optional[str] = None,
    ) -> SchedulingResult:
        """
        Pipeline principal BDI:
        1. Percibir  → cargar y validar datos del semestre
        2. Preparar  → filtrar dominios con AC-3
        3. Resolver  → CSP backtracking o MILP según tamaño
        4. Optimizar → SA post-optimización con U(A)
        5. Persistir → guardar en BD y generar reporte
        """
        schedule_id = schedule_id or str(uuid.uuid4())
        t0 = time.perf_counter()
        pipeline = self.intentions.build_scheduling_pipeline()

        logger.info(f"[HAIA] Iniciando ciclo de asignación — semestre={semester}, id={schedule_id}")

        # ── Intención 1: Percepción ──────────────────────────────────────────
        step = pipeline[0]
        step.status = IntentionStatus.RUNNING
        try:
            loader = DataLoader(self.db)
            instance, validation = loader.load_instance(semester)

            if not validation.is_valid:
                step.status = IntentionStatus.FAILED
                step.error = str(validation.errors)
                logger.error(f"[HAIA] Percepción fallida: {validation.errors}")
                return SchedulingResult(
                    schedule_id=schedule_id,
                    semester=semester,
                    assignments=[],
                    utility_score=0.0,
                    solver_used="none",
                    elapsed_seconds=time.perf_counter() - t0,
                    is_feasible=False,
                    violations=validation.errors,
                )

            self.beliefs.update_from_instance(instance, semester)
            self.beliefs.active_schedule_id = schedule_id
            step.status = IntentionStatus.COMPLETED
            step.result = instance
        except Exception as exc:
            step.status = IntentionStatus.FAILED
            step.error = str(exc)
            raise

        # ── Intención 2: Preprocesamiento AC-3 ──────────────────────────────
        step = pipeline[1]
        step.status = IntentionStatus.RUNNING
        try:
            from app.layer2_preprocessing.domain_filter import DomainFilter
            from app.layer2_preprocessing.ac3 import AC3Preprocessor

            domain_filter = DomainFilter()
            reduced_domains = domain_filter.filter(instance)

            ac3 = AC3Preprocessor()
            csp_domains, feasible = ac3.run(instance, reduced_domains)

            if not feasible:
                step.status = IntentionStatus.FAILED
                step.error = "AC-3 detected empty domain — problem is infeasible"
                logger.error(f"[HAIA] {step.error}")
                return SchedulingResult(
                    schedule_id=schedule_id,
                    semester=semester,
                    assignments=[],
                    utility_score=0.0,
                    solver_used="ac3",
                    elapsed_seconds=time.perf_counter() - t0,
                    is_feasible=False,
                    violations=[step.error],
                )

            step.status = IntentionStatus.COMPLETED
            step.result = csp_domains
        except Exception as exc:
            step.status = IntentionStatus.FAILED
            step.error = str(exc)
            raise

        # ── Intención 3: Solver (CSP Backtracking o MILP) ───────────────────
        step = pipeline[2]
        step.status = IntentionStatus.RUNNING
        try:
            from app.layer3_solver.solver_factory import SolverFactory

            factory = SolverFactory(config=self.config)
            solver = factory.select(instance, hint=solver_hint)

            logger.info(f"[HAIA] Solver seleccionado: {solver.__class__.__name__}")
            assignments = solver.solve(instance, csp_domains)
            solver_used = solver.name

            if not assignments:
                step.status = IntentionStatus.FAILED
                step.error = "Solver returned no assignments"
                return SchedulingResult(
                    schedule_id=schedule_id,
                    semester=semester,
                    assignments=[],
                    utility_score=0.0,
                    solver_used=solver_used,
                    elapsed_seconds=time.perf_counter() - t0,
                    is_feasible=False,
                    violations=["Solver found no feasible assignment"],
                )

            step.status = IntentionStatus.COMPLETED
            step.result = assignments
        except Exception as exc:
            step.status = IntentionStatus.FAILED
            step.error = str(exc)
            raise

        # ── Intención 4: Post-optimización SA ───────────────────────────────
        step = pipeline[3]
        step.status = IntentionStatus.RUNNING
        try:
            from app.layer4_optimization.simulated_annealing import SimulatedAnnealing
            from app.layer4_optimization.utility_function import UtilityCalculator

            sa = SimulatedAnnealing(config=self.config)
            optimized = sa.optimize(assignments, instance)

            calc = UtilityCalculator(weights=self.config.utility_weights)
            utility_score = calc.compute(optimized, instance)

            step.status = IntentionStatus.COMPLETED
            step.result = (optimized, utility_score)
        except Exception as exc:
            step.status = IntentionStatus.FAILED
            step.error = str(exc)
            raise

        # ── Intención 5: Persistir ───────────────────────────────────────────
        step = pipeline[4]
        step.status = IntentionStatus.RUNNING
        try:
            self._persist_assignments(schedule_id, optimized)
            step.status = IntentionStatus.COMPLETED
        except Exception as exc:
            step.status = IntentionStatus.FAILED
            step.error = str(exc)
            raise

        elapsed = time.perf_counter() - t0
        logger.info(
            f"[HAIA] Ciclo completado — U(A)={utility_score:.4f}, "
            f"asignaciones={len(optimized)}, solver={solver_used}, "
            f"tiempo={elapsed:.2f}s"
        )

        return SchedulingResult(
            schedule_id=schedule_id,
            semester=semester,
            assignments=optimized,
            utility_score=utility_score,
            solver_used=solver_used,
            elapsed_seconds=elapsed,
            is_feasible=True,
        )

    def handle_dynamic_event(self, event: DynamicEvent) -> RepairResult:
        """
        Gestión de cambios en mitad del semestre.
        Aplica Principio de Mínima Perturbación (Capa 5).
        """
        logger.info(f"[HAIA] Evento dinámico: {event.event_type} en {event.schedule_id}")
        handler = EventHandler()
        context = {
            "instance": self.beliefs.current_instance,
            "db": self.db,
            "config": self.config,
        }
        return handler.handle(event, context)

    def _persist_assignments(
        self, schedule_id: str, assignments: list[Assignment]
    ) -> None:
        """Guarda las asignaciones en la BD bajo el schedule_id dado."""
        from app.database.models import AssignmentModel, ScheduleModel

        schedule = (
            self.db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            return

        instance = self.beliefs.current_instance
        prof_by_subject: dict[str, str | None] = {
            s.code: s.professor_code for s in instance.subjects
        } if instance else {}

        for a in assignments:
            self.db.add(
                AssignmentModel(
                    schedule_id=schedule.id,
                    subject_code=a.subject_code,
                    classroom_code=a.classroom_code,
                    timeslot_code=a.timeslot_code,
                    professor_code=prof_by_subject.get(a.subject_code),
                    group_number=a.group_number,
                    session_number=a.session_number,
                    utilidad_score=a.utilidad_score,
                )
            )
        self.db.commit()
        logger.debug(f"[HAIA] {len(assignments)} asignaciones persistidas")
