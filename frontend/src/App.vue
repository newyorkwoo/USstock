<template>
  <div class="min-h-screen" style="background-color: var(--jp-paper);">
    <!-- 日式標題欄 -->
    <header class="border-b" style="background-color: var(--jp-white); border-color: var(--jp-border);">
      <div class="max-w-7xl mx-auto px-8 py-6">
        <h1 class="text-jp-2xl font-medium tracking-wider" style="color: var(--jp-ink);">
          美國股市分析系統
        </h1>
        <p class="text-jp-sm mt-1" style="color: var(--jp-ink-light);">Stock Market Analysis</p>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-8 py-8">
      <div>
        <!-- 指數選擇標籤 - 日式風格 -->
        <div class="jp-card mb-8">
          <div class="border-b" style="border-color: var(--jp-border);">
            <nav class="flex space-x-0" aria-label="Tabs">
              <button
                v-for="index in indices"
                :key="index.symbol"
                @click="selectedIndex = index.symbol"
                :class="[
                  selectedIndex === index.symbol
                    ? 'border-b-2 font-medium'
                    : 'border-transparent hover:bg-jp-hover',
                  'whitespace-nowrap py-5 px-8 text-jp-base transition-all duration-200'
                ]"
                :style="selectedIndex === index.symbol 
                  ? 'color: var(--jp-ink); border-color: var(--jp-ink);' 
                  : 'color: var(--jp-ink-light);'"
              >
                {{ index.name }}
              </button>
            </nav>
          </div>
        </div>

        <!-- 控制面板 - 日式風格 -->
        <div class="jp-card p-8 mb-8">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label class="block text-jp-sm font-medium mb-3" style="color: var(--jp-ink-light);">開始日期</label>
              <input 
                type="date" 
                v-model="startDate"
                min="2010-01-01"
                :max="todayStr"
                class="jp-input w-full"
              />
            </div>
            <div>
              <label class="block text-jp-sm font-medium mb-3" style="color: var(--jp-ink-light);">結束日期</label>
              <input 
                type="date" 
                v-model="endDate"
                min="2010-01-01"
                :max="todayStr"
                class="jp-input w-full"
              />
            </div>
            <div>
              <label class="block text-jp-sm font-medium mb-3" style="color: var(--jp-ink-light);">相關性閥值</label>
              <input 
                type="number" 
                v-model="correlationThreshold"
                step="0.01"
                min="0"
                max="1"
                class="jp-input w-full"
              />
            </div>
            <div class="flex items-end">
              <button
                @click="analyzeCorrelation"
                :disabled="analyzing"
                class="jp-btn w-full rounded-jp disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ analyzing ? '分析中...' : '開始分析' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 圖表區域 - 日式風格 -->
        <div class="jp-card p-8 mb-8">
          <!-- Loading 狀態 -->
          <div v-if="loading" class="flex items-center justify-center py-16">
            <div class="animate-spin rounded-full h-10 w-10 border-2" style="border-color: var(--jp-border); border-top-color: var(--jp-ink);"></div>
          </div>
          
          <!-- 圖表與統計 -->
          <div v-else>
            <div class="mb-8">
              <h2 class="text-jp-xl font-medium mb-4" style="color: var(--jp-ink);">
                {{ currentIndexName }}
              </h2>
              
              <!-- 統計數據 - 日式分隔 -->
              <div class="flex flex-wrap gap-8 text-jp-base">
                <div class="flex items-center">
                  <span style="color: var(--jp-ink-light);">當前價格</span>
                  <span class="mx-3" style="color: var(--jp-border);">|</span>
                  <span class="font-medium" style="color: var(--jp-ink);">{{ currentPrice }}</span>
                </div>
                <div class="flex items-center">
                  <span style="color: var(--jp-ink-light);">漲跌幅</span>
                  <span class="mx-3" style="color: var(--jp-border);">|</span>
                  <span 
                    class="font-medium"
                    :style="priceChange >= 0 ? 'color: var(--jp-red);' : 'color: var(--jp-green);'"
                  >
                    {{ priceChange >= 0 ? '+' : '' }}{{ priceChange }}%
                  </span>
                </div>
                <div class="flex items-center">
                  <span style="color: var(--jp-ink-light);">成交量</span>
                  <span class="mx-3" style="color: var(--jp-border);">|</span>
                  <span class="font-medium" style="color: var(--jp-ink);">{{ volume }}</span>
                </div>
                <div v-if="dataRange" class="flex items-center">
                  <span style="color: var(--jp-ink-light);">數據範圍</span>
                  <span class="mx-3" style="color: var(--jp-border);">|</span>
                  <span class="font-medium" style="color: var(--jp-ink);">{{ dataRange.start }} ~ {{ dataRange.end }} ({{ dataRange.count }} 筆)</span>
                </div>
              </div>
            </div>

            <KLineChart 
              v-if="chartData"
              :data="chartData"
              :symbol="selectedIndex"
              :stockData="selectedStockData"
              :drawdownPeriods="drawdownPeriods"
            />
          </div>
        </div>

        <!-- 相關性分析結果 - 日式風格 -->
        <div v-if="correlationResults.length > 0" class="jp-card p-8">
          <h3 class="text-jp-lg font-medium mb-6" style="color: var(--jp-ink);">
            相關性分析結果
            <span class="text-jp-sm font-normal ml-3" style="color: var(--jp-ink-light);">
              閥值 ≥ {{ correlationThreshold }}
            </span>
          </h3>
          <div class="max-h-[450px] overflow-y-auto">
            <CorrelationTable 
              :data="correlationResults"
              @select-stock="handleSelectStock"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import KLineChart from './components/KLineChart.vue'
