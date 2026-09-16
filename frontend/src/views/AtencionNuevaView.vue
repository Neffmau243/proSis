<template>
  <div class="admission-page">
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-skeleton v-if="initialLoading" :rows="8" animated />

    <template v-else>
      <el-empty
        v-if="isAdmission && !admissionPatient"
        description="No fue posible cargar el paciente para esta admisión."
      />

      <div
        v-else-if="showForm"
        class="admission-workbench"
        :class="{ 'admission-workbench--standalone': !isAdmission }"
      >
        <aside v-if="isAdmission && admissionPatient" class="admission-workbench__patient">
          <AdmissionPatientSummary
            :patient="admissionPatient"
            :saving="patientContextSaving"
            @update="updateAdmissionPatient"
          />
        </aside>

        <div class="admission-workbench__content">
          <el-card class="encounter-card" shadow="never">
            <el-form
              ref="formRef"
              :model="form"
              :rules="rules"
              :label-width="isAdmission ? 'auto' : '200px'"
              :label-position="isAdmission ? 'top' : 'right'"
              class="encounter-form"
            >
              <section
                class="clinical-section clinical-section--context"
                aria-labelledby="encounter-context-title"
              >
                <div class="attention-mode-control">
                  <el-form-item label="Modalidad de atención" prop="modalidad_atencion_codigo">
                    <div
                      class="attention-mode-selector"
                      role="group"
                      aria-label="Modalidad de atención"
                    >
                      <el-checkbox
                        :model-value="form.modalidad_atencion_codigo === 'AMBULATORIA'"
                        @change="selectAttentionMode('AMBULATORIA')"
                      >
                        Ambulatoria
                      </el-checkbox>
                      <el-checkbox
                        :model-value="form.modalidad_atencion_codigo === 'EMERGENCIA'"
                        @change="selectAttentionMode('EMERGENCIA')"
                      >
                        Emergencia
                      </el-checkbox>
                    </div>
                  </el-form-item>
                </div>
                <div class="clinical-section__heading">
                  <div>
                    <h3 id="encounter-context-title" class="clinical-section__title">
                      Atención y consultorio
                    </h3>
                    <p class="clinical-section__description">
                      {{
                        isAdmission
                          ? 'Seleccione consultorio, especialidad y profesional para la atención.'
                          : 'Defina dónde, cuándo y con quién se registra la atención.'
                      }}
                    </p>
                  </div>
                </div>
                <el-row :gutter="16">
                  <template v-if="isAdmission">
                    <el-col :span="24">
                      <el-form-item
                        class="admission-context-field"
                        label="Consultorio"
                        prop="consultorio_id"
                      >
                        <el-select
                          v-model="form.consultorio_id"
                          filterable
                          :loading="consultoriosLoading"
                          style="width: 100%"
                          placeholder="Seleccione el consultorio"
                        >
                          <el-option
                            v-for="office in consultorios"
                            :key="office.id"
                            :label="office.nombre"
                            :value="office.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item class="admission-context-field" label="Especialidad">
                        <el-select v-model="form.especialidad_codigo" clearable style="width: 100%">
                          <el-option
                            v-for="esp in especialidades"
                            :key="esp.codigo"
                            :label="esp.nombre"
                            :value="esp.codigo"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="24">
                      <el-form-item
                        class="admission-context-field"
                        label="Profesional"
                        prop="profesional_id"
                      >
                        <el-select
                          v-model="form.profesional_id"
                          filterable
                          remote
                          :remote-method="searchProfesionales"
                          :loading="profesionalesLoading"
                          style="width: 100%"
                          placeholder="Seleccione el profesional"
                        >
                          <el-option
                            v-for="prof in profesionales"
                            :key="prof.id"
                            :label="prof.nombre_completo"
                            :value="prof.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </template>

                  <template v-else>
                    <el-col :span="8">
                      <el-form-item label="Paciente" prop="paciente_id">
                        <el-select
                          v-model="form.paciente_id"
                          filterable
                          remote
                          :remote-method="searchPacientes"
                          :loading="pacientesLoading"
                          style="width: 100%"
                          placeholder="Busque por documento o nombre"
                          :disabled="lockPatientSelection"
                        >
                          <el-option
                            v-for="paciente in pacientesOptions"
                            :key="paciente.id"
                            :label="`${paciente.id} — ${paciente.tipo_documento_codigo} ${paciente.numero_documento}${paciente.primer_nombre ? ' · ' + paciente.primer_nombre : ''}`"
                            :value="paciente.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="Establecimiento" prop="establecimiento_id">
                        <el-select
                          v-model="form.establecimiento_id"
                          filterable
                          remote
                          :remote-method="searchEstablecimientos"
                          :loading="establecimientosLoading"
                          style="width: 100%"
                          placeholder="Busque"
                        >
                          <el-option
                            v-for="est in establecimientos"
                            :key="est.id"
                            :label="est.nombre"
                            :value="est.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="Consultorio" prop="consultorio_id">
                        <el-select
                          v-model="form.consultorio_id"
                          filterable
                          :loading="consultoriosLoading"
                          style="width: 100%"
                          placeholder="Según establecimiento"
                        >
                          <el-option
                            v-for="office in consultorios"
                            :key="office.id"
                            :label="office.nombre"
                            :value="office.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="Profesional" prop="profesional_id">
                        <el-select
                          v-model="form.profesional_id"
                          filterable
                          remote
                          :remote-method="searchProfesionales"
                          :loading="profesionalesLoading"
                          style="width: 100%"
                          placeholder="Busque"
                        >
                          <el-option
                            v-for="prof in profesionales"
                            :key="prof.id"
                            :label="prof.nombre_completo"
                            :value="prof.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="Especialidad">
                        <el-select v-model="form.especialidad_codigo" clearable style="width: 100%">
                          <el-option
                            v-for="esp in especialidades"
                            :key="esp.codigo"
                            :label="esp.nombre"
                            :value="esp.codigo"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="Fecha de atención" prop="fecha_atencion">
                        <el-date-picker
                          v-model="form.fecha_atencion"
                          type="datetime"
                          value-format="YYYY-MM-DDTHH:mm:ss"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                  </template>
                </el-row>

                <el-collapse
                  v-if="!isAdmission"
                  v-model="expandedContextDetails"
                  class="clinical-details"
                >
                  <el-collapse-item name="context-details">
                    <template #title>
                      <span class="clinical-details__title"
                        >Datos complementarios de la atención</span
                      >
                    </template>
                    <el-row :gutter="16">
                      <el-col :span="8">
                        <el-form-item label="Fecha efectiva (opcional)">
                          <el-date-picker
                            v-model="form.fecha_atendido"
                            type="datetime"
                            value-format="YYYY-MM-DDTHH:mm:ss"
                            style="width: 100%"
                            clearable
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Hora inicio">
                          <el-time-picker
                            v-model="form.hora_inicio"
                            value-format="HH:mm:ss"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Hora fin">
                          <el-time-picker
                            v-model="form.hora_fin"
                            value-format="HH:mm:ss"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item :label="isAdmission ? 'Motivo de admisión' : 'Admisión'">
                          <el-input
                            v-model="form.admision"
                            :placeholder="
                              isAdmission ? 'Motivo o referencia de ingreso' : undefined
                            "
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </el-collapse-item>
                </el-collapse>
              </section>

              <section
                class="clinical-section clinical-section--measurements"
                aria-labelledby="measurements-title"
              >
                <div class="clinical-population-selector">
                  <el-form-item label="Grupo de atención">
                    <div class="care-group-selector" role="group" aria-label="Grupo de atención">
                      <el-checkbox
                        :model-value="selectedCareGroup === 'NINOS_ADOLESCENTES_ADULTOS_MAYORES'"
                        @change="selectCareGroup('NINOS_ADOLESCENTES_ADULTOS_MAYORES')"
                      >
                        Niños, adolescentes, adultos y adultos mayores
                      </el-checkbox>
                      <el-checkbox
                        :model-value="selectedCareGroup === 'GESTANTES'"
                        @change="selectCareGroup('GESTANTES')"
                      >
                        Gestantes
                      </el-checkbox>
                      <el-checkbox
                        :model-value="selectedCareGroup === 'PUERPERAS'"
                        @change="selectCareGroup('PUERPERAS')"
                      >
                        Puérperas
                      </el-checkbox>
                    </div>
                  </el-form-item>
                </div>
                <div class="clinical-section__heading">
                  <div>
                    <h3 id="measurements-title" class="clinical-section__title">
                      Mediciones clínicas
                    </h3>
                    <p class="clinical-section__description">
                      Registre medidas y signos vitales tomados durante la atención.
                    </p>
                  </div>
                </div>
                <div class="measurement-groups">
                  <div class="measurement-group">
                    <h4 class="measurement-group__title">Antropometría</h4>
                    <el-row :gutter="16">
                      <el-col :span="24">
                        <el-form-item class="measurement-field" label="Peso actual (kg)">
                          <el-input-number
                            v-model="form.peso_kg"
                            :min="0"
                            :precision="2"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="24">
                        <el-form-item class="measurement-field" label="Talla (cm)">
                          <el-input-number
                            v-model="form.talla_cm"
                            :min="0"
                            :precision="2"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="24">
                        <el-form-item class="measurement-field" label="Perímetro abdominal (cm)">
                          <el-input-number
                            v-model="form.perimetro_abdominal_cm"
                            :min="0"
                            :precision="2"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </div>
                  <div class="measurement-group">
                    <h4 class="measurement-group__title">Presión arterial y temperatura</h4>
                    <div
                      class="vital-signs"
                      role="group"
                      aria-label="Presión arterial y temperatura"
                    >
                      <div class="vital-signs__pressure">
                        <span class="vital-signs__label">Diast.</span>
                        <el-input-number
                          v-model="form.presion_diastolica"
                          class="vital-signs__input"
                          :min="1"
                          :controls="false"
                          aria-label="Presión diastólica"
                        />
                        <span class="vital-signs__separator" aria-hidden="true">/</span>
                        <span class="vital-signs__label">Sist.</span>
                        <el-input-number
                          v-model="form.presion_sistolica"
                          class="vital-signs__input"
                          :min="1"
                          :controls="false"
                          aria-label="Presión sistólica"
                        />
                      </div>
                      <div class="vital-signs__temperature">
                        <span class="vital-signs__label">Temp.</span>
                        <el-input-number
                          v-model="form.temperatura_c"
                          class="vital-signs__input"
                          :min="0"
                          :precision="1"
                          :controls="false"
                          aria-label="Temperatura en grados Celsius"
                        />
                        <span class="vital-signs__unit">°C</span>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              <section
                class="clinical-section clinical-section--nutrition"
                aria-labelledby="nutrition-title"
              >
                <div class="clinical-section__heading">
                  <h3 id="nutrition-title" class="clinical-section__title">
                    Valoración nutricional
                  </h3>
                </div>
                <div class="nutrition-age" aria-live="polite">
                  <span class="nutrition-age__label">Edad actual del paciente</span>
                  <strong class="nutrition-age__value">{{ nutritionalAge }}</strong>
                </div>
                <el-row :gutter="16" class="nutrition-fields">
                  <el-col :span="24">
                    <el-form-item class="nutrition-field" label="Diagnóstico P/E">
                      <el-input
                        v-model="form.valoracion.diagnostico_peso_edad"
                        maxlength="100"
                        clearable
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item class="nutrition-field" label="Diagnóstico T/E">
                      <el-input
                        v-model="form.valoracion.diagnostico_talla_edad"
                        maxlength="100"
                        clearable
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="24">
                    <el-form-item class="nutrition-field" label="Diagnóstico P/T">
                      <el-input
                        v-model="form.valoracion.diagnostico_peso_talla"
                        maxlength="100"
                        clearable
                      />
                    </el-form-item>
                  </el-col>
                </el-row>

                <AdmissionFinalActions
                  :saving="saving"
                  :primary-label="isAdmission ? 'Guardar atención' : 'Registrar atención'"
                  @submit="submit"
                  @exit="cancel"
                  @pending="notifyUnavailableAction"
                />
              </section>
            </el-form>
          </el-card>
        </div>

        <div v-if="showHistorial" class="admission-workbench__history">
          <AdmissionHistory
            :entries="historial"
            :loading="historialLoading"
            @refresh="loadHistorial"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import AdmissionHistory from '@/components/admission/AdmissionHistory.vue'
