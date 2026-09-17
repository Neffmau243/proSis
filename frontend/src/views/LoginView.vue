<script setup lang="ts">
import { shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LoginAccessForm from '@/components/auth/LoginAccessForm.vue'
import LoginBrandPanel from '@/components/auth/LoginBrandPanel.vue'
import type { LoginPayload } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const loading = shallowRef(false)
const errorMessage = shallowRef<string | null>(null)

async function submit(payload: LoginPayload): Promise<void> {
  loading.value = true
  errorMessage.value = null
  try {
    await auth.login(payload)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : undefined
    router.push(redirect || { name: 'inicio' })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'No se pudo iniciar sesión.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login">
    <LoginBrandPanel />

    <section class="login__access">
      <div class="login__form-wrap">
        <el-card class="login__card" shadow="never">
          <LoginAccessForm :loading="loading" :error-message="errorMessage" @submit="submit" />
        </el-card>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login {
  display: grid;
  min-height: 100dvh;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  background: #f5f7fa;
}

.login__access {
  display: grid;
  box-sizing: border-box;
  min-width: 0;
  place-items: center;
  padding: clamp(2.5rem, 6vw, 6rem);
  background: #f5f7fa;
}

.login__form-wrap {
  width: min(100%, 25rem);
}

.login__card {
  border-radius: 12px;
}

.login__card :deep(.el-card__body) {
  padding: 28px;
}

@media (max-width: 919px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
  }

  .login__access {
    min-height: 100dvh;
    padding: clamp(2rem, 9vw, 4rem) clamp(1.5rem, 6vw, 3rem);
  }
}

@media (max-height: 640px) and (min-width: 920px) {
  .login__access {
    padding-block: 2rem;
  }
}
</style>
