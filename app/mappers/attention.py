"""Explicit ORM-to-DTO mapping for clinical attention responses."""

from app.models.clinical import Attention
from app.schemas.attention import (
    AttentionDiagnosisResponse,
    AttentionResponse,
    AttentionServiceResponse,
)


def attention_to_response(entity: Attention) -> AttentionResponse:
    return AttentionResponse(
        id=entity.id,
        paciente_id=entity.paciente_id,
        establecimiento_id=entity.establecimiento_id,
        profesional_id=entity.profesional_id,
        especialidad_codigo=entity.especialidad_codigo,
        consultorio_id=entity.consultorio_id,
        modalidad_atencion_codigo=entity.modalidad_atencion_codigo,
        grupo_etario_codigo=entity.grupo_etario_codigo,
        fecha_atencion=entity.fecha_atencion,
        fecha_atendido=entity.fecha_atendido,
        historia_clinica_snapshot=entity.historia_clinica_snapshot,
        edad_anios=entity.edad_anios,
        peso_kg=entity.peso_kg,
        talla_cm=entity.talla_cm,
        perimetro_abdominal_cm=entity.perimetro_abdominal_cm,
        presion_sistolica=entity.presion_sistolica,
        presion_diastolica=entity.presion_diastolica,
        temperatura_c=entity.temperatura_c,
        pe=entity.pe,
        te=entity.te,
        pt=entity.pt,
        hora_inicio=entity.hora_inicio,
        hora_fin=entity.hora_fin,
        admision=entity.admision,
        observaciones=entity.observaciones,
        estado=entity.estado,
        created_by_usuario_id=entity.created_by_usuario_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        prestaciones=[
            AttentionServiceResponse(
                numero_orden=item.numero_orden,
                prestacion_codigo=item.prestacion_codigo,
                cantidad=item.cantidad,
            )
            for item in entity.prestaciones
        ],
        diagnosticos=[
            AttentionDiagnosisResponse(
                numero_orden=item.numero_orden,
                cie10_codigo=item.cie10_codigo,
                tipo_diagnostico=item.tipo_diagnostico,
                observacion=item.observacion,
            )
            for item in entity.diagnosticos
        ],
    )
