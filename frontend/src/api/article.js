import request from './request'

export function submitArticle(data) {
  return request.post('/articles', data)
}

export function submitFromUrl(url, articleDate) {
  const data = { url }
  if (articleDate) data.articleDate = articleDate
  return request.post('/articles/from-url', data)
}

export function batchUpdateDate(articleIds, articleDate) {
  return request.put('/articles/batch-update-date', { articleIds, articleDate })
}

export function getArticleStatus(articleId) {
  return request.get(`/articles/${articleId}`)
}

export function getArticleList(params) {
  return request.get('/articles', { params })
}

export function retryArticle(articleId) {
  return request.post(`/articles/${articleId}/retry`)
}

export function deleteArticle(articleId) {
  return request.delete(`/articles/${articleId}`)
}

export function triggerDailySummary(summaryDate) {
  return request.post('/articles/daily-summary', null, { params: { summaryDate } })
}

export function getDailySummary(summaryDate) {
  return request.get(`/articles/daily-summary/${summaryDate}`)
}

export function getDailySummaries(params) {
  return request.get('/articles/daily-summaries', { params })
}
