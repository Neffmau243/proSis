from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.mappers.attention import attention_to_response


def test_attention_mapper_exposes_history_display_data_from_real_relations() -> None:
    entity = SimpleNamespace(
        id=1,
        paciente_id=10,
        establecimiento_id=2,
        profesional_id=3,
        especialidad_codigo="MEDICINA_GENERAL",
        consultorio_id=4,
        consultorio=SimpleNamespace(nombre="Consultorio de medicina"),
        modalidad_atencion_codigo="AMBULATORIA",
        grupo_etario_codigo="ADULTO",
        fecha_atencion=datetime(2026, 9, 10, 9, 30),
        fecha_atendido=None,
        historia_clinica_snapshot="HC-001",
        edad_anios=36,
        paciente=SimpleNamespace(fecha_nacimiento=date(1990, 5, 10)),
        peso_kg=Decimal("72.50"),
        talla_cm=Decimal("170.00"),
        perimetro_abdominal_cm=None,
        presion_sistolica=120,
        presion_diastolica=80,
        temperatura_c=Decimal("36.5"),
        imc=Decimal("25.087"),
        pe=None,
        te=None,
        pt=None,
        referencia_nutricional=None,
        hora_inicio=None,
        hora_fin=None,
        admision=None,
        observaciones=None,
        estado="ATENDIDO",
        created_by_usuario_id=7,
        created_at=datetime(2026, 9, 10, 9, 30),
        updated_at=datetime(2026, 9, 10, 9, 30),
        prestaciones=[],
        diagnosticos=[],
    )

    result = attention_to_response(entity)  # type: ignore[arg-type]

    assert result.consultorio_nombre == "Consultorio de medicina"
    assert result.edad_detallada == "36 años, 4 meses y 0 días"
