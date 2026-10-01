<template>
  <div>
    <div class="page-header">
      <h2>Consultorios</h2>
      <el-button @click="router.back()">Volver</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card>
      <div class="toolbar">
        <div class="toolbar-filters">
          <el-select
            v-model="filtroEstablecimiento"
            clearable
            filterable
            remote
            :remote-method="searchEstablishments"
            :loading="establishmentsLoading"
            placeholder="Filtrar por establecimiento"
            class="establishment-filter"
          >
            <el-option
              v-for="item in establishments"
              :key="item.id"
              :label="item.nombre"
              :value="item.id"
            />
          </el-select>
          <el-switch v-model="incluirInactivos" active-text="Incluir inactivos" />
        </div>
        <el-button type="primary" @click="openCreate">Nuevo consultorio</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        empty-text="Sin consultorios registrados"
        class="offices-table"
      >
        <el-table-column prop="codigo" label="Código" width="130" show-overflow-tooltip />
        <el-table-column prop="nombre" label="Nombre" min-width="180" show-overflow-tooltip />
        <el-table-column label="Establecimiento" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ establecimientoNombre(row.establecimiento_id) }}</template>
        </el-table-column>
        <el-table-column label="Especialidad" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ especialidadNombre(row.especialidad_codigo) }}</template>
        </el-table-column>
        <el-table-column label="Consultorio padre" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ consultorioPadreNombre(row.consultorio_padre_id) }}</template>
        </el-table-column>
        <el-table-column label="Estado" width="100">
          <template #default="{ row }">
            <el-tag :type="row.activo ? 'success' : 'danger'" size="small">
              {{ row.activo ? 'Activo' : 'Inactivo' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Acciones" min-width="240">
          <template #default="{ row }">
            <div class="actions-cell">
              <el-button link type="primary" @click="openEdit(row)">Editar</el-button>
              <el-button link type="primary" @click="openAssignments(row)">Asignaciones</el-button>
              <el-button link type="primary" :disabled="!row.activo" @click="deactivate(row)">
                Dar de baja
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Alta / edición de la ficha -->
    <el-dialog v-model="formVisible" :title="formTitle" width="560px">
      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
        class="form-alert"
      />
      <el-form ref="formRef" :model="form" :rules="rules" label-width="160px">
        <el-form-item label="Establecimiento" prop="establecimiento_id">
          <el-select
            v-model="form.establecimiento_id"
            filterable
            remote
            :remote-method="searchEstablishments"
            :loading="establishmentsLoading"
            :disabled="editingId !== null"
            placeholder="Seleccione un establecimiento"
            style="width: 100%"
          >
            <el-option
              v-for="item in establishments"
              :key="item.id"
              :label="item.nombre"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Código" prop="codigo">
          <el-input v-model="form.codigo" maxlength="30" />
        </el-form-item>
        <el-form-item label="Nombre" prop="nombre">
          <el-input v-model="form.nombre" maxlength="150" />
        </el-form-item>
        <el-form-item label="Especialidad" prop="especialidad_codigo">
          <el-select
            v-model="form.especialidad_codigo"
            clearable
            filterable
            placeholder="Sin especialidad"
            style="width: 100%"
          >
            <el-option
              v-for="item in especialidades"
              :key="item.codigo"
              :label="item.nombre"
              :value="item.codigo"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Consultorio padre" prop="consultorio_padre_id">
          <el-select
            v-model="form.consultorio_padre_id"
            clearable
            filterable
            placeholder="Sin padre"
            style="width: 100%"
          >
            <el-option
              v-for="item in parentOptions"
              :key="item.id"
              :label="`${item.codigo} — ${item.nombre}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">Guardar</el-button>
      </template>
    </el-dialog>

    <!-- Asignaciones del consultorio -->
    <el-dialog v-model="assignmentsVisible" :title="assignmentsTitle" width="820px">
      <el-alert
        v-if="assignmentsError"
        :title="assignmentsError"
        type="error"
        :closable="false"
        class="form-alert"
      />
      <p class="dialog-hint">
        La asignación vincula al profesional con el consultorio para la atención clínica. La tabla se
        muestra aunque esté vacía: significa que todavía no hay asignaciones históricas, no un error.
      </p>

      <div class="toolbar">
        <el-button type="primary" @click="openAssignForm">Asignar profesional</el-button>
        <el-button @click="loadAssignments">Recargar</el-button>
      </div>

      <el-table
        v-loading="assignmentsLoading"
        :data="assignments"
        empty-text="Sin asignaciones registradas"
      >
        <el-table-column label="Profesional" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ profesionalNombre(row.profesional_id) }}</template>
        </el-table-column>
        <el-table-column prop="fecha_inicio" label="Inicio" width="120" />
        <el-table-column label="Fin" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.fecha_fin === null" type="success" size="small">Vigente</el-tag>
            <span v-else>{{ row.fecha_fin }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Responsable" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.es_responsable" type="primary" size="small">Sí</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="Acciones" width="110">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              :disabled="row.fecha_fin !== null"
              @click="openClose(row)"
            >
              Cerrar
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-form
        v-if="assignFormVisible"
        ref="assignRef"
        :model="assignForm"
        :rules="assignRules"
        label-width="150px"
        class="assign-form"
      >
        <el-form-item label="Profesional" prop="profesional_id">
          <el-select
            v-model="assignForm.profesional_id"
            filterable
            remote
            :remote-method="searchProfesionales"
            :loading="professionalsLoading"
            placeholder="Busque por nombre o colegiatura"
            style="width: 100%"
          >
            <el-option
              v-for="item in professionalOptions"
              :key="item.id"
              :label="item.nombre_completo"
              :value="item.id"
            />
          </el-select>
          <div class="hint">El consultorio exige que el profesional tenga su especialidad.</div>
        </el-form-item>
        <el-form-item label="Fecha de inicio" prop="fecha_inicio">
          <el-date-picker
            v-model="assignForm.fecha_inicio"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Fecha de fin" prop="fecha_fin">
          <el-date-picker
            v-model="assignForm.fecha_fin"
            type="date"
            value-format="YYYY-MM-DD"
            clearable
            placeholder="Opcional"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Responsable">
          <el-checkbox v-model="assignForm.es_responsable">
            Es responsable del consultorio
          </el-checkbox>
        </el-form-item>
        <div class="form-actions">
          <el-button type="primary" :loading="savingAssignment" @click="submitAssignment">
            Guardar asignación
          </el-button>
          <el-button @click="assignFormVisible = false">Cancelar</el-button>
        </div>
      </el-form>
    </el-dialog>

    <!-- Cierre de asignación -->
    <el-dialog v-model="closeVisible" title="Cerrar asignación" width="460px">
      <el-alert
        v-if="closeError"
        :title="closeError"
        type="error"
        :closable="false"
        class="form-alert"
      />
      <p class="dialog-hint">
        Se cierra la asignación de
        <strong>{{ closeTarget ? profesionalNombre(closeTarget.profesional_id) : '' }}</strong>
        (inicio {{ closeTarget?.fecha_inicio }}). El cierre no puede ampliar una vigencia ya definida.
      </p>
      <el-form label-width="130px">
        <el-form-item label="Fecha de fin" required>
          <el-date-picker
            v-model="closeForm.fecha_fin"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeVisible = false">Cancelar</el-button>
        <el-button type="primary" :loading="savingClose" @click="submitClose">
          Cerrar asignación
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

import {
  catalogos,
  type EstablishmentCatalogItem,
  type OfficeCatalogItem,
  type ProfessionalCatalogItem,
  type SpecialtyCatalogItem,
} from '@/services/catalogos'
import {
  consultorios,
  type OfficeAssignmentResponse,
  type OfficeResponse,
} from '@/services/consultorios'

const router = useRouter()

// --- Catálogos de apoyo (nombres y selects) ---
const establishments = ref<EstablishmentCatalogItem[]>([])
const establishmentsLoading = ref(false)
const especialidades = ref<SpecialtyCatalogItem[]>([])
const parentOptions = ref<OfficeCatalogItem[]>([])
const professionalOptions = ref<ProfessionalCatalogItem[]>([])
const professionalsLoading = ref(false)
/** Nombres conocidos de profesionales, para resolver las asignaciones listadas. */
const professionalDirectory = ref<Record<number, string>>({})

function mergeEstablishments(items: EstablishmentCatalogItem[]): void {
  const known = new Map(establishments.value.map((item) => [item.id, item]))
  for (const item of items) known.set(item.id, item)
  establishments.value = [...known.values()]
}

async function searchEstablishments(query: string): Promise<void> {
  establishmentsLoading.value = true
  try {
    const page = await catalogos.establecimientos(query || undefined, 100, 0)
    mergeEstablishments(page.items)
  } catch {
    // El catálogo solo enriquece los selects; la vista sigue siendo útil sin él.
  } finally {
    establishmentsLoading.value = false
  }
}

async function searchProfesionales(query: string): Promise<void> {
  professionalsLoading.value = true
  try {
    const page = await catalogos.profesionales(query || undefined, 25, 0)
    professionalOptions.value = page.items
    for (const item of page.items) {
      professionalDirectory.value[item.id] = item.nombre_completo
    }
  } finally {
    professionalsLoading.value = false
  }
}

function establecimientoNombre(id: number): string {
  return establishments.value.find((item) => item.id === id)?.nombre ?? `Sede #${id}`
}

function especialidadNombre(codigo: string | null): string {
  if (codigo === null) return '—'
  return especialidades.value.find((item) => item.codigo === codigo)?.nombre ?? codigo
}

function consultorioPadreNombre(id: number | null): string {
  if (id === null) return '—'
  return rows.value.find((item) => item.id === id)?.nombre ?? `Consultorio #${id}`
}

function profesionalNombre(id: number): string {
  return professionalDirectory.value[id] ?? `Profesional #${id}`
}

// --- Lista de consultorios ---
const rows = ref<OfficeResponse[]>([])
const loading = ref(false)
const errorMessage = ref<string | null>(null)
const incluirInactivos = ref(false)
const filtroEstablecimiento = ref<number | null>(null)

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = null
  try {
    rows.value = await consultorios.list({
      establecimientoId: filtroEstablecimiento.value ?? undefined,
      incluirInactivos: incluirInactivos.value,
    })
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo cargar la lista de consultorios.'
  } finally {
    loading.value = false
  }
}

