import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    host: true,
    proxy: {
      '/api': {
        target: 'http://192.168.10.156:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://192.168.10.156:8000',
        ws: true,
      },
    },
  },
})
