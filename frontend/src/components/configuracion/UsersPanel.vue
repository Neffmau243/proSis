<template>
  <div>
    <div class="panel-toolbar">
      <el-switch
        :model-value="incluirInactivos"
        active-text="Incluir inactivos"
        @update:model-value="emit('update:incluirInactivos', $event as boolean)"
      />
      <el-button type="primary" @click="openCreate()">Nuevo usuario</el-button>
    </div>

    <el-alert
      v-if="errorMessage && !createVisible && !rolesVisible && !passwordVisible"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-table
      v-loading="loading"
      :data="rows"
      empty-text="Sin usuarios registrados"
      class="users-table"
    >
      <el-table-column prop="nombre_usuario" label="Usuario" min-width="180" show-overflow-tooltip />
      <el-table-column label="Roles" min-width="170">
        <template #default="{ row }">
          <div class="tags-cell">
            <el-tag v-for="role in row.roles" :key="role" size="small">{{ role }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Profesional vinculado" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ profesionalNombre(row.profesional_id) }}</template>
      </el-table-column>
      <el-table-column label="Último acceso" min-width="170">
        <template #default="{ row }">{{ formatDate(row.ultimo_acceso_at) }}</template>
      </el-table-column>
      <el-table-column label="Estado" width="110">
        <template #default="{ row }">
          <el-tag :type="row.activo ? 'success' : 'danger'" size="small">
            {{ row.activo ? 'Activo' : 'Inactivo' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Acciones" min-width="260">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRoles(row)">Roles</el-button>
          <el-button
            link
            type="primary"
            :disabled="!row.activo || row.id === auth.usuarioId"
            @click="openPassword(row)"
          >
            Contraseña
          </el-button>
          <el-button
            link
            type="primary"
            :disabled="!row.activo || row.id === auth.usuarioId"
            @click="deactivate(row)"
          >
            Dar de baja
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Alta de cuenta -->
    <el-dialog v-model="createVisible" title="Nuevo usuario" width="560px">
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" class="form-alert" />
      <el-form ref="createRef" :model="createForm" :rules="createRules" label-width="170px">
        <el-form-item label="Nombre de usuario" prop="nombre_usuario">
          <el-input v-model="createForm.nombre_usuario" placeholder="nombre.usuario (mín. 3)" />
        </el-form-item>
        <el-form-item label="Contraseña" prop="password">
          <el-input
            v-model="createForm.password"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            placeholder="8 dígitos"
            @input="createForm.password = normalizeNumericPassword($event)"
          />
        </el-form-item>
        <el-form-item label="Confirmar contraseña" prop="confirm">
          <el-input
            v-model="createForm.confirm"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            @input="createForm.confirm = normalizeNumericPassword($event)"
          />
        </el-form-item>
        <el-form-item label="Roles" prop="roles">
          <el-checkbox-group v-model="createForm.roles">
            <el-checkbox value="ADMIN">ADMIN — gestión administrativa</el-checkbox>
            <el-checkbox value="PROFESIONAL">PROFESIONAL — atención clínica</el-checkbox>
          </el-checkbox-group>
          <div class="hint">El rol PROFESIONAL requiere vincular un profesional activo.</div>
        </el-form-item>
        <el-form-item label="Profesional vinculado">
          <el-select
            v-model="createForm.profesional_id"
            clearable
            filterable
            remote
            :remote-method="searchProfesionales"
            :loading="profesionalesLoading"
            style="width: 100%"
            placeholder="Busque (obligatorio para PROFESIONAL)"
          >
            <el-option
              v-for="professional in profesionalOptions"
              :key="professional.id"
              :label="professional.nombre_completo"
              :value="professional.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">Crear usuario</el-button>
      </template>
    </el-dialog>

    <!-- Roles -->
    <el-dialog v-model="rolesVisible" title="Roles del usuario" width="440px">
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" class="form-alert" />
      <p class="dialog-hint">
        Usuario <strong>{{ rolesTarget?.nombre_usuario }}</strong>.
        <template v-if="!rolesTarget?.profesional_id">
          Sin profesional vinculado no se puede asignar PROFESIONAL.
        </template>
      </p>
      <el-checkbox-group v-model="rolesForm">
        <el-checkbox value="ADMIN">ADMIN — gestión administrativa</el-checkbox>
        <el-checkbox value="PROFESIONAL" :disabled="!rolesTarget?.profesional_id">
          PROFESIONAL — atención clínica
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="rolesVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="submitRoles">Guardar roles</el-button>
      </template>
    </el-dialog>

    <!-- Restablecer contraseña -->
    <el-dialog v-model="passwordVisible" title="Restablecer contraseña" width="460px">
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" class="form-alert" />
      <p class="dialog-hint">
        Nueva contraseña para <strong>{{ passwordTarget?.nombre_usuario }}</strong>. Ocho dígitos.
      </p>
      <el-form ref="passwordRef" :model="passwordForm" :rules="passwordRules" label-width="150px">
        <el-form-item label="Nueva contraseña" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            @input="passwordForm.new_password = normalizeNumericPassword($event)"
          />
        </el-form-item>
        <el-form-item label="Confirmar" prop="new_password_confirmation">
          <el-input
            v-model="passwordForm.new_password_confirmation"
            type="password"
            show-password
            autocomplete="new-password"
            inputmode="numeric"
            :maxlength="PASSWORD_LENGTH"
            @input="
              passwordForm.new_password_confirmation = normalizeNumericPassword($event)
            "
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="submitPassword">
          Restablecer
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import { catalogos, type ProfessionalCatalogItem } from '@/services/catalogos'
import { useAuthStore } from '@/stores/auth'
import { usuarios, type UserResponse } from '@/services/usuarios'
import {
  PASSWORD_LENGTH,
  normalizeNumericPassword,
  passwordFormatMessage,
  passwordPattern,
} from '@/utils/password'
import type { ProfessionalResponse } from '@/services/profesionales'

const props = defineProps<{
  rows: UserResponse[]
  loading: boolean
  incluirInactivos: boolean
  /** Profesionales cargados por el contenedor para resolver nombres. */
  professionals: ProfessionalResponse[]
  /** Profesional preseleccionado al crear una cuenta desde su ficha. */
  prefillProfessionalId: number | null
}>()

const emit = defineEmits<{
  (event: 'refresh'): void
  (event: 'update:incluirInactivos', value: boolean): void
  (event: 'consume-prefill'): void
}>()

const auth = useAuthStore()
const errorMessage = ref<string | null>(null)
const saving = ref(false)

// --- Alta ---
const createRef = ref<FormInstance>()
const createVisible = ref(false)
const profesionalOptions = ref<ProfessionalCatalogItem[]>([])
const profesionalesLoading = ref(false)
const createForm = reactive({
  nombre_usuario: '',
  password: '',
  confirm: '',
  roles: [] as string[],
  profesional_id: null as number | null,
})

const createRules: FormRules = {
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
    {
      validator: (_rule, value, callback) => {
        if (value && value !== createForm.password) {
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

// --- Roles ---
const rolesVisible = ref(false)
const rolesTarget = ref<UserResponse | null>(null)
const rolesForm = ref<string[]>([])

// --- Contraseña ---
const passwordVisible = ref(false)
const passwordTarget = ref<UserResponse | null>(null)
const passwordRef = ref<FormInstance>()
const passwordForm = reactive({ new_password: '', new_password_confirmation: '' })

const passwordRules: FormRules = {
  new_password: [
    { required: true, message: 'Ingrese la nueva contraseña.', trigger: 'blur' },
    { pattern: passwordPattern, message: passwordFormatMessage, trigger: 'blur' },
  ],
  new_password_confirmation: [
    { required: true, message: 'Confirme la contraseña.', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && value !== passwordForm.new_password) {
          callback(new Error('Las contraseñas no coinciden.'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function profesionalNombre(id: number | null): string {
  if (id === null) return '—'
  const found = props.professionals.find((item) => item.id === id)
  return found?.nombre_completo ?? `Profesional #${id}`
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  // El backend persiste UTC sin zona; sin la 'Z' el navegador lo leería como
  // hora local y mostraría una hora corrida. Se normaliza antes de formatear.
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(value)
  const parsed = new Date(hasZone ? value : `${value}Z`)
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString()
}

async function searchProfesionales(query: string): Promise<void> {
  profesionalesLoading.value = true
  try {
    const page = await catalogos.profesionales(query || undefined, 25, 0)
    profesionalOptions.value = page.items
  } finally {
    profesionalesLoading.value = false
  }
}

function openCreate(professionalId: number | null = null): void {
  errorMessage.value = null
  createForm.nombre_usuario = ''
  createForm.password = ''
  createForm.confirm = ''
  createForm.roles = professionalId === null ? [] : ['PROFESIONAL']
  createForm.profesional_id = professionalId
  profesionalOptions.value = []
  if (professionalId !== null) {
    // La ficha ya conoce al profesional: se muestra aunque no se busque.
    const found = props.professionals.find((item) => item.id === professionalId)
    if (found) {
      profesionalOptions.value = [
        { id: found.id, nombre_completo: found.nombre_completo, colegiatura: found.colegiatura, activo: found.activo },
      ]
    }
  }
  createRef.value?.clearValidate()
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  const valid = await createRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    const created = await usuarios.create({
      nombre_usuario: createForm.nombre_usuario.trim(),
      password: createForm.password,
      roles: createForm.roles,
      profesional_id: createForm.profesional_id,
    })
    ElMessage.success(`Usuario "${created.nombre_usuario}" creado.`)
    createVisible.value = false
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'No se pudo crear el usuario.'
  } finally {
    saving.value = false
  }
}

function openRoles(row: UserResponse): void {
  rolesTarget.value = row
  rolesForm.value = [...row.roles]
  errorMessage.value = null
  rolesVisible.value = true
}

async function submitRoles(): Promise<void> {
  if (!rolesTarget.value) return
  if (rolesForm.value.length === 0) {
    errorMessage.value = 'Seleccione al menos un rol.'
    return
  }
  saving.value = true
  errorMessage.value = null
  try {
    await usuarios.updateRoles(rolesTarget.value.id, rolesForm.value)
    ElMessage.success('Roles actualizados.')
    rolesVisible.value = false
    emit('refresh')
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudieron actualizar los roles.'
  } finally {
    saving.value = false
  }
}

function openPassword(row: UserResponse): void {
  passwordTarget.value = row
  passwordForm.new_password = ''
  passwordForm.new_password_confirmation = ''
  errorMessage.value = null
  passwordRef.value?.clearValidate()
  passwordVisible.value = true
}

async function submitPassword(): Promise<void> {
  if (!passwordTarget.value) return
  const valid = await passwordRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  errorMessage.value = null
  try {
    await usuarios.resetPassword(passwordTarget.value.id, {
      new_password: passwordForm.new_password,
      new_password_confirmation: passwordForm.new_password_confirmation,
    })
    ElMessage.success('Contraseña restablecida. La sesión anterior quedó invalidada.')
    passwordVisible.value = false
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo restablecer la contraseña.'
  } finally {
    saving.value = false
  }
}

async function deactivate(row: UserResponse): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `El usuario ${row.nombre_usuario} quedará inactivo y no podrá iniciar sesión. La baja es lógica: la cuenta se conserva.`,
      'Dar de baja usuario',
      { type: 'info', confirmButtonText: 'Dar de baja', cancelButtonText: 'Cancelar' },
    )
  } catch {
    return
  }
  errorMessage.value = null
  try {
    await usuarios.deactivate(row.id)
    ElMessage.success('Usuario dado de baja.')
    emit('refresh')
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo dar de baja al usuario.'
  }
}

// Al crear una cuenta desde la ficha de un profesional, se abre el alta ya vinculada.
watch(
  () => props.prefillProfessionalId,
  (professionalId) => {
    if (professionalId !== null) {
      openCreate(professionalId)
      emit('consume-prefill')
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.form-alert {
  margin-bottom: 16px;
}

/* Las celdas contienen los valores sin desbordar la columna: los tags envuelven. */
.users-table :deep(.cell) {
  word-break: normal;
  overflow-wrap: anywhere;
}

.tags-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dialog-hint {
  margin-top: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
