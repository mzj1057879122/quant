import request from './request'

export function getAllConfigs() {
  return request.get('/config')
}

export function getConfig(key) {
  return request.get(`/config/${key}`)
}

export function updateConfig(key, configValue) {
  return request.put(`/config/${key}`, { configValue })
}

export function getWatchList() {
  return request.get('/config/watch-list')
}

export function updateWatchList(stockCodes) {
  return request.put('/config/watch-list', { stockCodes })
}
