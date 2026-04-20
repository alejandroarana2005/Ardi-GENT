"""
HAIA Agent — Datos de prueba basados en la Universidad de Ibagué.
Coherentes con los datos reales de los semestres 2023-A y 2023-B usados en
La Cruz et al. (2024) "UniSchedApi".

Configuración:
    - 30 materias de Ingeniería de Sistemas
    - 15 aulas con capacidades 20, 30, 40, 60
    - 5 recursos: computadores, proyector, TV, lab_software, lab_electronica
    - 24 franjas: 4 por día × 6 días (Lunes-Sábado) — igual al modelo UniSchedApi
    - 20 docentes: 70% hora-cátedra, 30% tiempo completo
    - Restricciones: no lunes 7am, preferir mañanas, no > 3h consecutivas
"""

from __future__ import annotations

import random
from datetime import time

from app.domain.entities import (
    Classroom,
    Constraint,
    PreferenceSlot,
    Professor,
    Resource,
    ResourceRequirement,
    SchedulingInstance,
    Subject,
    TimeSlot,
)


# ─────────────────────── Recursos ────────────────────────────────────────────

def build_resources() -> list[Resource]:
    return [
        Resource(code="COMP", name="computers"),
        Resource(code="PROJ", name="projector"),
        Resource(code="TV", name="tv"),
        Resource(code="LSOFT", name="software_lab"),
        Resource(code="LELEC", name="electronics_lab"),
    ]


# ─────────────────────── Aulas ───────────────────────────────────────────────

def build_classrooms(resources: list[Resource]) -> list[Classroom]:
    comp = next(r for r in resources if r.code == "COMP")
    proj = next(r for r in resources if r.code == "PROJ")
    tv = next(r for r in resources if r.code == "TV")
    lsoft = next(r for r in resources if r.code == "LSOFT")
    lelec = next(r for r in resources if r.code == "LELEC")

    return [
        # Salones regulares
        Classroom("S101", "Salón 101", 40, (proj,)),
        Classroom("S102", "Salón 102", 40, (proj,)),
        Classroom("S103", "Salón 103", 30, (proj, tv)),
        Classroom("S104", "Salón 104", 30, (proj,)),
        Classroom("S105", "Salón 105", 20, (proj,)),
        Classroom("S201", "Salón 201", 60, (proj, tv)),
        Classroom("S202", "Salón 202", 60, (proj,)),
        Classroom("S203", "Salón 203", 40, (proj, tv)),
        Classroom("S204", "Salón 204", 30, (proj,)),
        Classroom("S205", "Salón 205", 20, ()),
        # Laboratorios
        Classroom("LSOF1", "Lab Software 1", 30, (comp, proj, lsoft)),
        Classroom("LSOF2", "Lab Software 2", 30, (comp, proj, lsoft)),
        Classroom("LSOF3", "Lab Software 3", 20, (comp, lsoft)),
        Classroom("LELE1", "Lab Electrónica 1", 25, (comp, lelec)),
        Classroom("LELE2", "Lab Electrónica 2", 25, (comp, lelec)),
    ]


# ─────────────────────── Franjas horarias ────────────────────────────────────

