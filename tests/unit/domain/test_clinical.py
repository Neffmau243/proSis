from decimal import Decimal

import pytest

from app.domain.clinical import ConfigurableClinicalProtocol, VitalSignPayload


def test_default_protocol_accepts_valid_vital_signs() -> None:
    protocol = ConfigurableClinicalProtocol()

    protocol.validate(
        VitalSignPayload(
            peso_kg=Decimal("65.20"),
            talla_cm=Decimal("168.0"),
            presion_sistolica=120,
            presion_diastolica=80,
            temperatura_c=Decimal("36.5"),
        ),
        age_in_months=360,
    )


def test_protocol_rejects_inverted_blood_pressure() -> None:
    with pytest.raises(ValueError, match="sistólica"):
        ConfigurableClinicalProtocol().validate(
            VitalSignPayload(presion_sistolica=70, presion_diastolica=80),
            age_in_months=360,
        )
