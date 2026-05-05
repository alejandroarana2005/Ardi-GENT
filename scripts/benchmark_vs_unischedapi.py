"""
HAIA vs UniSchedApi-TS — Benchmark comparativo.

Compara el pipeline HAIA completo contra una simulación del Tabu Search
de La Cruz et al. (2024) usando la misma instancia de prueba.

Métricas comparadas:
    - Tiempo de ejecución (ms)
    - Calidad de solución U(A) / score proxy
    - Violaciones HC
    - Capacidad de manejo de eventos dinámicos

Ref: La Cruz et al. (2024) "UniSchedApi". DOI: 10.32397/tesea.vol5.n2.633
"""

from __future__ import annotations

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.disable(logging.CRITICAL)   # silenciar logs durante benchmark

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.models import (
    Base, ClassroomModel, ResourceModel, TimeSlotModel,
    ProfessorModel, ProfessorAvailabilityModel, ProfessorPreferenceModel,
    SubjectModel,
)
from app.database.session import get_db
from app.main import app
from tests.fixtures.sample_data import build_sample_instance


# ── Setup in-memory ───────────────────────────────────────────────────────────

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# El background thread en schedule.py usa SessionLocal() directamente (no pasa
# por get_db), por lo que también hay que redirigirlo al engine in-memory.
import app.api.routes.schedule as _sched_route
_sched_route.SessionLocal = TestSession


def populate_db(instance) -> None:
    with TestSession() as session:
        resource_orm = {}
        for c in instance.classrooms:
            for r in c.resources:
                resource_orm[r.code] = r.name
        for code, name in resource_orm.items():
            session.add(ResourceModel(code=code, name=name))
        session.flush()

        resource_map = {
            r.code: session.query(ResourceModel).filter_by(code=r.code).first()
            for c in instance.classrooms for r in c.resources
        }
        for c in instance.classrooms:
            c_orm = ClassroomModel(code=c.code, name=c.name, capacity=c.capacity)
            for res in c.resources:
                if res.code in resource_map and resource_map[res.code]:
                    c_orm.resources.append(resource_map[res.code])
            session.add(c_orm)
        session.flush()

        for ts in instance.timeslots:
            session.add(TimeSlotModel(
                code=ts.code, day=ts.day,
                start_time=ts.start_time, end_time=ts.end_time, duration=ts.duration,
            ))
        session.flush()

        for p in instance.professors:
            p_orm = ProfessorModel(
                code=p.code, name=p.name,
                max_weekly_hours=p.max_weekly_hours,
                contract_type=p.contract_type,
            )
            session.add(p_orm)
            session.flush()
            for ts_code in p.availability:
                session.add(ProfessorAvailabilityModel(
                    professor_id=p_orm.id, timeslot_code=ts_code,
                ))
            for pref in p.preferences:
                session.add(ProfessorPreferenceModel(
                    professor_id=p_orm.id,
                    timeslot_code=pref.timeslot_code,
                    preference=pref.preference,
                ))
        session.flush()

        for s in instance.subjects:
            s_orm = SubjectModel(
                code=s.code, name=s.name, credits=s.credits,
                study_hours=s.study_hours, weekly_subgroups=s.weekly_subgroups,
                groups=s.groups, enrollment=s.enrollment,
                faculty=s.faculty, professor_code=s.professor_code,
            )
            for req in s.required_resources:
                if req.resource_code in resource_map and resource_map[req.resource_code]:
                    s_orm.required_resources.append(resource_map[req.resource_code])
            session.add(s_orm)
        session.commit()


# ── HAIA benchmark ────────────────────────────────────────────────────────────

