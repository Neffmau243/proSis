import { mount } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import { defineComponent, ref } from 'vue'
import { expect, test } from 'vitest'

import PatientRegistrationFamilySections from '@/components/patients/PatientRegistrationFamilySections.vue'
import type {
  ResponsibleRow,
  RiskRow,
} from '@/components/patients/patientRegistration.types'

const Host = defineComponent({
  components: { PatientRegistrationFamilySections },
  setup() {
    const responsables = ref<ResponsibleRow[]>([])
    const riesgos = ref<RiskRow[]>([])
    const telefono = ref('')
    return { responsables, riesgos, telefono }
  },
  template: `
    <PatientRegistrationFamilySections
      v-model:responsables="responsables"
      v-model:riesgos="riesgos"
      v-model:telefono-principal="telefono"
      :grupos-riesgo="[]"
    />
  `,
})

async function mountFamily() {
  const wrapper = mount(Host, {
    global: { plugins: [ElementPlus], components: ElementPlusIconsVue },
  })
  await wrapper.vm.$nextTick()
  return wrapper
}

// El backend rechaza un par tipo/número desparejado. El formulario solo captura
// el DNI, así que el tipo debe seguir al número: nunca al revés.
test('un responsable sin número de documento no envía tipo de documento', async () => {
  const wrapper = await mountFamily()
  const state = wrapper.vm as unknown as { responsables: ResponsibleRow[] }
  const [nombre, dni] = wrapper.findAll('.family-section')[1]!.findAll('input')

  await nombre!.setValue('Juan Pérez')
  expect(state.responsables).toEqual([
    {
      parentesco: 'PADRE',
      nombre_completo: 'Juan Pérez',
      tipo_documento_codigo: null,
      numero_documento: null,
      telefono: null,
      es_principal: false,
    },
  ])

  await dni!.setValue('12345678')
  expect(state.responsables[0]).toMatchObject({
    tipo_documento_codigo: 'DNI',
    numero_documento: '12345678',
  })

  await dni!.setValue('')
  expect(state.responsables[0]).toMatchObject({
    tipo_documento_codigo: null,
    numero_documento: null,
  })
})