import AdmissionFinalActions from '@/components/admission/AdmissionFinalActions.vue'
import AdmissionPatientSummary from '@/components/admission/AdmissionPatientSummary.vue'
import {
  catalogos,
  type EstablishmentCatalogItem,
  type OfficeCatalogItem,
  type ProfessionalCatalogItem,
  type SpecialtyCatalogItem,
} from '@/services/catalogos'
import { pacientes, type Patient, type PatientUpdatePayload } from '@/services/pacientes'
import {
  atenciones,
  type Attention,
  type AttentionCreatePayload,
  type NutritionalSnapshotPayload,
} from '@/services/atenciones'
import { formatCalendarAge } from '@/utils/calendarAge'

const props = withDefaults(
  defineProps<{
    admission?: boolean
  }>(),
  { admission: false },
)

const route = useRoute()
const router = useRouter()
const isAdmission = computed(() => props.admission)
// `patientId` es el parámetro canónico de la ruta de admisión. Conservamos
// `pacienteId` para que los accesos creados antes de este cambio no se rompan.
const preselectedPatientId = patientIdFromQuery(route.query.patientId ?? route.query.pacienteId)

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)
const initialLoading = ref(false)
const expandedContextDetails = shallowRef<string[]>([])

const pacientesOptions = ref<Patient[]>([])
const pacientesLoading = ref(false)
const admissionPatient = ref<Patient | null>(null)
const patientContextSaving = ref(false)
const lockPatientSelection = ref(false)
const establecimientos = ref<EstablishmentCatalogItem[]>([])
const establecimientosLoading = ref(false)
const consultorios = ref<OfficeCatalogItem[]>([])
const consultoriosLoading = ref(false)
const profesionales = ref<ProfessionalCatalogItem[]>([])
const profesionalesLoading = ref(false)
const especialidades = ref<SpecialtyCatalogItem[]>([])
const historial = ref<Attention[]>([])
const historialLoading = ref(false)

