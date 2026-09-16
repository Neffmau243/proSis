<script setup lang="ts">
import { toRef } from 'vue'

import {
  useAdmissionPatientDetails,
  type AdmissionPatientEditableField,
} from '@/composables/useAdmissionPatientDetails'
import type { Patient, PatientUpdatePayload } from '@/services/pacientes'

type PatientContextUpdate = Pick<
  PatientUpdatePayload,
  | 'sexo_codigo'
  | 'localidad'
  | 'direccion'
  | 'establecimiento_registro_id'
  | 'seguro_id'
>

const props = defineProps<{
  patient: Patient
  saving?: boolean
}>()

const emit = defineEmits<{
  update: [payload: PatientContextUpdate]
}>()

const {
  details,
  sexos,
  seguros,
  establecimientos,
  establecimientosLoading,
  searchEstablecimientos,
} = useAdmissionPatientDetails(toRef(props, 'patient'))

function saveValue<K extends AdmissionPatientEditableField>(
  field: K,
  value: PatientContextUpdate[K],
): void {
  if (value === props.patient[field]) return
  emit('update', { [field]: value } as PatientContextUpdate)
}

function saveText(field: 'localidad' | 'direccion', value: string): void {
  saveValue(field, value.trim() || null)
}

function saveNullableValue<
  K extends 'sexo_codigo' | 'establecimiento_registro_id' | 'seguro_id',
>(field: K, value: PatientContextUpdate[K] | undefined): void {
  saveValue(field, (value ?? null) as PatientContextUpdate[K])
}
</script>

<template>
  <section class="patient-context" aria-label="Datos del paciente para admisión">
    <header class="patient-context__header">
      <h3 class="patient-context__title">Datos del paciente</h3>
      <el-tag type="primary" effect="light">Admisión</el-tag>
    </header>

    <dl class="patient-context__details">
      <div v-for="detail in details" :key="detail.label">
        <dt>{{ detail.label }}</dt>
        <dd :class="{ 'patient-context__value--editable': detail.editableField }">
          <el-select
            v-if="detail.editableField === 'sexo_codigo'"
            class="patient-context__editor"
            style="width: 100%"
            :model-value="patient.sexo_codigo"
            :disabled="saving"
            :aria-label="detail.label"
            @change="saveNullableValue('sexo_codigo', $event)"
          >
            <el-option
              v-for="sexo in sexos"
              :key="sexo.codigo"
              :label="sexo.nombre"
              :value="sexo.codigo"
            />
          </el-select>
          <el-input
            v-else-if="detail.editableField === 'localidad'"
            class="patient-context__editor"
            style="width: 100%"
            :model-value="patient.localidad ?? ''"
            :disabled="saving"
            :aria-label="detail.label"
            @change="saveText('localidad', $event)"
          />
          <el-input
            v-else-if="detail.editableField === 'direccion'"
            class="patient-context__editor"
            style="width: 100%"
            :model-value="patient.direccion ?? ''"
            :disabled="saving"
            :aria-label="detail.label"
            @change="saveText('direccion', $event)"
          />
          <el-select
            v-else-if="detail.editableField === 'establecimiento_registro_id'"
            class="patient-context__editor"
            style="width: 100%"
            filterable
            remote
            remote-show-suffix
            :remote-method="searchEstablecimientos"
            :loading="establecimientosLoading"
            :model-value="patient.establecimiento_registro_id"
            :disabled="saving"
            :aria-label="detail.label"
            @change="saveNullableValue('establecimiento_registro_id', $event)"
          >
            <el-option
              v-for="establecimiento in establecimientos"
              :key="establecimiento.id"
              :label="establecimiento.nombre"
              :value="establecimiento.id"
            />
          </el-select>
          <el-select
            v-else-if="detail.editableField === 'seguro_id'"
            class="patient-context__editor"
            style="width: 100%"
            filterable
            :model-value="patient.seguro_id"
            :disabled="saving"
            :aria-label="detail.label"
            @change="saveNullableValue('seguro_id', $event)"
          >
            <el-option
              v-for="seguro in seguros"
              :key="seguro.id"
              :label="seguro.nombre"
              :value="seguro.id"
            />
          </el-select>
          <template v-else>{{ detail.value }}</template>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.patient-context {
  --patient-context-control-height: 26px;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background-color: var(--el-fill-color-blank);
}

.patient-context__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.patient-context__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.3;
}

.patient-context__details {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 3px;
  padding: 8px;
  margin: 0;
}

/* Solo las filas directas del <dl>: con `div` a secas esta grilla también alcanzaba
   al div raíz de el-input/el-select y lo dejaba en una columna de 94px. */
.patient-context__details > div {
  display: grid;
  grid-template-columns: 94px minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.patient-context__details dt {
  color: var(--el-text-color-secondary);
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1.35;
}

.patient-context__details dd {
  display: flex;
  align-items: center;
  box-sizing: border-box;
  inline-size: 100%;
  min-inline-size: 0;
  min-height: var(--patient-context-control-height);
  padding: 4px 7px;
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--el-text-color-primary);
  background-color: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 5px;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1.25;
}

.patient-context__details dd.patient-context__value--editable {
  display: block;
  min-height: var(--patient-context-control-height);
  padding: 0;
  overflow: visible;
  background-color: transparent;
  border: 0;
}

.patient-context__editor {
  display: block;
  width: 100% !important;
  max-width: none;
  min-inline-size: 0;
}

/* Altura única para inputs y selects: sin esto el-input mide 32px y el-select 26px,
   por lo que las filas quedaban desalineadas y se superponían entre sí. */
.patient-context__editor :deep(.el-input),
.patient-context__editor :deep(.el-select) {
  width: 100%;
}

.patient-context__editor :deep(.el-input__wrapper),
.patient-context__editor :deep(.el-select__wrapper) {
  display: flex;
  box-sizing: border-box;
  width: 100%;
  max-width: none;
  inline-size: 100%;
  height: var(--patient-context-control-height);
  min-height: var(--patient-context-control-height);
  padding: 0 7px;
  gap: 4px;
  background-color: var(--el-fill-color-light);
  border-radius: 5px;
  box-shadow: 0 0 0 1px var(--el-border-color) inset;
}

.patient-context__editor :deep(.el-input__inner) {
  height: var(--patient-context-control-height);
  line-height: var(--patient-context-control-height);
}

.patient-context__editor :deep(.el-select__selection) {
  min-height: 0;
  gap: 4px;
}

.patient-context__editor :deep(.el-input__inner),
.patient-context__editor :deep(.el-select__selected-item),
.patient-context__editor :deep(.el-select__input) {
  color: var(--el-text-color-primary);
  font-size: 11.5px;
  font-weight: 600;
}

@media (max-width: 560px) {
  .patient-context__header {
    flex-direction: column;
    gap: 8px;
  }

  .patient-context__details > div {
    grid-template-columns: 88px minmax(0, 1fr);
  }
}
</style>
