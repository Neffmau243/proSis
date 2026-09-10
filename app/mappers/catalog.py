"""Explicit model-to-DTO mappings for public reference catalogs."""

from __future__ import annotations

from app.models.catalog import (
    AgeGroup,
    AttentionMode,
    Cie10,
    DocumentType,
    Insurance,
    Profession,
    ServiceOffering,
    Sex,
    Specialty,
)
from app.models.organization import Establishment, Office, Ubigeo
from app.models.patient import RiskGroup
from app.models.security import Professional
from app.schemas.catalog import (
    AgeGroupCatalogItem,
    Cie10CatalogItem,
    CodeCatalogItem,
    EstablishmentCatalogItem,
    IdCatalogItem,
    OfficeCatalogItem,
    ProfessionalCatalogItem,
    RiskGroupCatalogItem,
    ServiceCatalogItem,
    SpecialtyCatalogItem,
    UbigeoCatalogItem,
)


def document_type_to_catalog_item(entity: DocumentType) -> CodeCatalogItem:
    return CodeCatalogItem(codigo=entity.codigo, nombre=entity.nombre, activo=entity.activo)


def sex_to_catalog_item(entity: Sex) -> CodeCatalogItem:
    return CodeCatalogItem(codigo=entity.codigo, nombre=entity.nombre, activo=entity.activo)


def insurance_to_catalog_item(entity: Insurance) -> IdCatalogItem:
    return IdCatalogItem(id=entity.id, codigo=entity.codigo, nombre=entity.nombre, activo=entity.activo)


def profession_to_catalog_item(entity: Profession) -> IdCatalogItem:
    return IdCatalogItem(id=entity.id, codigo=str(entity.id), nombre=entity.nombre, activo=entity.activo)


def specialty_to_catalog_item(entity: Specialty) -> SpecialtyCatalogItem:
    return SpecialtyCatalogItem(
        codigo=entity.codigo,
        nombre=entity.nombre,
        grupo=entity.grupo,
        activo=entity.activo,
    )


def attention_mode_to_catalog_item(entity: AttentionMode) -> CodeCatalogItem:
    return CodeCatalogItem(codigo=entity.codigo, nombre=entity.nombre, activo=entity.activo)


def age_group_to_catalog_item(entity: AgeGroup) -> AgeGroupCatalogItem:
    return AgeGroupCatalogItem(
        codigo=entity.codigo,
        nombre=entity.nombre,
        edad_minima_meses=entity.edad_minima_meses,
        edad_maxima_meses=entity.edad_maxima_meses,
        activo=entity.activo,
    )


def risk_group_to_catalog_item(entity: RiskGroup) -> RiskGroupCatalogItem:
    return RiskGroupCatalogItem(
        id=entity.id,
        codigo=entity.codigo,
        nombre=entity.nombre,
        descripcion=entity.descripcion,
        activo=entity.activo,
    )


def service_to_catalog_item(entity: ServiceOffering) -> ServiceCatalogItem:
    return ServiceCatalogItem(
        codigo=entity.codigo,
        descripcion=entity.descripcion,
        grupo=entity.grupo,
        activo=entity.activo,
    )


def cie10_to_catalog_item(entity: Cie10) -> Cie10CatalogItem:
    return Cie10CatalogItem(
        codigo=entity.codigo,
        descripcion=entity.descripcion,
        categoria=entity.categoria,
        activo=entity.activo,
    )


def establishment_to_catalog_item(entity: Establishment) -> EstablishmentCatalogItem:
    return EstablishmentCatalogItem(
        id=entity.id,
        codigo_renaes=entity.codigo_renaes,
        codigo_ideess=entity.codigo_ideess,
        nombre=entity.nombre,
        abreviatura=entity.abreviatura,
        activo=entity.activo,
    )


def office_to_catalog_item(entity: Office) -> OfficeCatalogItem:
    return OfficeCatalogItem(
        id=entity.id,
        establecimiento_id=entity.establecimiento_id,
        codigo=entity.codigo,
        nombre=entity.nombre,
        especialidad_codigo=entity.especialidad_codigo,
        activo=entity.activo,
    )


def professional_to_catalog_item(entity: Professional) -> ProfessionalCatalogItem:
    return ProfessionalCatalogItem(
        id=entity.id,
        nombre_completo=entity.nombre_completo,
        colegiatura=entity.colegiatura,
        activo=entity.activo,
    )


def ubigeo_to_catalog_item(entity: Ubigeo) -> UbigeoCatalogItem:
    return UbigeoCatalogItem(
        codigo=entity.codigo,
        departamento=entity.departamento,
        provincia=entity.provincia,
        distrito=entity.distrito,
        localidad=entity.localidad,
    )
