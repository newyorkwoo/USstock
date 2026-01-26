<template>
  <div class="w-full h-96">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial'
import 'chartjs-adapter-luxon'

Chart.register(...registerables, CandlestickController, CandlestickElement)

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
      
      // 準備蠟燭圖數據格式
      const candlestickData = props.data.map(d => ({
        x: d.date,
        o: d.open,    // open
        h: d.high,    // high
        l: d.low,     // low
        c: d.close    // close
      }))

      chartInstance = new Chart(ctx, {
        type: 'candlestick',
        data: {
          datasets: [
            {
              label: 'K線圖',
              data: candlestickData,
              // 上漲蠟燭（收盤 >= 開盤）- 紅色
              color: {
                up: '#ef4444',      // 上漲邊框 - 紅色
                down: '#22c55e',    // 下跌邊框 - 綠色
                unchanged: '#999'    // 無變化 - 灰色
              },
              borderColor: {
                up: '#ef4444',      // 上漲邊框 - 紅色  
                down: '#22c55e',    // 下跌邊框 - 綠色
                unchanged: '#999'
              },
              // 上漲蠟燭實心，下跌蠟燭空心
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false  // 不顯示圖例
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const data = context.raw
                  return [
                    `日期: ${data.x}`,
                    `開盤: ${data.o.toFixed(2)}`,
                    `最高: ${data.h.toFixed(2)}`,
                    `最低: ${data.l.toFixed(2)}`,
                    `收盤: ${data.c.toFixed(2)}`,
                    `漲跌: ${(data.c - data.o).toFixed(2)} (${((data.c - data.o) / data.o * 100).toFixed(2)}%)`
                  ]
                }
              }
            }
          },
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'day',
                displayFormats: {
                  day: 'yyyy-MM-dd'
                }
              },
              ticks: {
                maxRotation: 45,
                minRotation: 45,
                autoSkip: true,
                maxTicksLimit: 20
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
