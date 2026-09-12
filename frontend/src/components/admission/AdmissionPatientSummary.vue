<template>
  <section class="patient-context" aria-label="Paciente para admisión">
    <div class="patient-context__header">
      <div>
        <h3 class="patient-context__title">{{ fullName }}</h3>
        <p class="patient-context__subtitle">Paciente confirmado para esta admisión</p>
      </div>
      <el-tag type="primary" effect="light">Admisión</el-tag>
    </div>

    <dl class="patient-context__details">
      <div>
        <dt>Documento</dt>
        <dd>{{ patient.tipo_documento_codigo }} {{ patient.numero_documento }}</dd>
      </div>
      <div>
        <dt>Historia clínica</dt>
        <dd>{{ patient.historia_clinica || 'Sin historia clínica' }}</dd>
      </div>
      <div>
        <dt>Historia familiar</dt>
        <dd>{{ patient.historia_familiar || '—' }}</dd>
      </div>
      <div>
        <dt>Nacimiento</dt>
        <dd>{{ formatDate(patient.fecha_nacimiento) }} · {{ ageLabel }}</dd>
      </div>
      <div>
        <dt>Sexo</dt>
        <dd>{{ sexoLabel }}</dd>
      </div>
      <div>
        <dt>Teléfono</dt>
        <dd>{{ patient.telefono_principal || 'No registrado' }}</dd>
      </div>
      <div>
        <dt>Seguro</dt>
        <dd>{{ seguroLabel }}</dd>
      </div>
      <div>
        <dt>Grupo de riesgo</dt>
        <dd>{{ riesgoLabel }}</dd>
      </div>
      <div class="patient-context__wide">
        <dt>Dirección</dt>
        <dd>{{ direccionLabel }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { catalogos, type CodeCatalogItem, type IdCatalogItem } from '@/services/catalogos'
import type { Patient } from '@/services/pacientes'

const props = defineProps<{
  patient: Patient
}>()

const sexos = ref<CodeCatalogItem[]>([])
const seguros = ref<IdCatalogItem[]>([])

const fullName = computed(() => {
  const name = [
    props.patient.apellido_paterno,
    props.patient.apellido_materno,
    props.patient.primer_nombre,
    props.patient.otros_nombres,
  ]
    .filter(Boolean)
    .join(' ')

  return name || props.patient.numero_documento
})

const sexoLabel = computed(
  () =>
    sexos.value.find((sexo) => sexo.codigo === props.patient.sexo_codigo)?.nombre ??
    props.patient.sexo_codigo ??
    '—',
)

const ageLabel = computed(() => {
  const [year, month, day] = props.patient.fecha_nacimiento.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return 'Edad no disponible'

  const today = new Date()
  let age = today.getFullYear() - year
  const birthdayHasPassed =
    today.getMonth() + 1 > month || (today.getMonth() + 1 === month && today.getDate() >= day)

  if (!birthdayHasPassed) age -= 1
  return `${Math.max(age, 0)} años`
})

const seguroLabel = computed(
  () => seguros.value.find((seguro) => seguro.id === props.patient.seguro_id)?.nombre ?? '—',
)

const riesgoLabel = computed(() => {
  const activos = (props.patient.riesgos ?? [])
    .filter((riesgo) => !riesgo.fecha_fin)
    .map((riesgo) => riesgo.grupo_riesgo_nombre)
    .filter(Boolean)
  return activos.length > 0 ? activos.join(', ') : '—'
})

const direccionLabel = computed(() => {
  const parts = [props.patient.direccion, props.patient.localidad].filter(Boolean)
  return parts.length > 0 ? parts.join(' · ') : '—'
})

function formatDate(value: string | null): string {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return year && month && day ? `${day}/${month}/${year}` : value
}

onMounted(async () => {
  try {
    ;[sexos.value, seguros.value] = await Promise.all([catalogos.sexos(), catalogos.seguros()])
  } catch {
    // Sin catálogos solo se muestran los códigos; no bloquea la admisión.
  }
})
</script>

<style scoped>
.patient-context {
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background-color: var(--el-fill-color-blank);
}

.patient-context__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.patient-context__title {
  margin: 0;
  font-size: 16px;
  line-height: 1.3;
}

.patient-context__subtitle {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.patient-context__details {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  margin: 16px 0 0;
}

.patient-context__details div {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
  padding: 10px 0;
  border-top: 1px solid var(--el-border-color-lighter);
}

.patient-context__details dt {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.4;
}

.patient-context__details dd {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .patient-context {
    padding: 16px;
  }

  .patient-context__details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 20px;
  }

  .patient-context__details div {
    grid-template-columns: 88px minmax(0, 1fr);
  }
}

@media (max-width: 560px) {
  .patient-context__header {
    flex-direction: column;
    gap: 8px;
  }

  .patient-context__details {
    grid-template-columns: 1fr;
  }

  .patient-context__details div {
    grid-template-columns: 96px minmax(0, 1fr);
  }
}
</style>