def build_timeslots() -> list[TimeSlot]:
    """
    4 franjas × 6 días = 24 franjas.
    Franjas: 7-9h, 9-11h, 11-13h, 14-16h (mañana/tarde).
    Ref: La Cruz et al. (2024) — modelo de franjas Universidad de Ibagué.
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    day_codes = {"Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED",
                 "Thursday": "THU", "Friday": "FRI", "Saturday": "SAT"}

    slots_def = [
        ("1", time(7, 0),  time(9, 0),  2.0),
        ("2", time(9, 0),  time(11, 0), 2.0),
        ("3", time(11, 0), time(13, 0), 2.0),
        ("4", time(14, 0), time(16, 0), 2.0),
    ]

    timeslots = []
    for day in days:
        day_code = day_codes[day]
        for slot_num, start, end, dur in slots_def:
            timeslots.append(
                TimeSlot(
                    code=f"TS_{day_code}_{slot_num}",
                    day=day,
                    start_time=start,
                    end_time=end,
                    duration=dur,
                )
            )
    return timeslots


# ─────────────────────── Docentes ────────────────────────────────────────────

def _preference_for_slot(ts_code: str, contract_type: str) -> float:
    """
    Genera preferencia realista según franja horaria y tipo de contrato.
    Llamar con random.seed(42) activo para reproducibilidad.

    Franjas (4 por día):
        Slot 1 (7-9h)  → mañana     → [0.7, 1.0]
        Slot 2 (9-11h) → mañana     → [0.7, 1.0]
        Slot 3 (11-13h)→ almuerzo   → [0.1, 0.4]
        Slot 4 (14-16h)→ tarde      → [0.4, 0.7]
    No hay franjas de noche en el dataset U. Ibagué (max 16h).
    """
    slot_num = int(ts_code.split("_")[-1])
    if slot_num in (1, 2):
        return round(random.uniform(0.7, 1.0), 2)
    elif slot_num == 3:
        return round(random.uniform(0.1, 0.4), 2)
    else:  # slot_num == 4
        return round(random.uniform(0.4, 0.7), 2)


def build_professors(timeslots: list[TimeSlot]) -> list[Professor]:
    """
    20 docentes: 14 hora-cátedra (70%) + 6 tiempo completo (30%).
    Preferencias generadas con random.seed(42) para reproducibilidad.
    """
    random.seed(42)

    all_ts_codes = [ts.code for ts in timeslots]
    # Hora cátedra: disponibles L-V, máx 20h/sem
    hc_availability = tuple(c for c in all_ts_codes if not c.startswith("TS_SAT"))

    def make_prefs(ts_codes: list[str], contract_type: str) -> tuple[PreferenceSlot, ...]:
        return tuple(
            PreferenceSlot(
                timeslot_code=c,
                preference=_preference_for_slot(c, contract_type),
            )
            for c in ts_codes
        )

    professors = [
        # Tiempo completo (6)
        Professor(
            code="P001", name="Prof. García, Ana",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        Professor(
            code="P002", name="Prof. Rodríguez, Carlos",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        Professor(
            code="P003", name="Prof. Martínez, Laura",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        Professor(
            code="P004", name="Prof. López, Juan",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        Professor(
            code="P005", name="Prof. Hernández, María",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        Professor(
            code="P006", name="Prof. Vargas, Diego",
            availability=tuple(all_ts_codes),
            preferences=make_prefs(all_ts_codes, "tiempo_completo"),
            max_weekly_hours=40, contract_type="tiempo_completo",
        ),
        # Hora cátedra (14)
        Professor(
            code="P007", name="Prof. Torres, Camila",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P008", name="Prof. Jiménez, Pedro",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P009", name="Prof. Gómez, Sandra",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P010", name="Prof. Peña, Andrés",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P011", name="Prof. Ríos, Patricia",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P012", name="Prof. Castro, Felipe",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P013", name="Prof. Morales, Viviana",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P014", name="Prof. Reyes, Sergio",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P015", name="Prof. Ortiz, Daniela",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P016", name="Prof. Díaz, Ricardo",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P017", name="Prof. Suárez, Claudia",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P018", name="Prof. Mendoza, Hernán",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P019", name="Prof. Acosta, Gloria",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            code="P020", name="Prof. Parra, Mauricio",
            availability=hc_availability,
            preferences=make_prefs(list(hc_availability), "hora_catedra"),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
    ]
    return professors


# ─────────────────────── Materias ────────────────────────────────────────────

def build_subjects() -> list[Subject]:
    """
    30 materias del plan de estudios de Ingeniería de Sistemas,
    coherentes con la carga real de la Universidad de Ibagué.
    """
    comp = ResourceRequirement(resource_code="COMP")
    proj = ResourceRequirement(resource_code="PROJ")
    lsoft = ResourceRequirement(resource_code="LSOFT")
    lelec = ResourceRequirement(resource_code="LELEC")

    return [
        # ── Primer semestre ──────────────────────────────────────────────────
        Subject("ISIS101", "Fundamentos de Programación", 3, 4, 2, 2, 25,
                "P001", (comp,), (), faculty="ingenieria"),
        Subject("ISIS102", "Matemáticas Discretas", 3, 4, 2, 2, 40,
                "P002", (proj,), (), faculty="ingenieria"),
        Subject("ISIS103", "Introducción a Ingeniería de Sistemas", 2, 3, 1, 3, 40,
                "P003", (proj,), (), faculty="ingenieria"),
        Subject("MAT101", "Cálculo Diferencial", 4, 5, 2, 3, 40,
                "P004", (proj,), (), faculty="ingenieria"),
        Subject("FIS101", "Física Mecánica", 4, 5, 2, 2, 40,
                "P005", (proj,), (lelec,), faculty="ingenieria"),

        # ── Segundo semestre ─────────────────────────────────────────────────
        Subject("ISIS201", "Programación Orientada a Objetos", 3, 4, 2, 2, 25,
                "P006", (comp,), (proj,), faculty="ingenieria"),
        Subject("ISIS202", "Estructuras de Datos", 3, 4, 2, 2, 25,
                "P007", (comp,), (), faculty="ingenieria"),
        Subject("MAT201", "Cálculo Integral", 4, 5, 2, 3, 40,
                "P008", (proj,), (), faculty="ingenieria"),
        Subject("MAT202", "Álgebra Lineal", 3, 4, 2, 2, 40,
                "P009", (proj,), (), faculty="ingenieria"),
        Subject("ISIS203", "Circuitos Digitales", 3, 4, 2, 2, 22,
                "P010", (lelec,), (), faculty="ingenieria"),

        # ── Tercer semestre ──────────────────────────────────────────────────
        Subject("ISIS301", "Algoritmos y Complejidad", 3, 4, 2, 2, 28,
                "P011", (comp,), (), faculty="ingenieria"),
        Subject("ISIS302", "Bases de Datos I", 3, 4, 2, 2, 28,
                "P012", (comp, proj), (lsoft,), faculty="ingenieria"),
        Subject("ISIS303", "Arquitectura de Computadores", 3, 4, 2, 2, 35,
                "P013", (proj,), (lelec,), faculty="ingenieria"),
        Subject("MAT301", "Probabilidad y Estadística", 3, 4, 2, 2, 45,
                "P014", (proj,), (), faculty="ingenieria"),
        Subject("ISIS304", "Sistemas Operativos I", 3, 4, 2, 2, 30,
                "P015", (proj,), (comp,), faculty="ingenieria"),

        # ── Cuarto semestre ──────────────────────────────────────────────────
        Subject("ISIS401", "Redes de Computadores I", 3, 4, 2, 2, 28,
                "P016", (proj,), (comp,), faculty="ingenieria"),
        Subject("ISIS402", "Bases de Datos II", 3, 4, 2, 2, 25,
                "P012", (comp, lsoft), (), faculty="ingenieria"),
        Subject("ISIS403", "Ingeniería de Software I", 3, 4, 2, 2, 30,
                "P017", (proj,), (), faculty="ingenieria"),
        Subject("ISIS404", "Sistemas Operativos II", 3, 4, 2, 1, 28,
                "P015", (proj,), (comp,), faculty="ingenieria"),
        Subject("ISIS405", "Lógica y Programación Funcional", 2, 3, 1, 2, 25,
                "P001", (comp,), (), faculty="ingenieria"),

        # ── Quinto semestre ──────────────────────────────────────────────────
        Subject("ISIS501", "Ingeniería de Software II", 3, 4, 2, 2, 28,
                "P017", (proj,), (), faculty="ingenieria"),
        Subject("ISIS502", "Inteligencia Artificial", 3, 4, 2, 2, 30,
                "P006", (comp, proj), (), faculty="ingenieria"),
        Subject("ISIS503", "Redes de Computadores II", 3, 4, 2, 1, 25,
                "P016", (proj,), (), faculty="ingenieria"),
        Subject("ISIS504", "Desarrollo Web", 3, 4, 2, 2, 28,
                "P018", (comp, lsoft), (), faculty="ingenieria"),
        Subject("ISIS505", "Teoría de Compiladores", 3, 4, 2, 1, 22,
                "P011", (comp,), (), faculty="ingenieria"),

        # ── Sexto semestre ───────────────────────────────────────────────────
        Subject("ISIS601", "Electiva I — Machine Learning", 3, 4, 2, 1, 25,
                "P002", (comp, lsoft), (), faculty="ingenieria"),
        Subject("ISIS602", "Seguridad Informática", 3, 4, 2, 1, 28,
                "P019", (comp, proj), (), faculty="ingenieria"),
        Subject("ISIS603", "Desarrollo Móvil", 3, 4, 2, 1, 30,
                "P018", (comp, lsoft), (), faculty="ingenieria"),
        Subject("ISIS604", "Gestión de Proyectos TI", 2, 3, 1, 2, 35,
                "P020", (proj,), (), faculty="ingenieria"),
        Subject("ISIS605", "Electiva II — IoT", 3, 4, 2, 1, 22,
                "P010", (comp, lelec), (), faculty="ingenieria"),
    ]


# ─────────────────────── Instancia completa ──────────────────────────────────

def build_sample_instance(semester: str = "2024-A") -> SchedulingInstance:
    """
    Construye la instancia completa de prueba.
    Estadísticas esperadas (coherentes con La Cruz et al., 2024):
        - 30 materias, 54 asignaciones totales (grupos × sesiones)
        - 15 aulas, 24 franjas → 360 slots disponibles
        - Densidad: 54/360 = 15% (holgada, factible)
    """
    resources = build_resources()
    classrooms = build_classrooms(resources)
    timeslots = build_timeslots()
    professors = build_professors(timeslots)
    subjects = build_subjects()

    return SchedulingInstance(
        semester=semester,
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors,
    )


# ─────────────────────── Helpers para tests ──────────────────────────────────

def build_minimal_instance() -> SchedulingInstance:
    """Instancia mínima de 3 materias para tests unitarios rápidos."""
    resources = [Resource("PROJ", "projector"), Resource("COMP", "computers")]
    proj = ResourceRequirement(resource_code="PROJ")
    comp = ResourceRequirement(resource_code="COMP")

    classrooms = [
        Classroom("A1", "Aula 1", 30, (resources[0],)),
        Classroom("A2", "Aula 2", 25, (resources[0], resources[1])),
        Classroom("L1", "Lab 1", 20, (resources[1],)),
    ]
    timeslots = [
        TimeSlot("TS_MON_1", "Monday", time(7, 0),  time(9, 0),  2.0),
        TimeSlot("TS_MON_2", "Monday", time(9, 0),  time(11, 0), 2.0),
        TimeSlot("TS_TUE_1", "Tuesday", time(7, 0), time(9, 0),  2.0),
        TimeSlot("TS_TUE_2", "Tuesday", time(9, 0), time(11, 0), 2.0),
        TimeSlot("TS_WED_1", "Wednesday", time(7, 0), time(9, 0), 2.0),
        TimeSlot("TS_WED_2", "Wednesday", time(9, 0), time(11, 0), 2.0),
    ]
    professors = [
        Professor(
            "P_TEST1", "Prof. Test 1",
            availability=tuple(ts.code for ts in timeslots),
            preferences=tuple(
                PreferenceSlot(timeslot_code=ts.code, preference=0.8)
                for ts in timeslots
            ),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
        Professor(
            "P_TEST2", "Prof. Test 2",
            availability=tuple(ts.code for ts in timeslots),
            preferences=tuple(
                PreferenceSlot(timeslot_code=ts.code, preference=0.6)
                for ts in timeslots
            ),
            max_weekly_hours=20, contract_type="hora_catedra",
        ),
    ]
    subjects = [
        Subject("S001", "Materia A", 3, 4, 1, 1, 20, "P_TEST1", (proj,), ()),
        Subject("S002", "Materia B", 3, 4, 1, 1, 15, "P_TEST2", (comp,), ()),
        Subject("S003", "Materia C", 2, 3, 1, 1, 25, "P_TEST1", (), ()),
    ]

    return SchedulingInstance(
        semester="TEST",
        subjects=subjects,
        classrooms=classrooms,
        timeslots=timeslots,
        professors=professors,
    )
