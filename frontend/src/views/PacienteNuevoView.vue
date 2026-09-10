<template>
  <div>
    <div class="page-header">
      <h2>Nuevo paciente</h2>
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
      <el-form ref="formRef" :model="form" :rules="rules" label-width="180px">
        <h3>Identidad</h3>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Tipo de documento" prop="tipo_documento_codigo">
              <el-select v-model="form.tipo_documento_codigo" style="width: 100%">
                <el-option
                  v-for="tipo in tiposDocumento"
                  :key="tipo.codigo"
                  :label="tipo.nombre"
                  :value="tipo.codigo"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="N° documento" prop="numero_documento">
              <el-input v-model="form.numero_documento" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Historia clínica">
              <el-input v-model="form.historia_clinica" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Apellido paterno">
              <el-input v-model="form.apellido_paterno" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Apellido materno">
              <el-input v-model="form.apellido_materno" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Primer nombre" prop="primer_nombre">
              <el-input v-model="form.primer_nombre" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Otros nombres">
              <el-input v-model="form.otros_nombres" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Fecha de nacimiento" prop="fecha_nacimiento">
              <el-date-picker
                v-model="form.fecha_nacimiento"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                :disabled-date="(d: Date) => d.getTime() > Date.now()"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Sexo">
              <el-select v-model="form.sexo_codigo" clearable style="width: 100%">
                <el-option
                  v-for="sexo in sexos"
                  :key="sexo.codigo"
                  :label="sexo.nombre"
                  :value="sexo.codigo"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Fecha de inscripción">
              <el-date-picker
                v-model="form.fecha_inscripcion"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Seguro">
              <el-select v-model="form.seguro_id" clearable filterable style="width: 100%">
                <el-option
                  v-for="seguro in seguros"
                  :key="seguro.id"
                  :label="seguro.nombre"
                  :value="seguro.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Establecimiento de registro">
              <el-select
                v-model="form.establecimiento_registro_id"
                clearable
                filterable
                remote
                :remote-method="searchEstablecimientos"
                :loading="establecimientosLoading"
                style="width: 100%"
                placeholder="Busque por nombre"
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
            <el-form-item label="Ubigeo de residencia">
              <el-select
                v-model="form.ubigeo_residencia_codigo"
                clearable
                filterable
                remote
                :remote-method="searchUbigeos"
                :loading="ubigeosLoading"
                style="width: 100%"
                placeholder="Busque por departamento"
              >
                <el-option
                  v-for="ubigeo in ubigeos"
                  :key="ubigeo.codigo"
                  :label="`${ubigeo.departamento} / ${ubigeo.provincia} / ${ubigeo.distrito}`"
                  :value="ubigeo.codigo"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Localidad">
              <el-input v-model="form.localidad" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Dirección">
              <el-input v-model="form.direccion" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Teléfono principal">
              <el-input v-model="form.telefono_principal" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Condición">
              <el-input v-model="form.condicion" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider />
        <div class="section-head">
          <h3>Responsables (obligatorio si es menor de 18 años)</h3>
          <el-button size="small" @click="addResponsible">Agregar responsable</el-button>
        </div>
        <div v-for="(resp, index) in form.responsables" :key="index" class="repeat-block">
          <el-row :gutter="12">
            <el-col :span="4">
              <el-select v-model="resp.parentesco" placeholder="Parentesco" style="width: 100%">
                <el-option label="Madre" value="MADRE" />
                <el-option label="Padre" value="PADRE" />
                <el-option label="Tutor" value="TUTOR" />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input v-model="resp.nombre_completo" placeholder="Nombre completo" />
            </el-col>
            <el-col :span="4">
              <el-select v-model="resp.tipo_documento_codigo" clearable placeholder="Tipo doc." style="width: 100%">
                <el-option
                  v-for="tipo in tiposDocumento"
                  :key="tipo.codigo"
                  :label="tipo.nombre"
                  :value="tipo.codigo"
                />
              </el-select>
            </el-col>
            <el-col :span="4">
              <el-input v-model="resp.numero_documento" placeholder="N° doc." :disabled="!resp.tipo_documento_codigo" />
            </el-col>
            <el-col :span="3">
              <el-input v-model="resp.telefono" placeholder="Teléfono" />
            </el-col>
            <el-col :span="2">
              <el-tooltip content="Principal" placement="top">
                <el-switch v-model="resp.es_principal" />
              </el-tooltip>
            </el-col>
            <el-col :span="1">
              <el-button link type="danger" @click="removeResponsible(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
        </div>

        <el-divider />
        <div class="section-head">
          <h3>Grupos de riesgo</h3>
          <el-button size="small" @click="addRisk">Agregar riesgo</el-button>
        </div>
        <div v-for="(riesgo, index) in form.riesgos" :key="index" class="repeat-block">
          <el-row :gutter="12">
            <el-col :span="7">
              <el-select v-model="riesgo.grupo_riesgo_id" placeholder="Grupo de riesgo" style="width: 100%">
                <el-option
                  v-for="grupo in gruposRiesgo"
                  :key="grupo.id"
                  :label="grupo.nombre"
                  :value="grupo.id"
                />
              </el-select>
            </el-col>
            <el-col :span="5">
              <el-date-picker v-model="riesgo.fecha_inicio" type="date" value-format="YYYY-MM-DD" placeholder="Inicio" style="width: 100%" />
            </el-col>
            <el-col :span="5">
              <el-date-picker v-model="riesgo.fecha_fin" type="date" value-format="YYYY-MM-DD" placeholder="Fin (opcional)" clearable style="width: 100%" />
            </el-col>
            <el-col :span="6">
              <el-input v-model="riesgo.observacion" placeholder="Observación" />
            </el-col>
            <el-col :span="1">
              <el-button link type="danger" @click="removeRisk(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-col>
          </el-row>
        </div>

        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit">Registrar paciente</el-button>
          <el-button @click="router.back()">Cancelar</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import { catalogos, type CodeCatalogItem, type EstablishmentCatalogItem, type IdCatalogItem, type RiskGroupCatalogItem, type UbigeoCatalogItem } from '@/services/catalogos'
