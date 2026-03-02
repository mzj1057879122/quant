import request from './request'

export function getSignalList(params) {
  return request.get('/signals', { params })
}

export function getUnreadCount() {
  return request.get('/signals/unread')
}

export function getSignalStatistics(params) {
  return request.get('/signals/statistics', { params })
}

export function markSignalRead(signalId) {
  return request.put(`/signals/${signalId}/read`)
}

export function markAllRead() {
  return request.put('/signals/read-all')
}

export function getPreviousHighs(stockCode) {
  return request.get(`/signals/previous-highs/${stockCode}`)
}

export function getBreakoutAnalysis(stockCode) {
  return request.get(`/signals/breakout-analysis/${stockCode}`)
}

export function detectSignals() {
  return request.post('/signals/detect')
}