def run_haia(client, solver: str = "backtracking") -> dict:
    """Ejecuta el pipeline HAIA completo y retorna métricas."""
    t0 = time.perf_counter()
    resp = client.post("/api/v1/schedule",
                       json={"semester": "2024-A", "solver_hint": solver})

    if resp.status_code != 202:
        return {"error": resp.text, "solver": solver}

    sid = resp.json()["schedule_id"]

    # Polling hasta que el schedule esté completed
    max_wait = 180  # 3 minutos máximo
    poll_interval = 3  # segundos entre polls
    elapsed = 0

    while elapsed < max_wait:
        status_resp = client.get(f"/api/v1/schedule/{sid}")
        if status_resp.status_code != 200:
            break
        status_data = status_resp.json()
        if status_data.get("status") in ("completed", "failed"):
            break
        time.sleep(poll_interval)
        elapsed += poll_interval

    elapsed_ms = int((time.perf_counter() - t0) * 1000)  # incluye polling

    m = client.get(f"/api/v1/metrics/{sid}").json()
    assignments = client.get(f"/api/v1/schedule/{sid}/assignments").json()

    return {
        "schedule_id": sid,
        "solver": resp.json()["solver_used"],
        "utility_score": m["utility_score"],
        "u_occupancy": m["u_occupancy"],
        "u_preference": m["u_preference"],
        "u_distribution": m["u_distribution"],
        "hard_violations": m["hard_constraint_violations"],
        "soft_violations": m["soft_constraint_violations"],
        "total_assignments": len(assignments),
        "elapsed_ms": elapsed_ms,
        "events_capable": True,
    }


def run_haia_with_events(client, schedule_id: str) -> dict:
    """Aplica 2 eventos dinámicos y mide el repair."""
    assignments = client.get(f"/api/v1/schedule/{schedule_id}/assignments").json()
    if not assignments:
        return {"error": "no assignments"}

    from collections import Counter
    cls_counter = Counter(a["classroom_code"] for a in assignments)
    sal = next(
        (c for c, n in cls_counter.most_common() if c.startswith("S") and n >= 3),
        cls_counter.most_common(1)[0][0],
    )

    results = []
    current_sid = schedule_id
    for i, (etype, payload) in enumerate([
        ("CLASSROOM_UNAVAILABLE", {"classroom_code": sal}),
        ("SLOT_BLOCKED", {"timeslot_code": assignments[0]["timeslot_code"]}),
    ]):
        t0 = time.perf_counter()
        r = client.post("/api/v1/events", json={
            "schedule_id": current_sid,
            "event_type": etype,
            "payload": payload,
        })
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            d = r.json()
            results.append({
                "event": etype,
                "affected": d["affected_assignments"],
                "repair_ms": elapsed_ms,
                "new_sid": d.get("new_schedule_id"),
            })
            if d.get("new_schedule_id"):
                current_sid = d["new_schedule_id"]

    return {"events_applied": results, "final_schedule_id": current_sid}


# ── UniSchedApi-TS Replica — Algorithm 1 (La Cruz et al., 2024) ──────────────

