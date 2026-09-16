"""Authoritative nutritional indicators derived from clinical measurements.

The WHO 2006 tables apply to boys and girls from birth through 60 completed
months.  This module intentionally produces indicators only; it does not turn
them into diagnoses, which remain a clinician's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from math import isfinite

from anthro import compute

WHO_2006_REFERENCE = "OMS 2006 (0 a 60 meses)"
_MAX_WHO_AGE_DAYS = 1826
_THREE_DECIMALS = Decimal("0.001")


@dataclass(frozen=True)
class NutritionalIndicators:
    """Calculated values and a display-safe explanation of their availability."""

    imc: Decimal | None
    pe: Decimal | None
    te: Decimal | None
    pt: Decimal | None
    estado: str
    mensaje: str
    referencia: str | None


def calculate_nutritional_indicators(
    *,
    birth_date: date,
    sex_code: str | None,
    measured_on: date,
    weight_kg: Decimal | None,
    height_cm: Decimal | None,
) -> NutritionalIndicators:
    """Calculate BMI and WHO 2006 WAZ/HAZ/WHZ when the reference applies.

    ``P/E``, ``T/E`` and ``P/T`` are respectively WAZ, HAZ and WHZ.  BMI is
    intentionally still returned for an adult, while the child-only Z scores
    are not extrapolated beyond the WHO reference range.
    """

    imc = _calculate_bmi(weight_kg, height_cm)
    if weight_kg is None or height_cm is None:
        return NutritionalIndicators(
            imc=imc,
            pe=None,
            te=None,
            pt=None,
            estado="DATOS_INCOMPLETOS",
            mensaje="Ingrese peso y talla para calcular los indicadores nutricionales.",
            referencia=WHO_2006_REFERENCE,
        )

    age_days = (measured_on - birth_date).days
    if age_days < 0:
        return NutritionalIndicators(
            imc=imc,
            pe=None,
            te=None,
            pt=None,
            estado="FECHA_INVALIDA",
            mensaje="La fecha de medición no puede ser anterior al nacimiento.",
            referencia=None,
        )
    if age_days > _MAX_WHO_AGE_DAYS:
        return NutritionalIndicators(
            imc=imc,
            pe=None,
            te=None,
            pt=None,
            estado="NO_APLICA_EDAD",
            mensaje="P/E, T/E y P/T de OMS 2006 aplican de 0 a 60 meses.",
            referencia=None,
        )

    normalized_sex = {"M": "m", "F": "f"}.get((sex_code or "").upper())
    if normalized_sex is None:
        return NutritionalIndicators(
            imc=imc,
            pe=None,
            te=None,
            pt=None,
            estado="SIN_REFERENCIA_SEXO",
            mensaje="La referencia OMS 2006 requiere sexo registrado como femenino o masculino.",
            referencia=WHO_2006_REFERENCE,
        )

    result = compute(
        {
            "sex": normalized_sex,
            "dob": birth_date,
            "measured": measured_on,
            "weight_kg": float(weight_kg),
            "height_cm": float(height_cm),
        }
    )
    scores = (
        _as_decimal(result.get("z_wfa")),
        _as_decimal(result.get("z_lhfa")),
        _as_decimal(result.get("z_wflh")),
    )
    if any(score is None for score in scores) or result.get("errors"):
        return NutritionalIndicators(
            imc=imc,
            pe=None,
            te=None,
            pt=None,
            estado="NO_DISPONIBLE",
            mensaje="No fue posible calcular los indicadores con la referencia OMS 2006.",
            referencia=WHO_2006_REFERENCE,
        )

    pe, te, pt = scores
    return NutritionalIndicators(
        imc=imc,
        pe=pe,
        te=te,
        pt=pt,
        estado="CALCULADO",
        mensaje=(
            "Indicadores calculados con la referencia OMS 2006; "
            "valide la interpretación clínica."
        ),
        referencia=WHO_2006_REFERENCE,
    )


def _calculate_bmi(weight_kg: Decimal | None, height_cm: Decimal | None) -> Decimal | None:
    if weight_kg is None or height_cm is None or height_cm <= 0:
        return None
    height_m = height_cm / Decimal("100")
    return (weight_kg / (height_m * height_m)).quantize(_THREE_DECIMALS, ROUND_HALF_UP)


def _as_decimal(value: object) -> Decimal | None:
    if not isinstance(value, (int, float)) or not isfinite(value):
        return None
    return Decimal(str(value)).quantize(_THREE_DECIMALS, ROUND_HALF_UP)
