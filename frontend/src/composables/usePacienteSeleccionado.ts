import { ref } from 'vue'

import type { Patient } from '@/services/pacientes'

/**
 * Paciente "activo" del flujo legacy: la barra lateral ejecuta Ver / Modificar
 * datos / Borrar paciente sobre la fila seleccionada en la tabla Base de datos.
 *
 * Es estado singleton a nivel de módulo: la tabla lo escribe y la barra lateral
 * lo lee sin prop drilling ni acoplar los componentes.
 */
const seleccionado = ref<Patient | null>(null)
/** Se incrementa tras un alta o baja para que la tabla vuelva a consultar. */
const dataVersion = ref(0)

export function usePacienteSeleccionado() {
  function seleccionar(patient: Patient | null): void {
    seleccionado.value = patient
  }

  function notificarCambio(): void {
    dataVersion.value += 1
  }

  return { seleccionado, dataVersion, seleccionar, notificarCambio }
}
