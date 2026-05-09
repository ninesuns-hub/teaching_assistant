import { request } from './httpClient'

export async function sendChatMessage(payload) {
  // TODO: 后续改为真实后端接口，例如 /api/chat
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
