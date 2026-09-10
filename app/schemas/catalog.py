"""Read-only API contracts for form and reference catalogs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CodeCatalogItem(BaseModel):
    codigo: str
    nombre: str
    activo: bool


class IdCatalogItem(BaseModel):
    id: int = Field(gt=0)
    codigo: str
    nombre: str
    activo: bool


class SpecialtyCatalogItem(CodeCatalogItem):
    grupo: str | None = None


class ServiceCatalogItem(BaseModel):
    codigo: str
    descripcion: str
    grupo: str | None = None
    activo: bool


class Cie10CatalogItem(BaseModel):
    codigo: str
    descripcion: str
    categoria: str | None = None
    activo: bool


class AgeGroupCatalogItem(CodeCatalogItem):
    edad_minima_meses: int | None = Field(default=None, ge=0)
    edad_maxima_meses: int | None = Field(default=None, ge=0)


class RiskGroupCatalogItem(IdCatalogItem):
    descripcion: str | None = None


class EstablishmentCatalogItem(BaseModel):
    id: int = Field(gt=0)
    codigo_renaes: str | None = None
    codigo_ideess: str | None = None
    nombre: str
    abreviatura: str | None = None
    activo: bool


class OfficeCatalogItem(BaseModel):
    id: int = Field(gt=0)
    establecimiento_id: int = Field(gt=0)
    codigo: str
    nombre: str
    especialidad_codigo: str | None = None
    activo: bool


class ProfessionalCatalogItem(BaseModel):
    id: int = Field(gt=0)
    nombre_completo: str
    colegiatura: str | None = None
    activo: bool


class UbigeoCatalogItem(BaseModel):
    codigo: str
    departamento: str
    provincia: str
    distrito: str
    localidad: str | None = None
