<template>
  <div>
    <div class="page-header">
      <h2>Usuarios</h2>
      <el-button @click="router.back()">Volver</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      title="Gestión parcial: el backend aún no expone listado ni ficha de usuarios (no existe GET /usuarios). Por ahora se puede crear una cuenta nueva; roles, restablecimiento de contraseña y baja requieren conocer el ID por otro medio."
      class="form-alert"
    />

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card>
      <h3>Nuevo usuario</h3>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="180px" class="user-form">
        <el-form-item label="Nombre de usuario" prop="nombre_usuario">
          <el-input
            v-model="form.nombre_usuario"
            placeholder="nombre.usuario (mín. 3 caracteres)"
          />
        </el-form-item>
        <el-form-item label="Contraseña" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            placeholder="8 dígitos"
            @input="form.password = normalizeNumericPassword($event)"
          />
        </el-form-item>
        <el-form-item label="Confirmar contraseña" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            @input="form.confirm = normalizeNumericPassword($event)"
          />
        </el-form-item>
        <el-form-item label="Roles" prop="roles">
          <el-checkbox-group v-model="form.roles">
            <el-checkbox value="ADMIN">ADMIN — gestión administrativa</el-checkbox>
            <el-checkbox value="PROFESIONAL">PROFESIONAL — atención clínica</el-checkbox>
          </el-checkbox-group>
          <div class="hint">El rol PROFESIONAL requiere vincular un profesional activo.</div>
        </el-form-item>
        <el-form-item label="Profesional vinculado">
          <el-select
            v-model="form.profesional_id"
            clearable
            filterable
            remote
            :remote-method="searchProfesionales"
            :loading="profesionalesLoading"
            style="width: 100%"
            placeholder="Busque (obligatorio para PROFESIONAL)"
          >
            <el-option
              v-for="prof in profesionales"
              :key="prof.id"
              :label="prof.nombre_completo"
              :value="prof.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-actions">
          <el-button type="primary" :loading="saving" @click="submit">Crear usuario</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { catalogos, type ProfessionalCatalogItem } from '@/services/catalogos'
import { usuarios } from '@/services/usuarios'
import {
  PASSWORD_LENGTH,
  normalizeNumericPassword,
  passwordFormatMessage,
  passwordPattern,
} from '@/utils/password'

const router = useRouter()

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const profesionales = ref<ProfessionalCatalogItem[]>([])
const profesionalesLoading = ref(false)

const form = reactive({
  nombre_usuario: '',
  password: '',
  confirm: '',
  roles: [] as string[],
  profesional_id: null as number | null,
})

const rules: FormRules = {
  nombre_usuario: [
    { required: true, message: 'Ingrese el nombre de usuario.', trigger: 'blur' },
    { min: 3, message: 'Mínimo 3 caracteres.', trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Ingrese la contraseña.', trigger: 'blur' },
    { pattern: passwordPattern, message: passwordFormatMessage, trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: 'Confirme la contraseña.', trigger: 'blur' },
    { pattern: passwordPattern, message: passwordFormatMessage, trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && value !== form.password) {
          callback(new Error('Las contraseñas no coinciden.'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  roles: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.length === 0) {
          callback(new Error('Seleccione al menos un rol.'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
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

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    const created = await usuarios.create({
      nombre_usuario: form.nombre_usuario.trim(),
      password: form.password,
      roles: form.roles,
      profesional_id: form.profesional_id,
    })
    ElMessage.success(`Usuario "${created.nombre_usuario}" creado (ID ${created.id}).`)
    formRef.value?.resetFields()
    form.roles = []
    form.profesional_id = null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'No se pudo crear el usuario.'
  } finally {
    saving.value = false
  }
}
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

.user-form {
  max-width: 640px;
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.form-actions {
  margin-top: 8px;
}
</style>
