<template>
  <div class="patient-registration">
    <header class="page-header patient-registration__header">
      <h2>{{ titulo }}</h2>
      <el-button @click="router.back()">Volver</el-button>
    </header>

    <el-alert
      v-if="esAdmision"
      type="info"
      :closable="false"
      class="form-alert"
      title="Admisión: registre al paciente y su inscripción en el establecimiento."
    />

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card class="patient-registration__card" shadow="never">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="patient-registration__form"
      >
        <div class="patient-registration__layout">
          <section class="registration-panel registration-panel--primary" aria-labelledby="patient-data-title">
            <header class="registration-panel__header">
              <h3 id="patient-data-title" class="registration-panel__title">Base de datos</h3>
              <p class="registration-panel__description">
                Identificación, inscripción y datos de contacto del paciente.
              </p>
            </header>

            <div class="patient-registration__fields">
              <el-form-item class="registration-field" label="Tipo de documento" prop="tipo_documento_codigo">
                <el-select v-model="form.tipo_documento_codigo">
                  <el-option
                    v-for="tipo in tiposDocumento"
                    :key="tipo.codigo"
                    :label="tipo.nombre"
                    :value="tipo.codigo"
                  />
                </el-select>
              </el-form-item>
              <el-form-item class="registration-field" label="N.° documento" prop="numero_documento">
                <el-input v-model="form.numero_documento" />
              </el-form-item>
              <el-form-item class="registration-field" label="N.° historia clínica">
                <el-input v-model="form.historia_clinica" />
              </el-form-item>
              <el-form-item class="registration-field" label="Historia familiar">
                <el-input v-model="form.historia_familiar" />
              </el-form-item>
              <el-form-item class="registration-field" label="Fecha de nacimiento" prop="fecha_nacimiento">
                <el-date-picker
                  v-model="form.fecha_nacimiento"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :disabled-date="(d: Date) => d.getTime() > Date.now()"
                />
              </el-form-item>
              <el-form-item class="registration-field" label="Fecha de inscripción">
                <el-date-picker v-model="form.fecha_inscripcion" type="date" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item class="registration-field" label="Apellido paterno">
                <el-input v-model="form.apellido_paterno" />
              </el-form-item>
              <el-form-item class="registration-field" label="Apellido materno">
                <el-input v-model="form.apellido_materno" />
              </el-form-item>
              <el-form-item class="registration-field" label="Primer nombre" prop="primer_nombre">
                <el-input v-model="form.primer_nombre" />
              </el-form-item>
              <el-form-item class="registration-field" label="Otros nombres">
                <el-input v-model="form.otros_nombres" />
              </el-form-item>
              <el-form-item class="registration-field" label="Sexo">
                <el-select v-model="form.sexo_codigo" clearable>
                  <el-option
                    v-for="sexo in sexos"
                    :key="sexo.codigo"
                    :label="sexo.nombre"
                    :value="sexo.codigo"
                  />
                </el-select>
              </el-form-item>
              <el-form-item class="registration-field" label="Seguro">
                <el-select v-model="form.seguro_id" clearable filterable>
                  <el-option
                    v-for="seguro in seguros"
                    :key="seguro.id"
                    :label="seguro.nombre"
                    :value="seguro.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item class="registration-field" label="Establecimiento de registro">
                <el-select
                  v-model="form.establecimiento_registro_id"
                  clearable
                  filterable
                  remote
                  :remote-method="searchEstablecimientos"
                  :loading="establecimientosLoading"
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
              <el-form-item class="registration-field" label="Ubigeo de residencia">
                <el-select
                  v-model="form.ubigeo_residencia_codigo"
                  clearable
                  filterable
                  remote
                  :remote-method="searchUbigeos"
                  :loading="ubigeosLoading"
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
              <el-form-item class="registration-field" label="Localidad">
                <el-input v-model="form.localidad" />
              </el-form-item>
              <el-form-item class="registration-field" label="Dirección">
                <el-input v-model="form.direccion" />
              </el-form-item>
              <el-form-item class="registration-field" label="Teléfono principal">
                <el-input v-model="form.telefono_principal" />
              </el-form-item>
              <el-form-item class="registration-field" label="Condición">
                <el-input v-model="form.condicion" />
              </el-form-item>
            </div>
          </section>

          <PatientRegistrationFamilySections
            v-model:responsables="form.responsables"
            v-model:riesgos="form.riesgos"
            :tipos-documento="tiposDocumento"
            :grupos-riesgo="gruposRiesgo"
          />
        </div>

        <footer class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit">Registrar paciente</el-button>
          <el-button @click="router.back()">Cancelar</el-button>
        </footer>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import PatientRegistrationFamilySections from '@/components/patients/PatientRegistrationFamilySections.vue'
import { catalogos, type CodeCatalogItem, type EstablishmentCatalogItem, type IdCatalogItem, type RiskGroupCatalogItem, type UbigeoCatalogItem } from '@/services/catalogos'
import { pacientes } from '@/services/pacientes'

const route = useRoute()
const router = useRouter()

// La misma vista sirve al botón destacado "Admisión" y a "Nuevo paciente".
const esAdmision = computed(() => route.name === 'admision')
const titulo = computed(() => (esAdmision.value ? 'Admisión de paciente' : 'Nuevo paciente'))

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
  historia_familiar: '',
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
      historia_familiar: form.historia_familiar || null,
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
.patient-registration {
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.page-header h2 {
  margin: 0;
}

.form-alert {
  margin-bottom: 12px;
}

.patient-registration__card {
  min-width: 0;
  border-color: var(--el-border-color-lighter);
  border-radius: 12px;
}

.patient-registration__card :deep(.el-card__body) {
  padding: 14px;
}

.patient-registration__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(300px, 0.82fr);
  align-items: start;
  gap: 16px;
}

.registration-panel {
  min-width: 0;
}

.registration-panel--primary {
  padding-right: 16px;
  border-right: 1px solid var(--el-border-color-lighter);
}

.registration-panel__header {
  margin-bottom: 10px;
}

.registration-panel__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.registration-panel__description {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.35;
}

.patient-registration__fields {
  display: grid;
  gap: 5px;
}

.patient-registration__fields :deep(.registration-field) {
  display: grid;
  grid-template-columns: minmax(126px, 0.45fr) minmax(0, 1fr);
  align-items: center;
  min-width: 0;
  margin-bottom: 0;
}

.patient-registration__fields :deep(.registration-field .el-form-item__label) {
  height: auto;
  padding: 0 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.25;
}

.patient-registration__fields :deep(.registration-field .el-form-item__content) {
  min-width: 0;
  margin-left: 0 !important;
}

.patient-registration__fields :deep(.registration-field .el-select),
.patient-registration__fields :deep(.registration-field .el-date-editor) {
  width: 100%;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  margin-top: 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}

@media (max-width: 1060px) {
  .patient-registration__layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .registration-panel--primary {
    padding-right: 0;
    padding-bottom: 14px;
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }
}

@media (max-width: 640px) {
  .patient-registration__card :deep(.el-card__body) {
    padding: 12px;
  }

  .patient-registration__fields :deep(.registration-field) {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }

  .patient-registration__fields :deep(.registration-field .el-form-item__label) {
    padding-right: 0;
  }

  .form-actions {
    justify-content: stretch;
  }

  .form-actions :deep(.el-button) {
    flex: 1 1 0;
  }
}
</style>
