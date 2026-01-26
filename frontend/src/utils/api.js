import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export const fetchIndexData = async (symbol) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/index/${symbol}`)
    return response.data
  } catch (error) {
    console.error('獲取指數數據失敗:', error)
    throw error
  }
}

export const fetchCorrelationData = async (symbol) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/correlation/${symbol}`)
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