const form = reactive({
  paciente_id: null as number | null,
  establecimiento_id: null as number | null,
  consultorio_id: null as number | null,
  profesional_id: null as number | null,
  especialidad_codigo: null as string | null,
  modalidad_atencion_codigo: 'AMBULATORIA' as 'AMBULATORIA' | 'EMERGENCIA',
  fecha_atencion: '',
  fecha_atendido: null as string | null,
  peso_kg: null as number | null,
  talla_cm: null as number | null,
  perimetro_abdominal_cm: null as number | null,
  temperatura_c: null as number | null,
  presion_sistolica: null as number | null,
  presion_diastolica: null as number | null,
  hora_inicio: null as string | null,
  hora_fin: null as string | null,
  admision: '',
  valoracion: {
    diagnostico_peso_edad: '',
    diagnostico_talla_edad: '',
    diagnostico_peso_talla: '',
  },
})

type AttentionMode = 'AMBULATORIA' | 'EMERGENCIA'
type CareGroup = 'NINOS_ADOLESCENTES_ADULTOS_MAYORES' | 'GESTANTES' | 'PUERPERAS'
type AdmissionPatientContextUpdate = Pick<
  PatientUpdatePayload,
  | 'sexo_codigo'
  | 'localidad'
  | 'direccion'
  | 'establecimiento_registro_id'
  | 'seguro_id'
