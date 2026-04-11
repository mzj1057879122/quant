import request from './request'

export function getStrategyRules() {
  return request.get('/strategy/rules')
}

export function updateStrategyRule(key, value, updatedBy = 'xiaozhua') {
  return request.put(`/strategy/rules/${key}`, { value, updatedBy })
}
