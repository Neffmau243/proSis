import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// The test runner reuses the application alias but deliberately leaves the
// devtools plugin (and any HMR-only wiring) out of the test pipeline.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // Element Plus valida los formularios con `async-validator` y, al
      // resolver por condiciones de Node, el paquete cae en su build CJS cuyo
      // interop deja de ser un constructor: `validate()` entonces resuelve
      // ``true`` en silencio. Se fuerza el mismo build ESM que sirve el
      // navegador para que las pruebas ejerciten la validación real.
      'async-validator': 'async-validator/dist-web/index.js',
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
    restoreMocks: true,
    // Element Plus debe pasar por el resolvedor de Vite (y no por el de Node)
    // para recibir el build ESM de sus dependencias, igual que en el navegador.
    server: { deps: { inline: ['element-plus'] } },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/main.ts', 'src/types/**', 'src/**/*.d.ts'],
      // La lógica del cliente (utilidades, servicios, composables, store y
      // guardas de navegación) tiene un umbral alto porque un fallo ahí se
      // paga en pantalla. Las vistas de configuración todavía no lo alcanzan,
      // así que se exigen por glob y no en el total del proyecto.
      thresholds: {
        'src/utils/**': { statements: 95, branches: 90, functions: 90, lines: 95 },
        'src/services/**': { statements: 95, branches: 95, functions: 95, lines: 95 },
        'src/composables/**': { statements: 95, branches: 85, functions: 95, lines: 95 },
        'src/stores/**': { statements: 95, branches: 95, functions: 95, lines: 95 },
        'src/router/**': { statements: 65, branches: 90, functions: 45, lines: 65 },
        'src/layouts/**': { statements: 90, branches: 85, functions: 90, lines: 90 },
      },
    },
  },
})
