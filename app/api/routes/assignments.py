"""HAIA Agent — Endpoints CRUD de entidades maestras (subjects, classrooms, etc.)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ClassroomCreate,
    ClassroomResponse,
    ProfessorCreate,
    ProfessorResponse,
    SubjectCreate,
    SubjectResponse,
    TimeSlotCreate,
    TimeSlotResponse,
)
from app.database.models import (
    ClassroomModel,
    ProfessorAvailabilityModel,
    ProfessorModel,
    ProfessorPreferenceModel,
    ResourceModel,
    SubjectModel,
    TimeSlotModel,
)
from app.database.session import get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter(tags=["Master Data"])


# ─────────────────────── Subjects ────────────────────────────────────────────

@router.post("/subjects", response_model=SubjectResponse, status_code=201, summary="Crear materia")
def create_subject(body: SubjectCreate, db: Session = Depends(get_db)) -> SubjectResponse:
    existing = db.query(SubjectModel).filter(SubjectModel.code == body.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Subject '{body.code}' already exists")

    model = SubjectModel(
        code=body.code,
        name=body.name,
        credits=body.credits,
        study_hours=body.study_hours,
        weekly_subgroups=body.weekly_subgroups,
        groups=body.groups,
        enrollment=body.enrollment,
        faculty=body.faculty,
        professor_code=body.professor_code,
    )
    for rc in body.required_resource_codes:
        r = db.query(ResourceModel).filter(ResourceModel.code == rc).first()
        if r:
            model.required_resources.append(r)
    for rc in body.optional_resource_codes:
        r = db.query(ResourceModel).filter(ResourceModel.code == rc).first()
        if r:
            model.optional_resources.append(r)

    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/subjects", response_model=list[SubjectResponse], summary="Listar materias")
def list_subjects(db: Session = Depends(get_db)) -> list[SubjectResponse]:
    return db.query(SubjectModel).all()


# ─────────────────────── Classrooms ──────────────────────────────────────────

@router.post("/classrooms", response_model=ClassroomResponse, status_code=201, summary="Crear salón")
def create_classroom(body: ClassroomCreate, db: Session = Depends(get_db)) -> ClassroomResponse:
    existing = db.query(ClassroomModel).filter(ClassroomModel.code == body.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Classroom '{body.code}' already exists")

    model = ClassroomModel(code=body.code, name=body.name, capacity=body.capacity)
    for rc in body.resource_codes:
        r = db.query(ResourceModel).filter(ResourceModel.code == rc).first()
        if r:
            model.resources.append(r)

    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/classrooms", response_model=list[ClassroomResponse], summary="Listar salones")
def list_classrooms(db: Session = Depends(get_db)) -> list[ClassroomResponse]:
    return db.query(ClassroomModel).all()


# ─────────────────────── TimeSlots ───────────────────────────────────────────

@router.post("/timeslots", response_model=TimeSlotResponse, status_code=201, summary="Crear franja")
def create_timeslot(body: TimeSlotCreate, db: Session = Depends(get_db)) -> TimeSlotResponse:
    existing = db.query(TimeSlotModel).filter(TimeSlotModel.code == body.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"TimeSlot '{body.code}' already exists")

    model = TimeSlotModel(
        code=body.code,
        day=body.day,
        start_time=body.start_time,
        end_time=body.end_time,
        duration=body.duration,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/timeslots", response_model=list[TimeSlotResponse], summary="Listar franjas")
def list_timeslots(db: Session = Depends(get_db)) -> list[TimeSlotResponse]:
    return db.query(TimeSlotModel).all()


# ─────────────────────── Professors ──────────────────────────────────────────

@router.post("/professors", response_model=ProfessorResponse, status_code=201, summary="Crear docente")
def create_professor(body: ProfessorCreate, db: Session = Depends(get_db)) -> ProfessorResponse:
    existing = db.query(ProfessorModel).filter(ProfessorModel.code == body.code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Professor '{body.code}' already exists")

    model = ProfessorModel(
        code=body.code,
        name=body.name,
        max_weekly_hours=body.max_weekly_hours,
        contract_type=body.contract_type,
    )
    db.add(model)
    db.flush()

    for ts_code in body.availability:
        db.add(ProfessorAvailabilityModel(professor_id=model.id, timeslot_code=ts_code))
    for pref in body.preferences:
        db.add(ProfessorPreferenceModel(
            professor_id=model.id,
            timeslot_code=pref.timeslot_code,
            preference=pref.preference,
        ))

    db.commit()
    db.refresh(model)
    return model


@router.get("/professors", response_model=list[ProfessorResponse], summary="Listar docentes")
def list_professors(db: Session = Depends(get_db)) -> list[ProfessorResponse]:
    return db.query(ProfessorModel).all()
