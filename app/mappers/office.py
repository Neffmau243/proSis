from app.models.organization import Office, OfficeProfessional
from app.schemas.office import OfficeAssignmentResponse, OfficeResponse


def office_to_response(entity: Office) -> OfficeResponse:
    return OfficeResponse.model_validate(entity)


def office_assignment_to_response(entity: OfficeProfessional) -> OfficeAssignmentResponse:
    return OfficeAssignmentResponse.model_validate(entity)
