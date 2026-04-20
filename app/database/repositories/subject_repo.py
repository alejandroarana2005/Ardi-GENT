"""HAIA Agent — Repositorio de Subjects con patrón Repository."""

from sqlalchemy.orm import Session

from app.database.models import SubjectModel


class SubjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[SubjectModel]:
        return self.db.query(SubjectModel).all()

    def get_by_code(self, code: str) -> SubjectModel | None:
        return self.db.query(SubjectModel).filter(SubjectModel.code == code).first()

    def get_by_faculty(self, faculty: str) -> list[SubjectModel]:
        return self.db.query(SubjectModel).filter(SubjectModel.faculty == faculty).all()

    def create(self, subject: SubjectModel) -> SubjectModel:
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def bulk_create(self, subjects: list[SubjectModel]) -> list[SubjectModel]:
        self.db.add_all(subjects)
        self.db.commit()
        return subjects

    def delete(self, code: str) -> bool:
        subject = self.get_by_code(code)
        if subject:
            self.db.delete(subject)
            self.db.commit()
            return True
        return False
