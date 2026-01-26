<template>
  <div class="overflow-x-auto">
    <table class="min-w-full bg-white border border-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            股票代碼
          </th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            股票名稱
          </th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            相關係數
          </th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            相關性評級
          </th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr v-for="stock in data" :key="stock.symbol" class="hover:bg-gray-50">
          <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
            {{ stock.symbol }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            {{ stock.name }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
            {{ stock.correlation.toFixed(4) }}
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <span 
              :class="getCorrelationBadgeClass(stock.correlation)"
              class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
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
    }
  },
  setup() {
    const getCorrelationLevel = (corr) => {
      const absCorr = Math.abs(corr)
      if (absCorr >= 0.8) return '高度相關'
      if (absCorr >= 0.5) return '中度相關'
      if (absCorr >= 0.3) return '低度相關'
      return '弱相關'
    }

    const getCorrelationBadgeClass = (corr) => {
      const absCorr = Math.abs(corr)
      if (absCorr >= 0.8) return 'bg-red-100 text-red-800'
      if (absCorr >= 0.5) return 'bg-yellow-100 text-yellow-800'
      if (absCorr >= 0.3) return 'bg-blue-100 text-blue-800'
      return 'bg-gray-100 text-gray-800'
    }

    return {
      getCorrelationLevel,
      getCorrelationBadgeClass
    }
  }
}
</script>
