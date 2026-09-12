<template>
  <PagePlaceholder
    title="Referencia de laboratorio"
    description="Opción del sistema antiguo que todavía no tiene endpoint en el backend."
    :planned="planned"
  />
</template>

<script setup lang="ts">
import PagePlaceholder from '@/components/PagePlaceholder.vue'

const planned = [
  'Registrar órdenes de laboratorio (ref. laboratorio) asociadas a una atención.',
  'Consultar el estado de los resultados por paciente.',
  'Catálogo de exámenes por establecimiento.',
]
</script>