>

/** Temporary UI-only selection; no clinical persistence is attached yet. */
const selectedCareGroup = ref<CareGroup>('NINOS_ADOLESCENTES_ADULTOS_MAYORES')

const rules: FormRules = {
  paciente_id: [{ required: true, message: 'Seleccione el paciente.', trigger: 'change' }],
  establecimiento_id: [
    { required: true, message: 'Seleccione el establecimiento.', trigger: 'change' },
  ],
  consultorio_id: [{ required: true, message: 'Seleccione el consultorio.', trigger: 'change' }],
  profesional_id: [{ required: true, message: 'Seleccione el profesional.', trigger: 'change' }],
  modalidad_atencion_codigo: [
    { required: true, message: 'Seleccione la modalidad.', trigger: 'change' },
  ],
  fecha_atencion: [{ required: true, message: 'Indique la fecha de atención.', trigger: 'change' }],
}

/** El paciente de la admisión nunca debe quedar fuera del formulario. */
const showForm = computed(() => !isAdmission.value || admissionPatient.value !== null)

/** El historial necesita un paciente conocido (admisión o selección manual). */
const historialPatientId = computed(() =>
  isAdmission.value ? (admissionPatient.value?.id ?? null) : form.paciente_id,
)
const showHistorial = computed(() => !initialLoading.value && historialPatientId.value !== null)

