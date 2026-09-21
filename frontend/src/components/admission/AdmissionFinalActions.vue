<script setup lang="ts">
defineProps<{
  saving: boolean
  primaryLabel: string
  disabled?: boolean
  saved?: boolean
  printReady?: boolean
  disabledReason?: string
}>()

const emit = defineEmits<{
  submit: []
  exit: []
  print: []
  pending: [action: string]
}>()
</script>

<template>
  <footer class="admission-final-actions" aria-label="Acciones de admisión">
    <p v-if="disabledReason" class="admission-final-actions__reason" role="status">
      {{ disabledReason }}
    </p>
    <div class="admission-final-actions__tray" role="group" aria-label="Acciones de admisión">
      <el-button
        class="admission-final-actions__button"
        type="primary"
        :loading="saving"
        :disabled="disabled || saved"
        @click="emit('submit')"
      >
        <el-icon><DocumentChecked /></el-icon>
        <span>{{ primaryLabel }}</span>
      </el-button>
      <el-button
        class="admission-final-actions__button"
        :disabled="saving || disabled || !printReady"
        @click="emit('print')"
      >
        <el-icon><Printer /></el-icon>
        <span>Imprimir S.I.S.</span>
      </el-button>
      <el-button class="admission-final-actions__button" @click="emit('pending', 'Otra consulta')">
        <el-icon><SwitchButton /></el-icon>
        <span>Otra consulta</span>
      </el-button>
      <el-button class="admission-final-actions__button" @click="emit('pending', 'FUA adicional')">
        <el-icon><DocumentAdd /></el-icon>
        <span>FUA adicional</span>
      </el-button>
      <el-button class="admission-final-actions__button" type="danger" plain @click="emit('exit')">
        <el-icon><CircleClose /></el-icon>
        <span>Salir</span>
      </el-button>
    </div>
  </footer>
</template>

<style scoped>
.admission-final-actions {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.admission-final-actions__reason {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}

.admission-final-actions__tray {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  width: 100%;
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.admission-final-actions__button {
  display: inline-flex;
  min-width: 0;
  width: 100%;
  flex-direction: column;
  gap: 2px;
  min-height: 44px;
  height: auto;
  margin: 0 !important;
  padding: 5px 2px;
  border-width: 0 0 0 1px;
  border-radius: 0;
  font-size: 8.5px;
  line-height: 1.2;
  white-space: normal;
}

.admission-final-actions__button:first-child {
  border-left-width: 0;
}

.admission-final-actions__button :deep(.el-icon) {
  margin: 0;
  font-size: 14px;
}

.admission-final-actions__button :deep(.el-button__text) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
</style>
