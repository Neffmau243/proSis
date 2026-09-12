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
          <AdmissionPatientSummary :patient="admissionPatient" />
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
                <div class="clinical-section__heading">
                  <div>
                    <h3 id="encounter-context-title" class="clinical-section__title">
                      Atención y consultorio
                    </h3>
                    <p class="clinical-section__description">
                      Defina dónde, cuándo y con quién se registra la atención.
                    </p>
                  </div>
                </div>
                <el-row :gutter="16">
                  <el-col v-if="!isAdmission" :span="8">
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
                    <el-form-item label="Tipo de atención" prop="modalidad_atencion_codigo">
                      <el-radio-group v-model="form.modalidad_atencion_codigo">
                        <el-radio value="AMBULATORIA">Ambulatoria</el-radio>
                        <el-radio value="EMERGENCIA">Emergencia</el-radio>
                      </el-radio-group>
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
                </el-row>

                <el-collapse v-model="expandedContextDetails" class="clinical-details">
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
                      <el-col :span="8">
                        <el-form-item label="Peso actual (kg)">
                          <el-input-number
                            v-model="form.peso_kg"
                            :min="0"
                            :precision="2"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Talla (cm)">
                          <el-input-number
                            v-model="form.talla_cm"
                            :min="0"
                            :precision="2"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Perímetro abdominal (cm)">
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
                    <el-row :gutter="16">
                      <el-col :span="8">
                        <el-form-item label="Presión sistólica">
                          <el-input-number
                            v-model="form.presion_sistolica"
                            :min="1"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Presión diastólica">
                          <el-input-number
                            v-model="form.presion_diastolica"
                            :min="1"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Temperatura (°C)">
                          <el-input-number
                            v-model="form.temperatura_c"
                            :min="0"
                            :precision="1"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </div>
                  <div class="measurement-group">
                    <h4 class="measurement-group__title">
                      Indicadores nutricionales (P/E · T/E · P/T)
                    </h4>
                    <el-row :gutter="16">
                      <el-col :span="8">
                        <el-form-item label="P/E">
                          <el-input v-model="form.pe" />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="T/E">
                          <el-input v-model="form.te" />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="P/T">
                          <el-input v-model="form.pt" />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </div>
                </div>
              </section>

              <section
                class="clinical-section clinical-section--nutrition"
                aria-labelledby="nutrition-title"
              >
                <div class="clinical-section__heading">
                  <div>
                    <h3 id="nutrition-title" class="clinical-section__title">
                      Valoración nutricional
                    </h3>
                    <p class="clinical-section__description">
                      Opcional. Complete solo los indicadores evaluados.
                    </p>
                  </div>
                  <el-button
                    v-if="hasNutritionalData"
                    size="small"
                    text
                    type="danger"
                    @click="clearNutrition"
                  >
                    Limpiar
                  </el-button>
                </div>
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="Tipo de evaluación">
                      <el-select
                        v-model="form.valoracion.tipo"
                        filterable
                        allow-create
                        default-first-option
                        clearable
                        :value-on-clear="''"
                        placeholder="Ej. INGRESO, CONTROL, ALTA"
                        style="width: 100%"
                      >
                        <el-option
                          v-for="tipo in tiposValoracion"
                          :key="tipo"
                          :label="tipo"
                          :value="tipo"
                        />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="IMC">
                      <el-input-number
                        v-model="form.valoracion.imc"
                        :precision="3"
                        :controls="false"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="Hemoglobina (g/dL)">
                      <el-input-number
                        v-model="form.valoracion.hemoglobina"
                        :min="0"
                        :precision="2"
                        :controls="false"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="P/T — puntaje Z (whz)">
                      <el-input-number
                        v-model="form.valoracion.whz"
                        :precision="3"
                        :controls="false"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="T/E — puntaje Z (haz)">
                      <el-input-number
                        v-model="form.valoracion.haz"
                        :precision="3"
                        :controls="false"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="P/E — puntaje Z (waz)">
                      <el-input-number
                        v-model="form.valoracion.waz"
                        :precision="3"
                        :controls="false"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-collapse v-model="expandedNutritionDetails" class="clinical-details">
                  <el-collapse-item name="nutrition-details">
                    <template #title>
                      <span class="clinical-details__title"
                        >Indicadores y diagnóstico complementarios</span
                      >
                    </template>
                    <el-row :gutter="16">
                      <el-col :span="8">
                        <el-form-item label="Fecha de hemoglobina">
                          <el-date-picker
                            v-model="form.valoracion.fecha_hemoglobina"
                            type="date"
                            value-format="YYYY-MM-DD"
                            style="width: 100%"
                            clearable
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Edad gestacional (semanas)">
                          <el-input-number
                            v-model="form.valoracion.edad_gestacional_semanas"
                            :min="0"
                            :max="60"
                            :controls="false"
                            style="width: 100%"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Diagnóstico P/T">
                          <el-input
                            v-model="form.valoracion.diagnostico_peso_talla"
                            maxlength="100"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Diagnóstico T/E">
                          <el-input
                            v-model="form.valoracion.diagnostico_talla_edad"
                            maxlength="100"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="Diagnóstico P/E">
                          <el-input
                            v-model="form.valoracion.diagnostico_peso_edad"
                            maxlength="100"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="24">
                        <el-form-item label="Diagnóstico nutricional">
                          <el-input
                            v-model="form.valoracion.diagnostico"
                            type="textarea"
                            :rows="2"
                            maxlength="500"
                            show-word-limit
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </el-collapse-item>
                </el-collapse>
              </section>

              <footer class="form-actions">
                <div>
                  <h3 class="form-actions__title">Finalizar admisión</h3>
                  <p class="form-actions__description">
                    La atención se agregará al historial del paciente.
                  </p>
                </div>
                <div class="form-actions__buttons">
                  <el-button type="primary" :loading="saving" @click="submit">
                    {{ isAdmission ? 'Guardar atención' : 'Registrar atención' }}
                  </el-button>
                  <el-button @click="cancel">Cancelar</el-button>
                </div>
              </footer>
            </el-form>
          </el-card>

          <AdmissionHistory
            v-if="showHistorial"
            :entries="historial"
            :loading="historialLoading"
            :consultorio-label="consultorioLabel"
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
import type { FormInstance, FormRules } from 'element-plus'

