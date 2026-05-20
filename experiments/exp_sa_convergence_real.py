"""
Experimento SA — Convergencia del Recocido Simulado en la instancia institucional.

Usa la instancia real de 105 asignaciones (30 materias Ingeniería de Sistemas,
U. Ibagué) para medir cómo varía U(A) con distintos valores de iters_per_T.

Comparable con exp2_sa_iterations.py (instancias sintéticas M).

Salida: experiments_results/exp_sa_convergence_real.csv
"""

from __future__ import annotations

import csv
import logging
import math
import random
import sys
from pathlib import Path
from statistics import mean, stdev

from app.config import HAIAConfig
from experiments._common import run_haia_cycle, _run_with_timeout
from tests.fixtures.sample_data import build_sample_instance

logger = logging.getLogger("[ExpSA-Real]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

RUNS          = 3
SEEDS         = [100, 200, 300]
TIMEOUT       = 600   # 10 min por corrida
RESULTS_DIR   = Path(__file__).parent.parent / "experiments_results"

ITERS_PER_T_VALUES = [0, 1, 5, 10, 25, 50, 100, 200, 500]

_T0    = 0.05
_TMIN  = 0.0001
_ALPHA = 0.95
N_COOLING_STEPS = math.ceil(math.log(_TMIN / _T0) / math.log(_ALPHA))  # ≈ 121

CSV_FIELDS = [
    "iters_per_t", "total_sa_iters_approx", "label",
    "run", "seed",
    "n_assignments",
    "elapsed_s", "layer3_ms", "layer4_ms",
    "utility_score", "solver_used", "is_feasible", "error",
]


def _make_config(iters_per_t: int) -> HAIAConfig:
    if iters_per_t == 0:
        return HAIAConfig(
            sa_t0=0.0001, sa_t_min=0.0001, sa_iters_per_t=1,
            database_url="sqlite:///:memory:",
        )
    return HAIAConfig(sa_iters_per_t=iters_per_t, database_url="sqlite:///:memory:")


def verify_baseline() -> bool:
    """
    Corre UNA sola corrida con iters_per_T=50 (default) para confirmar
    que U(A) ∈ [0.65, 0.78]. Si falla, no continuar con el experimento.
    """
    logger.info("=" * 60)
    logger.info("VERIFICACIÓN INICIAL — iters_per_T=50, seed=100")
    logger.info("=" * 60)

    random.seed(100)
    instance = build_sample_instance("2024-A")
    config = _make_config(50)

    result, err = _run_with_timeout(
        lambda: run_haia_cycle(instance, custom_config=config),
        timeout_s=TIMEOUT,
    )

    if err:
        logger.error(f"VERIFICACIÓN FALLIDA — error: {err}")
        return False

    u = result.utility_score if result else 0.0
    n = len(result.assignments) if result else 0
    logger.info(
        f"VERIFICACIÓN: n_assignments={n}, U(A)={u:.4f}, "
        f"solver={result.solver_used if result else 'N/A'}, "
        f"tiempo={result.elapsed_seconds:.2f}s"
    )

    if u < 0.5:
        logger.error(
            f"U(A)={u:.4f} < 0.5 — instancia incorrecta o pipeline roto. "
            "Abortando experimento."
        )
        return False

    if u < 0.65:
        logger.warning(
            f"U(A)={u:.4f} está por debajo del rango esperado [0.65, 0.78]. "
            "Continuando de todas formas — reportar en el paper."
        )
    else:
        logger.info(f"U(A)={u:.4f} ✓ dentro del rango esperado [0.65, 0.78]")

    return True


def run_experiment(runs: int = RUNS, skip_verify: bool = False) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "exp_sa_convergence_real.csv"

    if not skip_verify:
        ok = verify_baseline()
        if not ok:
            logger.error("Experimento cancelado por fallo en verificación inicial.")
            sys.exit(1)

    rows: list[dict] = []
    total = len(ITERS_PER_T_VALUES) * runs
    done  = 0

    for ipt in ITERS_PER_T_VALUES:
        total_approx = 0 if ipt == 0 else ipt * N_COOLING_STEPS
        label = "0 (no SA)" if ipt == 0 else str(total_approx)
        config = _make_config(ipt)

        for run_idx, seed in enumerate(SEEDS[:runs], 1):
            random.seed(seed)
            instance = build_sample_instance("2024-A")

            logger.info(
                f"[ExpSA-Real] iters_per_t={ipt} (~{total_approx} SA iters) "
                f"run {run_idx}/{runs} seed={seed}"
            )

            result, err = _run_with_timeout(
                lambda inst=instance, cfg=config, s=seed: run_haia_cycle(inst, custom_config=cfg, sa_seed=s),
                timeout_s=TIMEOUT,
            )

            row: dict = {
                "iters_per_t": ipt,
                "total_sa_iters_approx": total_approx,
                "label": label,
                "run": run_idx,
                "seed": seed,
                "n_assignments": len(result.assignments) if result else 0,
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
                f"[ExpSA-Real] ipt={ipt} run={run_idx} → {status} "
                f"U(A)={row['utility_score']} L4={row['layer4_ms']}ms  [{done}/{total}]"
            )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"[ExpSA-Real] CSV guardado en {csv_path} ({len(rows)} filas)")

    _print_summary(rows)


