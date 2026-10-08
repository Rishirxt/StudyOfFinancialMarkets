import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const { VITE_BACKEND_URL = 'http://127.0.0.1:8001' } = loadEnv(mode, process.cwd(), '')
  const backend = VITE_BACKEND_URL.replace(/\/$/, '')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
        },
        '/ws': {
          target: backend.replace(/^http/, 'ws'),
          ws: true,
          changeOrigin: true,
        },
      },
    },
  }
})