const nutritionalPatient = computed<Patient | null>(() =>
  isAdmission.value
    ? admissionPatient.value
    : pacientesOptions.value.find((patient) => patient.id === form.paciente_id) ?? null,
)
const nutritionalAge = computed(() => {
  const birthDate = nutritionalPatient.value?.fecha_nacimiento
  if (!birthDate) return '—'

  return formatCalendarAge(birthDate, form.fecha_atencion || new Date()) ?? '—'
})

/** ¿El profesional registró algún dato de la valoración nutricional? */
const hasNutritionalData = computed(() => {
  const valoracion = form.valoracion
  return Boolean(
    valoracion.diagnostico_peso_edad.trim() ||
      valoracion.diagnostico_talla_edad.trim() ||
      valoracion.diagnostico_peso_talla.trim(),
  )
})

function patientIdFromQuery(value: unknown): number | null {
  const rawValue = Array.isArray(value) ? value[0] : value
  if (typeof rawValue !== 'string') return null

  const patientId = Number(rawValue)
  return Number.isSafeInteger(patientId) && patientId > 0 ? patientId : null
}

function formatCurrentDateTime(): string {
  const current = new Date()
  const local = new Date(current.getTime() - current.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 19)
}

/**
 * Precarga los datos del paciente en el formulario: el paciente queda fijado y,
 * cuando tiene establecimiento de registro, la atención se abre en esa sede.
 * Si no lo tiene, el consultorio elegido determina la sede requerida por el
 * backend. Consultorio, especialidad y profesional siguen siendo elecciones
 * explícitas de la admisión.
 */
function applyPatientContext(patient: Patient): void {
  form.paciente_id = patient.id
  if (patient.establecimiento_registro_id) {
    form.establecimiento_id = patient.establecimiento_registro_id
  }
}

/** Persiste las correcciones mínimas hechas desde el resumen de admisión. */
async function updateAdmissionPatient(payload: AdmissionPatientContextUpdate): Promise<void> {
  const currentPatient = admissionPatient.value
  if (!currentPatient || patientContextSaving.value) return

  patientContextSaving.value = true
  try {
    const updatedPatient = await pacientes.update(currentPatient.id, payload)
    admissionPatient.value = updatedPatient
    pacientesOptions.value = [updatedPatient]

    // La sede clínica ya elegida no se altera. Si aún no se escogió un consultorio,
    // sí se toma la nueva sede de registro como contexto inicial de la atención.
    if ('establecimiento_registro_id' in payload && form.consultorio_id === null) {
      form.establecimiento_id = updatedPatient.establecimiento_registro_id
    }

    ElMessage.success('Datos del paciente actualizados.')
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : 'No se pudo actualizar el dato del paciente.',
    )
  } finally {
    patientContextSaving.value = false
  }
}

/** Convierte el bloque en el payload del backend; `null` si no se registró nada. */
function buildNutritionalPayload(): NutritionalSnapshotPayload | null {
  if (!hasNutritionalData.value) return null
  const valoracion = form.valoracion
  return {
    diagnostico_peso_edad: valoracion.diagnostico_peso_edad.trim() || null,
    diagnostico_talla_edad: valoracion.diagnostico_talla_edad.trim() || null,
    diagnostico_peso_talla: valoracion.diagnostico_peso_talla.trim() || null,
  }
}

function selectAttentionMode(mode: AttentionMode): void {
  form.modalidad_atencion_codigo = mode
}

function selectCareGroup(group: CareGroup): void {
  selectedCareGroup.value = group
}

function notifyUnavailableAction(action: string): void {
  ElMessage.info(`${action} estará disponible próximamente.`)
}

async function searchPacientes(query: string): Promise<void> {
  pacientesLoading.value = true
  try {
    const page = await pacientes.search({
      q: query && query.trim().length >= 2 ? query.trim() : undefined,
      limit: 10,
      offset: 0,
    })
    pacientesOptions.value = page.items
  } finally {
    pacientesLoading.value = false
  }
}

