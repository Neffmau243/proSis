<template>
  <section class="patient-context" aria-label="Datos del paciente para admisión">
    <header class="patient-context__header">
      <h3 class="patient-context__title">Datos del paciente</h3>
      <el-tag type="primary" effect="light">Admisión</el-tag>
    </header>

    <dl class="patient-context__details">
      <div>
        <dt>N.° HC</dt>
        <dd>{{ patient.historia_clinica || '—' }}</dd>
      </div>
      <div>
        <dt>Historia familiar</dt>
        <dd>{{ patient.historia_familiar || '—' }}</dd>
      </div>
      <div>
        <dt>Documento</dt>
        <dd>{{ patient.tipo_documento_codigo }} {{ patient.numero_documento }}</dd>
      </div>
      <div>
        <dt>Nacimiento</dt>
        <dd>{{ formatDate(patient.fecha_nacimiento) }} · {{ ageLabel }}</dd>
      </div>
      <div>
        <dt>A. paterno</dt>
        <dd>{{ patient.apellido_paterno || '—' }}</dd>
      </div>
      <div>
        <dt>A. materno</dt>
        <dd>{{ patient.apellido_materno || '—' }}</dd>
      </div>
      <div>
        <dt>Primer nombre</dt>
        <dd>{{ patient.primer_nombre || '—' }}</dd>
      </div>
      <div>
        <dt>Otros nombres</dt>
        <dd>{{ patient.otros_nombres || '—' }}</dd>
      </div>
      <div>
        <dt>Sexo</dt>
        <dd>{{ sexoLabel }}</dd>
      </div>
      <div>
        <dt>Localidad</dt>
        <dd>{{ patient.localidad || '—' }}</dd>
      </div>
      <div>
        <dt>Dirección</dt>
        <dd>{{ patient.direccion || '—' }}</dd>
      </div>
      <div>
        <dt>Seguro</dt>
        <dd>{{ seguroLabel }}</dd>
      </div>
      <div>
        <dt>Teléfono</dt>
        <dd>{{ patient.telefono_principal || '—' }}</dd>
      </div>
      <div>
        <dt>Grupo de riesgo</dt>
        <dd>{{ riesgoLabel }}</dd>
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

function formatDate(value: string | null): string {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return year && month && day ? `${day}/${month}/${year}` : value
}

onMounted(async () => {
  try {
    ;[sexos.value, seguros.value] = await Promise.all([catalogos.sexos(), catalogos.seguros()])
  } catch {
    // Sin catálogos se muestran los códigos recibidos; no bloquea la admisión.
  }
})
</script>

<style scoped>
.patient-context {
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background-color: var(--el-fill-color-blank);
}

.patient-context__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.patient-context__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
}

.patient-context__details {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
  padding: 12px;
  margin: 0;
}

.patient-context__details div {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.patient-context__details dt {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
}

.patient-context__details dd {
  min-height: 28px;
  padding: 5px 7px;
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--el-text-color-primary);
  background-color: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

@media (max-width: 900px) {
  .patient-context__details {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 16px;
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
