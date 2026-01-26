import axios from 'axios'

// 在 Docker 環境中，Nginx 會將 /api 代理到後端
// 在開發環境中，直接連接到 localhost:8000
const API_BASE_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

// 配置 axios 全局超時時間為10分鐘，支持大量數據下載
axios.defaults.timeout = 600000 // 600秒 = 10分鐘

export const fetchIndexData = async (symbol, startDate = '2010-01-01', endDate = null) => {
  try {
    const params = { start_date: startDate }
    if (endDate) {
      params.end_date = endDate
    }
    const response = await axios.get(`${API_BASE_URL}/index/${symbol}`, { params })
    return response.data
  } catch (error) {
    console.error('獲取指數數據失敗:', error)
    throw error
  }
}

export const fetchCorrelationData = async (symbol) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/correlation/${symbol}`)
    return response.data
  } catch (error) {
    console.error('獲取相關性數據失敗:', error)
    throw error
  }
}

export const fetchAllIndices = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/indices`)
    return response.data
  } catch (error) {
    console.error('獲取所有指數失敗:', error)
    throw error
  }
}

export const analyzeCorrelationFromLocal = async (indexSymbol, threshold = 0.8, startDate = '2010-01-01', endDate = null) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/storage/correlation-analysis`, {
      index_symbol: indexSymbol,
      threshold: threshold,
      start_date: startDate,
      end_date: endDate
    })
    return response.data
  } catch (error) {
    console.error('本地數據相關性分析失敗:', error)
    throw error
  }
}
