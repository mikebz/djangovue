/**
 * Author: Mike Borozdin (mikebz@)
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Must match Django's STATIC_URL: in dev mode django-vite requests
  // `<dev server>/static/<entry>`, so Vite has to serve under the same prefix.
  // https://github.com/MrBin99/django-vite#configuration
  base: '/static/',
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: 'frontend/js/main.js',
      output: {
        entryFileNames: '[name]-[hash].js',
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name]-[hash].[ext]'
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    open: false,
    cors: true
  },
  publicDir: false,
  css: {
    devSourcemap: true
  },
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false
  }
})
