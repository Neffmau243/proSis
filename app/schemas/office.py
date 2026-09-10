"""Contracts for care-office administration and professional assignments."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OfficeAssignmentCreate(BaseModel):
    profesional_id: int = Field(gt=0)
    fecha_inicio: date
    fecha_fin: date | None = None
    es_responsable: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "OfficeAssignmentCreate":
        if self.fecha_fin is not None and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class OfficeAssignmentClose(BaseModel):
    fecha_fin: date


class OfficeAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consultorio_id: int
    profesional_id: int
    fecha_inicio: date
    fecha_fin: date | None
    es_responsable: bool


class OfficeCreate(BaseModel):
    """Data an administrator may use to register an active care office."""

    establecimiento_id: Annotated[int, Field(gt=0)]
    codigo: Annotated[str, Field(min_length=1, max_length=30)]
    nombre: Annotated[str, Field(min_length=2, max_length=150)]
    consultorio_padre_id: Annotated[int, Field(gt=0)] | None = None
    especialidad_codigo: Annotated[str, Field(min_length=1, max_length=20)] | None = None

    @field_validator("codigo", "nombre", "especialidad_codigo", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("codigo", "especialidad_codigo", mode="after")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class OfficeUpdate(BaseModel):
    """Whitelisted mutations for an office; active state has a dedicated action."""

    codigo: Annotated[str, Field(min_length=1, max_length=30)] | None = None
    nombre: Annotated[str, Field(min_length=2, max_length=150)] | None = None
    consultorio_padre_id: Annotated[int, Field(gt=0)] | None = None
    especialidad_codigo: Annotated[str, Field(min_length=1, max_length=20)] | None = None

    @field_validator("codigo", "nombre", "especialidad_codigo", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("codigo", "especialidad_codigo", mode="after")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class OfficeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    establecimiento_id: int
    consultorio_padre_id: int | None
    codigo: str
    nombre: str
    especialidad_codigo: str | None
    activo: bool
