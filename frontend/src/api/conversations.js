import { request } from './httpClient'

export async function fetchConversations() {
  return request('/api/conversations')
}

export async function createConversation(classId = null) {
  const query = classId ? `?class_id=${classId}` : ''
  return request(`/api/conversations${query}`, { method: 'POST' })
}

export async function fetchConversationMessages(conversationId) {
  return request(`/api/conversations/${conversationId}/messages`)
}
