"""
Generador de instancias sintéticas para experimentos de stress.
Tamaños: S / M / L / XL / XXL.
"""

from __future__ import annotations

import random
from datetime import time

from app.domain.entities import (
    Classroom,
    PreferenceSlot,
    Professor,
    SchedulingInstance,
    Subject,
    TimeSlot,
)

SIZE_CONFIG: dict[str, dict] = {
    "S":   {"subjects": 10,  "classrooms": 6,  "timeslots": 20, "professors": 8},
    "M":   {"subjects": 30,  "classrooms": 15, "timeslots": 30, "professors": 15},
    "L":   {"subjects": 60,  "classrooms": 25, "timeslots": 40, "professors": 25},
    "XL":  {"subjects": 100, "classrooms": 40, "timeslots": 50, "professors": 40},
    "XXL": {"subjects": 150, "classrooms": 60, "timeslots": 60, "professors": 55},
}

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
_START_HOURS = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
_FACULTIES = ["ingenieria", "ciencias", "humanidades", "economia"]
_CONTRACTS = ["hora_catedra", "medio_tiempo", "tiempo_completo"]
_CAPACITIES = [20, 30, 40, 50, 60, 80]


def generate_instance(size: str, seed: int = 42) -> SchedulingInstance:
    if size not in SIZE_CONFIG:
        raise ValueError(f"size must be one of {list(SIZE_CONFIG)}, got '{size}'")

    rng = random.Random(seed)
    cfg = SIZE_CONFIG[size]
    n_sub = cfg["subjects"]
    n_cls = cfg["classrooms"]
    n_ts  = cfg["timeslots"]
    n_pro = cfg["professors"]

    # ── Time slots ───────────────────────────────────────────────────────────
    timeslots: list[TimeSlot] = []
    slot_idx = 0
    for day in _DAYS:
        for h in _START_HOURS:
            if slot_idx >= n_ts:
                break
            code = f"TS_{day[:2].upper()}_{h:02d}"
            timeslots.append(TimeSlot(
                code=code,
                day=day,
                start_time=time(h, 0),
                end_time=time(h + 1, 0) if h < 23 else time(23, 59),
                duration=1.0,
            ))
            slot_idx += 1
        if slot_idx >= n_ts:
            break

    # ── Classrooms ───────────────────────────────────────────────────────────
    classrooms: list[Classroom] = []
    for i in range(n_cls):
        classrooms.append(Classroom(
            code=f"CLS_{i+1:03d}",
            name=f"Salon {i+1}",
            capacity=rng.choice(_CAPACITIES),
            resources=(),
        ))

    # ── Professors ───────────────────────────────────────────────────────────
    professors: list[Professor] = []
    ts_codes = [ts.code for ts in timeslots]
    for i in range(n_pro):
        avail_n = rng.randint(max(5, n_ts // 3), n_ts)
        availability = tuple(rng.sample(ts_codes, min(avail_n, len(ts_codes))))
        professors.append(Professor(
            code=f"PRF_{i+1:03d}",
            name=f"Profesor {i+1}",
            max_weekly_hours=rng.choice([8, 12, 16, 20, 40]),
            contract_type=rng.choice(_CONTRACTS),
            availability=availability,
            preferences=(),
        ))

    # ── Subjects ─────────────────────────────────────────────────────────────
    subjects: list[Subject] = []
    for i in range(n_sub):
        credits = rng.choice([2, 3, 4])
        professor = professors[i % n_pro]
        subjects.append(Subject(
            code=f"SUB_{i+1:03d}",
            name=f"Materia {i+1}",
            credits=credits,
            study_hours=credits,
            weekly_subgroups=1,
            groups=rng.choice([1, 1, 1, 2]),
            enrollment=rng.randint(15, 60),
            professor_code=professor.code,
            required_resources=(),
            optional_resources=(),
            faculty=rng.choice(_FACULTIES),
        ))

    return SchedulingInstance(
        semester=f"EXP_{size}_{seed}",
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors,
    )