watch([incluirInactivos, filtroEstablecimiento], load)

// --- Alta / edición ---
const formRef = ref<FormInstance>()
const formVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formError = ref<string | null>(null)
const form = reactive({
  establecimiento_id: null as number | null,
  codigo: '',
  nombre: '',
  especialidad_codigo: null as string | null,
  consultorio_padre_id: null as number | null,
})

const rules: FormRules = {
  establecimiento_id: [
    { required: true, message: 'Seleccione el establecimiento.', trigger: 'change' },
  ],
  codigo: [{ required: true, message: 'Ingrese el código.', trigger: 'blur' }],
  nombre: [
    { required: true, message: 'Ingrese el nombre.', trigger: 'blur' },
    { min: 2, message: 'Mínimo 2 caracteres.', trigger: 'blur' },
  ],
}

const formTitle = computed(() =>
  editingId.value === null ? 'Nuevo consultorio' : 'Editar consultorio',
)

async function loadParentOptions(): Promise<void> {
  const establishmentId = form.establecimiento_id
  parentOptions.value = []
  if (establishmentId === null) return
  try {
    const page = await catalogos.consultorios(establishmentId, undefined, 100, 0)
    // Un consultorio no puede ser su propio padre.
    parentOptions.value = page.items.filter((item) => item.id !== editingId.value)
  } catch {
    parentOptions.value = []
  }
}

