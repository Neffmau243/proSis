<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import AdmissionPatientSisSummary from './AdmissionPatientSisSummary.vue'
import PatientSisCodeFields from '@/components/patients/PatientSisCodeFields.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAdmissionPatientDetails } from '@/composables/useAdmissionPatientDetails'
import { useAdmissionPatientEditor } from '@/composables/useAdmissionPatientEditor'
import { patientFields, type PatientFieldKey } from '@/utils/patientDraft'
import { pacientes, type Patient } from '@/services/pacientes'
import type { CodeCatalogItem } from '@/services/catalogos'

const props = defineProps<{
  patient: Patient
  canEdit: boolean
  /** El permiso de baja vive fuera del editor: la admisión solo lo refleja. */
  canDelete?: boolean
  blocked?: boolean
  /** Catálogo cargado por la vista, que también lo usa para el diálogo de responsables. */
  tiposDocumento: CodeCatalogItem[]
}>()
const emit = defineEmits<{
  saved: [patient: Patient]
  dirtyChange: [dirty: boolean]
  busyChange: [busy: boolean]
  removed: [patient: Patient]
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
  sexos,
  seguros,
  etnias,
  catalogError,
  loadCatalogs,
  establishments,
  districts,
  localities,
  localitiesLoading,
  localitiesError,
  loadLocalities,
} = useAdmissionPatientDetails(toRef(props, 'patient'))
const removing = ref(false)
const fullName = computed(() =>
  [
    props.patient.apellido_paterno,
    props.patient.apellido_materno,
    props.patient.primer_nombre,
  ]
    .filter(Boolean)
    .join(' ') || `Paciente #${props.patient.id}`,
)
const disabled = computed(
  () => !props.canEdit || !props.patient.estado || saving.value || props.blocked,
)
const canRemove = computed(
  () => Boolean(props.canDelete) && props.patient.estado && !props.blocked && !saving.value,
)
const options = computed<
  Partial<Record<PatientFieldKey, { label: string; value: string | number }[]>>
>(() => ({
  tipo_documento_codigo: props.tiposDocumento.map((item) => ({
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
  localidad_id: localities.value.map((item) => ({ label: item.nombre, value: item.id })),
}))
function fieldOptions(key: PatientFieldKey) {
  const list = options.value[key] ?? []
  const value = draft[key]
  if (value && !list.some((item) => item.value === value)) {
    let label = String(value)
    if (key === 'ubigeo_residencia_codigo' && value === props.patient.ubigeo_residencia_codigo) {
      label = props.patient.distrito_residencia || label
    } else if (key === 'localidad_id' && typeof draft.localidad === 'string') {
      label = draft.localidad
    }
    return [{ value, label }, ...list]
  }
  return list
}

// La localidad pertenece a un distrito: al cambiarlo se limpia la selección y
// se recarga el catálogo SIS de ese distrito.
let currentDistrict: string | null = props.patient.ubigeo_residencia_codigo
watch(
  () => draft.ubigeo_residencia_codigo,
  (code) => {
    if (code !== currentDistrict) {
      draft.localidad_id = null
      draft.localidad = null
      currentDistrict = code
    }
    void loadLocalities(code || null)
  },
  { immediate: true },
)

function onLocalityChange(value: number | null): void {
  if (value === null) {
    draft.localidad = null
    return
  }
  const chosen = localities.value.find((item) => item.id === value)
  if (chosen) draft.localidad = chosen.nombre
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
async function removePatient(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `¿Dar de baja a ${fullName.value}? La baja es lógica: el historial se conserva.`,
      'Eliminar paciente',
      { type: 'warning', confirmButtonText: 'Eliminar', cancelButtonText: 'Cancelar' },
    )
  } catch {
    return
  }
  removing.value = true
  try {
    const result = await pacientes.deactivate(props.patient.id)
    ElMessage.success(result.mensaje)
    emit('removed', props.patient)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'No se pudo eliminar el paciente.')
  } finally {
    removing.value = false
  }
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
        <template v-for="field in patientFields" :key="field.key">
          <el-form-item
            :class="{ 'patient-context__insurance': field.key === 'seguro_id' }"
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
              v-else-if="field.key === 'localidad_id'"
              v-model="draft.localidad_id"
              filterable
              clearable
              :disabled="disabled || !draft.ubigeo_residencia_codigo"
              :loading="localitiesLoading"
              :aria-label="field.label"
              :placeholder="
                draft.ubigeo_residencia_codigo ? 'Seleccione' : 'Elija el distrito primero'
              "
              @change="onLocalityChange"
            >
              <el-option
                v-for="option in fieldOptions('localidad_id')"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
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
            <p
              v-if="field.key === 'localidad_id' && localitiesError"
              class="patient-context__field-error"
              role="alert"
            >
              {{ localitiesError }}
              <el-button
                link
                type="primary"
                @click="loadLocalities(draft.ubigeo_residencia_codigo || null)"
                >Reintentar</el-button
              >
            </p>
          </el-form-item>
          <PatientSisCodeFields
            v-if="field.key === 'seguro_id'"
            class="patient-context__insurance"
            :value="draft"
            :disabled="disabled"
            :errors="fieldErrors"
            @update="Object.assign(draft, $event)"
          />
        </template>
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
          <el-button
            v-if="canRemove"
            class="patient-context__remove"
            type="danger"
            :loading="removing"
            @click="removePatient"
          >
            Eliminar paciente
          </el-button>
        </div>
      </el-form>
      <AdmissionPatientSisSummary
        :patient="patient"
        :ethnicities="etnias"
        :show-affiliation="false"
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
.patient-context__insurance {
  grid-column: 1 / -1;
}
.patient-context__actions :deep(.el-button) {
  margin: 0;
}
/* La baja es una acción destructiva: se separa del guardado habitual. */
.patient-context__remove {
  margin-top: 8px !important;
  border-style: dashed;
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