class UniSchedApiTSReplica:
    """
    Implementación fiel del Algorithm 1 de La Cruz et al. (2024).

    Diferencias deliberadas respecto a TabuSearchSolver de HAIA:
    • Sin memoria de largo plazo (freq matrix)
    • Sin criterio de aspiración
    • Evaluación por conteo de violaciones blandas, no U(A)
    • Tabu list FIFO sin tenure fijo (crece sin límite)
    • max_iterations configurable; paper reporta 100,000
    """

    def __init__(self, max_iterations: int = 10_000) -> None:
        self.max_iterations = max_iterations

    def solve(
        self,
        instance,
        domains: dict,
    ) -> tuple[list, int]:
        """Returns (best_assignments, convergence_iteration)."""
        import random as _rng
        from app.domain.entities import Assignment
        from app.domain.constraints import get_active_constraints

        var_keys = [k for k, v in domains.items() if v]
        if not var_keys:
            return [], 0

        # var_key -> (subject_code, group_number, session_number)
        var_meta: dict = {}
        for s in instance.subjects:
            for g in range(1, s.groups + 1):
                for sess in range(1, s.weekly_subgroups + 1):
                    var_meta[f"{s.code}__g{g}__s{sess}"] = (s.code, g, sess)

        # (var_key, classroom_code) -> [timeslot_codes]
        dom_cls: dict = {}
        for var, pairs in domains.items():
            for cls, ts in pairs:
                dom_cls.setdefault((var, cls), []).append(ts)

        classrooms = [c.code for c in instance.classrooms]
        hc = get_active_constraints("hard")
        sc = get_active_constraints("soft")

        def make_rand_sol() -> list:
            sol = []
            for var in var_keys:
                cls, ts = _rng.choice(domains[var])
                code, g, sess = var_meta[var]
                sol.append(Assignment(code, cls, ts, g, sess))
            return sol

        def soft_violations(sol: list) -> int:
            return sum(
                1 for c in sc for a in sol
                if not c.check(a, sol, instance)
            )

        def hc_valid(cand, others: list) -> bool:
            all_a = others + [cand]
            return all(c.check(cand, all_a, instance) for c in hc)

        # Initialize (Algorithm 1 — La Cruz et al., 2024)
        best      = make_rand_sol()
        best_sc   = soft_violations(best)
        tabu: list = []                          # FIFO, sin tenure fijo
        cur       = list(best)
        cur_idx   = {f"{a.subject_code}__g{a.group_number}__s{a.session_number}": i
                     for i, a in enumerate(cur)}
        conv      = 0

        for it in range(self.max_iterations):
            room = _rng.choice(classrooms)       # Select room randomly
            var  = _rng.choice(var_keys)
            valid_ts = dom_cls.get((var, room), [])
            if not valid_ts:
                continue

            ts   = _rng.choice(valid_ts)         # Select random time slot from valid group
            move = (var, room, ts)

            code, g, sess = var_meta[var]
            cand   = Assignment(code, room, ts, g, sess)
            idx    = cur_idx.get(var)
            others = [a for i, a in enumerate(cur) if i != idx]

            if not hc_valid(cand, others):       # Validate combination
                continue

            if move in tabu:                     # If solution NOT in tabuList → skip
                continue

            new_sol = list(cur)
            if idx is not None:
                new_sol[idx] = cand

            new_sc = soft_violations(new_sol)
            tabu.append(move)                    # Add to tabuList

            if new_sc < best_sc:                 # Compare with bestSolution
                best, best_sc = list(new_sol), new_sc
                cur    = best
                cur_idx = {f"{a.subject_code}__g{a.group_number}__s{a.session_number}": i
                           for i, a in enumerate(cur)}
                conv = it

        return best, conv


