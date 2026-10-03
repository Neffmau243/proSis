// Dev-only: actual responses from patients created in the isolated audit DB.
// Does not access patient APIs, create attentions, or persist clinical data.
import { computed, createApp, h, shallowRef } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import '../src/assets/main.css'
import FuaPrintDialog from '../src/components/admission/FuaPrintDialog.vue'
import type { FuaPrintSnapshot } from '../src/types/fua'

type AuditCase = { attention_id: number; snapshot: FuaPrintSnapshot }
const response = await fetch('/tests/fixtures/fua-ethnicity-audit.json')
if (!response.ok) throw new Error('Primero ejecute la matriz de etnias en la base de pruebas.')
const cases: AuditCase[] = await response.json()
createApp({
  setup() {
    const selected = shallowRef(0)
    const visible = shallowRef(false)
    const current = computed(() => cases[selected.value]!)
    return () => h('main', [
      h('p', 'Pacientes ficticios guardados y recuperados en API/MySQL. Auditoría de impresión local.'),
      h('label', { for: 'audit-case' }, 'Caso guardado'),
      h('select', {
        id: 'audit-case', value: String(selected.value),
        onChange: (event: Event) => { selected.value = Number((event.target as HTMLSelectElement).value) },
      }, cases.map((entry, index) => h('option', { value: String(index) },
        `${entry.attention_id} · ${entry.snapshot.tipo_documento} · ${entry.snapshot.tipo_atencion} · ${entry.snapshot.grupo_atencion_codigo} · etnia ${entry.snapshot.etnia_codigo}`))),
      h('button', { onClick: () => { visible.value = true } }, 'Revisar FUA guardada'),
      h(FuaPrintDialog, { modelValue: visible.value, snapshot: current.value.snapshot,
        'onUpdate:modelValue': (value: boolean) => { visible.value = value },
      }),
    ])
  },
}).use(ElementPlus).mount('#app')
