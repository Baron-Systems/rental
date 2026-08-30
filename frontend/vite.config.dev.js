import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/assets/rental/frontend/',
  server: {
    port: 8080,
    host: '0.0.0.0',
    proxy: {
      '^/(app|login|api|assets|files)': {
        target: 'http://10.2.0.12:80',
        ws: true,
        changeOrigin: true,
        headers: {
          Host: 'renta.albaronsystems.com'
        }
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
})
