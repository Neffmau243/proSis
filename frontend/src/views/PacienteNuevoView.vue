<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import PatientRegistrationBaseSection from '@/components/patients/PatientRegistrationBaseSection.vue'
import PatientRegistrationFamilySections from '@/components/patients/PatientRegistrationFamilySections.vue'
import type {
  PatientRegistrationDraft,
  PatientRegistrationPatch,
} from '@/components/patients/patientRegistration.types'
import {
  catalogos,
  type CodeCatalogItem,
  type EstablishmentCatalogItem,
  type IdCatalogItem,
  type RiskGroupCatalogItem,
  type UbigeoCatalogItem,
} from '@/services/catalogos'
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

const form = reactive<PatientRegistrationDraft>({
  tipo_documento_codigo: '',
  numero_documento: '',
  historia_clinica: '',
  historia_familiar: '',
  apellido_paterno: '',
  apellido_materno: '',
  primer_nombre: '',
  otros_nombres: '',
  fecha_nacimiento: '',
  sexo_codigo: null,
  fecha_inscripcion: '',
  seguro_id: null,
  establecimiento_registro_id: null,
  ubigeo_residencia_codigo: null,
  localidad: '',
  direccion: '',
  telefono_principal: '',
  condicion: '',
  responsables: [],
  riesgos: [],
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

function updatePatientForm(changes: PatientRegistrationPatch): void {
  Object.assign(form, changes)
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
      responsables: form.responsables.map((responsable) => ({
        parentesco: responsable.parentesco,
        nombre_completo: responsable.nombre_completo,
        tipo_documento_codigo: responsable.tipo_documento_codigo,
        numero_documento: responsable.numero_documento,
        telefono: responsable.telefono,
        es_principal: responsable.es_principal,
        activo: true,
      })),
      riesgos: form.riesgos.map((riesgo) => ({
        grupo_riesgo_id: riesgo.grupo_riesgo_id!,
        fecha_inicio: riesgo.fecha_inicio,
        fecha_fin: riesgo.fecha_fin,
        observacion: riesgo.observacion || null,
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
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <div class="patient-registration__layout">
          <PatientRegistrationBaseSection
            :form="form"
            :tipos-documento="tiposDocumento"
            :sexos="sexos"
            :seguros="seguros"
            :establecimientos="establecimientos"
            :establecimientos-loading="establecimientosLoading"
            :ubigeos="ubigeos"
            :ubigeos-loading="ubigeosLoading"
            @update="updatePatientForm"
            @search-establecimientos="searchEstablecimientos"
            @search-ubigeos="searchUbigeos"
          />

          <PatientRegistrationFamilySections
            v-model:responsables="form.responsables"
            v-model:riesgos="form.riesgos"
            v-model:telefono-principal="form.telefono_principal"
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

<style scoped>
.patient-registration {
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.page-header h2 {
  margin: 0;
}

.form-alert {
  margin-bottom: 10px;
}

.patient-registration__card {
  min-width: 0;
  border-color: var(--el-border-color-lighter);
  border-radius: 8px;
}

.patient-registration__card :deep(.el-card__body) {
  padding: 12px;
}

.patient-registration__layout {
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(300px, 0.82fr);
  align-items: start;
  gap: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 10px;
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.form-actions :deep(.el-button) {
  min-height: 28px;
}

@media (max-width: 1060px) {
  .patient-registration__layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 640px) {
  .patient-registration__card :deep(.el-card__body) {
    padding: 10px;
  }

  .form-actions {
    justify-content: stretch;
  }

  .form-actions :deep(.el-button) {
    flex: 1 1 0;
  }
}
</style>
