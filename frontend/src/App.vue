<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Header -->
    <header class="bg-white shadow-md">
      <div class="container mx-auto px-4 py-6">
        <h1 class="text-3xl font-bold text-gray-800">美國股市分析系統</h1>
        <p class="text-gray-600 mt-2">三大指數即時追蹤與相關性分析</p>
      </div>
    </header>

    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8">
      <!-- Index Selection Tabs -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-8">
        <div class="flex space-x-4 border-b border-gray-200">
          <button
            v-for="index in indices"
            :key="index.symbol"
            @click="selectedIndex = index.symbol"
            :class="[
              'px-6 py-3 font-semibold transition-colors',
              selectedIndex === index.symbol
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-blue-500'
            ]"
          >
            {{ index.name }}
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p class="mt-4 text-gray-600">載入數據中...</p>
      </div>

      <!-- K-Line Chart -->
      <div v-else class="bg-white rounded-lg shadow-md p-6">
        <div class="mb-6">
          <h2 class="text-2xl font-bold text-gray-800">
            {{ getCurrentIndexName() }} K線圖
          </h2>
          <p class="text-sm text-gray-500 mt-1">紅色：收盤上漲 | 綠色：收盤下跌</p>
          <p v-if="dataRange" class="text-xs text-blue-600 mt-1">
            📊 數據範圍: {{ dataRange.start }} 至 {{ dataRange.end }} (共 {{ dataRange.count.toLocaleString() }} 筆)
          </p>
        </div>
        
        <KLineChart
          v-if="chartData"
          :data="chartData"
          :symbol="selectedIndex"
        />

        <!-- Statistics -->
        <div class="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-gray-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">當前價格</p>
            <p class="text-2xl font-bold text-gray-800">
              {{ currentPrice }}
            </p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">漲跌幅</p>
            <p 
              class="text-2xl font-bold"
              :class="priceChange >= 0 ? 'text-bull-red' : 'text-bear-green'"
            >
              {{ priceChange >= 0 ? '+' : '' }}{{ priceChange }}%
            </p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg">
            <p class="text-sm text-gray-600">成交量</p>
            <p class="text-2xl font-bold text-gray-800">
              {{ volume }}
            </p>
          </div>
        </div>

        <!-- Correlation Analysis -->
        <div class="mt-8">
          <h3 class="text-xl font-bold text-gray-800 mb-4">成分股相關性分析</h3>
          <CorrelationTable
            v-if="correlationData"
            :data="correlationData"
            :indexName="getCurrentIndexName()"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import KLineChart from './components/KLineChart.vue'
import CorrelationTable from './components/CorrelationTable.vue'
import { fetchIndexData, fetchCorrelationData } from './utils/api'

export default {
  name: 'App',
  components: {
    KLineChart,
    CorrelationTable
  },
  setup() {
    const indices = [
      { symbol: '^IXIC', name: 'NASDAQ' },
      { symbol: '^DJI', name: '道瓊工業指數' },
      { symbol: '^GSPC', name: 'S&P 500' }
    ]

    const selectedIndex = ref('^IXIC')
    const loading = ref(false)
    const chartData = ref(null)
    const correlationData = ref(null)
    const currentPrice = ref('--')
    const priceChange = ref(0)
    const volume = ref('--')
    const dataRange = ref(null)

    const loadData = async () => {
      loading.value = true
      
      // 重置數據
      currentPrice.value = '--'
      priceChange.value = 0
      volume.value = '--'
      chartData.value = null
      correlationData.value = null
      dataRange.value = null
      
      try {
        const data = await fetchIndexData(selectedIndex.value)
        chartData.value = data.history
        
        // 保存數據範圍信息
        if (data.data_range) {
          dataRange.value = data.data_range
        }
        
        if (data.history && data.history.length > 0) {
          const latest = data.history[data.history.length - 1]
          const previous = data.history[data.history.length - 2]
          
          currentPrice.value = latest.close.toFixed(2)
          priceChange.value = (((latest.close - previous.close) / previous.close) * 100).toFixed(2)
          volume.value = (latest.volume / 1000000).toFixed(2) + 'M'
        }

        const corrData = await fetchCorrelationData(selectedIndex.value)
        correlationData.value = corrData
      } catch (error) {
        console.error('載入數據失敗:', error)
      } finally {
        loading.value = false
      }
    }

    const getCurrentIndexName = () => {
      const index = indices.find(i => i.symbol === selectedIndex.value)
      return index ? index.name : ''
    }

    onMounted(() => {
      loadData()
    })

    watch(selectedIndex, () => {
      loadData()
    })

    return {
      indices,
      selectedIndex,
      loading,
      chartData,
      correlationData,
      currentPrice,
      priceChange,
      volume,
      dataRange,
      getCurrentIndexName
    }
  }
}
</script>
