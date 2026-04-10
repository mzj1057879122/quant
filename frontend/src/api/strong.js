import request from './request'

export function getStrongStockList(params) {
  return request.get('/strong/list', { params })
}
