import axios from 'axios'
import { message } from 'ant-design-vue'

const API_CONFIG_KEY = 'knomas_api_config'
const MODEL_PROFILES_KEY = 'knomas_model_profiles'

const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const http = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: 600000,
})

export const getApiConfig = () => {
  try {
    const raw = localStorage.getItem(API_CONFIG_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export const applyApiConfig = (config) => {
  if (!config) return

  if (config.backendBaseUrl) {
    http.defaults.baseURL = config.backendBaseUrl
  }

  if (config.apiKey) {
    http.defaults.headers.common['X-API-Key'] = config.apiKey
  } else {
    delete http.defaults.headers.common['X-API-Key']
  }

  if (config.model) {
    http.defaults.headers.common['X-Model-Name'] = config.model
  } else {
    delete http.defaults.headers.common['X-Model-Name']
  }

  if (config.baseUrl) {
    http.defaults.headers.common['X-LLM-Base-URL'] = config.baseUrl
  } else {
    delete http.defaults.headers.common['X-LLM-Base-URL']
  }
}

export const saveApiConfig = (config) => {
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify(config))
  applyApiConfig(config)
}

export const getModelProfiles = () => {
  try {
    const raw = localStorage.getItem(MODEL_PROFILES_KEY)
    if (!raw) return []
    return JSON.parse(raw)
  } catch {
    return []
  }
}

export const saveModelProfiles = (profiles) => {
  localStorage.setItem(MODEL_PROFILES_KEY, JSON.stringify(profiles))
}

applyApiConfig(getApiConfig())

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error?.response?.data
    const apiErr = data?.detail && typeof data.detail === 'object' ? data.detail : data
    const msg = apiErr?.message || error?.message || '请求失败'
    message.error(msg)
    return Promise.reject(error)
  },
)
