import pytest

from app.exceptions import BusinessRuleError
from app.schemas.age_group import AgeGroupRangeInput
from app.services.age_group import AgeGroupService


def group(code: str, minimum: int, maximum: int | None) -> AgeGroupRangeInput:
    return AgeGroupRangeInput(
        codigo=code,
        edad_minima_meses=minimum,
        edad_maxima_meses=maximum,
    )


def test_age_group_configuration_accepts_contiguous_ranges() -> None:
    AgeGroupService._validate_ranges(
        [group("NINO", 0, 143), group("ADOLESCENTE", 144, None)],
        require_continuity=True,
    )


def test_age_group_configuration_rejects_overlaps() -> None:
    with pytest.raises(BusinessRuleError, match="superponen"):
        AgeGroupService._validate_ranges(
            [group("NINO", 0, 143), group("ADOLESCENTE", 120, None)],
            require_continuity=False,
        )


def test_age_group_configuration_rejects_gaps_when_required() -> None:
    with pytest.raises(BusinessRuleError, match="hueco"):
        AgeGroupService._validate_ranges(
            [group("NINO", 0, 143), group("ADOLESCENTE", 145, None)],
            require_continuity=True,
        )


def test_age_group_input_accepts_year_and_month_boundaries() -> None:
    item = AgeGroupRangeInput(
        codigo="ADOLESCENTE",
        edad_minima={"anios": 12},
        edad_maxima={"anios": 17, "meses": 11},
    )

    assert item.edad_minima_meses == 144
    assert item.edad_maxima_meses == 215


def test_age_group_input_rejects_inconsistent_representations() -> None:
    with pytest.raises(ValueError, match="no coincide"):
        AgeGroupRangeInput(
            codigo="ADOLESCENTE",
            edad_minima_meses=143,
            edad_minima={"anios": 12},
        )
