import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const backendUrl = `http://localhost:${process.env.VITE_BACKEND_PORT || '5000'}`

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: parseInt(process.env.VITE_FRONTEND_PORT || '5173'),
    proxy: {
      '/api': { target: backendUrl, changeOrigin: true },
      '/audio': { target: backendUrl, changeOrigin: true },
      '/ws': { target: backendUrl, ws: true, changeOrigin: true },
      '/socket.io': { target: backendUrl, ws: true, changeOrigin: true },
    },
  },
})
