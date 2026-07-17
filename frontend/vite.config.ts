import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy requests to the FastAPI backend running on port 8000
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8080',
        ws: true,
      }
    }
  }
})