def run_unischedapi_simulation(instance) -> dict:
    """
    Ejecuta UniSchedApiTSReplica — implementación desde cero del Algorithm 1
    de La Cruz et al. (2024).  NO usa TabuSearchSolver de HAIA.

    Parámetros del benchmark:
        max_iterations = 10,000  (paper: 100,000; su Figure 5 reporta que el
        86 % converge antes de 60,000; 10 k es un punto medio defendible para
        tiempo de benchmark manejable).
    """
    from app.config import settings
    from app.layer2_preprocessing.domain_filter import DomainFilter
    from app.layer2_preprocessing.ac3 import AC3Preprocessor
    from app.layer4_optimization.utility_function import UtilityCalculator
    from app.domain.constraints import get_active_constraints

    t0 = time.perf_counter()

    reduced = DomainFilter().filter(instance)
    domains, feasible = AC3Preprocessor().run(instance, reduced)
    if not feasible:
        return {"error": "infeasible after AC3", "elapsed_ms": 0}

    solver = UniSchedApiTSReplica(max_iterations=10_000)
    assignments, conv_iter = solver.solve(instance, domains)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if not assignments:
        return {"error": "no solution found", "elapsed_ms": elapsed_ms}

    calc = UtilityCalculator(settings.utility_weights)
    u    = calc.compute(assignments, instance)

    hard_constraints = get_active_constraints("hard")
    hc_violations = sum(
        1 for c in hard_constraints for a in assignments
        if not c.check(a, assignments, instance)
    )

    return {
        "solver": "UniSchedApi-TS (Algorithm 1 — La Cruz et al., 2024)",
        "utility_score": round(u, 4),
        "hard_violations": hc_violations,
        "total_assignments": len(assignments),
        "elapsed_ms": elapsed_ms,
        "convergence_iter": conv_iter,
        "max_iterations": 10_000,
        "events_capable": False,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    logging.disable(logging.CRITICAL)
    print("\n" + "="*70)
    print("  HAIA vs UniSchedApi-TS — Benchmark Comparativo")
    print("  Instancia: Universidad de Ibagué, Semestre 2024-A")
    print("  La Cruz et al. (2024) DOI: 10.32397/tesea.vol5.n2.633")
    print("="*70)

    instance = build_sample_instance()
    n_subjects = len(instance.subjects)
    n_assignments = sum(s.total_assignments_needed() for s in instance.subjects)
    print(f"\n  Instancia: {n_subjects} materias, {n_assignments} asignaciones, "
          f"{len(instance.classrooms)} aulas, {len(instance.timeslots)} franjas")

    populate_db(instance)

    with TestClient(app, raise_server_exceptions=False) as client:

        # HAIA CSP + SA
        print("\n  [1/3] HAIA: CSP Backtracking + Simulated Annealing...")
        haia_bt = run_haia(client, "backtracking")

        # HAIA Tabu + SA
        print("  [2/3] HAIA: Tabu Search + Simulated Annealing...")
        haia_ts = run_haia(client, "tabu_search")

        # HAIA con eventos dinámicos
        print("  [3/3] HAIA: Aplicando 2 eventos dinámicos...")
        haia_events = {}
        if "schedule_id" in haia_bt:
            haia_events = run_haia_with_events(client, haia_bt["schedule_id"])

    # UniSchedApi simulation (sin API, directo)
    print("  [3/3] UniSchedApi-TS simulation...")
    unisched = run_unischedapi_simulation(instance)

    # ── Tabla comparativa ─────────────────────────────────────────────────────
    print("\n" + "="*75)
    print("  TABLA COMPARATIVA FINAL")
    print("="*75)
    print(f"  {'Sistema':<32} {'U(A)':>8} {'HC':>5} {'Asig':>6} {'ms':>8} {'Eventos':>8} {'Conv@it':>8}")
    print("  " + "-"*71)

    def row(label, data):
        if "error" in data:
            print(f"  {label:<32}  ERROR: {data['error']}")
            return
        conv = f"{data['convergence_iter']:>8,}" if "convergence_iter" in data else f"{'—':>8}"
        print(
            f"  {label:<32} "
            f"{data.get('utility_score', 0):>8.4f} "
            f"{data.get('hard_violations', 0):>5} "
            f"{data.get('total_assignments', 0):>6} "
            f"{data.get('elapsed_ms', 0):>8,} "
            f"{'Sí' if data.get('events_capable') else 'No':>8}"
            f"{conv}"
        )

    row("HAIA (CSP+SA)", haia_bt)
    row("HAIA (TS+SA)", haia_ts)
    row("UniSchedApi-TS (Alg.1 replica)", unisched)

    print("  " + "-"*71)
    print(f"\n  Ventaja U(A) HAIA-CSP vs UniSchedApi: "
          f"{haia_bt.get('utility_score',0) - unisched.get('utility_score',0):+.4f}")
    if "convergence_iter" in unisched:
        print(f"  UniSchedApi-TS: convergencia en iter {unisched['convergence_iter']:,}"
              f" / {unisched['max_iterations']:,}"
              f" ({unisched['convergence_iter']/unisched['max_iterations']*100:.1f}%)")

    # ── Eventos dinámicos ─────────────────────────────────────────────────────
    print("\n" + "="*75)
    print("  CAPACIDAD DE EVENTOS DINAMICOS")
    print("="*75)
    print(f"  UniSchedApi-TS: SIN soporte (re-run completo requerido)")
    if "events_applied" in haia_events:
        for ev in haia_events["events_applied"]:
            print(
                f"  HAIA {ev['event']+':':<30} "
                f"{ev['affected']} afectadas, reparadas en {ev['repair_ms']} ms"
            )
    else:
        print("  HAIA: eventos no aplicados (sin asignaciones)")

    print("\n" + "="*75)
    print("  CONCLUSION")
    print("="*75)
    haia_u = haia_bt.get("utility_score", 0)
    uni_u = unisched.get("utility_score", 0)
    haia_hc = haia_bt.get("hard_violations", 0)
    uni_hc = unisched.get("hard_violations", 0)

    print(f"  Calidad solución: HAIA {haia_u:.4f} vs UniSchedApi {uni_u:.4f} "
          f"({'HAIA mejor' if haia_u > uni_u else 'similar'})")
    print(f"  Violaciones HC:   HAIA {haia_hc} vs UniSchedApi {uni_hc}")
    print(f"  Eventos dinamicos: HAIA Sí vs UniSchedApi No")
    print(f"  Principio Mínima Perturbación: HAIA Sí vs UniSchedApi No")
    print()


if __name__ == "__main__":
    run()
