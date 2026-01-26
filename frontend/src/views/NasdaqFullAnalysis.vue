<template>
  <div class="nasdaq-full-analysis">
    <div class="header mb-6">
      <h2 class="text-3xl font-bold text-gray-800 mb-2">那斯達克全部股票相關性分析</h2>
      <p class="text-gray-600">分析所有那斯達克股票與那斯達克綜合指數的相關性</p>
    </div>

    <!-- 參數設置 -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 class="text-xl font-semibold mb-4">分析參數</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">起始日期</label>
          <input 
            v-model="startDate" 
            type="date" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">結束日期</label>
          <input 
            v-model="endDate" 
            type="date" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">最小相關係數</label>
          <input 
            v-model.number="minCorrelation" 
            type="number" 
            step="0.1" 
            min="0" 
            max="1"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">顯示數量</label>
          <select 
            v-model.number="limit" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option :value="50">前 50 名</option>
            <option :value="100">前 100 名</option>
            <option :value="200">前 200 名</option>
            <option :value="500">前 500 名</option>
            <option :value="1000">前 1000 名</option>
          </select>
        </div>
      </div>
      
      <div class="flex justify-between items-center">
        <div class="flex space-x-3">
          <button 
            @click="downloadAllData" 
            :disabled="downloading"
            class="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {{ downloading ? '下載中...' : '📥 下載全部股票資料' }}
          </button>
          
          <button 
            @click="startAnalysis" 
            :disabled="loading"
            class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {{ loading ? '分析中...' : '📊 開始分析' }}
          </button>
        </div>
        
        <div v-if="analysisInfo" class="text-sm text-gray-600">
          <span class="mr-4">總共分析: {{ analysisInfo.total_analyzed }} 支股票</span>
          <span class="mr-4">有效數據: {{ analysisInfo.total_with_data }} 支</span>
          <span>符合條件: {{ analysisInfo.filtered_count }} 支</span>
        </div>
      </div>
      
      <!-- 進度條 -->
      <div v-if="loading || downloading" class="mt-4">
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div 
            class="h-2 rounded-full transition-all duration-300" 
            :class="downloading ? 'bg-green-600' : 'bg-blue-600'"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <p class="text-sm text-gray-600 mt-2 text-center">{{ progressText }}</p>
      </div>
      
      <!-- 下載成功訊息 -->
      <div v-if="downloadSuccess" class="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
        <div class="flex items-start">
          <svg class="h-5 w-5 text-green-600 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          <div>
            <p class="text-green-800 font-semibold">下載完成！</p>
            <p class="text-green-700 text-sm mt-1">{{ downloadSuccess }}</p>
          </div>
        </div>
      </div>
      
      <!-- 錯誤訊息 -->
      <div v-if="error" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
        <p class="text-red-700">{{ error }}</p>
      </div>
    </div>

    <!-- 結果統計 -->
    <div v-if="analysisInfo && correlations.length > 0" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-600 mb-1">平均相關性</div>
        <div class="text-2xl font-bold text-blue-600">{{ averageCorrelation.toFixed(3) }}</div>
      </div>
      
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-600 mb-1">最高相關性</div>
        <div class="text-2xl font-bold text-green-600">{{ maxCorrelation.toFixed(3) }}</div>
      </div>
      
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-600 mb-1">最低相關性</div>
        <div class="text-2xl font-bold text-orange-600">{{ minCorrelationValue.toFixed(3) }}</div>
      </div>
      
      <div class="bg-white rounded-lg shadow-md p-4">
        <div class="text-sm text-gray-600 mb-1">數據點數</div>
        <div class="text-2xl font-bold text-purple-600">{{ analysisInfo.index.data_points }}</div>
      </div>
    </div>

    <!-- 相關性列表 -->
    <div v-if="correlations.length > 0" class="bg-white rounded-lg shadow-md overflow-hidden">
      <div class="p-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
        <h3 class="text-xl font-semibold">相關性排名</h3>
        
        <!-- 搜索框 -->
        <div class="flex items-center space-x-2">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="搜索股票代碼或名稱..."
            class="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
          <button 
            @click="exportToCSV"
            class="px-4 py-1 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors"
          >
            匯出 CSV
          </button>
        </div>
      </div>
      
      <div class="overflow-x-auto max-h-[600px]">
        <table class="w-full">
          <thead class="bg-gray-100 sticky top-0">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-700">排名</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-700">代碼</th>
              <th class="px-4 py-3 text-left text-sm font-semibold text-gray-700">公司名稱</th>
              <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">相關係數</th>
              <th class="px-4 py-3 text-center text-sm font-semibold text-gray-700">相關性</th>
              <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">P值</th>
              <th class="px-4 py-3 text-right text-sm font-semibold text-gray-700">數據點</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(item, index) in filteredCorrelations" 
              :key="item.symbol"
              class="border-b border-gray-200 hover:bg-gray-50 transition-colors"
            >
              <td class="px-4 py-3 text-sm text-gray-600">{{ index + 1 }}</td>
              <td class="px-4 py-3">
                <span class="font-mono font-semibold text-blue-600">{{ item.symbol }}</span>
              </td>
              <td class="px-4 py-3 text-sm text-gray-800">{{ item.name }}</td>
              <td class="px-4 py-3 text-right">
                <span class="font-semibold" :class="getCorrelationColor(item.correlation)">
                  {{ item.correlation.toFixed(4) }}
                </span>
              </td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center">
                  <div class="w-24 bg-gray-200 rounded-full h-2">
                    <div 
                      class="h-2 rounded-full transition-all"
                      :class="item.correlation >= 0 ? 'bg-green-500' : 'bg-red-500'"
                      :style="{ width: Math.abs(item.correlation) * 100 + '%' }"
                    ></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-right text-sm text-gray-600">
                {{ item.p_value.toFixed(6) }}
              </td>
              <td class="px-4 py-3 text-right text-sm text-gray-600">
                {{ item.data_points }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 無數據提示 -->
    <div v-else-if="!loading" class="bg-white rounded-lg shadow-md p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
      <h3 class="text-xl font-semibold text-gray-700 mb-2">尚未開始分析</h3>
      <p class="text-gray-600">點擊上方「開始分析」按鈕來分析所有那斯達克股票與指數的相關性</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

// 數據
const startDate = ref('2020-01-01')
const endDate = ref(new Date().toISOString().split('T')[0])
const minCorrelation = ref(0.5)
const limit = ref(100)
const loading = ref(false)
const downloading = ref(false)
const downloadSuccess = ref('')
const error = ref('')
const progress = ref(0)
const progressText = ref('')
const correlations = ref([])
const analysisInfo = ref(null)
const searchQuery = ref('')

// 計算屬性
const filteredCorrelations = computed(() => {
  if (!searchQuery.value) return correlations.value
  
  const query = searchQuery.value.toLowerCase()
  return correlations.value.filter(item => 
    item.symbol.toLowerCase().includes(query) || 
    item.name.toLowerCase().includes(query)
  )
})

const averageCorrelation = computed(() => {
  if (correlations.value.length === 0) return 0
  const sum = correlations.value.reduce((acc, item) => acc + Math.abs(item.correlation), 0)
  return sum / correlations.value.length
})

const maxCorrelation = computed(() => {
  if (correlations.value.length === 0) return 0
  return Math.max(...correlations.value.map(item => Math.abs(item.correlation)))
})

const minCorrelationValue = computed(() => {
  if (correlations.value.length === 0) return 0
  return Math.min(...correlations.value.map(item => Math.abs(item.correlation)))
})

// 方法
const getCorrelationColor = (correlation) => {
  const abs = Math.abs(correlation)
  if (abs >= 0.8) return 'text-green-600'
  if (abs >= 0.6) return 'text-blue-600'
  if (abs >= 0.4) return 'text-orange-600'
  return 'text-gray-600'
}

const downloadAllData = async () => {
  downloading.value = true
  downloadSuccess.value = ''
  error.value = ''
  progress.value = 0
  progressText.value = '正在準備下載...'
  
  try {
    // 模擬進度更新
    const progressInterval = setInterval(() => {
      if (progress.value < 90) {
        progress.value += 3
        if (progress.value < 30) {
          progressText.value = '正在下載股票數據 (批次 1/42)...'
        } else if (progress.value < 60) {
          progressText.value = '正在下載股票數據 (批次 20/42)...'
        } else {
          progressText.value = '正在下載股票數據 (批次 40/42)...'
        }
      }
    }, 2000)
    
    const response = await axios.post('/api/nasdaq/download-all', {
      start_date: startDate.value,
      end_date: endDate.value
    })
    
    clearInterval(progressInterval)
    progress.value = 100
    progressText.value = '下載完成！'
    
    const summary = response.data.summary
    downloadSuccess.value = `成功下載 ${summary.successful_downloads}/${summary.total_tickers} 支股票 (成功率: ${summary.success_rate})\n總數據點: ${summary.total_data_points.toLocaleString()}`
    
    console.log('下載結果:', response.data)
    
    // 3秒後清除成功訊息
    setTimeout(() => {
      downloadSuccess.value = ''
    }, 5000)
    
  } catch (err) {
    error.value = err.response?.data?.error || err.message || '下載失敗'
    console.error('下載錯誤:', err)
  } finally {
    downloading.value = false
  }
}

const startAnalysis = async () => {
  loading.value = true
  error.value = ''
  downloadSuccess.value = ''
  progress.value = 0
  progressText.value = '正在獲取股票列表...'
  
  try {
    // 模擬進度更新
    const progressInterval = setInterval(() => {
      if (progress.value < 90) {
        progress.value += 5
        if (progress.value < 30) {
          progressText.value = '正在下載股票數據...'
        } else if (progress.value < 60) {
          progressText.value = '正在計算相關性...'
        } else {
          progressText.value = '正在處理結果...'
        }
      }
    }, 1000)
    
    const response = await axios.get('/api/nasdaq/all-correlation', {
      params: {
        start_date: startDate.value,
        end_date: endDate.value,
        min_correlation: minCorrelation.value,
        limit: limit.value
      }
    })
    
    clearInterval(progressInterval)
    progress.value = 100
    progressText.value = '分析完成！'
    
    correlations.value = response.data.correlations || []
    analysisInfo.value = {
      total_analyzed: response.data.total_analyzed,
      total_with_data: response.data.total_with_data,
      filtered_count: response.data.filtered_count,
      index: response.data.index
    }
    
    console.log('分析結果:', response.data)
    
  } catch (err) {
    error.value = err.response?.data?.error || err.message || '分析失敗'
    console.error('分析錯誤:', err)
  } finally {
    loading.value = false
  }
}

const exportToCSV = () => {
  if (correlations.value.length === 0) return
  
  // 創建 CSV 內容
  const headers = ['排名', '代碼', '公司名稱', '相關係數', 'P值', '數據點']
  const rows = correlations.value.map((item, index) => [
    index + 1,
    item.symbol,
    item.name,
    item.correlation.toFixed(4),
    item.p_value.toFixed(6),
    item.data_points
  ])
  
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n')
  
  // 下載 CSV
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `nasdaq_correlation_${new Date().toISOString().split('T')[0]}.csv`
  link.click()
}
</script>

<style scoped>
.nasdaq-full-analysis {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
</style>
