import request from './request'

export function getLatestRuleReview() {
  return request.get('/rule-review/latest')
}

export function getRuleReviewList(params) {
  return request.get('/rule-review/list', { params })
}
