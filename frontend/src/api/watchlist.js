import request from './request'

export function getWatchlistItems(params) {
  return request.get('/watchlist/list', { params })
}

export function addWatchlistItem(data) {
  return request.post('/watchlist/add', data)
}

export function updateWatchlistItem(code, data) {
  return request.put(`/watchlist/${code}`, data)
}

export function deleteWatchlistItem(code) {
  return request.delete(`/watchlist/${code}`)
}
