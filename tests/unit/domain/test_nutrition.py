from datetime import date
from decimal import Decimal

from app.domain.nutrition import WHO_2006_REFERENCE, calculate_nutritional_indicators


def test_calculates_who_2006_scores_for_a_child_with_complete_measurements() -> None:
    indicators = calculate_nutritional_indicators(
        birth_date=date(2024, 1, 15),
        sex_code="M",
        measured_on=date(2025, 1, 15),
        weight_kg=Decimal("9.50"),
        height_cm=Decimal("75.20"),
    )

    assert indicators.imc == Decimal("16.799")
    assert indicators.pe == Decimal("-0.147")
    assert indicators.te == Decimal("-0.243")
    assert indicators.pt == Decimal("-0.056")
    assert indicators.estado == "CALCULADO"
    assert indicators.referencia == WHO_2006_REFERENCE


def test_keeps_bmi_but_does_not_extrapolate_child_scores_for_an_adult() -> None:
    indicators = calculate_nutritional_indicators(
        birth_date=date(1990, 5, 10),
        sex_code="F",
        measured_on=date(2026, 9, 12),
        weight_kg=Decimal("60.00"),
        height_cm=Decimal("160.00"),
    )

    assert indicators.imc == Decimal("23.438")
    assert (indicators.pe, indicators.te, indicators.pt) == (None, None, None)
    assert indicators.estado == "NO_APLICA_EDAD"
    assert indicators.referencia is None


def test_requires_weight_and_height_before_calculating_indicators() -> None:
    indicators = calculate_nutritional_indicators(
        birth_date=date(2024, 1, 15),
        sex_code="F",
        measured_on=date(2025, 1, 15),
        weight_kg=Decimal("9.00"),
        height_cm=None,
    )

    assert indicators.imc is None
    assert (indicators.pe, indicators.te, indicators.pt) == (None, None, None)
    assert indicators.estado == "DATOS_INCOMPLETOS"
