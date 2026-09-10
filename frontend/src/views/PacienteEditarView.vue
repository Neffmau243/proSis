<template>
  <div>
    <div class="page-header">
      <h2>Editar paciente</h2>
      <el-button @click="router.back()">Volver</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card v-loading="loading">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="180px">
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
            <el-form-item label="Primer nombre">
              <el-input v-model="form.primer_nombre" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Otros nombres">
              <el-input v-model="form.otros_nombres" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Fecha de nacimiento">
              <el-date-picker
                v-model="form.fecha_nacimiento"
                type="date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
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

        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit">Guardar cambios</el-button>
          <el-button @click="router.back()">Cancelar</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import {
  catalogos,
  type CodeCatalogItem,
  type IdCatalogItem,
  type UbigeoCatalogItem,
} from '@/services/catalogos'
import { pacientes, type Patient } from '@/services/pacientes'

const route = useRoute()
const router = useRouter()
const patientId = Number(route.params.id)

const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const tiposDocumento = ref<CodeCatalogItem[]>([])
const sexos = ref<CodeCatalogItem[]>([])
const seguros = ref<IdCatalogItem[]>([])
const ubigeos = ref<UbigeoCatalogItem[]>([])
const ubigeosLoading = ref(false)

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
  ubigeo_residencia_codigo: null as string | null,
  localidad: '',
  direccion: '',
  telefono_principal: '',
  condicion: '',
})

const rules: FormRules = {
  tipo_documento_codigo: [
    { required: true, message: 'Seleccione el tipo de documento.', trigger: 'change' },
  ],
  numero_documento: [
    { required: true, message: 'Ingrese el número de documento.', trigger: 'blur' },
  ],
  fecha_nacimiento: [
    { required: true, message: 'Indique la fecha de nacimiento.', trigger: 'change' },
  ],
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

function fillForm(patient: Patient): void {
  form.tipo_documento_codigo = patient.tipo_documento_codigo
  form.numero_documento = patient.numero_documento
  form.historia_clinica = patient.historia_clinica ?? ''
  form.apellido_paterno = patient.apellido_paterno ?? ''
  form.apellido_materno = patient.apellido_materno ?? ''
  form.primer_nombre = patient.primer_nombre ?? ''
  form.otros_nombres = patient.otros_nombres ?? ''
  form.fecha_nacimiento = patient.fecha_nacimiento
  form.sexo_codigo = patient.sexo_codigo
  form.fecha_inscripcion = patient.fecha_inscripcion ?? ''
  form.seguro_id = patient.seguro_id
  form.ubigeo_residencia_codigo = patient.ubigeo_residencia_codigo
  form.localidad = patient.localidad ?? ''
  form.direccion = patient.direccion ?? ''
  form.telefono_principal = patient.telefono_principal ?? ''
  form.condicion = patient.condicion ?? ''
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    await pacientes.update(patientId, {
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
      seguro_id: form.seguro_id,
      telefono_principal: form.telefono_principal || null,
      condicion: form.condicion || null,
    })
    router.push({ name: 'paciente-detalle', params: { id: patientId } })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo actualizar el paciente.'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [tipos, sexosResult, segurosResult, patient] = await Promise.all([
      catalogos.tiposDocumento(),
      catalogos.sexos(),
      catalogos.seguros(),
      pacientes.get(patientId),
    ])
    tiposDocumento.value = tipos
    sexos.value = sexosResult
    seguros.value = segurosResult
    fillForm(patient)
  } finally {
    loading.value = false
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

.form-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>