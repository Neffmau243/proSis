<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FuaPrintSnapshot } from '@/types/fua'
import {
  defaultFuaLayout, FUA_LAYOUT_KEY, fuaValues, fuaWarnings,
  layoutProblems, parseFuaLayout, printFua,
} from '@/utils/fuaPrint'

const visible = defineModel<boolean>({ required: true })
const props = defineProps<{
  snapshot: FuaPrintSnapshot
}>()
const layout = ref(defaultFuaLayout())
const availableFields = computed(() => layout.value.fields.filter(field => field.id !== 'codigo_renipress' || props.snapshot.renipress_preimpreso === false))
const selectedId = ref('ipress_nombre')
const selected = computed(() => layout.value.fields.find((field) => field.id === selectedId.value)!)
const acknowledged = ref(false)
const printing = ref(false)
const localError = ref('')
const background = ref('')
const tab = ref('datos')
const snapshot = computed(() => props.snapshot)
const values = computed(() => fuaValues(snapshot.value))
const warnings = computed(() => fuaWarnings(snapshot.value))
const geometryErrors = computed(() => layoutProblems(layout.value, values.value))
const canPrint = computed(() => layout.value.calibrated && !geometryErrors.value.length &&
  (!warnings.value.length || acknowledged.value))
const fieldControls = [
  { key: 'x', label: 'X (mm)', min: 0, max: 400 }, { key: 'y', label: 'Y (mm)', min: 0, max: 600 },
  { key: 'width', label: 'Ancho (mm)', min: 1, max: 400 }, { key: 'height', label: 'Alto (mm)', min: 1, max: 30 },
  { key: 'font', label: 'Fuente (pt)', min: 5, max: 20 }, { key: 'step', label: 'Paso entre caracteres (mm; 0 = normal)', min: 0, max: 15 },
  { key: 'skip', label: 'Omitir caracteres iniciales (año preimpreso)', min: 0, max: 2 },
] as const

watch(() => [visible.value, props.snapshot] as const, ([open]) => {
  if (!open) return
  acknowledged.value = false
  localError.value = ''
}, { immediate: true })
try {
  const saved = localStorage.getItem(FUA_LAYOUT_KEY)
  if (saved) layout.value = parseFuaLayout(saved)
} catch { localError.value = 'No se pudo leer la calibración. Se usan posiciones de ejemplo.' }

function saveLayout(): void {
  try {
    localStorage.setItem(FUA_LAYOUT_KEY, JSON.stringify(parseFuaLayout(JSON.stringify(layout.value))))
    ElMessage.success('Calibración guardada en este navegador, sin datos del paciente.')
  } catch { localError.value = 'No se pudo guardar la calibración. Revise sus valores o el almacenamiento del navegador.' }
}
function changeGeometry(): void { layout.value.calibrated = false }
function loadBackground(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
    localError.value = 'Use un escaneo PNG, JPG o WebP de hasta 10 MB.'
    return
  }
  if (background.value) URL.revokeObjectURL(background.value)
  background.value = URL.createObjectURL(file)
}
function clearBackground(): void {
  if (background.value) URL.revokeObjectURL(background.value)
  background.value = ''
}
watch(visible, (open) => { if (!open) clearBackground() })
onBeforeUnmount(clearBackground)
async function print(test: boolean): Promise<void> {
  if (printing.value || (!test && !canPrint.value)) return
  localError.value = ''
  printing.value = true
  try { await printFua(layout.value, values.value, test) }
  catch (error) { localError.value = error instanceof Error ? error.message : 'No se pudo imprimir.' }
  finally { printing.value = false }
}
</script>

