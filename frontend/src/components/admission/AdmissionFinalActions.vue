<script setup lang="ts">
import {
  CircleClose,
  DocumentAdd,
  DocumentChecked,
  Printer,
  SwitchButton,
} from '@element-plus/icons-vue'
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
      <el-button
        class="admission-final-actions__button"
        disabled
        title="Otra consulta: aún no disponible"
      >
        <el-icon><SwitchButton /></el-icon>
        <span>Otra consulta</span>
      </el-button>
      <el-button
        class="admission-final-actions__button"
        disabled
        title="FUA adicional: aún no disponible"
      >
        <el-icon><DocumentAdd /></el-icon>
        <span>FUA adicional</span>
      </el-button>
      <el-button
        class="admission-final-actions__button"
        type="danger"
        plain
        :disabled="saving"
        @click="emit('exit')"
      >
        <el-icon><CircleClose /></el-icon>
        <span>Salir</span>
      </el-button>
    </div>
  </footer>
</template>

<style scoped>
.admission-final-actions {
  grid-area: actions;
  align-self: start;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--admission-border, #b9cbdf);
  border-radius: 4px;
  background: var(--admission-panel, #e8eff7);
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
  gap: 4px;
}

.admission-final-actions__button {
  display: inline-flex;
  min-width: 0;
  width: 100%;
  flex-direction: column;
  gap: 2px;
  min-height: 60px;
  height: auto;
  margin: 0 !important;
  padding: 6px 4px;
  border-width: 1px;
  border-radius: 2px;
  font-size: 11px;
  line-height: 1.2;
  white-space: normal;
}

.admission-final-actions__button :deep(.el-icon) {
  margin: 0;
  font-size: 14px;
}

.admission-final-actions__button :deep(> span) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
@media (max-width: 480px) {
  .admission-final-actions__tray {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
