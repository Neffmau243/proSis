<template>
  <div class="base-datos">
    <div class="page-header">
      <div>
        <h2>Base de datos</h2>
        <p class="page-header__sub">
          {{ total }} paciente(s) registrado(s)
          <span v-if="seleccionado">· {{ fullName(seleccionado) }} seleccionado</span>
        </p>
      </div>
      <el-button v-if="can('PACIENTE_EDITAR')" type="primary" size="large" @click="router.push({ name: 'paciente-nuevo' })">
        <el-icon><Plus /></el-icon>
        <span class="btn-label">Nuevo paciente</span>
      </el-button>
    </div>

    <!-- Búsqueda: filtra mientras se escribe -->
    <el-card class="filters" shadow="never">
      <el-radio-group v-model="mode" class="filters__modes">
        <el-radio-button
          v-for="option in modes"
          :key="option.value"
          :value="option.value"
          :disabled="Boolean(option.pending)"
        >
          {{ option.label }}
        </el-radio-button>
      </el-radio-group>

      <div class="filters__row">
        <el-input
          v-model="term"
          size="large"
          clearable
          :placeholder="placeholder"
          class="filters__input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button size="large" :loading="loading" title="Refrescar" @click="refresh">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-checkbox v-if="can('PACIENTE_DAR_BAJA')" v-model="incluirBajas">
          Incluir bajas
        </el-checkbox>
      </div>

      <p class="filters__hint">
        <template v-if="loading">Buscando…</template>
        <template v-else-if="term.trim()">{{ resultHint }}</template>
        <template v-else>Escriba para filtrar; sin datos se muestra toda la base.</template>
      </p>
    </el-card>

    <el-card shadow="never">
      <el-table
        :data="rows"
        v-loading="loading"
        row-key="id"
        highlight-current-row
        :current-row-key="seleccionado?.id"
        empty-text="Sin resultados"
        @row-click="onRowClick"
        @row-dblclick="ver"
      >
        <el-table-column label="N° Historia" min-width="130">
          <template #default="{ row }">{{ row.historia_clinica || '—' }}</template>
        </el-table-column>
        <el-table-column label="H. Familiar" min-width="110">
          <template #default="{ row }">{{ row.historia_familiar || '—' }}</template>
        </el-table-column>
        <el-table-column label="N° DNI" min-width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.numero_documento }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="apellido_paterno" label="Apellido paterno" min-width="140" />
        <el-table-column prop="apellido_materno" label="Apellido materno" min-width="140" />
        <el-table-column prop="primer_nombre" label="Primer nombre" min-width="130" />
        <el-table-column prop="otros_nombres" label="Otros nombres" min-width="130" />
        <el-table-column label="Sexo" width="100">
          <template #default="{ row }">{{ sexLabel(row.sexo_codigo) }}</template>
        </el-table-column>
        <el-table-column label="Disi" width="90" align="center">
          <template #header>
            <el-tooltip
              content="Indicador administrativo: ALT = activo, BAJA = inactivo"
              placement="top"
            >
              <span>Disi</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-tag :type="row.estado ? 'success' : 'info'" size="small">
              {{ row.estado ? 'ALT' : 'BAJA' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Acciones" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="ver(row)">Ver</el-button>
            <el-button
              v-if="can('PACIENTE_EDITAR')"
              link
              type="primary"
              @click.stop="editar(row)"
            >
              Modificar
            </el-button>
            <el-button
              v-if="can('PACIENTE_DAR_BAJA') && row.estado"
              link
              type="danger"
              @click.stop="confirmDeactivate(row)"
            >
              Borrar
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        layout="total, prev, pager, next, sizes"
        :total="total"
        :page-size="limit"
        :current-page="currentPage"
        :page-sizes="[25, 50, 100]"
        @current-change="(page: number) => search(page)"
        @size-change="(size: number) => { changeLimit(size); search(1) }"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { usePagination } from '@/composables/usePagination'
import { usePacienteSeleccionado } from '@/composables/usePacienteSeleccionado'
import { useAuthStore } from '@/stores/auth'
import { catalogos, type CodeCatalogItem } from '@/services/catalogos'
import { pacientes, type Patient, type PatientSearchParams } from '@/services/pacientes'

type SearchMode = 'dni' | 'hc_exacta' | 'hc_similar' | 'h_familiar' | 'nombres'

interface SearchModeOption {
  value: SearchMode
  label: string
  placeholder: string
  /** Modalidad del sistema antiguo que el backend todavía no filtra. */
  pending?: string
}

const router = useRouter()
const auth = useAuthStore()
const { limit, total, currentPage, applyPage, goToPage, changeLimit } = usePagination()
const { seleccionado, dataVersion, seleccionar, notificarCambio } = usePacienteSeleccionado()

// El DNI es el dato que más se usa: es la modalidad por defecto.
const modes: SearchModeOption[] = [
  { value: 'dni', label: 'DNI', placeholder: 'Escriba el número de DNI…' },
  {
    value: 'hc_exacta',
    label: 'H. Clínica exacta',
    placeholder: 'N° de historia clínica completo',
  },
  {
    value: 'hc_similar',
    label: 'H. Clínica similar',
    placeholder: 'Parte del N° de historia clínica',
  },
  { value: 'nombres', label: 'Apellidos y nombres', placeholder: 'Apellidos o nombres' },
  {
    value: 'h_familiar',
    label: 'H. Familiar',
    placeholder: 'Código de historia familiar',
    pending: 'Pendiente: el backend aún no filtra por historia familiar.',
  },
]

const mode = ref<SearchMode>('dni')
const term = ref('')
const incluirBajas = ref(false)
const rows = ref<Patient[]>([])
const loading = ref(false)
const sexos = ref<CodeCatalogItem[]>([])

const placeholder = computed(
  () => modes.find((option) => option.value === mode.value)?.placeholder ?? '',
)

const resultHint = computed(() => {
  if (total.value === 0) return 'Sin coincidencias.'
  if (total.value === 1) return '1 coincidencia · paciente seleccionado.'
  return `${total.value} coincidencias.`
})

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

function fullName(patient: Patient): string {
  return [
    patient.apellido_paterno,
    patient.apellido_materno,
    patient.primer_nombre,
    patient.otros_nombres,
  ]
    .filter(Boolean)
    .join(' ')
}

function sexLabel(codigo: string | null): string {
  return sexos.value.find((sexo) => sexo.codigo === codigo)?.nombre ?? (codigo ?? '—')
}

/** Traduce la modalidad elegida a los filtros que acepta el backend. */
function buildParams(): PatientSearchParams | null {
  const value = term.value.trim()
  const base = {
    incluir_inactivos: incluirBajas.value,
    limit: limit.value,
    offset: (currentPage.value - 1) * limit.value,
  }

  if (mode.value === 'h_familiar') {
    ElMessage.info('La búsqueda por H. Familiar se habilitará cuando el backend la soporte.')
    return null
  }

  // Sin dato: se lista toda la base, como al abrir la tabla en el sistema antiguo.
  if (!value) return { ...base }

  switch (mode.value) {
    case 'hc_exacta':
      return { ...base, historia_clinica: value }
    // El backend solo ofrece coincidencia parcial con `q` (DNI, historia
    // clínica y nombres); se usa para DNI, "dato similar" y apellidos. Con
    // menos de 2 caracteres no filtra y se sigue mostrando toda la base.
    case 'dni':
    case 'hc_similar':
    case 'nombres':
      if (value.length < 2) return { ...base }
      return { ...base, q: value }
  }
}

async function search(page: number): Promise<void> {
  goToPage(page)
  const params = buildParams()
  if (!params) return

  loading.value = true
  try {
    const result = await pacientes.search(params)
    rows.value = result.items
    applyPage(result)
    // Búsqueda dinámica: si el filtro deja un único paciente, queda listo
    // para Modificar / Borrar sin tener que seleccionarlo a mano.
    const onlyMatch = result.items.length === 1 ? result.items[0] : undefined
    if (term.value.trim() && onlyMatch) {
      seleccionar(onlyMatch)
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'No se pudo consultar la base de datos.')
  } finally {
    loading.value = false
  }
}

function refresh(): void {
  search(currentPage.value)
}

// Filtrado en vivo con un pequeño retardo para no golpear el backend en cada tecla.
let debounce: ReturnType<typeof setTimeout> | undefined
watch([term, mode, incluirBajas], () => {
  if (debounce) clearTimeout(debounce)
  debounce = setTimeout(() => search(1), 280)
})

function onRowClick(row: Patient): void {
  seleccionar(row)
}

function ver(row: Patient): void {
  seleccionar(row)
  router.push({ name: 'paciente-detalle', params: { id: row.id } })
}

function editar(row: Patient): void {
  seleccionar(row)
  router.push({ name: 'paciente-editar', params: { id: row.id } })
}

async function confirmDeactivate(patient: Patient): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `¿Dar de baja a ${fullName(patient)}? La baja es lógica: el historial se conserva.`,
      'Borrar paciente',
      { type: 'warning', confirmButtonText: 'Dar de baja', cancelButtonText: 'Cancelar' },
    )
  } catch {
    return
  }
  try {
    const result = await pacientes.deactivate(patient.id)
    ElMessage.success(result.mensaje)
    seleccionar(null)
    notificarCambio()
    search(currentPage.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'No se pudo dar de baja.')
  }
}

// La barra lateral puede dar de baja al paciente seleccionado: la tabla recarga.
watch(dataVersion, () => search(currentPage.value))

onBeforeUnmount(() => {
  if (debounce) clearTimeout(debounce)
})

onMounted(async () => {
  try {
    sexos.value = await catalogos.sexos()
  } catch {
    // Sin catálogo de sexos solo se muestra el código; no bloquea la tabla.
  }
  search(1)
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0 0 4px;
}

.page-header__sub {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.filters {
  margin-bottom: 16px;
  border-radius: 12px;
}

.filters__modes {
  margin-bottom: 12px;
}

.filters__row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filters__input {
  flex: 1;
  min-width: 280px;
}

.filters__hint {
  margin: 10px 2px 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.mono {
  font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', monospace;
  letter-spacing: 0.01em;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.btn-label {
  margin-left: 6px;
}
</style>
