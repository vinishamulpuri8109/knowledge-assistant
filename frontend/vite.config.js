import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies /api to the FastAPI backend, so the browser sees one origin.
const BACKEND = process.env.VITE_BACKEND_URL || 'http://localhost:8010'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': BACKEND } },
})
