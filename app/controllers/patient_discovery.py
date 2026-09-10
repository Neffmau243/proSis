"""HTTP adapter for scoped, paginated patient discovery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import Permissions
from app.schemas.common import PageResponse
from app.schemas.discovery import PatientSearchCriteria
from app.schemas.patient import PatientResponse
from app.services.discovery import PatientDiscoveryService


router = APIRouter(prefix="/patients", tags=["Pacientes"])

DatabaseSession = Annotated[Session, Depends(get_db)]
PatientReader = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PATIENT_READ)),
]


@router.get("", response_model=PageResponse[PatientResponse], summary="Buscar pacientes")
def search_patients(
    principal: PatientReader,
    db: DatabaseSession,
    tipo_documento_codigo: Annotated[str | None, Query(min_length=1, max_length=10)] = None,
    numero_documento: Annotated[str | None, Query(min_length=1, max_length=30)] = None,
    historia_clinica: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    establecimiento_id: Annotated[int | None, Query(gt=0)] = None,
    incluir_inactivos: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageResponse[PatientResponse]:
    criteria = PatientSearchCriteria(
        tipo_documento_codigo=tipo_documento_codigo,
        numero_documento=numero_documento,
        historia_clinica=historia_clinica,
        q=q,
        establecimiento_id=establecimiento_id,
        incluir_inactivos=incluir_inactivos,
        limit=limit,
        offset=offset,
    )
    return PatientDiscoveryService(db).search(
        criteria,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )
