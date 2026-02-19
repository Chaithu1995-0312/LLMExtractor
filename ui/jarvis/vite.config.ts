import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/jarvis': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },
      '/tasks': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },
      '/cognition': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        // No rewrite — /api/* is forwarded as-is to Flask's /api/* routes
      },
      '/socket.io': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false,
        ws: true, // Enable WebSocket proxying for Socket.IO
      },
    },
  },
})
