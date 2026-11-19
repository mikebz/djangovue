/**
 * Author: Mike Borozdin (mikebz@)
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
    manifest: true,
    // Output keeps Vite's default `assets/[name]-[hash]` naming. Django serves
    // everything under /static/assets/ as immutable, so only content-hashed
    // files may land there.
    rollupOptions: {
      input: 'frontend/js/main.js'
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