async function searchEstablecimientos(query: string): Promise<void> {
  establecimientosLoading.value = true
  try {
    const page = await catalogos.establecimientos(query || undefined, 25, 0)
    establecimientos.value = page.items
  } finally {
    establecimientosLoading.value = false
  }
}

async function searchProfesionales(query: string): Promise<void> {
  profesionalesLoading.value = true
  try {
    const page = await catalogos.profesionales(query || undefined, 25, 0)
    profesionales.value = page.items
  } finally {
    profesionalesLoading.value = false
  }
}

async function loadConsultorios(): Promise<void> {
  consultoriosLoading.value = true
  try {
    const page = await catalogos.consultorios(
      form.establecimiento_id ?? undefined,
      undefined,
      50,
      0,
    )
    consultorios.value = page.items
  } finally {
    consultoriosLoading.value = false
  }
}

async function loadHistorial(): Promise<void> {
  const patientId = historialPatientId.value
  if (!patientId) {
    historial.value = []
    return
  }
  historialLoading.value = true
  try {
    historial.value = await atenciones.listByPatient(patientId)
  } catch {
    // Sin permiso de lectura clínica (o sin atenciones) se deja la tabla vacía.
    historial.value = []
  } finally {
    historialLoading.value = false
  }
}

// Al cambiar el establecimiento, se recargan los consultorios de esa sede.
// Conservamos el seleccionado si justamente fue él quien definió la sede.
watch(
  () => form.establecimiento_id,
  (establishmentId) => {
    const selectedOffice = consultorios.value.find((office) => office.id === form.consultorio_id)
    if (!selectedOffice || selectedOffice.establecimiento_id !== establishmentId) {
      form.consultorio_id = null
    }
    void loadConsultorios()
  },
)

// En "Nueva atención" el paciente se elige a mano: su historial se recarga y,
// si aún no hay sede, se precarga la de registro del paciente.
watch(
  () => form.paciente_id,
  (id) => {
    const selected = pacientesOptions.value.find((item) => item.id === id)
    if (selected && !isAdmission.value && !form.establecimiento_id) {
      applyPatientContext(selected)
    }
    void loadHistorial()
  },
)

// El consultorio define la sede y la especialidad cuando las trae asignadas.
watch(
  () => form.consultorio_id,
  (id) => {
    if (id === null) return
    const office = consultorios.value.find((item) => item.id === id)
    if (office && form.establecimiento_id !== office.establecimiento_id) {
      form.establecimiento_id = office.establecimiento_id
    }
    if (office?.especialidad_codigo) {
      form.especialidad_codigo = office.especialidad_codigo
    }
  },
)

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const valoracion = buildNutritionalPayload()
  saving.value = true
  errorMessage.value = null
  try {
    const payload: AttentionCreatePayload = {
      paciente_id: form.paciente_id!,
      establecimiento_id: form.establecimiento_id!,
      consultorio_id: form.consultorio_id!,
      profesional_id: form.profesional_id!,
      especialidad_codigo: form.especialidad_codigo,
      modalidad_atencion_codigo: form.modalidad_atencion_codigo,
      fecha_atencion: form.fecha_atencion,
      fecha_atendido: form.fecha_atendido,
      peso_kg: form.peso_kg,
      talla_cm: form.talla_cm,
      perimetro_abdominal_cm: form.perimetro_abdominal_cm,
      temperatura_c: form.temperatura_c,
      presion_sistolica: form.presion_sistolica,
      presion_diastolica: form.presion_diastolica,
      hora_inicio: form.hora_inicio,
      hora_fin: form.hora_fin,
      admision: form.admision || null,
      valoracion_nutricional: valoracion,
    }
    const created = await atenciones.create(payload)
    router.push({ name: 'atencion-detalle', params: { id: created.id } })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo registrar la atención.'
  } finally {
    saving.value = false
  }
}

function cancel(): void {
  if (isAdmission.value && admissionPatient.value) {
    router.push({ name: 'paciente-detalle', params: { id: admissionPatient.value.id } })
    return
  }
  router.back()
}

