import request from './request'

export function submitKnowledge(data) {
  return request.post('/knowledge', data)
}

export function submitKnowledgeFromUrl(data) {
  return request.post('/knowledge/from-url', data)
}

export function getKnowledgeList(params) {
  return request.get('/knowledge', { params })
}

export function getKnowledge(id) {
  return request.get(`/knowledge/${id}`)
}

export function updateKnowledge(id, data) {
  return request.put(`/knowledge/${id}`, data)
}

export function retryKnowledge(id) {
  return request.post(`/knowledge/${id}/retry`)
}

export function reExtractKnowledge(id) {
  return request.post(`/knowledge/${id}/re-extract`)
}

export function deleteKnowledge(id) {
  return request.delete(`/knowledge/${id}`)
}

export function rebuildFramework() {
  return request.post('/knowledge/framework/rebuild')
}

export function getLatestFramework() {
  return request.get('/knowledge/framework/latest')
}

export function getFrameworkHistory(params) {
  return request.get('/knowledge/framework/history', { params })
}
