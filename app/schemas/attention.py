"""Pydantic contracts for clinical attention use cases."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AttentionModeCode(str, Enum):
    AMBULATORY = "AMBULATORIA"
    EMERGENCY = "EMERGENCIA"


class AttentionStatus(str, Enum):
    ATTENDED = "ATENDIDO"
    CANCELLED = "ANULADO"


class AttentionServiceInput(BaseModel):
    prestacion_codigo: Annotated[str, Field(min_length=1, max_length=30)]
    cantidad: Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)] = Decimal("1")

    @field_validator("prestacion_codigo", mode="before")
    @classmethod
    def normalize_code(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class AttentionDiagnosisInput(BaseModel):
    cie10_codigo: Annotated[str, Field(min_length=1, max_length=20)]
    tipo_diagnostico: Annotated[str, Field(max_length=50)] | None = None
    observacion: Annotated[str, Field(max_length=500)] | None = None

    @field_validator("cie10_codigo", mode="before")
    @classmethod
    def normalize_code(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("tipo_diagnostico", "observacion", mode="before")
    @classmethod
    def trim_optional_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class NutritionalSnapshotInput(BaseModel):
    """Optional historic nutrition record created atomically with an attention."""

    tipo: Annotated[str, Field(min_length=1, max_length=20)]
    hemoglobina: Annotated[Decimal, Field(ge=0, max_digits=5, decimal_places=2)] | None = None
    fecha_hemoglobina: date | None = None
    edad_gestacional_semanas: Annotated[int, Field(ge=0, le=60)] | None = None
    imc: Annotated[Decimal, Field(max_digits=6, decimal_places=3)] | None = None
    whz: Annotated[Decimal, Field(max_digits=6, decimal_places=3)] | None = None
    haz: Annotated[Decimal, Field(max_digits=6, decimal_places=3)] | None = None
    waz: Annotated[Decimal, Field(max_digits=6, decimal_places=3)] | None = None
    diagnostico_peso_edad: Annotated[str, Field(max_length=100)] | None = None
    diagnostico_talla_edad: Annotated[str, Field(max_length=100)] | None = None
    diagnostico_peso_talla: Annotated[str, Field(max_length=100)] | None = None
    diagnostico: Annotated[str, Field(max_length=500)] | None = None


class AttentionCreate(BaseModel):
    """Input excluding fields that the backend must calculate or own."""

    paciente_id: Annotated[int, Field(gt=0)]
    establecimiento_id: Annotated[int, Field(gt=0)]
    profesional_id: Annotated[int, Field(gt=0)]
    especialidad_codigo: Annotated[str, Field(max_length=20)] | None = None
    consultorio_id: Annotated[int, Field(gt=0)]
    modalidad_atencion_codigo: AttentionModeCode
    fecha_atencion: datetime
    fecha_atendido: datetime | None = None
    peso_kg: Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)] | None = None
    talla_cm: Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)] | None = None
    perimetro_abdominal_cm: Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)] | None = None
    presion_sistolica: Annotated[int, Field(gt=0, le=999)] | None = None
    presion_diastolica: Annotated[int, Field(gt=0, le=999)] | None = None
    temperatura_c: Annotated[Decimal, Field(max_digits=4, decimal_places=1)] | None = None
    pe: Annotated[str, Field(max_length=50)] | None = None
    te: Annotated[str, Field(max_length=50)] | None = None
    pt: Annotated[str, Field(max_length=50)] | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    admision: Annotated[str, Field(max_length=100)] | None = None
    observaciones: str | None = None
    prestaciones: list[AttentionServiceInput] = Field(default_factory=list)
    diagnosticos: list[AttentionDiagnosisInput] = Field(default_factory=list)
    valoracion_nutricional: NutritionalSnapshotInput | None = None

    @field_validator("especialidad_codigo", mode="before")
    @classmethod
    def normalize_specialty(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("pe", "te", "pt", "admision", "observaciones", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_times(self) -> "AttentionCreate":
        if self.hora_inicio is not None and self.hora_fin is not None and self.hora_fin < self.hora_inicio:
            raise ValueError("hora_fin no puede ser anterior a hora_inicio")
        if self.fecha_atendido is not None and self.fecha_atendido < self.fecha_atencion:
            raise ValueError("fecha_atendido no puede ser anterior a fecha_atencion")
        return self


class AttentionCancellationInput(BaseModel):
    observaciones: Annotated[str, Field(min_length=5, max_length=10_000)]

    @field_validator("observaciones", mode="before")
    @classmethod
    def require_reason(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("La anulación requiere una justificación")
        return value.strip()


class AttentionServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero_orden: int
    prestacion_codigo: str
    cantidad: Decimal


class AttentionDiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero_orden: int
    cie10_codigo: str
    tipo_diagnostico: str | None
    observacion: str | None


class AttentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    establecimiento_id: int
    profesional_id: int
    especialidad_codigo: str | None
    consultorio_id: int
    modalidad_atencion_codigo: str
    grupo_etario_codigo: str
    fecha_atencion: datetime
    fecha_atendido: datetime | None
    historia_clinica_snapshot: str | None
    edad_anios: int | None
    peso_kg: Decimal | None
    talla_cm: Decimal | None
    perimetro_abdominal_cm: Decimal | None
    presion_sistolica: int | None
    presion_diastolica: int | None
    temperatura_c: Decimal | None
    pe: str | None
    te: str | None
    pt: str | None
    hora_inicio: time | None
    hora_fin: time | None
    admision: str | None
    observaciones: str | None
    estado: str
    created_by_usuario_id: int | None
    created_at: datetime
    updated_at: datetime
    prestaciones: list[AttentionServiceResponse] = Field(default_factory=list)
    diagnosticos: list[AttentionDiagnosisResponse] = Field(default_factory=list)
