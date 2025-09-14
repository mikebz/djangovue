import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  
  // Entry point
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: 'frontend/js/main.js',
      output: {
        // Keep similar naming convention for Django integration
        entryFileNames: '[name]-[hash].js',
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name]-[hash].[ext]'
      }
    }
  },

  // Development server
  server: {
    host: '127.0.0.1',
    port: 3000,
    open: false,
    cors: true
  },

  // Asset handling
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'frontend'),
      '~': path.resolve(__dirname, 'frontend')
    }
  },

  // Public assets
  publicDir: false, // Don't copy public assets to dist
  
  // CSS handling
  css: {
    devSourcemap: true
  },

  // Define environment variables
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false
  }
})