onMounted(async () => {
  initialLoading.value = true
  errorMessage.value = null
  try {
    if (isAdmission.value && preselectedPatientId === null) {
      errorMessage.value =
        'Seleccione un paciente desde la Base de datos antes de iniciar una admisión.'
      return
    }

    const [especialidadesResult, estResult, profesionalesResult, patient] = await Promise.all([
      catalogos.especialidades(),
      catalogos.establecimientos(undefined, 25, 0),
      catalogos.profesionales(undefined, 50, 0),
      preselectedPatientId === null ? Promise.resolve(null) : pacientes.get(preselectedPatientId),
    ])
    especialidades.value = especialidadesResult
    establecimientos.value = estResult.items
    profesionales.value = profesionalesResult.items

    if (patient) {
      pacientesOptions.value = [patient]
      lockPatientSelection.value = true
      applyPatientContext(patient)
      if (isAdmission.value) {
        admissionPatient.value = patient
        form.fecha_atencion = formatCurrentDateTime()
        if (!form.establecimiento_id) await loadConsultorios()
      }
    }
  } catch (error) {
    form.paciente_id = null
    lockPatientSelection.value = false
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo preparar la admisión del paciente.'
  } finally {
    initialLoading.value = false
    void loadHistorial()
  }
})
</script>

<style scoped>
.admission-page {
  --admission-space-tight: 6px;
  --admission-space: 12px;
  --admission-space-wide: 16px;
}

.form-alert {
  margin-bottom: var(--admission-space);
}

.admission-workbench {
  display: grid;
  grid-template-areas:
    'patient content'
    'history history';
  grid-template-columns: minmax(224px, 260px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.admission-workbench--standalone {
  grid-template-areas:
    'content'
    'history';
  grid-template-columns: minmax(0, 1fr);
}

.admission-workbench__patient {
  grid-area: patient;
  display: flex;
  min-width: 0;
}

.admission-workbench__patient :deep(.patient-context) {
  flex: 1 1 auto;
}

.admission-workbench__content {
  grid-area: content;
  display: grid;
  min-width: 0;
  gap: 12px;
}

.admission-workbench__history {
  grid-area: history;
  min-width: 0;
}

.encounter-card {
  min-width: 0;
  border-color: var(--el-border-color-lighter);
  border-radius: 12px;
  container-type: inline-size;
}

.encounter-card :deep(.el-card__body) {
  padding: 14px;
}

.encounter-form {
  display: grid;
  grid-template-areas:
    'context nutrition'
    'measurements nutrition';
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: var(--admission-space-wide) 16px;
}

.clinical-section {
  min-width: 0;
}

.clinical-section--context {
  grid-area: context;
}

.clinical-section--measurements {
  grid-area: measurements;
  padding-top: var(--admission-space-wide);
  border-top: 1px solid var(--el-border-color-lighter);
}

.clinical-section--nutrition {
  grid-area: nutrition;
  display: flex;
  flex-direction: column;
  padding-left: 16px;
  border-left: 1px solid var(--el-border-color-lighter);
}

.clinical-section__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--admission-space);
  margin-bottom: 10px;
}

.clinical-section__title,
.measurement-group__title {
  margin: 0;
  color: var(--el-text-color-primary);
}

