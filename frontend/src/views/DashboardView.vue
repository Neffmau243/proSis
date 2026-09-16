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
      <el-button v-if="can('PACIENTE_EDITAR')" type="primary" @click="router.push({ name: 'paciente-nuevo' })">
        <el-icon><Plus /></el-icon>
        <span class="btn-label">Nuevo paciente</span>
      </el-button>
    </div>

    <el-card class="patient-table-card" shadow="never">
      <el-table
        class="patient-results-table"
        :data="rows"
        :height="tableHeight"
        size="small"
        v-loading="loading"
        row-key="id"
        highlight-current-row
        :current-row-key="seleccionado?.id"
        empty-text="Sin resultados"
        @scroll="onTableScroll"
        @row-click="onRowClick"
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

    </el-card>

    <DniSearchMatch :patient-name="dniPatientName" />

    <!-- Búsqueda: filtra mientras se escribe y conserva la tabla visible arriba. -->
    <el-card class="filters" shadow="never">
      <div class="filters__layout">
        <div class="filters__criteria" role="group" aria-label="Criterio de búsqueda">
          <div class="filters__modes">
            <el-checkbox
              v-for="option in modes"
              :key="option.value"
              :model-value="mode === option.value"
              :disabled="Boolean(option.pending)"
              @change="selectSearchMode(option.value)"
            >
              {{ option.label }}
            </el-checkbox>
          </div>
          <el-checkbox v-if="can('PACIENTE_DAR_BAJA')" v-model="incluirBajas">
            Incluir bajas
          </el-checkbox>
        </div>

        <div class="filters__search">
          <div class="filters__row">
            <el-input
              v-model="term"
              size="default"
              clearable
              :placeholder="placeholder"
              class="filters__input"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button size="default" :loading="loading" title="Refrescar" @click="refresh">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>

          <p class="filters__hint">
            <template v-if="loading">Buscando…</template>
            <template v-else-if="term.trim()">{{ resultHint }}</template>
            <template v-else>Escriba para filtrar; sin datos se muestra toda la base.</template>
          </p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { usePacienteSeleccionado } from '@/composables/usePacienteSeleccionado'
import DniSearchMatch from '@/components/patient/DniSearchMatch.vue'
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
const { seleccionado, dataVersion, seleccionar, notificarCambio } = usePacienteSeleccionado()

// Sin paginación visible, se solicita el máximo permitido y la tabla conserva su alto.
const listingLimit = 100
const tableHeight = 340
const tableRowHeight = 31
const total = ref(0)
const hasMore = ref(false)
const loadingMore = ref(false)
let queryVersion = 0

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

