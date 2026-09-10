"""HTTP adapter for the patient bounded context.

Routes only bind HTTP contracts/dependencies to service methods.  Validation
of patient rules and all persistence interactions remain outside this module.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import Permissions
from app.schemas.patient import (
    PatientCreate,
    PatientDeactivationResponse,
    PatientResponsibleCreate,
    PatientResponsibleResponse,
    PatientResponsibleUpdate,
    PatientResponse,
    PatientRiskCreate,
    PatientRiskResponse,
    PatientRiskUpdate,
    PatientUpdate,
)
from app.services.patient import PatientService


router = APIRouter(prefix="/patients", tags=["Pacientes"])


def get_patient_service(
    session: Annotated[Session, Depends(get_db)],
) -> PatientService:
    """Constructs the request-scoped patient use-case service."""

    return PatientService(session)


PatientServiceDependency = Annotated[PatientService, Depends(get_patient_service)]
ReadPrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PATIENT_READ)),
]
CreatePrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PATIENT_WRITE)),
]
UpdatePrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PATIENT_WRITE)),
]
DeactivatePrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_permissions(Permissions.PATIENT_DEACTIVATE)),
]


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    service: PatientServiceDependency,
    principal: CreatePrincipal,
) -> PatientResponse:
    return service.create(
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    service: PatientServiceDependency,
    principal: ReadPrincipal,
) -> PatientResponse:
    return service.get(
        patient_id,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    service: PatientServiceDependency,
    principal: UpdatePrincipal,
) -> PatientResponse:
    return service.update(
        patient_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.delete("/{patient_id}", response_model=PatientDeactivationResponse)
def deactivate_patient(
    patient_id: int,
    service: PatientServiceDependency,
    principal: DeactivatePrincipal,
) -> PatientDeactivationResponse:
    return service.deactivate(
        patient_id,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.post(
    "/{patient_id}/responsibles",
    response_model=PatientResponsibleResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_responsible(
    patient_id: int,
    payload: PatientResponsibleCreate,
    service: PatientServiceDependency,
    principal: UpdatePrincipal,
) -> PatientResponsibleResponse:
    return service.add_responsible(
        patient_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.patch(
    "/{patient_id}/responsibles/{responsible_id}",
    response_model=PatientResponsibleResponse,
)
def update_responsible(
    patient_id: int,
    responsible_id: int,
    payload: PatientResponsibleUpdate,
    service: PatientServiceDependency,
    principal: UpdatePrincipal,
) -> PatientResponsibleResponse:
    return service.update_responsible(
        patient_id,
        responsible_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.post(
    "/{patient_id}/risk-groups",
    response_model=PatientRiskResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_risk(
    patient_id: int,
    payload: PatientRiskCreate,
    service: PatientServiceDependency,
    principal: UpdatePrincipal,
) -> PatientRiskResponse:
    return service.add_risk(
        patient_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@router.patch(
    "/{patient_id}/risk-groups/{risk_group_id}/{start_date}",
    response_model=PatientRiskResponse,
)
def update_risk(
    patient_id: int,
    risk_group_id: int,
    start_date: date,
    payload: PatientRiskUpdate,
    service: PatientServiceDependency,
    principal: UpdatePrincipal,
) -> PatientRiskResponse:
    return service.update_risk(
        patient_id,
        risk_group_id,
        start_date,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )
