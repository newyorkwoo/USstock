<template>
  <div class="overflow-x-auto">
    <table class="min-w-full" style="background: var(--jp-white);">
      <thead class="sticky top-0 z-10" style="background: var(--jp-paper);">
        <tr>
          <th class="px-6 py-4 text-left text-jp-sm font-medium tracking-wider" style="color: var(--jp-ink-light); background: var(--jp-paper); border-bottom: 1px solid var(--jp-border);">
            股票代碼
          </th>
          <th class="px-6 py-4 text-left text-jp-sm font-medium tracking-wider" style="color: var(--jp-ink-light); background: var(--jp-paper); border-bottom: 1px solid var(--jp-border);">
            股票名稱
          </th>
          <th class="px-6 py-4 text-left text-jp-sm font-medium tracking-wider" style="color: var(--jp-ink-light); background: var(--jp-paper); border-bottom: 1px solid var(--jp-border);">
            相關係數
          </th>
          <th class="px-6 py-4 text-left text-jp-sm font-medium tracking-wider" style="color: var(--jp-ink-light); background: var(--jp-paper); border-bottom: 1px solid var(--jp-border);">
            相關性評級
          </th>
        </tr>
      </thead>
      <tbody style="background: var(--jp-white);">
        <tr v-if="data.length === 0">
          <td colspan="4" class="px-6 py-6 text-center text-jp-base" style="color: var(--jp-ink-light);">
            沒有找到符合條件的股票
          </td>
        </tr>
        <tr 
          v-for="stock in data" 
          :key="stock.symbol" 
          class="transition-colors duration-150"
          :style="selectedStock === stock.symbol 
            ? 'background: var(--jp-hover);' 
            : ''"
          style="border-bottom: 1px solid var(--jp-border);"
          @mouseenter="$event.target.style.background = 'var(--jp-hover)'"
          @mouseleave="$event.target.style.background = selectedStock === stock.symbol ? 'var(--jp-hover)' : ''"
        >
          <td 
            class="px-6 py-4 whitespace-nowrap text-jp-base font-medium cursor-pointer transition-colors"
            style="color: var(--jp-blue);"
            @click="emit('select-stock', stock)"
          >
            {{ stock.symbol }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-jp-base" style="color: var(--jp-ink-light);">
            {{ stock.name }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-jp-base font-medium" style="color: var(--jp-ink);">
            {{ stock.correlation.toFixed(4) }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <span 
              :class="getCorrelationBadgeClass(stock.correlation)"
              class="px-3 py-1 inline-flex text-jp-sm font-medium rounded-jp"
            >
              {{ getCorrelationLevel(stock.correlation) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: 'CorrelationTable',
  props: {
    data: {
      type: Array,
      required: true
    },
    indexName: {
      type: String,
      required: true
    },
    selectedStock: {
      type: String,
      default: null
    }
  },
  emits: ['select-stock'],
  setup(props, { emit }) {
    const getCorrelationLevel = (corr) => {
      const absCorr = Math.abs(corr)
      if (absCorr >= 0.8) return '高度相關'
      if (absCorr >= 0.5) return '中度相關'
      if (absCorr >= 0.3) return '低度相關'
      return '弱相關'
    }

    const getCorrelationBadgeClass = (corr) => {
      const absCorr = Math.abs(corr)
      // 日式配色徽章
      if (absCorr >= 0.8) return 'bg-red-50 text-jp-red border border-red-200'
      if (absCorr >= 0.5) return 'bg-amber-50 text-jp-gold border border-amber-200'
      if (absCorr >= 0.3) return 'bg-blue-50 text-jp-blue border border-blue-200'
      return 'bg-gray-50 text-jp-ink-light border border-gray-200'
    }

    return {
      emit,
      getCorrelationLevel,
      getCorrelationBadgeClass
    }
  }
}
</script>
