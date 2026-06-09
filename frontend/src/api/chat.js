import { request } from './httpClient'

export async function sendChatMessage(payload, onChunk) {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
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
