<template>
  <div>
    <div class="page-header">
      <h2>Nueva atención</h2>
      <el-button @click="router.back()">Volver</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="200px">
        <h3>Contexto de la atención</h3>
        <el-row :gutter="16">
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
                :disabled="preselectedPatientId !== null"
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
            <el-form-item label="Modalidad" prop="modalidad_atencion_codigo">
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
            <el-form-item label="Admisión">
              <el-input v-model="form.admision" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />
        <h3>Signos vitales</h3>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="Peso (kg)">
              <el-input-number v-model="form.peso_kg" :min="0" :precision="2" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Talla (cm)">
              <el-input-number v-model="form.talla_cm" :min="0" :precision="2" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Perímetro abdominal (cm)">
              <el-input-number v-model="form.perimetro_abdominal_cm" :min="0" :precision="2" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Temperatura (°C)">
              <el-input-number v-model="form.temperatura_c" :min="0" :precision="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Presión sistólica">
              <el-input-number v-model="form.presion_sistolica" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Presión diastólica">
              <el-input-number v-model="form.presion_diastolica" :min="1" :controls="false" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Hora inicio">
              <el-time-picker v-model="form.hora_inicio" value-format="HH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="Hora fin">
              <el-time-picker v-model="form.hora_fin" value-format="HH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="P/E">
              <el-input v-model="form.pe" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="T/E">
              <el-input v-model="form.te" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="P/T">
              <el-input v-model="form.pt" />
            </el-form-item>
          </el-col>
          <el-col :span="18">
            <el-form-item label="Observaciones">
              <el-input v-model="form.observaciones" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />
        <div class="section-head">
          <h3>Prestaciones</h3>
          <el-button size="small" @click="addPrestacion">Agregar prestación</el-button>
        </div>
        <div v-for="(item, index) in form.prestaciones" :key="index" class="repeat-block">
          <el-row :gutter="12">
            <el-col :span="14">
              <el-select
                v-model="item.prestacion_codigo"
                filterable
                remote
                :remote-method="(q: string) => searchPrestaciones(q, index)"
                :loading="prestacionesLoading[index]"
                style="width: 100%"
                placeholder="Busque la prestación"
              >
                <el-option
                  v-for="prestacion in prestaciones[index]"
                  :key="prestacion.codigo"
                  :label="`${prestacion.codigo} — ${prestacion.descripcion}`"
                  :value="prestacion.codigo"
                />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input-number v-model="item.cantidad" :min="0.01" :precision="2" :controls="false" style="width: 100%" placeholder="Cantidad" />
            </el-col>
            <el-col :span="2">
              <el-button link type="danger" @click="form.prestaciones.splice(index, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
        </div>

        <el-divider />
        <div class="section-head">
          <h3>Diagnósticos (CIE-10)</h3>
          <el-button size="small" @click="addDiagnostico">Agregar diagnóstico</el-button>
        </div>
        <div v-for="(item, index) in form.diagnosticos" :key="index" class="repeat-block">
          <el-row :gutter="12">
            <el-col :span="10">
              <el-select
                v-model="item.cie10_codigo"
                filterable
                remote
                :remote-method="(q: string) => searchCie10(q, index)"
                :loading="cie10Loading[index]"
                style="width: 100%"
                placeholder="Busque el código CIE-10"
              >
                <el-option
                  v-for="codigo in cie10[index]"
                  :key="codigo.codigo"
                  :label="`${codigo.codigo} — ${codigo.descripcion}`"
                  :value="codigo.codigo"
                />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input v-model="item.tipo_diagnostico" placeholder="Tipo (ej. PRINCIPAL)" />
            </el-col>
            <el-col :span="6">
              <el-input v-model="item.observacion" placeholder="Observación" />
            </el-col>
            <el-col :span="2">
              <el-button link type="danger" @click="form.diagnosticos.splice(index, 1)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
        </div>

        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit">Registrar atención</el-button>
          <el-button @click="router.back()">Cancelar</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import {
  catalogos,
  type Cie10CatalogItem,
  type EstablishmentCatalogItem,
  type OfficeCatalogItem,
  type ProfessionalCatalogItem,
  type ServiceCatalogItem,
  type SpecialtyCatalogItem,
} from '@/services/catalogos'
import { pacientes, type Patient } from '@/services/pacientes'
import { atenciones } from '@/services/atenciones'

