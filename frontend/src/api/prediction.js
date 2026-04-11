import request from './request'

export function getDailyPrediction(params) {
  return request.get('/prediction/daily', { params })
}
