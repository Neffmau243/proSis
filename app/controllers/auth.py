"""Routers for login and the administrator-managed user lifecycle."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AuthenticatedPrincipal, CurrentPrincipal, require_roles
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LoginUsernameOption,
    PasswordChangeRequest,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
    UserRolesUpdate,
)
from app.services.audit import AuditService
from app.services.auth import AuthenticationService
from app.services.user import UserService

auth_router = APIRouter(prefix="/auth", tags=["Autenticación"])
users_router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

DatabaseSession = Annotated[Session, Depends(get_db)]
Administrator = Annotated[AuthenticatedPrincipal, Depends(require_roles("ADMIN"))]


@auth_router.get(
    "/usuarios-activos",
    response_model=list[LoginUsernameOption],
    summary="Listar usuarios disponibles para iniciar sesión",
)
def list_active_login_users(db: DatabaseSession) -> list[LoginUsernameOption]:
    # Deliberately public for the internal team's login selector. It exposes
    # only usernames for accounts that can actually authenticate.
    return [
        LoginUsernameOption(nombre_usuario=username)
        for username in AuthenticationService(db).list_active_usernames()
    ]


@auth_router.post("/login", response_model=AccessTokenResponse, summary="Iniciar sesión")
def login(
    payload: LoginRequest,
    request: Request,
    db: DatabaseSession,
) -> AccessTokenResponse:
    # Do not trust forwarded headers here. A deployment that terminates a
    # proxy must configure trusted proxy middleware explicitly; otherwise an
    # arbitrary client could select its own rate-limit bucket.
    client_ip = request.client.host if request.client is not None else None
    return AuthenticationService(db).login(payload, client_ip=client_ip)


@auth_router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Cambiar mi contraseña",
)
def change_own_password(
    payload: PasswordChangeRequest,
    principal: CurrentPrincipal,
    db: DatabaseSession,
) -> Response:
    UserService(db, audit=AuditService(db).record).change_own_password(
        payload,
        actor_id=principal.user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    principal: Administrator,
    db: DatabaseSession,
) -> UserResponse:
    return UserService(db, audit=AuditService(db).record).create(
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@users_router.put("/{user_id}/roles", response_model=UserResponse)
def assign_roles(
    user_id: int,
    payload: UserRolesUpdate,
    principal: Administrator,
    db: DatabaseSession,
) -> UserResponse:
    return UserService(db, audit=AuditService(db).record).assign_roles(
        user_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@users_router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    principal: Administrator,
    db: DatabaseSession,
) -> UserResponse:
    return UserService(db, audit=AuditService(db).record).deactivate(
        user_id,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )


@users_router.put(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Restablecer contraseña de usuario",
)
def reset_user_password(
    user_id: int,
    payload: PasswordResetRequest,
    principal: Administrator,
    db: DatabaseSession,
) -> Response:
    UserService(db, audit=AuditService(db).record).reset_password(
        user_id,
        payload,
        actor_id=principal.user_id,
        actor_roles=principal.roles,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# The module exposes one router for application assembly while retaining
# cohesive subrouters for authentication and user administration. This must be
# composed after declarations because FastAPI copies child routes on inclusion.
router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
