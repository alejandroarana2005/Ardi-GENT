"""
Experimento 1 — Escalabilidad del pipeline HAIA.
Mide tiempo total y U(A) para instancias S/M/L/XL/XXL con 3 corridas cada una.
Salida: experiments_results/exp1_scalability.csv
"""

from __future__ import annotations

import csv
import logging
import os
import time
from pathlib import Path

from experiments._common import run_haia_cycle, _run_with_timeout
from experiments.instance_generator import SIZE_CONFIG, generate_instance

logger = logging.getLogger("[Exp1-Scalability]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

SIZES   = list(SIZE_CONFIG.keys())   # S M L XL XXL
RUNS    = 3
TIMEOUT = 1800  # 30 min per run
RESULTS_DIR = Path(__file__).parent.parent / "experiments_results"

CSV_FIELDS = [
    "size", "run", "seed",
    "n_subjects", "n_classrooms", "n_timeslots", "n_professors",
    "n_assignments_needed", "n_assignments_produced",
    "elapsed_s", "utility_score", "solver_used",
    "is_feasible", "layer1_ms", "layer2_ms", "layer3_ms", "layer4_ms",
    "error",
]


def run_experiment(sizes: list[str] = SIZES, runs: int = RUNS) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "exp1_scalability.csv"

    rows: list[dict] = []
    total = len(sizes) * runs
    done  = 0

    for size in sizes:
        cfg = SIZE_CONFIG[size]
        for run_idx in range(1, runs + 1):
            seed = run_idx * 100
            instance = generate_instance(size, seed=seed)
            n_needed = sum(s.total_assignments_needed() for s in instance.subjects)

            logger.info(
                f"[Exp1] {size} run {run_idx}/{runs} "
                f"(subjects={cfg['subjects']}, timeslots={cfg['timeslots']}, seed={seed})"
            )

            result, err = _run_with_timeout(
                lambda inst=instance: run_haia_cycle(inst),
                timeout_s=TIMEOUT,
            )

            row: dict = {
                "size": size,
                "run": run_idx,
                "seed": seed,
                "n_subjects": cfg["subjects"],
                "n_classrooms": cfg["classrooms"],
                "n_timeslots": cfg["timeslots"],
                "n_professors": cfg["professors"],
                "n_assignments_needed": n_needed,
                "n_assignments_produced": len(result.assignments) if result else 0,
                "elapsed_s": round(result.elapsed_seconds, 3) if result else None,
                "utility_score": round(result.utility_score, 6) if result else None,
                "solver_used": result.solver_used if result else None,
                "is_feasible": result.is_feasible if result else False,
                "layer1_ms": result.layer_times.get("layer1_ms") if result else None,
                "layer2_ms": result.layer_times.get("layer2_ms") if result else None,
                "layer3_ms": result.layer_times.get("layer3_ms") if result else None,
                "layer4_ms": result.layer_times.get("layer4_ms") if result else None,
                "error": err,
            }
            rows.append(row)
            done += 1

            status = "OK" if result and result.is_feasible else f"FAIL({err})"
            logger.info(
                f"[Exp1] {size} run {run_idx} → {status} "
                f"U(A)={row['utility_score']} t={row['elapsed_s']}s  [{done}/{total}]"
            )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"[Exp1] CSV guardado en {csv_path} ({len(rows)} filas)")


if __name__ == "__main__":
    import sys
    # Support quick dry-run: python -m experiments.exp1_scalability --dry
    if "--dry" in sys.argv:
        logger.info("[Exp1] DRY-RUN: solo tamaño S, 1 corrida")
        run_experiment(sizes=["S"], runs=1)
    else:
        run_experiment()
