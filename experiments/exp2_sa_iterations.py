"""
Experimento 2 — Convergencia del Recocido Simulado (SA).
Mide U(A) y tiempo de optimización para distintos valores de iters_per_T,
usando una instancia fija de tamaño M.

Valores de iters_per_T: 0 (sin SA), 1, 5, 10, 25, 50 (default), 100, 200, 500
N_cooling_steps ≈ log(T_min/T0)/log(alpha) ≈ log(0.0001/0.05)/log(0.95) ≈ 121

Salida: experiments_results/exp2_sa_iterations.csv
"""

from __future__ import annotations

import csv
import logging
import math
from pathlib import Path

from app.config import HAIAConfig
from experiments._common import NO_SA_CONFIG, run_haia_cycle, _run_with_timeout
from experiments.instance_generator import generate_instance

logger = logging.getLogger("[Exp2-SA-Iterations]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

INSTANCE_SIZE = "M"
RUNS          = 3
TIMEOUT       = 600   # 10 min per run
RESULTS_DIR   = Path(__file__).parent.parent / "experiments_results"

# iters_per_T values — 0 means "no SA" (use NO_SA_CONFIG trick)
ITERS_PER_T_VALUES = [0, 1, 5, 10, 25, 50, 100, 200, 500]

# Approximate N_cooling_steps for default T0/T_min/alpha
_T0    = 0.05
_TMIN  = 0.0001
_ALPHA = 0.95
N_COOLING_STEPS = math.ceil(math.log(_TMIN / _T0) / math.log(_ALPHA))  # ≈ 121

CSV_FIELDS = [
    "iters_per_t", "total_sa_iters_approx", "label",
    "run", "seed",
    "elapsed_s", "layer3_ms", "layer4_ms",
    "utility_score", "solver_used", "is_feasible", "error",
]


def _make_config(iters_per_t: int) -> HAIAConfig:
    if iters_per_t == 0:
        return NO_SA_CONFIG
    return HAIAConfig(
        sa_iters_per_t=iters_per_t,
        database_url="sqlite:///:memory:",
    )


def run_experiment(runs: int = RUNS) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "exp2_sa_iterations.csv"

    rows: list[dict] = []
    total = len(ITERS_PER_T_VALUES) * runs
    done  = 0

    for ipt in ITERS_PER_T_VALUES:
        total_approx = 0 if ipt == 0 else ipt * N_COOLING_STEPS
        label = f"0 (no SA)" if ipt == 0 else str(total_approx)
        config = _make_config(ipt)

        for run_idx in range(1, runs + 1):
            seed = run_idx * 100
            instance = generate_instance(INSTANCE_SIZE, seed=seed)

            logger.info(
                f"[Exp2] iters_per_t={ipt} (~{total_approx} SA iters) "
                f"run {run_idx}/{runs} seed={seed}"
            )

            result, err = _run_with_timeout(
                lambda inst=instance, cfg=config: run_haia_cycle(inst, custom_config=cfg),
                timeout_s=TIMEOUT,
            )

            row: dict = {
                "iters_per_t": ipt,
                "total_sa_iters_approx": total_approx,
                "label": label,
                "run": run_idx,
                "seed": seed,
                "elapsed_s": round(result.elapsed_seconds, 3) if result else None,
                "layer3_ms": result.layer_times.get("layer3_ms") if result else None,
                "layer4_ms": result.layer_times.get("layer4_ms") if result else None,
                "utility_score": round(result.utility_score, 6) if result else None,
                "solver_used": result.solver_used if result else None,
                "is_feasible": result.is_feasible if result else False,
                "error": err,
            }
            rows.append(row)
            done += 1

            status = "OK" if result and result.is_feasible else f"FAIL({err})"
            logger.info(
                f"[Exp2] ipt={ipt} run={run_idx} → {status} "
                f"U(A)={row['utility_score']} L4={row['layer4_ms']}ms  [{done}/{total}]"
            )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"[Exp2] CSV guardado en {csv_path} ({len(rows)} filas)")


if __name__ == "__main__":
    run_experiment()
