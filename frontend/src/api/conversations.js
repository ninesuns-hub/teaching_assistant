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

export async function deleteConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`, { method: 'DELETE' })
}

export async function renameConversation(conversationId, title) {
  return request(`/api/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export async function submitConversationFeedback(conversationId, messageId, feedbackType) {
  return request(`/api/conversations/${conversationId}/messages/${messageId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback_type: feedbackType }),
  })
}
