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
      if (!chartCanvas.value || !props.data || props.data.length === 0) {
        console.log('Chart creation skipped:', {
          hasCanvas: !!chartCanvas.value,
          hasData: !!props.data,
          dataLength: props.data?.length
        })
        return
      }

      // 銷毀舊圖表
      if (chartInstance) {
        chartInstance.destroy()
      }

      const ctx = chartCanvas.value.getContext('2d')
      
      // 準備折線圖數據格式 - 使用收盤價
      const lineData = props.data.map(d => ({
        x: d.date,
        y: d.close
      }))

      console.log('Creating chart with data points:', lineData.length)

      try {
        chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          datasets: [
            {
              label: '收盤價',
              data: lineData,
              borderColor: '#3b82f6',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.1,
              pointRadius: 0,
              pointHoverRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `收盤價: ${context.parsed.y.toFixed(2)}`
                }
              }
            }
          },
          scales: {
            x: {
              type: 'category',
              ticks: {
                maxRotation: 45,
                minRotation: 45,
                autoSkip: true,
                maxTicksLimit: 20,
                callback: function(value, index) {
                  // 每隔幾個顯示一次日期
                  const data = this.chart.data.datasets[0].data[index]
                  return data ? data.x : ''
                }
              }
            },
            y: {
              display: true,
              beginAtZero: false,
              position: 'right'
            }
          }
        }
      })
      console.log('Chart created successfully')
    } catch (error) {
      console.error('Error creating chart:', error)
    }
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
