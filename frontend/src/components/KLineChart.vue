<template>
  <div class="w-full h-96">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

export default {
  name: 'KLineChart',
  props: {
    data: {
      type: Array,
      required: true
    },
    symbol: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const chartCanvas = ref(null)
    let chartInstance = null

    const createChart = () => {
      if (!chartCanvas.value || !props.data || props.data.length === 0) return

      // 銷毀舊圖表
      if (chartInstance) {
        chartInstance.destroy()
      }

      const ctx = chartCanvas.value.getContext('2d')
      
      // 準備數據
      const labels = props.data.map(d => d.date)
      const prices = props.data.map(d => d.close)
      
      // K線顏色 - 紅色上漲，綠色下跌
      const colors = props.data.map(d => {
        return d.close >= d.open ? '#ef4444' : '#22c55e'
      })

      chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: '收盤價',
              data: prices,
              backgroundColor: colors,
              borderColor: colors,
              borderWidth: 1
            },
            {
              label: '最高價',
              data: props.data.map(d => d.high),
              type: 'line',
              borderColor: '#94a3b8',
              borderWidth: 1,
              pointRadius: 0,
              fill: false
            },
            {
              label: '最低價',
              data: props.data.map(d => d.low),
              type: 'line',
              borderColor: '#cbd5e1',
              borderWidth: 1,
              pointRadius: 0,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const dataPoint = props.data[context.dataIndex]
                  return [
                    `開盤: ${dataPoint.open.toFixed(2)}`,
                    `收盤: ${dataPoint.close.toFixed(2)}`,
                    `最高: ${dataPoint.high.toFixed(2)}`,
                    `最低: ${dataPoint.low.toFixed(2)}`,
                    `成交量: ${(dataPoint.volume / 1000000).toFixed(2)}M`
                  ]
                }
              }
            }
          },
          scales: {
            x: {
              display: true,
              ticks: {
                maxRotation: 45,
                minRotation: 45
              }
            },
            y: {
              display: true,
              beginAtZero: false
            }
          }
        }
      })
    }

    onMounted(() => {
      createChart()
    })

    watch(() => [props.data, props.symbol], () => {
      createChart()
    }, { deep: true })

    return {
      chartCanvas
    }
  }
}
</script>
