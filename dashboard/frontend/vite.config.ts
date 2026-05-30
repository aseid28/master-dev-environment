import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/agents': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: true,  // proxy WebSocket connections too (for /agents/.../terminal)
      },
      '/health': 'http://localhost:8080',
    },
  },
})
