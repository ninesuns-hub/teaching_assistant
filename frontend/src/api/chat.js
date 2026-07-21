import { getToken } from './httpClient'

export async function sendChatMessage(payload, onChunk) {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
  const token = getToken()
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const data = await response.json()
      if (Array.isArray(data.detail)) {
        detail = data.detail.map((item) => item.msg || JSON.stringify(item)).join('；')
      } else {
        detail = data.detail || data.message || detail
      }
    } catch {
      // Keep the HTTP status fallback when the response body is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  const conversationId = response.headers.get('X-Conversation-Id')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    if (onChunk) onChunk(chunk)
  }

  return conversationId ? Number(conversationId) : null
}

export async function sendWelcomeMessage(classId, onChunk) {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
  const token = getToken()
  const query = classId ? `?class_id=${classId}` : ''
  const response = await fetch(`${API_BASE_URL}/api/chat/welcome${query}`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch {
      // Keep the HTTP status fallback when the response body is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const chunk = decoder.decode(value, { stream: true })
    if (onChunk) onChunk(chunk)
  }
}