const route = useRoute()
const router = useRouter()
const preselectedPatientId = route.query.pacienteId ? Number(route.query.pacienteId) : null

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const pacientesOptions = ref<Patient[]>([])
const pacientesLoading = ref(false)
const establecimientos = ref<EstablishmentCatalogItem[]>([])
const establecimientosLoading = ref(false)
const consultorios = ref<OfficeCatalogItem[]>([])
const consultoriosLoading = ref(false)
const profesionales = ref<ProfessionalCatalogItem[]>([])
const profesionalesLoading = ref(false)
const especialidades = ref<SpecialtyCatalogItem[]>([])
const prestaciones = ref<ServiceCatalogItem[][]>([])
const prestacionesLoading = ref<boolean[]>([])
const cie10 = ref<Cie10CatalogItem[][]>([])
const cie10Loading = ref<boolean[]>([])

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
  observaciones: '',
  prestaciones: [] as { prestacion_codigo: string | null; cantidad: number | null }[],
  diagnosticos: [] as { cie10_codigo: string | null; tipo_diagnostico: string; observacion: string }[],
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
  fecha_atencion: [
    { required: true, message: 'Indique la fecha de atención.', trigger: 'change' },
  ],
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

async function searchPrestaciones(query: string, index: number): Promise<void> {
  prestacionesLoading.value[index] = true
  try {
    const page = await catalogos.prestaciones(query || undefined, 25, 0)
    prestaciones.value[index] = page.items
  } finally {
    prestacionesLoading.value[index] = false
  }
}

async function searchCie10(query: string, index: number): Promise<void> {
  cie10Loading.value[index] = true
  try {
    const page = await catalogos.cie10(query || undefined, 25, 0)
    cie10.value[index] = page.items
  } finally {
    cie10Loading.value[index] = false
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

// Al cambiar el establecimiento, se recargan los consultorios de esa sede.
watch(() => form.establecimiento_id, () => loadConsultorios())

function addPrestacion(): void {
  form.prestaciones.push({ prestacion_codigo: null, cantidad: 1 })
  prestaciones.value.push([])
  prestacionesLoading.value.push(false)
}

function addDiagnostico(): void {
  form.diagnosticos.push({ cie10_codigo: null, tipo_diagnostico: '', observacion: '' })
  cie10.value.push([])
  cie10Loading.value.push(false)
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    const created = await atenciones.create({
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
      observaciones: form.observaciones || null,
      prestaciones: form.prestaciones
        .filter((item) => item.prestacion_codigo)
        .map((item) => ({ prestacion_codigo: item.prestacion_codigo!, cantidad: String(item.cantidad ?? 1) })),
      diagnosticos: form.diagnosticos
        .filter((item) => item.cie10_codigo)
        .map((item) => ({
          cie10_codigo: item.cie10_codigo!,
          tipo_diagnostico: item.tipo_diagnostico || null,
          observacion: item.observacion || null,
        })),
    })
    router.push({ name: 'atencion-detalle', params: { id: created.id } })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo registrar la atención.'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const [especialidadesResult, estResult] = await Promise.all([
    catalogos.especialidades(),
    catalogos.establecimientos(undefined, 25, 0),
  ])
  especialidades.value = especialidadesResult
  establecimientos.value = estResult.items

  if (preselectedPatientId !== null) {
    form.paciente_id = preselectedPatientId
    try {
      const patient = await pacientes.get(preselectedPatientId)
      pacientesOptions.value = [patient]
    } catch {
      // El paciente no existe o está fuera de ámbito; el selector queda libre.
    }
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.form-alert {
  margin-bottom: 16px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-head h3 {
  margin: 0;
}

.repeat-block {
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 8px;
}
</style>