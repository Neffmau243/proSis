"""HTTP boundary for issuing clinical documents."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import Permissions
from app.schemas.document import (
    CertificateIssueInput,
    CertificateResponse,
    FuaIssueInput,
    FuaResponse,
    ReferralCreateInput,
    ReferralResponse,
)
from app.services.document import DocumentService

router = APIRouter(prefix="/documentos", tags=["Documentos clínicos"])
DatabaseSession = Annotated[Session, Depends(get_db)]
FuaIssuer = Annotated[AuthenticatedPrincipal, Depends(require_permissions(Permissions.FUA_ISSUE))]
CertificateIssuer = Annotated[
    AuthenticatedPrincipal, Depends(require_permissions(Permissions.CERTIFICATE_ISSUE))
]
ReferralIssuer = Annotated[
    AuthenticatedPrincipal, Depends(require_permissions(Permissions.REFERENCE_ISSUE))
]


@router.post("/fua", response_model=FuaResponse, status_code=status.HTTP_201_CREATED)
def issue_fua(payload: FuaIssueInput, principal: FuaIssuer, db: DatabaseSession) -> FuaResponse:
    return DocumentService(db).issue_fua(
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.post("/certificados", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
def issue_certificate(
    payload: CertificateIssueInput, principal: CertificateIssuer, db: DatabaseSession
) -> CertificateResponse:
    return DocumentService(db).issue_certificate(
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.post("/referencias", response_model=ReferralResponse, status_code=status.HTTP_201_CREATED)
def create_referral(
    payload: ReferralCreateInput, principal: ReferralIssuer, db: DatabaseSession
) -> ReferralResponse:
    return DocumentService(db).create_referral(
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )
