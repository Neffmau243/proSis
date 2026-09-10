<template>
  <el-config-provider :locale="es">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import es from 'element-plus/es/locale/lang/es'

import { useAuthStore } from '@/stores/auth'

// Rehidrata la sesión persistida (refresco de página o entrada directa a una
// URL): el guard de rutas ya validó la sesión contra localStorage; aquí se
// llena el store reactivo para que menú y botones dependan de permisos reales.
useAuthStore().hydrateFromStorage()
</script>