"""HAIA Agent — Repositorio de TimeSlots con patrón Repository."""

from sqlalchemy.orm import Session

from app.database.models import TimeSlotModel


class TimeSlotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[TimeSlotModel]:
        return self.db.query(TimeSlotModel).order_by(TimeSlotModel.day, TimeSlotModel.start_time).all()

    def get_by_code(self, code: str) -> TimeSlotModel | None:
        return self.db.query(TimeSlotModel).filter(TimeSlotModel.code == code).first()

    def get_by_day(self, day: str) -> list[TimeSlotModel]:
        return self.db.query(TimeSlotModel).filter(TimeSlotModel.day == day).all()

    def create(self, timeslot: TimeSlotModel) -> TimeSlotModel:
        self.db.add(timeslot)
        self.db.commit()
        self.db.refresh(timeslot)
        return timeslot

    def bulk_create(self, timeslots: list[TimeSlotModel]) -> list[TimeSlotModel]:
        self.db.add_all(timeslots)
        self.db.commit()
        return timeslots
