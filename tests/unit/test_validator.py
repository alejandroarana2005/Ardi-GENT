"""Tests unitarios para el validador de instancias (Capa 1)."""

from tests.fixtures.sample_data import build_minimal_instance, build_sample_instance
from app.layer1_perception.validator import InstanceValidator
from app.domain.entities import Subject


class TestInstanceValidator:
    def test_minimal_instance_is_valid(self):
        instance = build_minimal_instance()
        validator = InstanceValidator()
        result = validator.validate(instance)
        assert result.is_valid, result.errors

    def test_sample_instance_is_valid(self):
        instance = build_sample_instance()
        validator = InstanceValidator()
        result = validator.validate(instance)
        assert result.is_valid, result.errors

    def test_detects_empty_subjects(self):
        instance = build_minimal_instance()
        # Vaciar materias
        instance = instance.__class__(
            semester=instance.semester,
            subjects=[],
            classrooms=instance.classrooms,
            timeslots=instance.timeslots,
            professors=instance.professors,
        )
        validator = InstanceValidator()
        result = validator.validate(instance)
        assert not result.is_valid
        assert any("materias" in e.lower() for e in result.errors)

    def test_detects_invalid_professor_reference(self):
        import dataclasses
        instance = build_minimal_instance()
        # Crear materia con docente inexistente
        bad_subject = dataclasses.replace(instance.subjects[0], professor_code="PHANTOM")
        new_subjects = [bad_subject] + instance.subjects[1:]
        bad_instance = instance.__class__(
            semester=instance.semester,
            subjects=new_subjects,
            classrooms=instance.classrooms,
            timeslots=instance.timeslots,
            professors=instance.professors,
        )
        validator = InstanceValidator()
        result = validator.validate(bad_instance)
        assert not result.is_valid