import AdmissionHistory from '@/components/admission/AdmissionHistory.vue'
import AdmissionPatientSummary from '@/components/admission/AdmissionPatientSummary.vue'
import {
  catalogos,
  type EstablishmentCatalogItem,
  type OfficeCatalogItem,
  type ProfessionalCatalogItem,
  type SpecialtyCatalogItem,
} from '@/services/catalogos'
import { pacientes, type Patient } from '@/services/pacientes'
import {
  atenciones,
  type Attention,
  type AttentionCreatePayload,
  type NutritionalSnapshotPayload,
} from '@/services/atenciones'

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

/** Opciones sugeridas; el select permite escribir valores propios de la IPRESS. */
const tiposValoracion = ['INGRESO', 'CONTROL', 'ALTA']

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)
const initialLoading = ref(false)
const expandedContextDetails = shallowRef<string[]>([])
const expandedNutritionDetails = shallowRef<string[]>([])

const pacientesOptions = ref<Patient[]>([])
const pacientesLoading = ref(false)
const admissionPatient = ref<Patient | null>(null)
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
  pe: '',
  te: '',
  pt: '',
  admision: '',
  valoracion: {
    tipo: '',
    imc: null as number | null,
    whz: null as number | null,
    haz: null as number | null,
    waz: null as number | null,
    diagnostico_peso_edad: '',
    diagnostico_talla_edad: '',
    diagnostico_peso_talla: '',
    hemoglobina: null as number | null,
    fecha_hemoglobina: null as string | null,
    edad_gestacional_semanas: null as number | null,
    diagnostico: '',
  },
})

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

