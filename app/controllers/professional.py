"""HTTP boundary for administrator-managed professional records."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import Permissions
from app.schemas.professional import (
    ProfessionalCreate,
    ProfessionalResponse,
    ProfessionalSpecialtiesUpdate,
    ProfessionalUpdate,
)
from app.services.audit import AuditService
from app.services.professional import ProfessionalService

router = APIRouter(prefix="/configuracion/profesionales", tags=["Configuración"])

DatabaseSession = Annotated[Session, Depends(get_db)]
ProfessionalAdministrator = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PROFESSIONAL_MANAGE)),
]


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    _: ProfessionalAdministrator,
    db: DatabaseSession,
    incluir_inactivos: bool = Query(default=False),
) -> list[ProfessionalResponse]:
    return ProfessionalService(db).list(include_inactive=incluir_inactivos)


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(
    professional_id: int,
    _: ProfessionalAdministrator,
    db: DatabaseSession,
) -> ProfessionalResponse:
    return ProfessionalService(db).get(professional_id)


@router.post("", response_model=ProfessionalResponse, status_code=status.HTTP_201_CREATED)
def create_professional(
    payload: ProfessionalCreate,
    principal: ProfessionalAdministrator,
    db: DatabaseSession,
) -> ProfessionalResponse:
    return ProfessionalService(db, audit=AuditService(db).record).create(
        payload,
        actor_id=principal.user_id,
    )


@router.patch("/{professional_id}", response_model=ProfessionalResponse)
def update_professional(
    professional_id: int,
    payload: ProfessionalUpdate,
    principal: ProfessionalAdministrator,
    db: DatabaseSession,
) -> ProfessionalResponse:
    return ProfessionalService(db, audit=AuditService(db).record).update(
        professional_id,
        payload,
        actor_id=principal.user_id,
    )


@router.put("/{professional_id}/especialidades", response_model=ProfessionalResponse)
def replace_professional_specialties(
    professional_id: int,
    payload: ProfessionalSpecialtiesUpdate,
    principal: ProfessionalAdministrator,
    db: DatabaseSession,
) -> ProfessionalResponse:
    return ProfessionalService(db, audit=AuditService(db).record).replace_specialties(
        professional_id,
        payload,
        actor_id=principal.user_id,
    )


@router.delete("/{professional_id}", response_model=ProfessionalResponse)
def deactivate_professional(
    professional_id: int,
    principal: ProfessionalAdministrator,
    db: DatabaseSession,
) -> ProfessionalResponse:
    return ProfessionalService(db, audit=AuditService(db).record).deactivate(
        professional_id,
        actor_id=principal.user_id,
    )
