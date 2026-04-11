import request from './request'

export function getLatestBrief(params) {
  return request.get('/brief/latest', { params })
}

export function getBriefList(params) {
  return request.get('/brief/list', { params })
}

export function getBriefByDate(briefDate) {
  return request.get(`/brief/${briefDate}`)
}