/** ¿El profesional registró algún dato de la valoración nutricional? */
const hasNutritionalData = computed(() => {
  const valoracion = form.valoracion
  return Boolean(
    valoracion.tipo.trim() ||
    valoracion.imc !== null ||
    valoracion.whz !== null ||
    valoracion.haz !== null ||
    valoracion.waz !== null ||
    valoracion.hemoglobina !== null ||
    valoracion.fecha_hemoglobina ||
    valoracion.edad_gestacional_semanas !== null ||
    valoracion.diagnostico_peso_edad.trim() ||
    valoracion.diagnostico_talla_edad.trim() ||
    valoracion.diagnostico_peso_talla.trim() ||
    valoracion.diagnostico.trim(),
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

function consultorioLabel(id: number): string {
  return consultorios.value.find((office) => office.id === id)?.nombre ?? `#${id}`
}

/**
 * Precarga los datos del paciente en el formulario: el paciente queda fijado y,
 * cuando tiene establecimiento de registro, la atención se abre en esa sede.
 * Consultorio, profesional y los signos vitales se dejan libres para
 * elegirlos/registrarlos en cada atención.
 */
function applyPatientContext(patient: Patient): void {
  form.paciente_id = patient.id
  if (patient.establecimiento_registro_id) {
    form.establecimiento_id = patient.establecimiento_registro_id
  }
}

function clearNutrition(): void {
  Object.assign(form.valoracion, {
    tipo: '',
    imc: null,
    whz: null,
    haz: null,
    waz: null,
    diagnostico_peso_edad: '',
    diagnostico_talla_edad: '',
    diagnostico_peso_talla: '',
    hemoglobina: null,
    fecha_hemoglobina: null,
    edad_gestacional_semanas: null,
    diagnostico: '',
  })
}

/** Convierte el bloque en el payload del backend; `null` si no se registró nada. */
function buildNutritionalPayload(): NutritionalSnapshotPayload | null {
  if (!hasNutritionalData.value) return null
  const valoracion = form.valoracion
  return {
    tipo: valoracion.tipo.trim(),
    imc: valoracion.imc,
    whz: valoracion.whz,
    haz: valoracion.haz,
    waz: valoracion.waz,
    hemoglobina: valoracion.hemoglobina,
    fecha_hemoglobina: valoracion.fecha_hemoglobina || null,
    edad_gestacional_semanas: valoracion.edad_gestacional_semanas,
    diagnostico_peso_edad: valoracion.diagnostico_peso_edad.trim() || null,
    diagnostico_talla_edad: valoracion.diagnostico_talla_edad.trim() || null,
    diagnostico_peso_talla: valoracion.diagnostico_peso_talla.trim() || null,
    diagnostico: valoracion.diagnostico.trim() || null,
  }
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
  if (!form.establecimiento_id) {
    consultorios.value = []
    form.consultorio_id = null
    return
  }
  consultoriosLoading.value = true
  try {
    const page = await catalogos.consultorios(form.establecimiento_id, undefined, 50, 0)
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
watch(
  () => form.establecimiento_id,
  () => {
    form.consultorio_id = null
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

// El consultorio define la especialidad de la atención cuando la trae asignada.
watch(
  () => form.consultorio_id,
  (id) => {
    if (id === null) return
    const office = consultorios.value.find((item) => item.id === id)
    if (office?.especialidad_codigo) {
      form.especialidad_codigo = office.especialidad_codigo
    }
  },
)

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const valoracion = buildNutritionalPayload()
  if (valoracion && !valoracion.tipo) {
    errorMessage.value =
      'Indique el tipo de la valoración nutricional (ej. INGRESO, CONTROL, ALTA).'
    return
  }

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
      pe: form.pe || null,
      te: form.te || null,
      pt: form.pt || null,
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

    const [especialidadesResult, estResult, patient] = await Promise.all([
      catalogos.especialidades(),
      catalogos.establecimientos(undefined, 25, 0),
      preselectedPatientId === null ? Promise.resolve(null) : pacientes.get(preselectedPatientId),
    ])
    especialidades.value = especialidadesResult
    establecimientos.value = estResult.items

    if (patient) {
      pacientesOptions.value = [patient]
      lockPatientSelection.value = true
      applyPatientContext(patient)
      if (isAdmission.value) {
        admissionPatient.value = patient
        form.fecha_atencion = formatCurrentDateTime()
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
  --admission-space-tight: 8px;
  --admission-space: 16px;
  --admission-space-wide: 24px;
}

.form-alert {
  margin-bottom: var(--admission-space);
}

.admission-workbench {
  display: grid;
  grid-template-columns: minmax(236px, 280px) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.admission-workbench--standalone {
  grid-template-columns: minmax(0, 1fr);
}

.admission-workbench__patient {
  min-width: 0;
}

.admission-workbench__content {
  display: grid;
  min-width: 0;
  gap: 20px;
}

.encounter-card {
  min-width: 0;
  border-color: var(--el-border-color-lighter);
  border-radius: 12px;
  container-type: inline-size;
}

.encounter-card :deep(.el-card__body) {
  padding: 20px;
}

.encounter-form {
  display: grid;
  grid-template-areas:
    'context nutrition'
    'measurements nutrition'
    'actions actions';
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: var(--admission-space-wide) 20px;
}

.clinical-section {
  min-width: 0;
}

.clinical-section--context {
  grid-area: context;
}

.clinical-section--measurements {
  grid-area: measurements;
}

.clinical-section--nutrition {
  grid-area: nutrition;
  padding-left: 20px;
  border-left: 1px solid var(--el-border-color-lighter);
}

.clinical-section__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--admission-space);
  margin-bottom: var(--admission-space);
}

.clinical-section__title,
.form-actions__title,
.measurement-group__title {
  margin: 0;
  color: var(--el-text-color-primary);
}

.clinical-section__title,
.form-actions__title {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
}

.clinical-section__description,
.form-actions__description {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.45;
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

.clinical-section--nutrition :deep(.el-col:not(.el-col-24)) {
  flex: 0 0 50%;
  max-width: 50%;
}

.clinical-section--nutrition :deep(.el-col-24) {
  flex: 0 0 100%;
  max-width: 100%;
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
  margin-bottom: 12px;
}

:deep(.encounter-form .el-form-item__label) {
  height: auto;
  padding: 0 0 5px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
}

:deep(.encounter-form .el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}

:deep(.encounter-form .el-radio) {
  margin-right: 0;
}

.form-actions {
  grid-area: actions;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--admission-space);
  padding-top: var(--admission-space-wide);
  border-top: 1px solid var(--el-border-color-lighter);
}

.form-actions__buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--admission-space-tight);
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
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 680px) {
  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .form-actions__buttons {
    justify-content: stretch;
  }

  .form-actions__buttons :deep(.el-button) {
    flex: 1 1 auto;
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
