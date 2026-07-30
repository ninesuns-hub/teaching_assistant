import {
  API_BASE_URL,
  getToken,
  request,
  uploadRequest,
} from './httpClient'


export async function uploadChatAttachments(files) {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  return uploadRequest('/api/chat/attachments', formData)
}


export function fetchChatAttachment(attachmentId) {
  return request(`/api/chat/attachments/${attachmentId}`)
}


export function deletePendingChatAttachment(attachmentId) {
  return request(`/api/chat/attachments/${attachmentId}`, {
    method: 'DELETE',
  })
}


export async function fetchChatAttachmentFile(attachmentId, download = false) {
  const token = getToken()
  const query = download ? '?download=true' : ''
  const response = await fetch(
    `${API_BASE_URL}/api/chat/attachments/${attachmentId}/file${query}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  )
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch {
      // Preserve the HTTP fallback for non-JSON responses.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.blob()
}
