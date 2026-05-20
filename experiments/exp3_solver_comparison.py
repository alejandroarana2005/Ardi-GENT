"""
Experimento 3 — Comparación de solvers.
Para instancia fija M, mide U(A) y tiempo con y sin SA para cada solver.
Solvers: backtracking | tabu_search | milp

Salida: experiments_results/exp3_solver_comparison.csv
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from experiments._common import NO_SA_CONFIG, run_haia_cycle, _run_with_timeout
from experiments.instance_generator import generate_instance

logger = logging.getLogger("[Exp3-Solver-Comparison]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

INSTANCE_SIZE = "M"
RUNS          = 3
TIMEOUT       = 900   # 15 min per run (MILP puede tardar)
RESULTS_DIR   = Path(__file__).parent.parent / "experiments_results"
SOLVERS       = ["backtracking", "tabu_search", "milp"]

CSV_FIELDS = [
    "solver", "sa_enabled", "run", "seed",
    "elapsed_s", "layer3_ms", "layer4_ms",
    "utility_score", "n_assignments", "is_feasible", "error",
]


def run_experiment(runs: int = RUNS) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "exp3_solver_comparison.csv"

    rows: list[dict] = []
    total = len(SOLVERS) * 2 * runs  # with SA + without SA
    done  = 0

    for solver in SOLVERS:
        for sa_enabled in [False, True]:
            config = None if sa_enabled else NO_SA_CONFIG

            for run_idx in range(1, runs + 1):
                seed = run_idx * 100
                instance = generate_instance(INSTANCE_SIZE, seed=seed)
                sa_label = "with_SA" if sa_enabled else "no_SA"

                logger.info(
                    f"[Exp3] solver={solver} {sa_label} run={run_idx}/{runs} seed={seed}"
                )

                result, err = _run_with_timeout(
                    lambda inst=instance, s=solver, c=config: (
                        run_haia_cycle(inst, solver_hint=s, custom_config=c)
                    ),
                    timeout_s=TIMEOUT,
                )

                row: dict = {
                    "solver": solver,
                    "sa_enabled": sa_enabled,
                    "run": run_idx,
                    "seed": seed,
                    "elapsed_s": round(result.elapsed_seconds, 3) if result else None,
                    "layer3_ms": result.layer_times.get("layer3_ms") if result else None,
                    "layer4_ms": result.layer_times.get("layer4_ms") if result else None,
                    "utility_score": round(result.utility_score, 6) if result else None,
                    "n_assignments": len(result.assignments) if result else 0,
                    "is_feasible": result.is_feasible if result else False,
                    "error": err,
                }
                rows.append(row)
                done += 1

                status = "OK" if result and result.is_feasible else f"FAIL({err})"
                logger.info(
                    f"[Exp3] {solver} {sa_label} run={run_idx} → {status} "
                    f"U(A)={row['utility_score']} t={row['elapsed_s']}s  [{done}/{total}]"
                )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"[Exp3] CSV guardado en {csv_path} ({len(rows)} filas)")


if __name__ == "__main__":
    run_experiment()
