import { mergeConfig } from 'vite'
import baseConfig from '../vite.config.ts'

// Real application and API; no mocked requests. Keep localhost:5173 untouched.
export default mergeConfig(baseConfig, {
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true },
    },
  },
})
