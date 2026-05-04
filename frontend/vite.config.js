import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Paths relativos para o APK (Capacitor) carregar corretamente com file://
  base: './',
  build: {
    // Evita falhas quando `dist/` está com permissões/owner diferentes (ex: gerado por container)
    outDir: 'dist-build',
    emptyOutDir: true,
  },
  server: {
    port: 5689,
    host: true,
    watch: { usePolling: true, interval: 300 },
    proxy: {
      '/api': {
        target: 'http://192.168.10.167:5688',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://192.168.10.167:5688',
        ws: true,
      },
    },
  },
  define: {
    // Variáveis de ambiente para o frontend
    __API_URL__: JSON.stringify('http://192.168.10.167:5688/api'),
    __WS_URL__: JSON.stringify('ws://192.168.10.167:5688/ws'),
  },
})
// trigger hot-reload restart