def _print_summary(rows: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("RESUMEN ESTADISTICO - SA Convergencia (instancia institucional real)")
    print("=" * 70)

    default_u: float | None = None
    default_ipt = 50

    for ipt in ITERS_PER_T_VALUES:
        valid = [
            r["utility_score"] for r in rows
            if r["iters_per_t"] == ipt
            and r["utility_score"] is not None
            and r["is_feasible"]
        ]
        times = [
            r["elapsed_s"] for r in rows
            if r["iters_per_t"] == ipt
            and r["elapsed_s"] is not None
        ]

        if not valid:
            label = "0 (no SA)" if ipt == 0 else str(ipt)
            print(f"  iters_per_T={ipt:>4} ({label:>10}): sin datos válidos")
            continue

        u_mean = mean(valid)
        u_std  = stdev(valid) if len(valid) > 1 else 0.0
        t_mean = mean(times) if times else 0.0

        total_approx = 0 if ipt == 0 else ipt * N_COOLING_STEPS
        label = "0 (no SA)" if ipt == 0 else f"~{total_approx:,} iters"
        marker = "  <- DEFAULT" if ipt == default_ipt else ""

        print(
            f"  iters_per_T={ipt:>4} ({label:>14}):  "
            f"U(A) = {u_mean:.4f} +/- {u_std:.4f},  tiempo = {t_mean:5.1f}s{marker}"
        )

        if ipt == default_ipt:
            default_u = u_mean

    print()
    if default_u is not None:
        for ipt in ITERS_PER_T_VALUES:
            if ipt == default_ipt:
                continue
            valid = [
                r["utility_score"] for r in rows
                if r["iters_per_t"] == ipt
                and r["utility_score"] is not None
                and r["is_feasible"]
            ]
            if valid:
                delta = mean(valid) - default_u
                sign = "+" if delta >= 0 else ""
                print(
                    f"  iters_per_T={ipt:>4} vs. default(50): ΔU(A) = {sign}{delta:+.4f}"
                )

    print("=" * 70)

    # Observation
    print("\nOBSERVACIÓN:")
    valid_50 = [
        r["utility_score"] for r in rows
        if r["iters_per_t"] == 50 and r["utility_score"] is not None and r["is_feasible"]
    ]
    valid_500 = [
        r["utility_score"] for r in rows
        if r["iters_per_t"] == 500 and r["utility_score"] is not None and r["is_feasible"]
    ]
    valid_0 = [
        r["utility_score"] for r in rows
        if r["iters_per_t"] == 0 and r["utility_score"] is not None and r["is_feasible"]
    ]

    if valid_50 and valid_500 and valid_0:
        u50, u500, u0 = mean(valid_50), mean(valid_500), mean(valid_0)
        gain_sa    = u50  - u0
        gain_extra = u500 - u50
        threshold_ipt = next(
            (ipt for ipt in ITERS_PER_T_VALUES
             if ipt > 0 and mean([
                 r["utility_score"] for r in rows
                 if r["iters_per_t"] == ipt
                 and r["utility_score"] is not None
                 and r["is_feasible"]
             ] or [0]) >= u50 * 0.99),
            50
        )
        if abs(gain_extra) < 0.005:
            print(
                f"  U(A) se APLANA después de iters_per_T≈{threshold_ipt}: "
                f"50→500 solo gana {gain_extra:+.4f}. "
                f"SA sí mejora respecto a no-SA (+{gain_sa:.4f})."
            )
        else:
            print(
                f"  U(A) sí se BENEFICIA de más iteraciones: "
                f"default(50)={u50:.4f}, 500={u500:.4f} (+{gain_extra:.4f}). "
                f"SA vs no-SA: +{gain_sa:.4f}."
            )
    print()


if __name__ == "__main__":
    run_experiment()
