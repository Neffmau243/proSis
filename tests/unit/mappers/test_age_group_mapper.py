from app.mappers.age_group import age_group_to_response
from app.models.catalog import AgeGroup


def test_age_group_mapper_exposes_exact_and_human_readable_bounds() -> None:
    result = age_group_to_response(
        AgeGroup(
            codigo="ADOLESCENTE",
            nombre="Adolescente",
            edad_minima_meses=144,
            edad_maxima_meses=215,
            activo=True,
        )
    )

    assert result.edad_minima_meses == 144
    assert result.edad_minima.model_dump() == {"anios": 12, "meses": 0}
    assert result.edad_maxima.model_dump() == {"anios": 17, "meses": 11}
    assert result.rango_edad_legible == "De 12 años a 17 años y 11 meses"


def test_age_group_mapper_describes_open_ended_range() -> None:
    result = age_group_to_response(
        AgeGroup(
            codigo="ADULTO_MAYOR",
            nombre="Adulto mayor",
            edad_minima_meses=720,
            edad_maxima_meses=None,
            activo=True,
        )
    )

    assert result.edad_maxima is None
    assert result.rango_edad_legible == "Desde 60 años"
