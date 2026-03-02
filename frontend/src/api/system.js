import request from './request'

export function healthCheck() {
  return request.get('/system/health')
}

export function getTaskStatus() {
  return request.get('/system/task-status')
}

export function runTask(taskName) {
  return request.post(`/system/run-task/${taskName}`)
}
