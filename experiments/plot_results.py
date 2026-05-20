"""
Genera 4 gráficas PNG a partir de los CSVs en experiments_results/.
DPI=150, 8×5 pulgadas, paleta colorblind-friendly (Okabe-Ito).
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless — no GUI needed
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

logger = logging.getLogger("[plot_results]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

RESULTS_DIR = Path(__file__).parent.parent / "experiments_results"
DPI = 150
FIG_SIZE = (8, 5)

# Okabe-Ito colorblind-friendly palette
_OI = ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
       "#0072B2", "#D55E00", "#CC79A7", "#000000"]


def _save(fig: plt.Figure, name: str) -> None:
    path = RESULTS_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Guardado: {path}")


# ── Plot 1: Escalabilidad ─────────────────────────────────────────────────────

def plot_scalability() -> None:
    csv_path = RESULTS_DIR / "exp1_scalability.csv"
    if not csv_path.exists():
        logger.warning(f"[plot1] No encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df = df[df["error"].isna() & df["is_feasible"]]
    if df.empty:
        logger.warning("[plot1] Sin datos válidos en exp1")
        return

    grp = df.groupby("size").agg(
        mean_t=("elapsed_s", "mean"),
        std_t=("elapsed_s", "std"),
        mean_u=("utility_score", "mean"),
        std_u=("utility_score", "std"),
        n_subjects=("n_subjects", "first"),
    ).reset_index()

    size_order = ["S", "M", "L", "XL", "XXL"]
    grp["_ord"] = grp["size"].map({s: i for i, s in enumerate(size_order)})
    grp = grp.sort_values("_ord")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZE)

    # Time (log scale)
    ax1.errorbar(
        grp["size"], grp["mean_t"], yerr=grp["std_t"].fillna(0),
        marker="o", color=_OI[1], capsize=4, linewidth=2,
    )
    ax1.set_yscale("log")
    ax1.set_xlabel("Tamaño de instancia")
    ax1.set_ylabel("Tiempo total (s, escala log)")
    ax1.set_title("Escalabilidad — Tiempo")
    ax1.grid(True, which="both", alpha=0.3)

    # Utility
    ax2.errorbar(
        grp["size"], grp["mean_u"], yerr=grp["std_u"].fillna(0),
        marker="s", color=_OI[2], capsize=4, linewidth=2,
    )
    ax2.set_ylim(0, 1)
    ax2.set_xlabel("Tamaño de instancia")
    ax2.set_ylabel("U(A) media")
    ax2.set_title("Escalabilidad — Calidad U(A)")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Experimento 1 — Escalabilidad HAIA", fontsize=12, fontweight="bold")
    fig.tight_layout()
    _save(fig, "exp1_scalability.png")


# ── Plot 2: Convergencia SA ───────────────────────────────────────────────────

def plot_sa_convergence() -> None:
    csv_path = RESULTS_DIR / "exp2_sa_iterations.csv"
    if not csv_path.exists():
        logger.warning(f"[plot2] No encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df = df[df["error"].isna() & df["is_feasible"]]
    if df.empty:
        logger.warning("[plot2] Sin datos válidos en exp2")
        return

    grp = df.groupby("iters_per_t").agg(
        mean_u=("utility_score", "mean"),
        std_u=("utility_score", "std"),
        mean_l4=("layer4_ms", "mean"),
        std_l4=("layer4_ms", "std"),
        total_sa=("total_sa_iters_approx", "first"),
    ).reset_index()
    grp = grp.sort_values("iters_per_t")

    labels = grp["total_sa"].astype(str)
    labels = labels.replace("0", "0\n(no SA)")
    x = np.arange(len(grp))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZE)

    ax1.bar(x, grp["mean_u"], color=_OI[0], alpha=0.85, width=0.6,
            yerr=grp["std_u"].fillna(0), capsize=4)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7)
    ax1.set_ylim(0, 1)
    ax1.set_xlabel("Iteraciones SA (aprox.)")
    ax1.set_ylabel("U(A) media")
    ax1.set_title("SA — Calidad vs Iteraciones")
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(x, grp["mean_l4"] / 1000, color=_OI[4], alpha=0.85, width=0.6,
            yerr=(grp["std_l4"].fillna(0) / 1000), capsize=4)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=7)
    ax2.set_xlabel("Iteraciones SA (aprox.)")
    ax2.set_ylabel("Tiempo Capa 4 (s)")
    ax2.set_title("SA — Tiempo vs Iteraciones")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("Experimento 2 — Convergencia del Recocido Simulado",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    _save(fig, "exp2_sa_iterations.png")


# ── Plot 3: Comparación de solvers ────────────────────────────────────────────

def plot_solver_comparison() -> None:
    csv_path = RESULTS_DIR / "exp3_solver_comparison.csv"
    if not csv_path.exists():
        logger.warning(f"[plot3] No encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df = df[df["error"].isna() & df["is_feasible"]]
    if df.empty:
        logger.warning("[plot3] Sin datos válidos en exp3")
        return

    grp = df.groupby(["solver", "sa_enabled"]).agg(
        mean_u=("utility_score", "mean"),
        std_u=("utility_score", "std"),
        mean_t=("elapsed_s", "mean"),
        std_t=("elapsed_s", "std"),
    ).reset_index()

    solvers = ["backtracking", "tabu_search", "milp"]
    x = np.arange(len(solvers))
    w = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZE)

    for i, (sa_enabled, label, color) in enumerate(
        [(False, "Sin SA", _OI[0]), (True, "Con SA", _OI[1])]
    ):
        sub = grp[grp["sa_enabled"] == sa_enabled].set_index("solver").reindex(solvers)
        ax1.bar(x + i * w - w / 2, sub["mean_u"].fillna(0),
                w, label=label, color=color, alpha=0.85,
                yerr=sub["std_u"].fillna(0), capsize=4)
        ax2.bar(x + i * w - w / 2, sub["mean_t"].fillna(0),
                w, label=label, color=color, alpha=0.85,
                yerr=sub["std_t"].fillna(0), capsize=4)

    ax1.set_xticks(x)
    ax1.set_xticklabels(solvers, rotation=10, fontsize=9)
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("U(A) media")
    ax1.set_title("Calidad por solver")
    ax1.legend(fontsize=8)
    ax1.grid(axis="y", alpha=0.3)

    ax2.set_xticks(x)
    ax2.set_xticklabels(solvers, rotation=10, fontsize=9)
    ax2.set_ylabel("Tiempo total (s)")
    ax2.set_title("Tiempo por solver")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("Experimento 3 — Comparación de Solvers",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    _save(fig, "exp3_solver_comparison.png")


# ── Plot 4: Eventos dinámicos ─────────────────────────────────────────────────

def plot_dynamic_events() -> None:
    csv_path = RESULTS_DIR / "exp4_dynamic_events.csv"
    if not csv_path.exists():
        logger.warning(f"[plot4] No encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df = df[df["error"].isna() & df["event_idx"] > 0]
    if df.empty:
        logger.warning("[plot4] Sin datos válidos en exp4")
        return

    grp = df.groupby(["n_events_target", "event_idx"]).agg(
        mean_repair=("repair_elapsed_s", "mean"),
        std_repair=("repair_elapsed_s", "std"),
        mean_du=("delta_utility", "mean"),
        std_du=("delta_utility", "std"),
        mean_perturb=("perturbation_ratio", "mean"),
    ).reset_index()

    # Summary by n_events_target (last event of each run)
    summary = df[df["event_idx"] == df.groupby(
        ["n_events_target", "run"])["event_idx"].transform("max")
    ].groupby("n_events_target").agg(
        mean_total_repair=("repair_elapsed_s", lambda x: df.loc[x.index.get_level_values(0) if hasattr(x.index, 'get_level_values') else x.index, "repair_elapsed_s"].sum() / 3
                          if False else x.sum()),
        mean_du=("delta_utility", "mean"),
        std_du=("delta_utility", "std"),
    ).reset_index()

    n_events_vals = sorted(df["n_events_target"].unique())
    x = np.arange(len(n_events_vals))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIG_SIZE)

    # Mean repair time per event for each N_EVENTS target
    for i, n in enumerate(n_events_vals):
        sub = grp[grp["n_events_target"] == n]
        ax1.plot(
            sub["event_idx"], sub["mean_repair"],
            marker="o", label=f"N={n}", color=_OI[i % len(_OI)], linewidth=1.5,
        )
    ax1.set_xlabel("Índice del evento")
    ax1.set_ylabel("Tiempo de reparación (s)")
    ax1.set_title("Tiempo de reparación por evento")
    ax1.legend(fontsize=8, title="Eventos totales")
    ax1.grid(alpha=0.3)

    # ΔU(A) by N_EVENTS target
    means = [
        df[df["n_events_target"] == n]["delta_utility"].mean()
        for n in n_events_vals
    ]
    stds = [
        df[df["n_events_target"] == n]["delta_utility"].std()
        for n in n_events_vals
    ]
    ax2.bar([str(n) for n in n_events_vals], means, color=_OI[5], alpha=0.85,
            yerr=[s if not np.isnan(s) else 0 for s in stds], capsize=4)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("Número de eventos")
    ax2.set_ylabel("ΔU(A) promedio")
    ax2.set_title("Impacto en calidad del horario")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("Experimento 4 — Re-optimización Dinámica (Capa 5)",
                 fontsize=12, fontweight="bold")
    fig.tight_layout()
    _save(fig, "exp4_dynamic_events.png")


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    plot_scalability()
    plot_sa_convergence()
    plot_solver_comparison()
    plot_dynamic_events()
    logger.info("[plot_results] Todas las gráficas generadas.")


if __name__ == "__main__":
    main()
