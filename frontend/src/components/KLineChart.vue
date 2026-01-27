<template>
  <div class="w-full h-96">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import 'chartjs-adapter-date-fns'

Chart.register(...registerables, annotationPlugin)

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
      // 使用 ISO 日期格式，Chart.js time scale 會自動解析
      const lineData = props.data.map(d => ({
        x: d.date,
        y: d.close
      }))

      console.log('Creating chart with data points:', lineData.length)

      // 準備數據集陣列
      const datasets = [
        {
          label: props.symbol + ' 收盤價',
          data: lineData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'y'
        }
      ]

      // 如果有選中的股票數據，添加到圖表中
      console.log('Stock data check:', { 
        hasStockData: !!props.stockData, 
        stockSymbol: props.stockData?.symbol,
        dataLength: props.stockData?.data?.length 
      })
      
      if (props.stockData && props.stockData.data && props.stockData.data.length > 0) {
        console.log('Adding stock overlay:', props.stockData.symbol)
        const stockLineData = props.stockData.data.map(d => ({
          x: d.date,
          y: d.close
        }))
        
        datasets.push({
          label: props.stockData.symbol + ' 收盤價',
          data: stockLineData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'y1'
        })
      }

      try {
        // 創建圖表配置
        const chartConfig = {
        type: 'line',
        data: {
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: props.stockData ? true : false,
              position: 'top'
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `收盤價: ${context.parsed.y.toFixed(2)}`
                }
              }
            },
            // 添加下跌區間標註插件
            annotation: props.drawdownPeriods && props.drawdownPeriods.length > 0 ? {
              annotations: props.drawdownPeriods.reduce((acc, period, idx) => {
                // 數據驗證：確保日期格式正確且在合理範圍內
                const peakDate = period.peak_date
                const troughDate = period.trough_date
                
                // 調試日誌（開發環境）
                if (process.env.NODE_ENV === 'development') {
                  console.log(`波段${idx + 1}: ${peakDate} → ${troughDate} (${(period.drawdown_pct * 100).toFixed(1)}%)`)
                }
                
                // 驗證日期：確保谷底日期不晚於峰值日期
                if (troughDate && peakDate && troughDate >= peakDate) {
                  // 添加陰影區域（只標示峰值到谷底之間）
                  // 使用 ISO 日期格式，Chart.js time scale 會自動解析
                  acc[`drawdown_box_${idx}`] = {
                    type: 'box',
                    xScaleID: 'x',  // 明確指定使用 x 軸
                    xMin: peakDate,
                    xMax: troughDate,
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderColor: 'rgba(239, 68, 68, 0.3)',
                    borderWidth: 1,
                    label: {
                      display: true,
                      content: `↓${(period.drawdown_pct * 100).toFixed(1)}%`,
                      position: 'start',
                      backgroundColor: 'rgba(255, 255, 255, 0.9)',
                      color: 'rgb(220, 38, 38)',
                      font: {
                        size: 11,
                        weight: 'bold'
                      }
                    }
                  }
                } else {
                  console.warn(`跳過無效的波段數據: ${peakDate} → ${troughDate}`)
                }
                
                return acc
              }, {})
            } : undefined
          },
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'month',
                displayFormats: {
                  month: 'yyyy-MM'
                },
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
                display: props.stockData ? true : false,
                text: props.symbol
              }
            },
            y1: {
              display: props.stockData ? true : false,
              beginAtZero: false,
              position: 'left',
              title: {
                display: true,
                text: props.stockData ? props.stockData.symbol : ''
              },
              grid: {
                drawOnChartArea: false
              }
            }
          }
        },
        plugins: props.drawdownPeriods && props.drawdownPeriods.length > 0 ? [
          {
            id: 'drawdownAnnotations'
          }
        ] : []
      }
      
      chartInstance = new Chart(ctx, chartConfig)
      console.log('Chart created successfully with', props.drawdownPeriods?.length || 0, 'drawdown periods')
    } catch (error) {
      console.error('Error creating chart:', error)
    }
  }

    onMounted(() => {
      createChart()
    })

    watch(() => [props.data, props.symbol, props.stockData, props.drawdownPeriods], () => {
      createChart()
    }, { deep: true })

    return {
      chartCanvas
    }
  }
}
</script>