import { pacientes } from '@/services/pacientes'

const router = useRouter()

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const tiposDocumento = ref<CodeCatalogItem[]>([])
const sexos = ref<CodeCatalogItem[]>([])
const seguros = ref<IdCatalogItem[]>([])
const gruposRiesgo = ref<RiskGroupCatalogItem[]>([])
const establecimientos = ref<EstablishmentCatalogItem[]>([])
const establecimientosLoading = ref(false)
const ubigeos = ref<UbigeoCatalogItem[]>([])
const ubigeosLoading = ref(false)

interface ResponsibleRow {
  parentesco: 'MADRE' | 'PADRE' | 'TUTOR'
  nombre_completo: string
  tipo_documento_codigo: string | null
  numero_documento: string | null
  telefono: string | null
  es_principal: boolean
}

interface RiskRow {
  grupo_riesgo_id: number | null
  fecha_inicio: string
  fecha_fin: string | null
  observacion: string
}

const form = reactive({
  tipo_documento_codigo: '',
  numero_documento: '',
  historia_clinica: '',
  apellido_paterno: '',
  apellido_materno: '',
  primer_nombre: '',
  otros_nombres: '',
  fecha_nacimiento: '',
  sexo_codigo: null as string | null,
  fecha_inscripcion: '',
  seguro_id: null as number | null,
  establecimiento_registro_id: null as number | null,
  ubigeo_residencia_codigo: null as string | null,
  localidad: '',
  direccion: '',
  telefono_principal: '',
  condicion: '',
  responsables: [] as ResponsibleRow[],
  riesgos: [] as RiskRow[],
})

const rules: FormRules = {
  tipo_documento_codigo: [
    { required: true, message: 'Seleccione el tipo de documento.', trigger: 'change' },
  ],
  numero_documento: [
    { required: true, message: 'Ingrese el número de documento.', trigger: 'blur' },
  ],
  primer_nombre: [{ required: true, message: 'Ingrese al menos un nombre.', trigger: 'blur' }],
  fecha_nacimiento: [
    { required: true, message: 'Indique la fecha de nacimiento.', trigger: 'change' },
  ],
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

async function searchUbigeos(query: string): Promise<void> {
  ubigeosLoading.value = true
  try {
    const page = await catalogos.ubigeos(query || undefined, 25, 0)
    ubigeos.value = page.items
  } finally {
    ubigeosLoading.value = false
  }
}

function addResponsible(): void {
  form.responsables.push({
    parentesco: 'MADRE',
    nombre_completo: '',
    tipo_documento_codigo: null,
    numero_documento: null,
    telefono: null,
    es_principal: false,
  })
}

function removeResponsible(index: number): void {
  form.responsables.splice(index, 1)
}

function addRisk(): void {
  form.riesgos.push({
    grupo_riesgo_id: null,
    fecha_inicio: '',
    fecha_fin: null,
    observacion: '',
  })
}

function removeRisk(index: number): void {
  form.riesgos.splice(index, 1)
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    const created = await pacientes.create({
      tipo_documento_codigo: form.tipo_documento_codigo,
      numero_documento: form.numero_documento,
      historia_clinica: form.historia_clinica || null,
      fecha_nacimiento: form.fecha_nacimiento,
      fecha_inscripcion: form.fecha_inscripcion || null,
      apellido_paterno: form.apellido_paterno || null,
      apellido_materno: form.apellido_materno || null,
      primer_nombre: form.primer_nombre || null,
      otros_nombres: form.otros_nombres || null,
      sexo_codigo: form.sexo_codigo,
      ubigeo_residencia_codigo: form.ubigeo_residencia_codigo,
      localidad: form.localidad || null,
      direccion: form.direccion || null,
      establecimiento_registro_id: form.establecimiento_registro_id,
      seguro_id: form.seguro_id,
      telefono_principal: form.telefono_principal || null,
      condicion: form.condicion || null,
      responsables: form.responsables.map((r) => ({
        parentesco: r.parentesco,
        nombre_completo: r.nombre_completo,
        tipo_documento_codigo: r.tipo_documento_codigo,
        numero_documento: r.numero_documento,
        telefono: r.telefono,
        es_principal: r.es_principal,
        activo: true,
      })),
      riesgos: form.riesgos.map((r) => ({
        grupo_riesgo_id: r.grupo_riesgo_id!,
        fecha_inicio: r.fecha_inicio,
        fecha_fin: r.fecha_fin,
        observacion: r.observacion || null,
      })),
    })
    router.push({ name: 'paciente-detalle', params: { id: created.id } })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo registrar el paciente.'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const [tipos, sexosResult, segurosResult, riesgosResult] = await Promise.all([
    catalogos.tiposDocumento(),
    catalogos.sexos(),
    catalogos.seguros(),
    catalogos.gruposRiesgo(),
  ])
  tiposDocumento.value = tipos
  sexos.value = sexosResult
  seguros.value = segurosResult
  gruposRiesgo.value = riesgosResult
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