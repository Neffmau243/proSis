<template>
  <PagePlaceholder
    title="Auditoría"
    description="El permiso AUDITORIA_LEER existe y la base registra cada operación (actor, acción, fecha, foto antes/después), pero el backend todavía no expone un endpoint de consulta."
    :planned="[
      'Pendiente del backend: GET de auditoría con filtros por actor, acción, tabla y rango de fechas',
      'La UI consumirá el sobre paginado estándar (items/total/limit/offset/has_more)',
      'Nunca se muestran contraseñas ni secretos: el backend los redacta antes de guardar',
    ]"
  />
</template>

<script setup lang="ts">
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>