watch(() => form.establecimiento_id, loadParentOptions)

function openCreate(): void {
  editingId.value = null
  form.establecimiento_id = filtroEstablecimiento.value ?? null
  form.codigo = ''
  form.nombre = ''
  form.especialidad_codigo = null
  form.consultorio_padre_id = null
  formError.value = null
  formRef.value?.clearValidate()
  formVisible.value = true
  loadParentOptions()
}

function openEdit(row: OfficeResponse): void {
  editingId.value = row.id
  form.establecimiento_id = row.establecimiento_id
  form.codigo = row.codigo
  form.nombre = row.nombre
  form.especialidad_codigo = row.especialidad_codigo
  form.consultorio_padre_id = row.consultorio_padre_id
  formError.value = null
  formRef.value?.clearValidate()
  formVisible.value = true
  loadParentOptions()
}

async function submitForm(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  formError.value = null
  try {
    if (editingId.value === null) {
      await consultorios.create({
        establecimiento_id: form.establecimiento_id as number,
        codigo: form.codigo.trim(),
        nombre: form.nombre.trim(),
        consultorio_padre_id: form.consultorio_padre_id,
        especialidad_codigo: form.especialidad_codigo,
      })
      ElMessage.success('Consultorio creado.')
      formVisible.value = false
    } else {
      await consultorios.update(editingId.value, {
        codigo: form.codigo.trim(),
        nombre: form.nombre.trim(),
        consultorio_padre_id: form.consultorio_padre_id,
        especialidad_codigo: form.especialidad_codigo,
      })
      ElMessage.success('Consultorio actualizado.')
      formVisible.value = false
    }
    await load()
  } catch (error) {
    formError.value =
      error instanceof Error ? error.message : 'No se pudo guardar el consultorio.'
  } finally {
    saving.value = false
  }
}