<template>
  <el-dialog v-model="visible" title="Imprimir S.I.S. · FUA preimpresa" width="min(1120px, 96vw)"
    top="3vh" :close-on-click-modal="false" destroy-on-close>
    <p class="fua-intro">Copia conservada al guardar la atención. Reimprimir no crea otra consulta.
      Solo se imprimen datos y marcas; el número del formulario preimpreso no se reemplaza.</p>
    <el-alert v-if="localError" :title="localError" type="error" :closable="false" />
    <el-tabs v-model="tab">
      <el-tab-pane label="Datos de la FUA" name="datos">
        <dl class="fua-summary">
          <div><dt>Personal que atiende</dt><dd>{{ snapshot.personal_atiende === 'IPRESS' ? 'De la IPRESS' : snapshot.personal_atiende || 'Sin registrar' }}</dd></div>
          <div><dt>Lugar de atención</dt><dd>{{ snapshot.lugar_atencion === 'INTRAMURAL' ? 'Intramural' : snapshot.lugar_atencion || 'Sin registrar' }}</dd></div>
          <div><dt>Atención en la FUA</dt><dd>{{ snapshot.tipo_atencion || 'Sin registrar' }} · según la modalidad guardada</dd></div>
          <div><dt>RENIPRESS</dt><dd>{{ snapshot.renipress_preimpreso !== false ? 'Ya viene impreso en la hoja; no se sobreimprime.' : snapshot.codigo_renipress || 'Sin registrar' }}</dd></div>
          <div><dt>Paciente</dt><dd>{{ snapshot.apellido_paterno }} {{ snapshot.apellido_materno }}, {{ snapshot.primer_nombre }} {{ snapshot.otros_nombres }}</dd></div>
          <div><dt>Afiliación SIS del paciente</dt><dd>{{ snapshot.sis_diresa || '—' }} · {{ values.sis_numero_completo || 'Sin registrar' }}</dd></div>
          <div><dt>Etnia declarada · código</dt><dd>{{ snapshot.etnia_codigo || 'Sin declarar' }}</dd></div>
          <div><dt>Identificación</dt><dd>{{ snapshot.tipo_documento }} {{ snapshot.numero_documento }} · TDI {{ snapshot.tdi || 'sin equivalencia' }}</dd></div>
          <div><dt>Atención</dt><dd>{{ snapshot.fecha_atencion }} · {{ snapshot.hora_atencion.slice(0, 5) }}</dd></div>
          <div><dt>Peso / talla / PA / IMC / PAB</dt><dd>{{ values.peso_kg || '—' }} kg / {{ values.talla_cm || '—' }} cm / {{ values.pa || '—' }} mmHg / {{ values.imc || '—' }} / {{ values.perimetro_abdominal_cm || '—' }} cm</dd></div>
        </dl>
        <p>La sede aporta personal y lugar; la ficha del paciente aporta afiliación y etnia. No necesita volver a seleccionarlos al imprimir.</p>
        <el-alert v-if="warnings.length" type="warning" title="Campos pendientes de revisar" :closable="false">
          <p>{{ warnings.join(' · ') }}</p>
        </el-alert>
        <el-checkbox v-if="warnings.length" v-model="acknowledged">Revisé los faltantes; completaré los que correspondan a mano.</el-checkbox>
        <p>No es una validación integral del SIS: prestaciones, diagnósticos, firmas, vacunas y otros campos quedan fuera de este prellenado.</p>
      </el-tab-pane>
      <el-tab-pane label="Vista previa y calibración" name="calibracion">
        <el-alert title="Posiciones iniciales orientativas: pruebe en papel en blanco antes de usar una FUA." type="warning" :closable="false" />
        <div class="fua-calibration">
          <div class="fua-controls">
            <el-form label-position="top" @change="changeGeometry">
              <el-form-item label="Ancho de la hoja (mm)"><el-input-number v-model="layout.width" :min="100" :max="400" :value-on-clear="216" @change="changeGeometry" /></el-form-item>
              <el-form-item label="Alto de la hoja (mm)"><el-input-number v-model="layout.height" :min="150" :max="600" :value-on-clear="356" @change="changeGeometry" /></el-form-item>
              <el-form-item label="Desplazamiento horizontal (mm)"><el-input-number v-model="layout.offsetX" :min="-50" :max="50" :step="0.5" :value-on-clear="0" @change="changeGeometry" /></el-form-item>
              <el-form-item label="Desplazamiento vertical (mm)"><el-input-number v-model="layout.offsetY" :min="-50" :max="50" :step="0.5" :value-on-clear="0" @change="changeGeometry" /></el-form-item>
              <el-form-item label="Campo a ajustar"><el-select v-model="selectedId"><el-option v-for="field in availableFields" :key="field.id" :value="field.id" :label="field.label" /></el-select></el-form-item>
              <el-checkbox v-model="selected.enabled" @change="changeGeometry">Imprimir este campo</el-checkbox>
              <el-form-item v-for="control in fieldControls" :key="control.key" :label="control.label">
                <el-input-number v-model="selected[control.key]" :min="control.min" :max="control.max" :step="control.key === 'skip' ? 1 : 0.5" :precision="control.key === 'skip' ? 0 : 2" :value-on-clear="control.min" @change="changeGeometry" />
              </el-form-item>
            </el-form>
            <label for="fua-scan">Escaneo vacío, solo como guía (no se imprime ni se sube)</label>
            <input id="fua-scan" type="file" accept="image/png,image/jpeg,image/webp" @change="loadBackground" />
            <el-button v-if="background" @click="clearBackground">Quitar guía</el-button>
          </div>
          <div class="fua-preview-scroll" aria-label="Vista previa de posiciones sobre la hoja">
            <div class="fua-preview" :style="{ width: `${layout.width}mm`, height: `${layout.height}mm` }">
              <img v-if="background" :src="background" alt="Escaneo de referencia; no se imprime" class="fua-background" />
              <button v-for="field in availableFields.filter(f => f.enabled)" :key="field.id" type="button"
                class="fua-position" :class="{ 'fua-position--selected': selectedId === field.id }"
                :aria-label="`Ajustar ${field.label}`" :title="field.label"
                :style="{ left: `${field.x + layout.offsetX}mm`, top: `${field.y + layout.offsetY}mm`, width: `${field.width}mm`, height: `${field.height}mm`, fontSize: `${field.font}pt` }"
                @click="selectedId = field.id">
                <template v-if="field.step && values[field.id]">
                  <span v-for="(char, index) in [...(values[field.id] || '').slice(field.skip)]" :key="index" :style="{ position: 'absolute', left: `${index * field.step}mm` }">{{ char }}</span>
                </template>
                <template v-else>{{ (values[field.id] || '').slice(field.skip) || '·' }}</template>
              </button>
            </div>
          </div>
        </div>
        <p>Imprima a tamaño real / 100 %, sin márgenes ni encabezados. Seleccione en el controlador el mismo tamaño de papel. La vista previa del navegador no verifica la impresora física.</p>
        <el-alert v-if="geometryErrors.length" title="Ajustes necesarios para imprimir" type="error" :closable="false">
          <ul><li v-for="message in geometryErrors" :key="message">{{ message }}</li></ul>
        </el-alert>
        <div class="fua-calibration-actions">
          <el-button :loading="printing" @click="print(true)">Imprimir prueba sin datos</el-button>
          <el-checkbox v-model="layout.calibrated">Comprobé tamaño y alineación en una prueba física.</el-checkbox>
          <el-button @click="saveLayout">Guardar calibración</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
    <template #footer>
      <div class="fua-footer">
        <span v-if="!canPrint">{{ !layout.calibrated || geometryErrors.length ? 'Revise la pestaña de calibración.' : 'Confirme los campos pendientes en Datos de la FUA.' }}</span>
        <el-button @click="visible = false">Cerrar</el-button>
        <el-button type="primary" :loading="printing" :disabled="!canPrint" @click="print(false)">Imprimir solo datos</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.fua-intro { margin-top: 0; }
