import axios from 'axios'

// 在 Docker 環境中，Nginx 會將 /api 代理到後端
// 在開發環境中，直接連接到 localhost:8000
const API_BASE_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

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
