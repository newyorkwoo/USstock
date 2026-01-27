import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true
  },
  build: {
    // 代碼分割優化
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue'],
          'charts': ['chart.js', 'chartjs-adapter-date-fns', 'chartjs-plugin-annotation']
        }
      }
    },
    // 壓縮選項
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // 移除 console.log
        drop_debugger: true
      }
    },
    // 提高 chunk 大小警告閾值
    chunkSizeWarningLimit: 1000
  }
})
