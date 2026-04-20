"""
HAIA Agent — Capa 3: Factory de solvers.
Selecciona automáticamente el solver según tamaño de la instancia:
  ≤ 150 cursos → CSP Backtracking (más explícito, mejor para instancias pequeñas)
  >  150 cursos → MILP CP-SAT (OR-Tools, mejor para escala)
  hint='tabu_search' → Tabu Search (compatible con UniSchedApi, La Cruz et al. 2024)
"""

import logging

from app.config import HAIAConfig
from app.domain.entities import SchedulingInstance

logger = logging.getLogger("[HAIA Layer3-SolverFactory]")


class SolverFactory:
    def __init__(self, config: HAIAConfig) -> None:
        self.config = config

    def select(self, instance: SchedulingInstance, hint: str | None = None):
        """Retorna el solver apropiado para la instancia."""
        total = sum(s.total_assignments_needed() for s in instance.subjects)

        if hint == "tabu_search":
            from app.layer3_solver.tabu_search import TabuSearchSolver
            logger.info(f"[Layer3-Factory] Solver forzado: TabuSearch (hint)")
            return TabuSearchSolver(config=self.config)

        if hint == "milp":
            from app.layer3_solver.milp_solver import MILPSolver
            logger.info(f"[Layer3-Factory] Solver forzado: MILP (hint)")
            return MILPSolver(config=self.config)

        if hint == "backtracking":
            from app.layer3_solver.csp_backtracking import CSPBacktrackingSolver
            logger.info(f"[Layer3-Factory] Solver forzado: Backtracking (hint)")
            return CSPBacktrackingSolver(config=self.config)

        if total <= 50:
            from app.layer3_solver.csp_backtracking import CSPBacktrackingSolver
            logger.info(f"[Layer3-Factory] Seleccionado: Backtracking (total={total} ≤ 50)")
            return CSPBacktrackingSolver(config=self.config)
        elif total <= self.config.solver_backtrack_threshold:
            from app.layer3_solver.tabu_search import TabuSearchSolver
            logger.info(
                f"[Layer3-Factory] Seleccionado: TabuSearch (50 < total={total} ≤ {self.config.solver_backtrack_threshold})"
            )
            return TabuSearchSolver(config=self.config)
        else:
            from app.layer3_solver.milp_solver import MILPSolver
            logger.info(
                f"[Layer3-Factory] Seleccionado: MILP (total={total} > {self.config.solver_backtrack_threshold})"
            )
            return MILPSolver(config=self.config)
