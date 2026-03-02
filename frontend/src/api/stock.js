import request from './request'

export function getStockList(params) {
  return request.get('/stocks', { params })
}

export function getStockDetail(stockCode) {
  return request.get(`/stocks/${stockCode}`)
}

export function syncStocks() {
  return request.post('/stocks/sync')
}

export function getQuotes(stockCode, params) {
  return request.get(`/quotes/${stockCode}`, { params })
}

export function getLatestQuote(stockCode) {
  return request.get(`/quotes/${stockCode}/latest`)
}

export function fetchQuotes(stockCode) {
  return request.post('/quotes/fetch', null, { params: { stockCode } })
}
