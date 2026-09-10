import pytest
from pydantic import ValidationError

from app.core.dependencies import AuthenticatedPrincipal, require_permissions
from app.domain.authorization import ASSIGNABLE_ROLE_CODES, Permissions, RolePermissionPolicy
from app.exceptions import AuthorizationError, BusinessRuleError
from app.services.user import UserService
from app.schemas.auth import UserRolesUpdate


def test_admin_has_administrative_but_not_clinical_permissions() -> None:
    permissions = RolePermissionPolicy().resolve(["ADMIN"])

    assert permissions == Permissions.ADMINISTRATIVE
    assert permissions.isdisjoint(Permissions.CLINICAL)


def test_professional_can_perform_own_clinical_work_but_not_administration() -> None:
    assert RolePermissionPolicy().resolve(["PROFESIONAL"]) == frozenset(
        {
            Permissions.PATIENT_READ,
            Permissions.PATIENT_WRITE,
            Permissions.ATTENTION_CREATE,
            Permissions.ATTENTION_READ,
            Permissions.ATTENTION_CANCEL,
            Permissions.FUA_ISSUE,
            Permissions.CERTIFICATE_ISSUE,
            Permissions.REFERENCE_ISSUE,
        }
    )


def test_legacy_role_codes_have_no_permissions_or_assignment_path() -> None:
    policy = RolePermissionPolicy()

    assert policy.resolve(["REGISTRO", "AUDITOR"]) == frozenset()
    assert ASSIGNABLE_ROLE_CODES == frozenset({"ADMIN", "PROFESIONAL"})


def test_professional_cannot_deactivate_a_patient() -> None:
    principal = AuthenticatedPrincipal(
        user_id=7,
        username="profesional.demo",
        roles=frozenset({"PROFESIONAL"}),
        permissions=RolePermissionPolicy().resolve(["PROFESIONAL"]),
    )

    with pytest.raises(AuthorizationError):
        require_permissions(Permissions.PATIENT_DEACTIVATE)(principal)


def test_user_service_rejects_retired_roles_before_querying_the_catalog() -> None:
    class Session:
        rolled_back = False

        def rollback(self) -> None:
            self.rolled_back = True

    session = Session()

    with pytest.raises(BusinessRuleError, match="no están habilitados") as exc_info:
        UserService(session)._resolve_roles(["REGISTRO"])  # type: ignore[arg-type]

    assert exc_info.value.code == "ROL_NO_HABILITADO"
    assert session.rolled_back is True


def test_user_contract_rejects_retired_or_duplicate_roles() -> None:
    with pytest.raises(ValidationError, match="Roles no habilitados"):
        UserRolesUpdate(roles=["REGISTRO"])

    with pytest.raises(ValidationError, match="No se puede repetir"):
        UserRolesUpdate(roles=["PROFESIONAL", "PROFESIONAL"])
