import { request } from './httpClient'

export function fetchMemorySettings() {
  return request('/api/memory/settings')
}

export function updateMemorySettings(enabled) {
  return request('/api/memory/settings', {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  })
}

export function fetchMemories(params = {}) {
  const query = new URLSearchParams()
  if (params.classId) query.set('class_id', params.classId)
  if (params.memoryType) query.set('memory_type', params.memoryType)
  if (params.cursor) query.set('cursor', params.cursor)
  const suffix = query.toString() ? `?${query}` : ''
  return request(`/api/memories${suffix}`)
}

export function editMemory(memoryId, content) {
  return request(`/api/memories/${memoryId}`, {
    method: 'PATCH',
    body: JSON.stringify({ content }),
  })
}

export function deleteMemory(memoryId) {
  return request(`/api/memories/${memoryId}`, { method: 'DELETE' })
}

export function clearMemories() {
  return request('/api/memories?scope=all', { method: 'DELETE' })
}
