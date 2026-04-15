import request from './request'

export function getWatchlistItems(params) {
  return request.get('/watchlist/items', { params })
}

export function addWatchlistItem(data) {
  return request.post('/watchlist/add', data)
}

export function updateWatchlistItem(code, data) {
  return request.put(`/watchlist/${code}`, data)
}

export function updateWatchlistSector(code, sector) {
  return request.patch(`/watchlist/items/${code}/sector`, { sector })
}

export function reorderWatchlist(items) {
  return request.post('/watchlist/reorder', items)
}

export function getSectorColors() {
  return request.get('/watchlist/sector-colors')
}

export function saveSectorColor(sector, color) {
  return request.post('/watchlist/sector-colors', { sector, color })
}

export function deleteWatchlistItem(code) {
  return request.delete(`/watchlist/${code}`)
}