async function deactivate(row: OfficeResponse): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `Se dará de baja el consultorio ${row.nombre}. La baja es lógica: el consultorio y sus asignaciones históricas se conservan.`,
      'Dar de baja consultorio',
      { type: 'info', confirmButtonText: 'Dar de baja', cancelButtonText: 'Cancelar' },
    )
  } catch {
    return
  }
  errorMessage.value = null
  try {
    await consultorios.deactivate(row.id)
    ElMessage.success('Consultorio dado de baja.')
    await load()
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo dar de baja el consultorio.'
  }
}

// --- Asignaciones de profesionales ---
const assignmentsVisible = ref(false)
const officeTarget = ref<OfficeResponse | null>(null)
const assignments = ref<OfficeAssignmentResponse[]>([])
const assignmentsLoading = ref(false)
const assignmentsError = ref<string | null>(null)
const assignFormVisible = ref(false)
const savingAssignment = ref(false)
const assignRef = ref<FormInstance>()
const assignForm = reactive({
  profesional_id: null as number | null,
  fecha_inicio: '',
  fecha_fin: '',
  es_responsable: false,
})

const assignRules: FormRules = {
  profesional_id: [{ required: true, message: 'Seleccione el profesional.', trigger: 'change' }],
  fecha_inicio: [{ required: true, message: 'Indique la fecha de inicio.', trigger: 'change' }],
}

const assignmentsTitle = computed(() =>
  officeTarget.value ? `Profesionales · ${officeTarget.value.nombre}` : 'Profesionales',
)

function openAssignments(row: OfficeResponse): void {
  officeTarget.value = row
  assignmentsError.value = null
  assignFormVisible.value = false
  assignmentsVisible.value = true
  loadAssignments()
}

