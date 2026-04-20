"""HAIA Agent — Reporting: Generador de resumen JSON del horario. Stub Fase 1."""

import json
import logging
from datetime import datetime

from app.domain.entities import Assignment, SchedulingResult

logger = logging.getLogger("[HAIA Reporting-ReportGenerator]")


class ReportGenerator:
    def generate_json(self, result: SchedulingResult) -> str:
        report = {
            "schedule_id": result.schedule_id,
            "semester": result.semester,
            "generated_at": datetime.utcnow().isoformat(),
            "solver_used": result.solver_used,
            "utility_score": result.utility_score,
            "is_feasible": result.is_feasible,
            "elapsed_seconds": result.elapsed_seconds,
            "total_assignments": len(result.assignments),
            "assignments": [
                {
                    "subject_code": a.subject_code,
                    "classroom_code": a.classroom_code,
                    "timeslot_code": a.timeslot_code,
                    "group": a.group_number,
                    "session": a.session_number,
                }
                for a in result.assignments
            ],
            "violations": result.violations,
        }
        return json.dumps(report, indent=2, ensure_ascii=False)