import CorrelationTable from './components/CorrelationTable.vue'
import { fetchIndexData, analyzeCorrelationFromLocal, fetchStockDataFromLocal } from './utils/api'

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
    const analyzing = ref(false)
    const chartData = ref(null)
    const currentPrice = ref('--')
    const priceChange = ref(0)
    const volume = ref('--')
    const dataRange = ref(null)
    const correlationThreshold = ref(0.9)
    const correlationResults = ref([])
    const selectedStockData = ref(null)
    const drawdownPeriods = ref([])
    
    // 數據緩存
    const dataCache = ref({})
    const drawdownCache = ref({})
    
    // 當前指數名稱 - 使用 computed 優化
    const currentIndexName = computed(() => {
      return indices.find(i => i.symbol === selectedIndex.value)?.name || ''
    })

    // 日期選擇器
    const today = new Date()
    const todayStr = today.toISOString().split('T')[0]
    const startDate = ref('2010-01-01')
    const endDate = ref(todayStr)

    const loadData = async () => {
      loading.value = true
      
      try {
        const cacheKey = `${selectedIndex.value}_${startDate.value}_${endDate.value}`
        
        // 檢查緩存
        if (dataCache.value[cacheKey]) {
          const cached = dataCache.value[cacheKey]
          chartData.value = cached.history
          currentPrice.value = cached.currentPrice
          priceChange.value = cached.priceChange
          volume.value = cached.volume
          dataRange.value = cached.dataRange
          await loadDrawdownPeriods()
          loading.value = false
          return
        }
        
        const response = await fetchIndexData(selectedIndex.value, startDate.value, endDate.value)
        
        // API 返回 {data_range: {...}, history: [...]} 格式
        if (response && response.history && response.history.length > 0) {
          const history = response.history
          
          // 轉換為圖表組件需要的格式 (陣列格式)
          chartData.value = history
          
          // 計算統計數據
          const lastClose = history[history.length - 1].close
          const prevClose = history[history.length - 2].close
          const change = ((lastClose - prevClose) / prevClose * 100).toFixed(2)
          const lastVolume = history[history.length - 1].volume
          
          currentPrice.value = lastClose.toFixed(2)
          priceChange.value = parseFloat(change)
          volume.value = lastVolume ? (lastVolume / 1e6).toFixed(2) + 'M' : '--'
          
          dataRange.value = response.data_range
          
          // 緩存數據
          dataCache.value[cacheKey] = {
            history,
            currentPrice: currentPrice.value,
            priceChange: priceChange.value,
            volume: volume.value,
            dataRange: response.data_range
          }
          
          // 同時載入波段下跌區間數據
          await loadDrawdownPeriods()
        }
      } catch (error) {
        console.error(`載入 ${selectedIndex.value} 數據失敗:`, error)
      } finally {
        loading.value = false
      }
    }

    const loadDrawdownPeriods = async () => {
      try {
        const cacheKey = `${selectedIndex.value}_0.15`
        
        // 檢查緩存
        if (drawdownCache.value[cacheKey]) {
          drawdownPeriods.value = drawdownCache.value[cacheKey]
          return
        }
        
        const response = await fetch('http://localhost:8000/storage/drawdown-periods', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            index_symbol: selectedIndex.value,
            threshold: 0.15  // 15% 下跌閾值
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          // 數據驗證和清理：過濾掉任何無效的波段數據
          let validPeriods = (data.drawdown_periods || []).filter(period => {
            // 確保必要欄位存在
            if (!period.peak_date || !period.trough_date) {
              console.warn('跳過缺少日期的波段:', period)
              return false
            }
            
            // 確保谷底日期在峰值之後
            if (period.trough_date < period.peak_date) {
              console.warn('跳過日期順序錯誤的波段:', period.peak_date, '→', period.trough_date)
              return false
            }
            
            // 確保下跌百分比有效
            if (!period.drawdown_pct || period.drawdown_pct <= 0 || period.drawdown_pct > 1) {
              console.warn('跳過下跌百分比異常的波段:', period.drawdown_pct)
              return false
            }
            
            return true
          })
          
          // 根據用戶選擇的日期範圍過濾波段
          // 只顯示谷底日期在選擇範圍內的波段
          const filteredPeriods = validPeriods.filter(period => {
            const troughDate = period.trough_date
            const peakDate = period.peak_date
            
            // 波段的谷底必須在用戶選擇的日期範圍內
            // 或者波段與用戶選擇的範圍有重疊
            return troughDate >= startDate.value && peakDate <= endDate.value
          })
          
          drawdownPeriods.value = filteredPeriods
          
          // 緩存數據
          const cacheKey = `${selectedIndex.value}_0.15`
          drawdownCache.value[cacheKey] = filteredPeriods
          
          console.log(`找到 ${filteredPeriods.length} 個有效波段下跌區間 (原始數據: ${data.drawdown_periods?.length || 0} 個, 過濾後: ${validPeriods.length} 個)`)
          
          // 調試：顯示每個波段的日期範圍
          filteredPeriods.forEach((p, i) => {
            console.log(`  ${i + 1}. ${p.peak_date} → ${p.trough_date} (${(p.drawdown_pct * 100).toFixed(1)}%)`)
          })
        }
      } catch (error) {
        console.error('載入波段下跌區間失敗:', error)
      }
    }

    const analyzeCorrelation = async () => {
      analyzing.value = true
      correlationResults.value = []
      selectedStockData.value = null
      
      // 先重新載入 K 線圖數據（使用新的日期範圍）
      await loadData()
      
      try {
        const response = await analyzeCorrelationFromLocal(
          selectedIndex.value,
          startDate.value,
          endDate.value,
          correlationThreshold.value
        )
        
        // API 返回 {correlations: [...]} 格式
        const results = response.correlations || response || []
        
        if (results && results.length > 0) {
          correlationResults.value = results
          console.log(`找到 ${results.length} 支相關股票`)
        } else {
          alert('未找到符合條件的相關股票')
        }
      } catch (error) {
        console.error('相關性分析失敗:', error)
        alert('相關性分析失敗，請稍後再試')
      } finally {
        analyzing.value = false
      }
    }

    const handleSelectStock = async (stock) => {
      try {
        const stockData = await fetchStockDataFromLocal(
          stock.symbol,
          startDate.value,
          endDate.value
        )
        
        // API 返回 {data: [...]} 格式
        if (stockData && stockData.data && stockData.data.length > 0) {
          selectedStockData.value = {
            symbol: stock.symbol,
            data: stockData.data
          }
          console.log(`已載入股票 ${stock.symbol} 數據，共 ${stockData.data.length} 筆`)
        } else {
          console.warn(`股票 ${stock.symbol} 沒有數據`)
        }
      } catch (error) {
        console.error(`載入股票 ${stock.symbol} 失敗:`, error)
        alert(`載入股票數據失敗: ${error.message}`)
      }
    }

    // 監聽選中指數的變化
    watch(selectedIndex, () => {
      loadData()
      correlationResults.value = []
      selectedStockData.value = null
    })

    // 監聽日期範圍變化，自動重新載入K線圖數據（使用 debounce 避免頻繁請求）
    let dateChangeTimer = null
    watch([startDate, endDate], () => {
      // 清除之前的定時器
      if (dateChangeTimer) {
        clearTimeout(dateChangeTimer)
      }
      // 延遲 500ms 後執行，避免用戶還在選擇日期時就觸發請求
      dateChangeTimer = setTimeout(() => {
        loadData()
      }, 500)
    })

    onMounted(() => {
      loadData()
    })

    return {
      indices,
      selectedIndex,
      loading,
      analyzing,
      chartData,
      currentPrice,
      priceChange,
      volume,
      dataRange,
      todayStr,
      startDate,
      endDate,
      correlationThreshold,
      correlationResults,
      selectedStockData,
      drawdownPeriods,
      currentIndexName,
      analyzeCorrelation,
      handleSelectStock
    }
  }
}
</script>

<style scoped>
</style>
