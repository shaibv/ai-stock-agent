import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/status': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/logs': 'http://localhost:8000',
      '/run': 'http://localhost:8000',
      '/seed-db': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
  },
})
