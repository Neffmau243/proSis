<template>
  <div class="login">
    <el-card class="login__card">
      <h1 class="login__title">Sistema de Salud IPRESS</h1>
      <p class="login__subtitle">Inicie sesión para continuar</p>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="false"
        class="login__error"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submit"
      >
        <el-form-item label="Usuario" prop="nombre_usuario">
          <el-input
            v-model="form.nombre_usuario"
            name="username"
            autocomplete="username"
            placeholder="nombre.usuario"
          />
        </el-form-item>
        <el-form-item label="Contraseña" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            name="password"
            autocomplete="current-password"
            show-password
            placeholder="••••••••"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="login__submit">
          Ingresar
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMessage = ref<string | null>(null)

const form = reactive({
  nombre_usuario: '',
  password: '',
})

const rules: FormRules = {
  nombre_usuario: [
    { required: true, message: 'Ingrese su nombre de usuario.', trigger: 'blur' },
  ],
  password: [{ required: true, message: 'Ingrese su contraseña.', trigger: 'blur' }],
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  errorMessage.value = null
  try {
    await auth.login(form)
    const redirect =
      typeof route.query.redirect === 'string' ? route.query.redirect : undefined
    router.push(redirect || { name: 'inicio' })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo iniciar sesión.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%);
}

.login__card {
  width: 100%;
  max-width: 380px;
}

.login__title {
  margin: 0 0 4px;
  font-size: 20px;
}

.login__subtitle {
  margin: 0 0 16px;
  color: var(--el-text-color-secondary);
}

.login__error {
  margin-bottom: 16px;
}

.login__submit {
  width: 100%;
  margin-top: 4px;
}
</style>