<template>
  <div class="password-page">
    <h2 class="password-page__heading">Cambiar contraseña</h2>

    <el-card class="password-page__card">
      <el-alert
        v-if="success"
        type="success"
        :closable="false"
        title="Contraseña actualizada. Vuelva a iniciar sesión."
        class="password-page__alert"
      />
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="false"
        class="password-page__alert"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submit"
      >
        <el-form-item label="Contraseña actual" prop="current_password">
          <el-input
            v-model="form.current_password"
            type="password"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>
        <el-form-item label="Nueva contraseña" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="Confirmar nueva contraseña" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" :disabled="success">
          Guardar
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import { changeMyPassword } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const success = ref(false)
const errorMessage = ref<string | null>(null)

const form = reactive({
  current_password: '',
  new_password: '',
  confirm: '',
})

const rules: FormRules = {
  current_password: [
    { required: true, message: 'Ingrese su contraseña actual.', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: 'Ingrese la nueva contraseña.', trigger: 'blur' },
    { min: 12, message: 'La contraseña debe tener al menos 12 caracteres.', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && value === form.current_password) {
          callback(new Error('La nueva contraseña debe ser diferente de la actual.'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  confirm: [
    { required: true, message: 'Confirme la nueva contraseña.', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value && value !== form.new_password) {
          callback(new Error('Las contraseñas no coinciden.'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMessage.value = null
  try {
    // El backend responde 204; el cliente cierra la sesión local y pide un
    // nuevo inicio (GUIA_FRONTEND_RUTAS.md, sección 2).
    await changeMyPassword({
      current_password: form.current_password,
      new_password: form.new_password,
    })
    success.value = true
    auth.logout()
    setTimeout(() => router.push({ name: 'login' }), 1500)
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo cambiar la contraseña.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.password-page__heading {
  margin: 0 0 16px;
}

.password-page__card {
  max-width: 480px;
}

.password-page__alert {
  margin-bottom: 16px;
}
</style>