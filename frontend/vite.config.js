import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // Evita falhas quando `dist/` está com permissões/owner diferentes (ex: gerado por container)
    outDir: 'dist-build',
    emptyOutDir: true,
  },
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
  define: {
    // Variáveis de ambiente para o frontend
    __API_URL__: JSON.stringify('http://192.168.10.156:8000/api'),
    __WS_URL__: JSON.stringify('ws://192.168.10.156:8000/ws'),
  },
})
