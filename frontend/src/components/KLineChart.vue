<template>
  <div class="w-full h-96 relative">
    <canvas ref="chartCanvas"></canvas>
    <button
      v-if="isZoomed"
      @click="resetZoom"
      class="absolute top-2 left-2 bg-white/90 hover:bg-white text-gray-700 text-xs px-2 py-1 rounded shadow border border-gray-300 cursor-pointer z-10"
    >
      重置縮放
    </button>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import zoomPlugin from 'chartjs-plugin-zoom'
import 'chartjs-adapter-date-fns'
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial'

Chart.register(...registerables, annotationPlugin, zoomPlugin, CandlestickController, CandlestickElement)

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
    },
    stockData: {
      type: Object,
      default: null
    },
    drawdownPeriods: {
      type: Array,
      default: () => []
    }
  },
  setup(props) {
    const chartCanvas = ref(null)
    const isZoomed = ref(false)
    let chartInstance = null

    const resetZoom = () => {
      if (chartInstance) {
        chartInstance.resetZoom()
        isZoomed.value = false
      }
    }

    const createChart = async () => {
      await nextTick()
      if (!chartCanvas.value || !props.data || props.data.length === 0) return

      if (chartInstance) {
        chartInstance.destroy()
        isZoomed.value = false
      }

      const ctx = chartCanvas.value.getContext('2d')

      // 判斷是否有真實 OHLC（非 close 填充）
      const hasOHLC = props.data.some(d =>
        d.open !== d.close || d.high !== d.close || d.low !== d.close
      )

      const timestamps = props.data.map(d => new Date(d.date).getTime())
      const minDate = new Date(Math.min(...timestamps))
      const maxDate = new Date(Math.max(...timestamps))

      const datasets = []

      if (hasOHLC) {
        datasets.push({
          type: 'candlestick',
          label: props.symbol,
          data: props.data.map(d => ({
            x: new Date(d.date).getTime(),
            o: d.open,
            h: d.high,
            l: d.low,
            c: d.close
          })),
          color: {
            up: 'rgba(197, 61, 67, 0.85)',      // 上漲：朱色
            down: 'rgba(58, 95, 58, 0.85)',      // 下跌：松葉色
            unchanged: 'rgba(92, 92, 92, 0.7)'
          },
          borderColor: {
            up: 'rgb(197, 61, 67)',
            down: 'rgb(58, 95, 58)',
            unchanged: 'rgb(92, 92, 92)'
          },
          yAxisID: 'y'
        })
      } else {
        // 本地數據尚未重建時回退為折線圖
        datasets.push({
          type: 'line',
          label: props.symbol + ' 收盤價',
          data: props.data.map(d => ({ x: d.date, y: d.close })),
          borderColor: '#2E4A62',
          backgroundColor: 'rgba(46, 74, 98, 0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'y'
        })
      }

      // 疊加個股折線
      if (props.stockData?.data?.length > 0) {
        datasets.push({
          type: 'line',
          label: props.stockData.symbol + ' 收盤價',
          data: props.stockData.data.map(d => ({
            x: new Date(d.date).getTime(),
            y: d.close
          })),
          borderColor: '#C49A00',
          backgroundColor: 'rgba(196, 154, 0, 0.08)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'y1'
        })
      }

      // 建立下跌區間標註
      const annotations = {}
      if (props.drawdownPeriods?.length > 0) {
        props.drawdownPeriods.forEach((period, idx) => {
          if (period.trough_date >= period.peak_date) {
            annotations[`drawdown_box_${idx}`] = {
              type: 'box',
              xScaleID: 'x',
              xMin: period.peak_date,
              xMax: period.trough_date,
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              borderColor: 'rgba(239, 68, 68, 0.3)',
              borderWidth: 1,
              label: {
                display: true,
                content: `↓${(period.drawdown_pct * 100).toFixed(1)}%`,
                position: 'start',
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                color: 'rgb(197, 61, 67)',
                font: { size: 11, weight: 'bold' }
              }
            }
          }
        })
      }

      chartInstance = new Chart(ctx, {
        type: hasOHLC ? 'candlestick' : 'line',
        data: { datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: !!props.stockData,
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const raw = context.raw
                  if (raw?.o !== undefined) {
                    return [
                      `開: ${raw.o.toFixed(2)}`,
                      `高: ${raw.h.toFixed(2)}`,
                      `低: ${raw.l.toFixed(2)}`,
                      `收: ${raw.c.toFixed(2)}`
                    ]
                  }
                  return `收盤價: ${context.parsed.y.toFixed(2)}`
                }
              }
            },
            zoom: {
              zoom: {
                wheel: { enabled: true },
                pinch: { enabled: true },
                mode: 'x',
                onZoom: () => { isZoomed.value = true }
              },
              pan: {
                enabled: true,
                mode: 'x',
                onPan: () => { isZoomed.value = true }
              },
              limits: {
                x: { min: minDate, max: maxDate }
              }
            },
            annotation: Object.keys(annotations).length > 0
              ? { annotations }
              : undefined
          },
          scales: {
            x: {
              type: 'time',
              min: minDate,
              max: maxDate,
              time: {
                unit: 'month',
                displayFormats: { month: 'yyyy-MM' },
                tooltipFormat: 'yyyy-MM-dd'
              },
              ticks: {
                maxRotation: 45,
                minRotation: 45,
                autoSkip: true,
                maxTicksLimit: 15
              }
            },
            y: {
              display: true,
              beginAtZero: false,
              position: 'right',
              title: {
                display: !!props.stockData,
                text: props.symbol
              }
            },
            y1: {
              display: !!props.stockData,
              beginAtZero: false,
              position: 'left',
              title: {
                display: true,
                text: props.stockData?.symbol || ''
              },
              grid: { drawOnChartArea: false }
            }
          }
        }
      })
    }

    onMounted(createChart)

    watch(
      () => [props.data, props.symbol, props.stockData, props.drawdownPeriods],
      createChart,
      { deep: true }
    )

    return { chartCanvas, isZoomed, resetZoom }
  }
}
</script>
