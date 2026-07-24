import { getToken, request } from './httpClient'

async function consumeChatStream(response, onEvent) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const isSseV1 = response.headers.get('X-Chat-Stream-Protocol') === 'sse-v1'
  let buffer = ''
  let donePayload = {}

  if (!isSseV1) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const delta = decoder.decode(value, { stream: true })
      if (delta) onEvent?.({ type: 'content', delta })
    }
    return donePayload
  }

  const dispatchFrame = (frame) => {
    if (!frame.trim()) return
    let type = 'message'
    const dataLines = []
    frame.split(/\r?\n/).forEach((line) => {
      if (line.startsWith('event:')) type = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    })
    if (!dataLines.length) return
    let payload
    try {
      payload = JSON.parse(dataLines.join('\n'))
    } catch {
      payload = { message: dataLines.join('\n') }
    }
    if (type === 'done') donePayload = payload
    onEvent?.({ type, ...payload })
  }

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const frames = buffer.split(/\r?\n\r?\n/)
    buffer = frames.pop() || ''
    frames.forEach(dispatchFrame)
    if (done) break
  }
  if (buffer.trim()) dispatchFrame(buffer)
  return donePayload
}

export async function sendChatMessage(payload, onEvent) {
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
  const donePayload = await consumeChatStream(response, onEvent)
  return {
    conversationId: donePayload.conversation_id || conversationId || null,
    messageId: donePayload.message_id || null,
  }
}

export async function sendWelcomeMessage(classId, onChunk, signal) {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
  const token = getToken()
  const query = classId ? `?class_id=${classId}` : ''
  const response = await fetch(`${API_BASE_URL}/api/chat/welcome${query}`, {
    method: 'POST',
    signal,
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

  await consumeChatStream(response, (event) => {
    if (event.type === 'content' && event.delta) onChunk?.(event.delta)
    else if (event.type === 'error' && event.message) onChunk?.(event.message)
  })
}

export function repairMermaidDiagram(payload) {
  return request('/api/chat/mermaid/repair', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 60_000,
  })
}
