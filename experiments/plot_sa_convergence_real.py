"""
Gráfica — Convergencia del SA en la instancia institucional real.
Lee experiments_results/exp_sa_convergence_real.csv y genera:
    experiments_results/exp_sa_convergence_real.png

Eje X : iters_per_T (log scale; 0 = punto especial separado a la izquierda)
Eje Y1: U(A) promedio ± std  (azul/verde)
Eje Y2: tiempo total (s)     (naranja)
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

logger = logging.getLogger("[plot-SA-real]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

RESULTS_DIR = Path(__file__).parent.parent / "experiments_results"
DPI         = 150
FIG_SIZE    = (8, 5)

_BLUE   = "#0072B2"
_GREEN  = "#009E73"
_ORANGE = "#E69F00"
_RED    = "#D55E00"
_GRAY   = "#999999"


def main() -> None:
    csv_path = RESULTS_DIR / "exp_sa_convergence_real.csv"
    if not csv_path.exists():
        logger.error(f"CSV no encontrado: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df = df[df["error"].isna() & df["is_feasible"].astype(bool)]
    if df.empty:
        logger.error("Sin filas válidas en el CSV.")
        return

    grp = (
        df.groupby("iters_per_t")
        .agg(
            mean_u=("utility_score", "mean"),
            std_u=("utility_score", "std"),
            mean_t=("elapsed_s", "mean"),
            std_t=("elapsed_s", "std"),
            total_sa=("total_sa_iters_approx", "first"),
        )
        .reset_index()
        .sort_values("iters_per_t")
    )
    grp["std_u"] = grp["std_u"].fillna(0)
    grp["std_t"] = grp["std_t"].fillna(0)

    # Split into "no SA" (ipt=0) and "with SA" (ipt > 0)
    row_nosa  = grp[grp["iters_per_t"] == 0]
    grp_sa    = grp[grp["iters_per_t"] >  0]

    nosa_u = float(row_nosa["mean_u"].iloc[0]) if not row_nosa.empty else None
    nosa_t = float(row_nosa["mean_t"].iloc[0]) if not row_nosa.empty else None

    # X positions: one fake position for 0 then log-positions for the rest
    ipt_vals = grp_sa["iters_per_t"].values
    x_log    = np.log10(ipt_vals)          # 0, 0.699, 1, 1.398, 1.699, 2, 2.301, 2.699
    x_offset = x_log[0] - 1.5             # gap before first point
    x_nosa   = x_offset - 0.6             # position of the "no SA" point

    fig, ax1 = plt.subplots(figsize=FIG_SIZE)
    ax2 = ax1.twinx()

    # ── U(A) line (left axis) ─────────────────────────────────────────────────
    ax1.errorbar(
        x_log, grp_sa["mean_u"], yerr=grp_sa["std_u"],
        marker="o", color=_BLUE, linewidth=2, capsize=4, label="U(A) con SA",
        zorder=3,
    )

    # "no SA" point (special, left of the log range)
    if nosa_u is not None:
        ax1.errorbar(
            [x_nosa], [nosa_u],
            yerr=[float(row_nosa["std_u"].iloc[0])],
            marker="D", color=_GREEN, markersize=8, capsize=4,
            linewidth=0, elinewidth=1.5, label="U(A) sin SA (baseline)",
            zorder=4,
        )
        # horizontal dashed baseline
        ax1.axhline(nosa_u, color=_GREEN, linestyle="--", linewidth=1.2,
                    alpha=0.6, zorder=2)

    # ── Tiempo (right axis) ───────────────────────────────────────────────────
    ax2.errorbar(
        x_log, grp_sa["mean_t"], yerr=grp_sa["std_t"],
        marker="s", color=_ORANGE, linewidth=1.5, capsize=3,
        linestyle="--", label="Tiempo (s)", zorder=3,
    )
    if nosa_t is not None:
        ax2.errorbar(
            [x_nosa], [nosa_t],
            marker="D", color=_ORANGE, markersize=6, alpha=0.6,
            linewidth=0, zorder=3,
        )

    # ── Annotation: default (ipt=50) ─────────────────────────────────────────
    default_row = grp_sa[grp_sa["iters_per_t"] == 50]
    if not default_row.empty:
        xd = float(np.log10(50))
        yd = float(default_row["mean_u"].iloc[0])
        ax1.annotate(
            "★ default\n(iters_per_T=50)",
            xy=(xd, yd),
            xytext=(xd + 0.35, yd + 0.015),
            fontsize=8,
            color=_BLUE,
            arrowprops=dict(arrowstyle="->", color=_BLUE, lw=1.2),
        )

    # ── X-axis ticks ──────────────────────────────────────────────────────────
    all_x     = [x_nosa] + list(x_log)
    all_labels = ["0\n(no SA)"] + [
        f"{v:,}" if v >= 1000 else str(v)
        for v in grp_sa["total_sa"].astype(int).values
    ]
    # Add gap indicator between "no SA" and the rest
    ax1.axvline(x=(x_nosa + x_log[0]) / 2, color=_GRAY, linewidth=0.8,
                linestyle=":", alpha=0.5)

    ax1.set_xticks(all_x)
    ax1.set_xticklabels(all_labels, fontsize=7)
    ax1.set_xlabel("iters_per_T  →  Iteraciones SA totales aproximadas", fontsize=9)

    # ── Axes labels & formatting ──────────────────────────────────────────────
    ax1.set_ylabel("U(A) promedio", color=_BLUE, fontsize=9)
    ax2.set_ylabel("Tiempo total (s)", color=_ORANGE, fontsize=9)
    ax1.tick_params(axis="y", labelcolor=_BLUE)
    ax2.tick_params(axis="y", labelcolor=_ORANGE)

    y_margin = 0.04
    all_u = list(grp["mean_u"]) + ([nosa_u] if nosa_u else [])
    ax1.set_ylim(min(all_u) - y_margin, max(all_u) + y_margin + 0.04)

    ax1.grid(axis="y", alpha=0.25, zorder=1)
    ax1.grid(axis="x", alpha=0.12, zorder=1)

    # ── Legend ────────────────────────────────────────────────────────────────
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc="lower right", fontsize=8, framealpha=0.9)

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.suptitle(
        "Convergencia del Recocido Simulado en la instancia institucional\n"
        "(105 asignaciones, 3 corridas por configuración)",
        fontsize=10, fontweight="bold", y=1.01,
    )
    fig.tight_layout()

    out = RESULTS_DIR / "exp_sa_convergence_real.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Guardado: {out}")


if __name__ == "__main__":
    main()