async function loadAssignments(): Promise<void> {
  const office = officeTarget.value
  if (!office) return
  assignmentsLoading.value = true
  assignmentsError.value = null
  try {
    assignments.value = await consultorios.listAssignments(office.id)
  } catch (error) {
    assignmentsError.value =
      error instanceof Error ? error.message : 'No se pudieron cargar las asignaciones.'
  } finally {
    assignmentsLoading.value = false
  }
}

function openAssignForm(): void {
  assignForm.profesional_id = null
  assignForm.fecha_inicio = ''
  assignForm.fecha_fin = ''
  assignForm.es_responsable = false
  assignRef.value?.clearValidate()
  assignFormVisible.value = true
}

async function submitAssignment(): Promise<void> {
  if (!officeTarget.value) return
  const valid = await assignRef.value?.validate().catch(() => false)
  if (!valid) return

  const professionalId = assignForm.profesional_id
  const fechaInicio = assignForm.fecha_inicio
  if (professionalId === null || !fechaInicio) return
  if (assignForm.fecha_fin && assignForm.fecha_fin < fechaInicio) {
    assignmentsError.value = 'La fecha de fin no puede ser anterior a la fecha de inicio.'
    return
  }

  savingAssignment.value = true
  assignmentsError.value = null
  try {
    await consultorios.assign(officeTarget.value.id, {
      profesional_id: professionalId,
      fecha_inicio: fechaInicio,
      fecha_fin: assignForm.fecha_fin === '' ? null : assignForm.fecha_fin,
      es_responsable: assignForm.es_responsable,
    })
    ElMessage.success('Profesional asignado.')
    assignFormVisible.value = false
    await loadAssignments()
  } catch (error) {
    assignmentsError.value =
      error instanceof Error ? error.message : 'No se pudo asignar el profesional.'
  } finally {
    savingAssignment.value = false
  }
}

const closeVisible = ref(false)
const closeTarget = ref<OfficeAssignmentResponse | null>(null)
const closeError = ref<string | null>(null)
const savingClose = ref(false)
const closeForm = reactive({ fecha_fin: '' })

function openClose(row: OfficeAssignmentResponse): void {
  closeTarget.value = row
  closeForm.fecha_fin = ''
  closeError.value = null
  closeVisible.value = true
}

async function submitClose(): Promise<void> {
  const office = officeTarget.value
  const target = closeTarget.value
  if (!office || !target) return
  if (!closeForm.fecha_fin) {
    closeError.value = 'Indique la fecha de fin.'
    return
  }
  if (closeForm.fecha_fin < target.fecha_inicio) {
    closeError.value = 'La fecha de fin no puede ser anterior a la fecha de inicio.'
    return
  }

  savingClose.value = true
  closeError.value = null
  try {
    await consultorios.closeAssignment(
      office.id,
      target.profesional_id,
      target.fecha_inicio,
      closeForm.fecha_fin,
    )
    ElMessage.success('Asignación cerrada.')
    closeVisible.value = false
    await loadAssignments()
  } catch (error) {
    closeError.value =
      error instanceof Error ? error.message : 'No se pudo cerrar la asignación.'
  } finally {
    savingClose.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    load(),
    searchEstablishments(''),
    catalogos
      .especialidades()
      .then((items) => {
        especialidades.value = items
      })
      .catch(() => undefined),
    catalogos
      .profesionales(undefined, 100, 0)
      .then((page) => {
        for (const item of page.items) {
          professionalDirectory.value[item.id] = item.nombre_completo
        }
      })
      .catch(() => undefined),
  ])
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.form-alert {
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.establishment-filter {
  width: 280px;
}

/* Las celdas contienen los valores sin desbordar la columna. */
.offices-table :deep(.cell) {
  word-break: normal;
  overflow-wrap: anywhere;
}

.actions-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 10px;
}

.actions-cell :deep(.el-button + .el-button) {
  margin-left: 0;
}

.dialog-hint {
  margin-top: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.assign-form {
  margin-top: 16px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-left: 150px;
}
</style>
