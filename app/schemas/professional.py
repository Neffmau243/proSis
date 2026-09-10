"""API contracts for administrator-managed health professionals."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfessionalSpecialtyInput(BaseModel):
    especialidad_codigo: Annotated[str, Field(min_length=1, max_length=20)]
    es_principal: bool = False

    @field_validator("especialidad_codigo", mode="before")
    @classmethod
    def normalize_code(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class _SpecialtyListValidation(BaseModel):
    """Reusable validation for an unambiguous specialty assignment list."""

    especialidades: list[ProfessionalSpecialtyInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_specialties(self) -> "_SpecialtyListValidation":
        codes = [item.especialidad_codigo for item in self.especialidades]
        if len(codes) != len(set(codes)):
            raise ValueError("No se puede repetir una especialidad.")
        if sum(item.es_principal for item in self.especialidades) > 1:
            raise ValueError("Solo una especialidad puede ser principal.")
        if self.especialidades and not any(item.es_principal for item in self.especialidades):
            raise ValueError("Cuando hay especialidades, una debe marcarse como principal.")
        return self


class ProfessionalCreate(_SpecialtyListValidation):
    codigo_legacy: Annotated[int, Field(gt=0)] | None = None
    numero_documento: Annotated[str, Field(min_length=1, max_length=30)] | None = None
    nombre_completo: Annotated[str, Field(min_length=2, max_length=200)]
    profesion_id: Annotated[int, Field(gt=0)] | None = None
    colegiatura: Annotated[str, Field(min_length=1, max_length=50)] | None = None

    @field_validator("numero_documento", "nombre_completo", "colegiatura", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class ProfessionalUpdate(BaseModel):
    codigo_legacy: Annotated[int, Field(gt=0)] | None = None
    numero_documento: Annotated[str, Field(min_length=1, max_length=30)] | None = None
    nombre_completo: Annotated[str, Field(min_length=2, max_length=200)] | None = None
    profesion_id: Annotated[int, Field(gt=0)] | None = None
    colegiatura: Annotated[str, Field(min_length=1, max_length=50)] | None = None

    @field_validator("numero_documento", "nombre_completo", "colegiatura", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class ProfessionalSpecialtiesUpdate(_SpecialtyListValidation):
    """Complete replacement of an administrator-managed specialty list."""


class ProfessionalSpecialtyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    especialidad_codigo: str
    es_principal: bool


class ProfessionalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo_legacy: int | None
    numero_documento: str | None
    nombre_completo: str
    profesion_id: int | None
    colegiatura: str | None
    activo: bool
    created_at: datetime
    updated_at: datetime
    especialidades: list[ProfessionalSpecialtyResponse] = Field(default_factory=list)
