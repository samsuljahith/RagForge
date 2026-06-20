import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../ragforge/ui_static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true, rewrite: p => p.replace(/^\/api/, '') },
      '/health': 'http://localhost:8000',
      '/traces': 'http://localhost:8000',
      '/ui': 'http://localhost:8000',
    },
  },
})
