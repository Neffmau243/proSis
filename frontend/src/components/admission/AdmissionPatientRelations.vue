<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import ResponsibleDialog from '@/components/patient/ResponsibleDialog.vue'
import RiskDialog from '@/components/patient/RiskDialog.vue'
import type { Patient, PatientResponsible, PatientRisk } from '@/services/pacientes'
import type { CodeCatalogItem, RiskGroupCatalogItem } from '@/services/catalogos'

const props = defineProps<{
  patient: Patient
  disabled?: boolean
  canEdit: boolean
  tiposDocumento: CodeCatalogItem[]
  gruposRiesgo: RiskGroupCatalogItem[]
}>()
const emit = defineEmits<{ saved: [patient: Patient]; busyChange: [busy: boolean] }>()
const responsibleOpen = shallowRef(false)
const riskOpen = shallowRef(false)
const editingResponsible = shallowRef<PatientResponsible | null>(null)
const editingRisk = shallowRef<PatientRisk | null>(null)
const activeResponsibles = computed(() => props.patient.responsables.filter((item) => item.activo))
const mother = computed(
  () =>
    activeResponsibles.value.find((item) => item.parentesco === 'MADRE' && item.es_principal) ??
    activeResponsibles.value.find((item) => item.parentesco === 'MADRE'),
)
const busy = computed(() => responsibleOpen.value || riskOpen.value)
watch(busy, (value) => emit('busyChange', value), { flush: 'sync' })
function editResponsible(item: PatientResponsible | null) {
  editingResponsible.value = item
  responsibleOpen.value = true
}
function editRisk(item: PatientRisk | null) {
  editingRisk.value = item
  riskOpen.value = true
}
function responsibleSaved(item: PatientResponsible) {
  const others = props.patient.responsables.filter((existing) => existing.id !== item.id)
  emit('saved', { ...props.patient, responsables: [...others, item] })
}
function riskSaved(item: PatientRisk) {
  const others = props.patient.riesgos.filter(
    (existing) =>
      existing.grupo_riesgo_id !== item.grupo_riesgo_id ||
      existing.fecha_inicio !== item.fecha_inicio,
  )
  const group = props.gruposRiesgo.find((option) => option.id === item.grupo_riesgo_id)
  emit('saved', {
    ...props.patient,
    riesgos: [
      ...others,
      { ...item, grupo_riesgo_nombre: item.grupo_riesgo_nombre ?? group?.nombre ?? null },
    ],
  })
}
</script>

<template>
  <section class="patient-relations" aria-label="Responsables y riesgos del paciente">
    <h4 class="patient-relations__title">Grupo de riesgo</h4>
    <p v-if="!patient.riesgos.length" class="patient-relations__value">Sin registrar</p>
    <div
      v-for="item in patient.riesgos"
      :key="`${item.grupo_riesgo_id}-${item.fecha_inicio}`"
      class="patient-relations__row"
    >
      <span
        >{{ item.grupo_riesgo_nombre ?? `Grupo ${item.grupo_riesgo_id}` }} · {{ item.fecha_inicio
        }}{{ item.fecha_fin ? ` a ${item.fecha_fin}` : ' · Sin cierre' }}</span
      >
      <el-button
        v-if="canEdit"
        link
        type="primary"
        :disabled="disabled"
        :aria-label="`Editar riesgo ${item.grupo_riesgo_nombre ?? item.grupo_riesgo_id}`"
        @click="editRisk(item)"
        >Editar</el-button
      >
    </div>
    <el-button v-if="canEdit" link type="primary" :disabled="disabled" @click="editRisk(null)"
      >Agregar riesgo</el-button
    >
    <h4 class="patient-relations__title">Nombre de madre</h4>
    <p class="patient-relations__value">{{ mother?.nombre_completo ?? 'Sin registrar' }}</p>
    <el-button
      v-if="canEdit"
      link
      type="primary"
      :disabled="disabled"
      @click="editResponsible(mother ?? null)"
      >{{ mother ? 'Editar madre' : 'Agregar madre' }}</el-button
    >
    <details class="patient-relations__details">
      <summary>Responsables ({{ activeResponsibles.length }})</summary>
      <div v-for="item in patient.responsables" :key="item.id" class="patient-relations__row">
        <span
          >{{ item.nombre_completo }} · {{ item.parentesco
          }}{{ item.activo ? '' : ' · Inactivo' }}</span
        >
        <el-button
          v-if="canEdit"
          link
          type="primary"
          :disabled="disabled"
          :aria-label="`Editar responsable ${item.nombre_completo}`"
          @click="editResponsible(item)"
          >Editar</el-button
        >
      </div>
      <el-button
        v-if="canEdit"
        link
        type="primary"
        :disabled="disabled"
        @click="editResponsible(null)"
        >Agregar responsable</el-button
      >
    </details>
    <p v-if="canEdit" class="patient-relations__hint">
      Cada responsable y periodo de riesgo se guarda desde su formulario.
    </p>
    <ResponsibleDialog
      v-model="responsibleOpen"
      :patient-id="patient.id"
      :responsible="editingResponsible"
      :tipos-documento="tiposDocumento"
      @saved="responsibleSaved"
    />
    <RiskDialog
      v-model="riskOpen"
      :patient-id="patient.id"
      :riesgo="editingRisk"
      :grupos-riesgo="gruposRiesgo"
      @saved="riskSaved"
    />
  </section>
</template>

<style scoped>
.patient-relations {
  margin-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.patient-relations__title {
  margin: 12px 0 4px;
  font-size: 12px;
}
.patient-relations__value,
.patient-relations__hint {
  margin: 4px 0;
  font-size: 12px;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
.patient-relations__hint {
  color: var(--el-text-color-regular);
}
.patient-relations__details {
  margin-top: 10px;
  font-size: 12px;
}
.patient-relations__details > summary {
  cursor: pointer;
  padding-block: 4px;
}
.patient-relations__row {
  display: flex;
  align-items: start;
  gap: 8px;
  justify-content: space-between;
  margin: 6px 0;
  font-size: 12px;
  overflow-wrap: anywhere;
}
</style>
