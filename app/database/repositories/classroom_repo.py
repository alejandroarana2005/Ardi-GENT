"""HAIA Agent — Repositorio de Classrooms con patrón Repository."""

from sqlalchemy.orm import Session

from app.database.models import ClassroomModel


class ClassroomRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[ClassroomModel]:
        return self.db.query(ClassroomModel).all()

    def get_by_code(self, code: str) -> ClassroomModel | None:
        return self.db.query(ClassroomModel).filter(ClassroomModel.code == code).first()

    def get_by_min_capacity(self, min_capacity: int) -> list[ClassroomModel]:
        return (
            self.db.query(ClassroomModel)
            .filter(ClassroomModel.capacity >= min_capacity)
            .all()
        )

    def create(self, classroom: ClassroomModel) -> ClassroomModel:
        self.db.add(classroom)
        self.db.commit()
        self.db.refresh(classroom)
        return classroom

    def bulk_create(self, classrooms: list[ClassroomModel]) -> list[ClassroomModel]:
        self.db.add_all(classrooms)
        self.db.commit()
        return classrooms
