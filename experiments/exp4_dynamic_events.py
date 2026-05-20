"""
Experimento 4 — Re-optimización dinámica (Capa 5).
Aplica N eventos PROFESSOR_CANCELLED sucesivos sobre un horario inicial
y mide tiempo de reparación y ΔU(A) acumulado.

Salida: experiments_results/exp4_dynamic_events.csv
"""

from __future__ import annotations

import csv
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.bdi.agent import HAIAAgent
from app.config import settings
from app.database.models import ScheduleModel
from app.layer5_dynamic.event_handler import DynamicEvent
from experiments._common import (
    populate_db, run_haia_on_db, setup_in_memory_db, _run_with_timeout,
)
from experiments.instance_generator import generate_instance

logger = logging.getLogger("[Exp4-DynamicEvents]")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)

INSTANCE_SIZE = "M"
RUNS          = 3
TIMEOUT       = 300   # 5 min per full run (initial + all repairs)
RESULTS_DIR   = Path(__file__).parent.parent / "experiments_results"
N_EVENTS_LIST = [1, 5, 10, 20]

CSV_FIELDS = [
    "n_events_target", "run", "seed",
    "initial_utility", "initial_assignments",
    "event_idx", "professor_code",
    "repair_elapsed_s", "repair_affected", "repair_repaired",
    "perturbation_ratio", "final_utility",
    "delta_utility", "is_successful", "error",
]


def _run_scenario(instance, n_events: int) -> list[dict]:
    """
    Run one complete scenario: initial schedule + n_events repair cycles.
    Returns list of row dicts (one per event, plus baseline row at event_idx=0).
    """
    _, Session = setup_in_memory_db()
    rows: list[dict] = []

    with Session() as db:
        populate_db(db, instance)

        # Initial schedule
        initial_result = run_haia_on_db(db, instance, solver_hint=None, custom_config=None)
        if not initial_result.is_feasible:
            return [{
                "event_idx": 0,
                "error": f"Initial solve infeasible: {initial_result.violations}",
            }]

        initial_utility = initial_result.utility_score
        initial_assignments = len(initial_result.assignments)
        current_schedule_id = initial_result.schedule_id

        rows.append({
            "event_idx": 0,
            "professor_code": None,
            "repair_elapsed_s": None,
            "repair_affected": None,
            "repair_repaired": None,
            "perturbation_ratio": None,
            "final_utility": round(initial_utility, 6),
            "delta_utility": 0.0,
            "is_successful": True,
            "initial_utility": round(initial_utility, 6),
            "initial_assignments": initial_assignments,
            "error": None,
        })

        # Pick professors that have subjects (cycle through them to avoid repeats)
        prof_codes = [p.code for p in instance.professors]
        n_actual = min(n_events, len(prof_codes))

        for ev_idx in range(1, n_actual + 1):
            prof_code = prof_codes[(ev_idx - 1) % len(prof_codes)]

            agent = HAIAAgent(db_session=db, config=settings)
            event = DynamicEvent(
                event_type="PROFESSOR_CANCELLED",
                schedule_id=current_schedule_id,
                payload={"professor_code": prof_code},
            )

            repair = agent.handle_dynamic_event(event)

            # Read updated utility from DB if repair succeeded
            final_utility = initial_utility
            if repair.is_successful and repair.new_schedule_id:
                sched = (
                    db.query(ScheduleModel)
                    .filter(ScheduleModel.schedule_id == repair.new_schedule_id)
                    .first()
                )
                if sched:
                    final_utility = sched.utility_score
                current_schedule_id = repair.new_schedule_id

            rows.append({
                "event_idx": ev_idx,
                "professor_code": prof_code,
                "repair_elapsed_s": round(repair.elapsed_seconds, 3),
                "repair_affected": repair.affected_count,
                "repair_repaired": repair.repaired_count,
                "perturbation_ratio": round(repair.perturbation_ratio, 4),
                "final_utility": round(final_utility, 6),
                "delta_utility": round(final_utility - initial_utility, 6),
                "is_successful": repair.is_successful,
                "initial_utility": round(initial_utility, 6),
                "initial_assignments": initial_assignments,
                "error": None if repair.is_successful else repair.message,
            })

            if not repair.is_successful:
                logger.warning(
                    f"[Exp4] Reparación fallida en evento {ev_idx}: {repair.message}"
                )
                break

    return rows


def run_experiment(runs: int = RUNS) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / "exp4_dynamic_events.csv"

    all_rows: list[dict] = []
    total = len(N_EVENTS_LIST) * runs
    done  = 0

    for n_events in N_EVENTS_LIST:
        for run_idx in range(1, runs + 1):
            seed = run_idx * 100
            instance = generate_instance(INSTANCE_SIZE, seed=seed)

            logger.info(
                f"[Exp4] n_events={n_events} run={run_idx}/{runs} seed={seed}"
            )

            scenario_rows, err = _run_with_timeout(
                lambda inst=instance, n=n_events: _run_scenario(inst, n),
                timeout_s=TIMEOUT,
            )

            if err or scenario_rows is None:
                all_rows.append({
                    "n_events_target": n_events,
                    "run": run_idx,
                    "seed": seed,
                    "event_idx": -1,
                    "error": err or "unknown error",
                    **{f: None for f in CSV_FIELDS
                       if f not in ("n_events_target", "run", "seed", "event_idx", "error")},
                })
                done += 1
                logger.error(f"[Exp4] scenario error: {err}")
                continue

            for row in scenario_rows:
                row["n_events_target"] = n_events
                row["run"] = run_idx
                row["seed"] = seed
            all_rows.extend(scenario_rows)
            done += 1

            final_row = scenario_rows[-1]
            logger.info(
                f"[Exp4] n_events={n_events} run={run_idx} → "
                f"ΔU(A)={final_row.get('delta_utility')} "
                f"repair_t={final_row.get('repair_elapsed_s')}s  [{done}/{total}]"
            )

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"[Exp4] CSV guardado en {csv_path} ({len(all_rows)} filas)")


if __name__ == "__main__":
    run_experiment()
