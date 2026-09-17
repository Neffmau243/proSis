<script setup lang="ts">
import { reactive, useTemplateRef } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import { useLoginUsernames } from '@/composables/useLoginUsernames'
import type { LoginPayload } from '@/services/auth'
import {
  PASSWORD_LENGTH,
  normalizeNumericPassword,
  passwordFormatMessage,
  passwordPattern,
} from '@/utils/password'

defineProps<{
  loading: boolean
  errorMessage: string | null
}>()

const emit = defineEmits<{
  submit: [payload: LoginPayload]
}>()

const formRef = useTemplateRef<FormInstance>('formRef')
const credentials = reactive<LoginPayload>({
  nombre_usuario: '',
  password: '',
})
const {
  usernames,
  loading: usernamesLoading,
  unavailable: usernamesUnavailable,
} = useLoginUsernames()

const rules: FormRules<LoginPayload> = {
  nombre_usuario: [{ required: true, message: 'Ingrese su nombre de usuario.', trigger: 'blur' }],
  password: [
    { required: true, message: 'Ingrese su contraseña.', trigger: 'blur' },
    { pattern: passwordPattern, message: passwordFormatMessage, trigger: 'blur' },
  ],
}

function onPasswordInput(value: string): void {
  credentials.password = normalizeNumericPassword(value)
}

async function validateAndSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  emit('submit', { ...credentials })
}
</script>

<template>
  <div class="login-form">
    <header class="login-form__header">
      <h1 class="login-form__title">Inicie sesión</h1>
      <p class="login-form__subtitle">Use sus credenciales para continuar.</p>
    </header>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="login-form__error"
    />

    <el-form
      ref="formRef"
      :model="credentials"
      :rules="rules"
      label-position="top"
      class="login-form__fields"
      @submit.prevent="validateAndSubmit"
    >
      <el-form-item label="Usuario" prop="nombre_usuario">
        <el-select
          v-if="!usernamesUnavailable"
          v-model="credentials.nombre_usuario"
          filterable
          default-first-option
          :loading="usernamesLoading"
          no-match-text="No se encontró ningún usuario."
          no-data-text="No hay usuarios activos disponibles."
          placeholder="Seleccione o escriba su usuario"
          class="login-form__control"
        >
          <el-option
            v-for="username in usernames"
            :key="username"
            :label="username"
            :value="username"
          />
        </el-select>
        <el-input
          v-else
          v-model="credentials.nombre_usuario"
          name="username"
          autocomplete="username"
          placeholder="nombre.usuario"
          autofocus
        />
      </el-form-item>

      <el-form-item label="Contraseña" prop="password">
        <el-input
          v-model="credentials.password"
          type="password"
          name="password"
          autocomplete="current-password"
          show-password
          inputmode="numeric"
          :maxlength="PASSWORD_LENGTH"
          placeholder="8 dígitos"
          @input="onPasswordInput"
          @keyup.enter="validateAndSubmit"
        />
      </el-form-item>

      <el-button
        type="primary"
        native-type="submit"
        :loading="loading"
        :disabled="loading"
        class="login-form__submit"
      >
        Ingresar
      </el-button>
    </el-form>
  </div>
</template>

<style scoped>
.login-form {
  display: grid;
  gap: 1.5rem;
}

.login-form__header {
  display: grid;
  gap: 0.375rem;
}

.login-form__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.25;
}

.login-form__subtitle {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 0.875rem;
  line-height: 1.45;
}

.login-form__error {
  margin: 0;
}

.login-form__fields {
  display: grid;
  gap: 1.125rem;
}

.login-form__fields :deep(.el-form-item) {
  margin-bottom: 0;
}

.login-form__fields :deep(.el-form-item__label) {
  padding-bottom: 0.375rem;
  color: var(--el-text-color-primary);
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.25;
}

.login-form__fields :deep(.el-input__wrapper) {
  min-height: 2.5rem;
}

.login-form__control {
  width: 100%;
}

.login-form__submit {
  width: 100%;
  height: 2.5rem;
  margin-top: 0.125rem;
  font-weight: 600;
}

@media (max-width: 919px) {
  .login-form {
    gap: 1.5rem;
  }
}
</style>