.fua-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.fua-summary dt { font-weight: 600; color: var(--el-text-color-primary); }
.fua-summary dd { margin: 4px 0 0; overflow-wrap: anywhere; }
.fua-calibration { display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 20px; margin-top: 16px; }
.fua-controls { max-height: 60vh; overflow: auto; padding-right: 12px; }
.fua-controls input[type='file'] { max-width: 100%; margin: 8px 0; }
.fua-preview-scroll { max-height: 65vh; overflow: auto; background: var(--el-fill-color); padding: 12px; border: 1px solid var(--el-border-color); }
.fua-preview { position: relative; background: white; zoom: 0.7; }
.fua-background { position: absolute; width: 100%; height: 100%; object-fit: fill; }
.fua-position { position: absolute; margin: 0; padding: 0; border: 0; outline: 0.2mm dashed #677386; text-align: left; background: transparent; color: #111; font-family: 'Courier New', monospace; line-height: 1.2; white-space: nowrap; cursor: pointer; }
.fua-position--selected, .fua-position:focus-visible { outline: 0.6mm solid #1252a1; background: #e5f0ff; }
.fua-position:hover { background: #e5f0ff; }
.fua-footer, .fua-calibration-actions { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: 12px; }
.fua-footer span { margin-right: auto; }
@media (max-width: 700px) {
  .fua-summary, .fua-calibration { grid-template-columns: minmax(0, 1fr); }
  .fua-controls { max-height: none; }
  .fua-footer { align-items: stretch; }
  .fua-footer .el-button { margin: 0; }
}
</style>