/** Solo se destaca una coincidencia de DNI exacta devuelta por el backend. */
const dniPatientName = computed<string | null>(() => {
  const dni = term.value.trim()
  if (mode.value !== 'dni' || !dni) return null

  const patient = rows.value.find((item) => item.numero_documento === dni)
  if (!patient) return null

  return fullName(patient) || null
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
function buildParams(offset = 0): PatientSearchParams | null {
  const value = term.value.trim()
  const base = {
    incluir_inactivos: incluirBajas.value,
    limit: listingLimit,
    offset,
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

async function search(requestVersion = ++queryVersion): Promise<void> {
  if (requestVersion !== queryVersion) return

  const params = buildParams()
  if (!params) {
    rows.value = []
    total.value = 0
    hasMore.value = false
    return
  }

  hasMore.value = false
  loadingMore.value = false
  loading.value = true
  try {
    const result = await pacientes.search(params)
    if (requestVersion !== queryVersion) return

    rows.value = result.items
    total.value = result.total
    hasMore.value = result.has_more
    // Búsqueda dinámica: si el filtro deja un único paciente, queda listo
    // para Modificar / Borrar sin tener que seleccionarlo a mano.
    const onlyMatch = result.items.length === 1 ? result.items[0] : undefined
    if (term.value.trim() && onlyMatch) {
      seleccionar(onlyMatch)
    }
  } catch (error) {
    if (requestVersion === queryVersion) {
      ElMessage.error(error instanceof Error ? error.message : 'No se pudo consultar la base de datos.')
    }
  } finally {
    if (requestVersion === queryVersion) loading.value = false
  }
}

async function loadMore(): Promise<void> {
  if (loading.value || loadingMore.value || !hasMore.value) return

  const requestVersion = queryVersion
  const params = buildParams(rows.value.length)
  if (!params) return

  loadingMore.value = true
  try {
    const result = await pacientes.search(params)
    if (requestVersion !== queryVersion) return

    const loadedIds = new Set(rows.value.map((patient) => patient.id))
    const nextRows = result.items.filter((patient) => !loadedIds.has(patient.id))
    rows.value = [...rows.value, ...nextRows]
    total.value = result.total
    hasMore.value = result.has_more && nextRows.length > 0
  } catch (error) {
    if (requestVersion === queryVersion) {
      ElMessage.error(error instanceof Error ? error.message : 'No se pudo cargar más pacientes.')
    }
  } finally {
    loadingMore.value = false
  }
}

function refresh(): void {
  search()
}

function onTableScroll({ scrollTop }: { scrollTop: number }): void {
  const remainingHeight = rows.value.length * tableRowHeight - (scrollTop + tableHeight)
  if (remainingHeight <= tableRowHeight * 6) void loadMore()
}

/** La interfaz usa checkboxes, pero cada búsqueda admite un solo criterio. */
function selectSearchMode(searchMode: SearchMode): void {
  mode.value = searchMode
}

// Filtrado en vivo con un pequeño retardo para no golpear el backend en cada tecla.
let debounce: ReturnType<typeof setTimeout> | undefined
watch([term, mode, incluirBajas], () => {
  const requestVersion = ++queryVersion
  if (debounce) clearTimeout(debounce)
  debounce = setTimeout(() => search(requestVersion), 280)
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
    search()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'No se pudo dar de baja.')
  }
}

// La barra lateral puede dar de baja al paciente seleccionado: la tabla recarga.
watch(dataVersion, () => search())

onBeforeUnmount(() => {
  if (debounce) clearTimeout(debounce)
})

onMounted(async () => {
  try {
    sexos.value = await catalogos.sexos()
  } catch {
    // Sin catálogo de sexos solo se muestra el código; no bloquea la tabla.
  }
  search()
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.page-header h2 {
  margin: 0 0 2px;
  font-size: 20px;
  line-height: 1.2;
}

.page-header__sub {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.patient-table-card :deep(.el-card__body) {
  padding: 12px;
}

.filters {
  margin-top: 8px;
  border-radius: 12px;
}

.filters :deep(.el-card__body) {
  padding: 10px 12px;
}

.filters__layout {
  display: grid;
  grid-template-columns: minmax(180px, 0.3fr) minmax(0, 0.7fr);
  gap: 12px;
  align-items: stretch;
}

.filters__criteria {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding-right: 12px;
  border-right: 1px solid var(--el-border-color-lighter);
}

.filters__modes {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
  gap: 2px;
}

.filters__modes :deep(.el-checkbox) {
  height: 24px;
  line-height: 24px;
  margin-right: 0;
}

.filters__criteria > :deep(.el-checkbox) {
  height: 24px;
  line-height: 24px;
}

.filters__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filters__search {
  align-self: center;
  min-width: 0;
}

.filters__input {
  flex: 1;
  min-width: 0;
}

.filters__hint {
  margin: 4px 2px 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 680px) {
  .filters__layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  .filters__criteria {
    padding-right: 0;
    padding-bottom: 10px;
    border-right: 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .filters__search {
    align-self: stretch;
  }

  .filters__modes {
    flex-direction: row;
    gap: 4px 10px;
  }
}

.mono {
  font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', monospace;
  letter-spacing: 0.01em;
}

.patient-results-table :deep(.el-table__header-wrapper th.el-table__cell) {
  padding: 5px 0;
  font-size: 12px;
  white-space: nowrap;
}

.patient-results-table :deep(.el-table__body td.el-table__cell) {
  padding: 4px 0;
}

.patient-results-table :deep(.el-table__body .cell) {
  overflow: hidden;
  font-size: 13px;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.patient-results-table :deep(.el-table-fixed-column--right .cell) {
  white-space: nowrap;
}

.btn-label {
  margin-left: 6px;
}
</style>