.clinical-section__title {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.clinical-section__description {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.35;
}

.measurement-groups {
  display: grid;
  gap: var(--admission-space);
}

.measurement-group + .measurement-group {
  padding-top: var(--admission-space);
  border-top: 1px solid var(--el-border-color-lighter);
}

.measurement-group__title {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.35;
}

.measurement-group__description {
  margin: 2px 0 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.nutrition-age {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--admission-space);
  margin-bottom: 10px;
  padding: 8px 10px;
  color: var(--el-color-primary-dark-2);
  background-color: var(--el-color-primary-light-9);
  border-top: 1px solid var(--el-color-primary-light-7);
  border-bottom: 1px solid var(--el-color-primary-light-7);
}

.nutrition-age__label {
  color: inherit;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.35;
}

.nutrition-age__value {
  min-width: 0;
  color: var(--el-text-color-primary);
  font-size: clamp(15px, 1.2vw, 18px);
  font-weight: 700;
  line-height: 1.3;
  overflow-wrap: anywhere;
  text-align: end;
}

.nutrition-fields {
  display: grid;
  gap: 2px;
}

.vital-signs,
.vital-signs__pressure,
.vital-signs__temperature {
  display: flex;
  align-items: center;
}

.vital-signs {
  flex-wrap: nowrap;
  gap: 8px;
  margin-top: 4px;
}

.vital-signs__pressure,
.vital-signs__temperature {
  flex: 0 0 auto;
  gap: 4px;
}

.vital-signs__label,
.vital-signs__unit,
.vital-signs__separator {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}

.vital-signs__separator {
  color: var(--el-text-color-regular);
}

.vital-signs :deep(.vital-signs__input) {
  width: clamp(46px, 6vw, 64px);
}

.clinical-details {
  margin-top: 4px;
  border-top: 1px solid var(--el-border-color-lighter);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.clinical-details :deep(.el-collapse-item__header) {
  height: 34px;
  color: var(--el-text-color-secondary);
  background-color: transparent;
  border-bottom: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
}

.clinical-details :deep(.el-collapse-item__wrap) {
  background-color: transparent;
  border-bottom: 0;
}

.clinical-details :deep(.el-collapse-item__content) {
  padding-bottom: 0;
}

.clinical-details__title {
  line-height: 1.35;
}

:deep(.encounter-form .el-form-item) {
  margin-bottom: 8px;
}

:deep(.encounter-form .el-form-item__label) {
  height: auto;
  padding: 0 0 3px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.35;
}

:deep(.admission-context-field) {
  display: flex;
  align-items: center;
  gap: var(--admission-space);
}

:deep(.admission-context-field .el-form-item__label) {
  flex: 0 0 116px;
  justify-content: flex-start;
  padding: 0;
}

:deep(.admission-context-field .el-form-item__content) {
  flex: 1 1 auto;
  min-width: 0;
  margin-left: 0 !important;
}

:deep(.measurement-field),
:deep(.nutrition-field) {
  display: flex;
  align-items: center;
  gap: var(--admission-space);
}

.nutrition-fields :deep(.nutrition-field) {
  margin-bottom: 0;
  padding: 6px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.nutrition-fields :deep(.el-col:last-child .nutrition-field) {
  border-bottom: 0;
}

:deep(.measurement-field .el-form-item__label),
:deep(.nutrition-field .el-form-item__label) {
  flex: 0 1 170px;
  min-width: 124px;
  justify-content: flex-start;
  padding: 0;
}

:deep(.measurement-field .el-form-item__content),
:deep(.nutrition-field .el-form-item__content) {
  flex: 1 1 auto;
  min-width: 0;
  margin-left: 0 !important;
}

:deep(.encounter-form .el-radio-group),
:deep(.encounter-form .el-checkbox-group),
.attention-mode-selector,
.care-group-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
}

:deep(.encounter-form .el-radio),
:deep(.encounter-form .el-checkbox) {
  margin-right: 0;
}

@container (max-width: 700px) {
  .encounter-form {
    grid-template-areas:
      'context'
      'measurements'
      'nutrition'
      'actions';
    grid-template-columns: minmax(0, 1fr);
  }

  .clinical-section--nutrition {
    padding-top: var(--admission-space-wide);
    padding-left: 0;
    border-top: 1px solid var(--el-border-color-lighter);
    border-left: 0;
  }
}

@media (max-width: 900px) {
  .admission-workbench {
    grid-template-areas:
      'patient'
      'content'
      'history';
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
  }

  .admission-workbench--standalone {
    grid-template-areas:
      'content'
      'history';
  }
}

@media (max-width: 680px) {
  .nutrition-age {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .nutrition-age__value {
    text-align: start;
  }

  :deep(.admission-context-field) {
    flex-direction: column;
    align-items: stretch;
    gap: 0;
  }

  :deep(.admission-context-field .el-form-item__label) {
    flex-basis: auto;
    padding-bottom: 5px;
  }

  :deep(.measurement-field),
  :deep(.nutrition-field) {
    flex-direction: column;
    align-items: stretch;
    gap: 0;
  }

  :deep(.measurement-field .el-form-item__label),
  :deep(.nutrition-field .el-form-item__label) {
    flex-basis: auto;
    min-width: 0;
    padding-bottom: 5px;
  }

  .encounter-card :deep(.el-card__body) {
    padding: var(--admission-space);
  }

  .clinical-section--nutrition :deep(.el-col),
  .clinical-section :deep(.el-col) {
    flex: 0 0 100%;
    max-width: 100%;
  }
}
</style>
