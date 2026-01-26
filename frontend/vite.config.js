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
          'vendor': ['vue', 'axios'],
          'charts': ['chart.js', 'vue-chartjs']
        }
      }
    },
    // 啟用壓縮
    minify: 'esbuild',  // 使用 esbuild 壓縮（更快）
    // 優化 chunk 大小警告閾值
    chunkSizeWarningLimit: 1000,
    // 啟用 CSS 代碼分割
    cssCodeSplit: true,
    // 生成 source map（可選，生產環境可關閉）
    sourcemap: false
  },
  // 優化依賴預構建
  optimizeDeps: {
    include: ['vue', 'axios', 'chart.js', 'vue-chartjs']
  }
})
