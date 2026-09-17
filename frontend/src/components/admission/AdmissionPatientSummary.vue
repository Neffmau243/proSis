<script setup lang="ts">
import { computed, toRef, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AdmissionPatientRelations from './AdmissionPatientRelations.vue'
import { useAdmissionPatientDetails } from '@/composables/useAdmissionPatientDetails'
import { useAdmissionPatientEditor } from '@/composables/useAdmissionPatientEditor'
import { patientFields, type PatientFieldKey } from '@/utils/patientDraft'
import { pacientes, type Patient } from '@/services/pacientes'

const props = defineProps<{ patient: Patient; canEdit: boolean; blocked?: boolean }>()
const emit = defineEmits<{
  saved: [patient: Patient]
  dirtyChange: [dirty: boolean]
  busyChange: [busy: boolean]
}>()
const { draft, saving, dirty, error, fieldErrors, save, reset } = useAdmissionPatientEditor({
  patient: toRef(props, 'patient'),
  canEdit: () => props.canEdit && props.patient.estado,
  blocked: () => Boolean(props.blocked),
  update: pacientes.update,
  onSaved: (patient) => {
    emit('saved', patient)
    ElMessage.success('Datos del paciente actualizados.')
  },
})
const {
  tiposDocumento,
  sexos,
  seguros,
  gruposRiesgo,
  catalogError,
  loadCatalogs,
  establishments,
  districts,
  ageLabel,
  grupoEtarioLabel,
} = useAdmissionPatientDetails(toRef(props, 'patient'))
const disabled = computed(
  () => !props.canEdit || !props.patient.estado || saving.value || props.blocked,
)
const options = computed<
  Partial<Record<PatientFieldKey, { label: string; value: string | number }[]>>
>(() => ({
  tipo_documento_codigo: tiposDocumento.value.map((item) => ({
    label: item.nombre,
    value: item.codigo,
  })),
  sexo_codigo: sexos.value.map((item) => ({ label: item.nombre, value: item.codigo })),
  seguro_id: seguros.value.map((item) => ({ label: item.nombre, value: item.id })),
  establecimiento_registro_id: establishments.items.value.map((item) => ({
    label: item.nombre,
    value: item.id,
  })),
  ubigeo_residencia_codigo: districts.items.value.map((item) => ({
    label: `${item.distrito} · ${item.provincia} · ${item.departamento}`,
    value: item.codigo,
  })),
}))
function fieldOptions(key: PatientFieldKey) {
  const list = options.value[key] ?? []
  const value = draft[key]
  if (value && !list.some((item) => item.value === value)) {
    const label =
      key === 'ubigeo_residencia_codigo' && value === props.patient.ubigeo_residencia_codigo
        ? props.patient.distrito_residencia || String(value)
        : String(value)
    return [{ value, label }, ...list]
  }
  return list
}
function searchDistricts(query: string) {
  districts.search(
    query,
    districts.items.value.filter((item) => item.codigo === draft.ubigeo_residencia_codigo),
  )
}
function searchEstablishments(query: string) {
  establishments.search(
    query,
    establishments.items.value.filter((item) => item.id === draft.establecimiento_registro_id),
  )
}
watch(dirty, (value) => emit('dirtyChange', value), { immediate: true, flush: 'sync' })
watch(saving, (value) => emit('busyChange', value), { flush: 'sync' })
</script>

<template>
  <section class="patient-context" aria-labelledby="patient-context-title">
    <header class="patient-context__header">
      <h3 id="patient-context-title" class="patient-context__title">Datos del paciente</h3>
      <el-tag type="primary" effect="light" size="small">Admisión</el-tag>
    </header>
    <div class="patient-context__body">
      <el-alert v-if="catalogError" :title="catalogError" type="warning" :closable="false">
        <el-button link type="primary" @click="loadCatalogs">Reintentar catálogos</el-button>
      </el-alert>
      <p v-if="!canEdit" class="patient-context__hint">No tiene permiso para editar estos datos.</p>
      <el-form
        class="patient-context__form"
        :model="draft"
        label-position="left"
        label-width="110px"
        @submit.prevent="save"
      >
        <el-form-item
          v-for="field in patientFields"
          :key="field.key"
          :label="field.label"
          :error="fieldErrors[field.key]"
          :required="'required' in field && field.required"
        >
          <el-input
            v-if="field.kind === 'text'"
            v-model="draft[field.key]"
            :maxlength="'max' in field ? field.max : undefined"
            :disabled="disabled"
            :aria-label="field.label"
            :inputmode="field.key === 'telefono_principal' ? 'tel' : 'text'"
          />
          <el-input
            v-else-if="field.kind === 'date'"
            v-model="draft[field.key]"
            type="date"
            :disabled="disabled"
            :aria-label="field.label"
          />
          <el-select
            v-else
            v-model="draft[field.key]"
            filterable
            :clearable="!('required' in field && field.required)"
            :disabled="disabled"
            :aria-label="field.label"
            placeholder="Seleccione"
            :remote="
              field.key === 'ubigeo_residencia_codigo' ||
              field.key === 'establecimiento_registro_id'
            "
            :remote-method="
              field.key === 'ubigeo_residencia_codigo' ? searchDistricts : searchEstablishments
            "
            :loading="
              field.key === 'ubigeo_residencia_codigo'
                ? districts.loading.value
                : field.key === 'establecimiento_registro_id' && establishments.loading.value
            "
          >
            <el-option
              v-for="option in fieldOptions(field.key)"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <p
            v-if="field.key === 'ubigeo_residencia_codigo' && districts.error.value"
            class="patient-context__field-error"
            role="alert"
          >
            {{ districts.error.value }}
            <el-button
              link
              type="primary"
              @click="districts.load(draft.ubigeo_residencia_codigo || undefined)"
              >Reintentar</el-button
            >
          </p>
          <p
            v-if="field.key === 'establecimiento_registro_id' && establishments.error.value"
            class="patient-context__field-error"
            role="alert"
          >
            {{ establishments.error.value }}
            <el-button link type="primary" @click="establishments.load()">Reintentar</el-button>
          </p>
        </el-form-item>
        <div v-if="canEdit" class="patient-context__actions">
          <el-alert v-if="error" :title="error" type="error" :closable="false" />
          <p class="patient-context__hint" role="status">
            {{ dirty ? 'Tiene cambios sin guardar.' : 'Datos del paciente guardados.' }}
          </p>
          <el-button
            type="primary"
            native-type="submit"
            :loading="saving"
            :disabled="!dirty || disabled"
            >Guardar cambios</el-button
          >
          <el-button v-if="dirty" :disabled="disabled" @click="reset">Descartar cambios</el-button>
        </div>
      </el-form>
      <dl class="patient-context__derived">
        <div>
          <dt>Edad actual</dt>
          <dd>{{ ageLabel }}</dd>
        </div>
        <div>
          <dt>Grupo etario</dt>
          <dd>{{ grupoEtarioLabel }}</dd>
        </div>
      </dl>
      <p class="patient-context__hint">Se calculan con la fecha de nacimiento guardada.</p>
      <AdmissionPatientRelations
        :patient="patient"
        :disabled="disabled"
        :can-edit="canEdit"
        :tipos-documento="tiposDocumento"
        :grupos-riesgo="gruposRiesgo"
        @saved="emit('saved', $event)"
        @busy-change="emit('busyChange', $event)"
      />
    </div>
  </section>
</template>

<style scoped>
.patient-context {
  min-width: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  background: var(--el-fill-color-blank);
}
.patient-context__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.patient-context__title {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.patient-context__body {
  padding: 12px;
}
.patient-context__form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  margin-top: 8px;
}
.patient-context__form :deep(.el-form-item) {
  margin-bottom: 0;
  min-width: 0;
}
.patient-context__form :deep(.el-form-item__label) {
  height: auto;
  line-height: 1.4;
  padding: 6px 8px 0 0;
  margin-bottom: 4px;
  font-size: 12px;
}
.patient-context__form :deep(.el-form-item__error) {
  position: static;
  line-height: 1.4;
}
.patient-context__form :deep(.el-form-item__content) {
  display: block;
  min-width: 0;
}
.patient-context__form :deep(.el-input),
.patient-context__form :deep(.el-select) {
  width: 100%;
}
.patient-context__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
  grid-column: 1 / -1;
}
.patient-context__actions :deep(.el-button) {
  margin: 0;
}
.patient-context__hint {
  margin: 6px 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}
.patient-context__field-error {
  color: var(--el-color-danger);
  font-size: 12px;
  margin: 4px 0 0;
}
.patient-context__derived {
  margin: 16px 0 0;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}
.patient-context__derived > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 6px;
}
.patient-context__derived dd {
  margin: 0;
  font-weight: 600;
}
@media (min-width: 561px) and (max-width: 900px) {
  .patient-context__form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .patient-context__form :deep(.el-input__inner),
  .patient-context__form :deep(.el-select__input) {
    font-size: 16px;
  }
  .patient-context__form :deep(.el-form-item) {
    flex-direction: column;
  }
  .patient-context__form :deep(.el-form-item__label) {
    width: auto !important;
  }
  .patient-context__form :deep(.el-form-item__content) {
    width: 100%;
    margin-left: 0 !important;
  }
}
</style>
