"""HTTP boundary for age-group configuration."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import Permissions
from app.schemas.age_group import AgeGroupConfigurationInput, AgeGroupResponse
from app.services.audit import AuditService
from app.services.age_group import AgeGroupService

router = APIRouter(prefix="/configuracion/grupos-etarios", tags=["Configuración"])

DatabaseSession = Annotated[Session, Depends(get_db)]
AgeGroupAdministrator = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.AGE_GROUP_CONFIGURE)),
]


@router.get("", response_model=list[AgeGroupResponse], summary="Listar grupos etarios")
def list_age_groups(_: AgeGroupAdministrator, db: DatabaseSession) -> list[AgeGroupResponse]:
    return AgeGroupService(db).list()


@router.put(
    "",
    response_model=list[AgeGroupResponse],
    status_code=status.HTTP_200_OK,
    summary="Configurar rangos de grupos etarios",
)
def configure_age_groups(
    payload: AgeGroupConfigurationInput,
    principal: AgeGroupAdministrator,
    db: DatabaseSession,
) -> list[AgeGroupResponse]:
    return AgeGroupService(db, audit=AuditService(db).record).configure(
        payload, actor_id=principal.user_id
    )
