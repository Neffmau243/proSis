import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// El CSS de Element Plus se carga antes que el propio: los tokens de
// main.css (texto en negro) tienen que quedar después para poder sobrescribir
// los valores por defecto de la librería.
import 'element-plus/dist/index.css'
import './assets/main.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// Registra todos los iconos de Element Plus como componentes globales
// (User, Plus, Document, ArrowDown, ...). Importación on-demand puede
// agregarse después si el bundle crece.
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')