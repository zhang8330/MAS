import { http } from './http'

export const getFunctions = (params = {}) => http.get('/api/datasets/ccg/functions', { params })
export const getFunction = (id) => http.get(`/api/datasets/ccg/functions/${id}`)
export const evaluateMetrics = (payload) => http.post('/api/metrics/evaluate', payload)

export const runGenerate = (payload, config = {}) => http.post('/api/generate', payload, config)
export const runPAA = (payload, config = {}) => http.post('/api/run/paa', payload, config)
export const runRGA = (payload, config = {}) => http.post('/api/run/rga', payload, config)
export const runCGA = (payload, config = {}) => http.post('/api/run/cga', payload, config)
export const runVA = (payload, config = {}) => http.post('/api/run/va', payload, config)
