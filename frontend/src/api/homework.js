import { request, uploadRequest, getToken, API_BASE_URL } from './httpClient'

export async function fetchHomeworks(classId) {
  return request(`/api/homework/classes/${classId}/homeworks`)
}

export async function createHomework(classId, { title, description = '', dueAt = '', files = [] }) {
  const formData = new FormData()
  formData.append('title', title)
  formData.append('description', description || '')
  formData.append('due_at', dueAt || '')
  files.forEach(file => formData.append('files', file))
  return uploadRequest(`/api/homework/classes/${classId}/homeworks`, formData)
}

export async function deleteHomework(homeworkId) {
  return request(`/api/homework/homeworks/${homeworkId}`, { method: 'DELETE' })
}

export async function submitHomework(
  homeworkId,
  { content = '', files = [], retainedAttachmentIds = [] },
) {
  const formData = new FormData()
  formData.append('content', content || '')
  files.forEach(file => formData.append('files', file))
  formData.append('retained_attachment_ids', JSON.stringify(retainedAttachmentIds))
  return uploadRequest(`/api/homework/homeworks/${homeworkId}/submit`, formData)
}

export async function fetchHomeworkSubmissions(homeworkId) {
  return request(`/api/homework/homeworks/${homeworkId}/submissions`)
}

async function fetchBlob(path) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
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
  return response.blob()
}

export async function downloadHomeworkAttachment(homeworkId) {
  return fetchBlob(`/api/homework/homeworks/${homeworkId}/attachment`)
}

export async function fetchHomeworkAttachmentFile(homeworkId, attachmentId, download = false) {
  const query = download ? '?download=true' : ''
  return fetchBlob(`/api/homework/homeworks/${homeworkId}/attachments/${attachmentId}/file${query}`)
}

export async function downloadSubmissionFile(submissionId) {
  return fetchBlob(`/api/homework/submissions/${submissionId}/file`)
}

export async function fetchSubmissionAttachmentFile(
  submissionId,
  attachmentId,
  download = false,
) {
  const query = download ? '?download=true' : ''
  return fetchBlob(
    `/api/homework/submissions/${submissionId}/attachments/${attachmentId}/file${query}`,
  )
}
