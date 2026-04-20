"""
HAIA — Re-seeding de preferencias docentes con valores realistas (seed=42).

Actualiza professor_preferences en la BD con los valores generados por
build_professors() del fixture, que usa random.seed(42) para reproducibilidad.

Uso:
    DATABASE_URL="sqlite:///./haia_e2e.db" python scripts/reseed_professor_preferences.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.database.models import ProfessorModel, ProfessorPreferenceModel, TimeSlotModel
from tests.fixtures.sample_data import build_timeslots, build_professors


def reseed() -> None:
    db = SessionLocal()
    try:
        # Cargar franjas del DB para construir instancia coherente
        ts_rows = db.query(TimeSlotModel).all()
        if not ts_rows:
            print("ERROR: No hay franjas horarias en la BD. Ejecuta las migraciones primero.")
            return

        from app.domain.entities import TimeSlot
        timeslots = [
            TimeSlot(
                code=r.code, day=r.day,
                start_time=r.start_time, end_time=r.end_time, duration=r.duration,
            )
            for r in ts_rows
        ]

        professors_fixture = build_professors(timeslots)
        prof_map = {p.code: p for p in professors_fixture}

        updated = 0
        skipped = 0
        for prof_orm in db.query(ProfessorModel).all():
            fixture = prof_map.get(prof_orm.code)
            if fixture is None:
                skipped += 1
                continue

            # Borrar preferencias existentes
            db.query(ProfessorPreferenceModel).filter_by(professor_id=prof_orm.id).delete()

            # Insertar nuevas preferencias
            for pref in fixture.preferences:
                db.add(ProfessorPreferenceModel(
                    professor_id=prof_orm.id,
                    timeslot_code=pref.timeslot_code,
                    preference=pref.preference,
                ))
            updated += 1

        db.commit()
        print(f"Preferencias actualizadas para {updated} docentes ({skipped} omitidos).")

        # Verificación rápida
        total = db.query(ProfessorPreferenceModel).count()
        from sqlalchemy import func
        avg = db.query(func.avg(ProfessorPreferenceModel.preference)).scalar()
        print(f"Total de filas en professor_preferences: {total}")
        print(f"Preferencia promedio: {avg:.3f}")

    finally:
        db.close()


if __name__ == "__main__":
    reseed()
