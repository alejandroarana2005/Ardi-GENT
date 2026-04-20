"""HAIA Agent — Repositorio de Assignments con patrón Repository."""

from sqlalchemy.orm import Session

from app.database.models import AssignmentModel, ScheduleModel


class AssignmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_schedule(self, schedule_id: str) -> list[AssignmentModel]:
        schedule = (
            self.db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            return []
        return (
            self.db.query(AssignmentModel)
            .filter(AssignmentModel.schedule_id == schedule.id)
            .all()
        )

    def get_by_subject(self, schedule_id: str, subject_code: str) -> list[AssignmentModel]:
        return [
            a for a in self.get_by_schedule(schedule_id)
            if a.subject_code == subject_code
        ]

    def bulk_create(self, assignments: list[AssignmentModel]) -> list[AssignmentModel]:
        self.db.add_all(assignments)
        self.db.commit()
        return assignments

    def update_score(self, assignment_id: int, score: float) -> AssignmentModel | None:
        a = self.db.query(AssignmentModel).filter(AssignmentModel.id == assignment_id).first()
        if a:
            a.utilidad_score = score
            self.db.commit()
            self.db.refresh(a)
        return a
