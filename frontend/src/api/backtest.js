import request from './request'

export function getBacktestStats(params) {
  return request.get('/backtest/stats', { params })
}

export function getBacktestList(params) {
  return request.get('/backtest/list', { params })
}

export function getBacktestTrend(params) {
  return request.get('/backtest/trend', { params })
}

export function getStockBacktest(stockCode) {
  return request.get(`/backtest/stock/${stockCode}`)
}
