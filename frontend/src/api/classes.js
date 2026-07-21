import { request, uploadRequest, getToken, API_BASE_URL } from './httpClient'

export async function fetchMyClasses() {
  return request('/api/classes/mine')
}

export async function createClass(name) {
  return request('/api/classes', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export async function joinClass(inviteCode) {
  return request('/api/classes/join', {
    method: 'POST',
    body: JSON.stringify({ invite_code: inviteCode }),
  })
}

export async function fetchClassMaterials(classId) {
  return request(`/api/classes/${classId}/materials`)
}

export async function uploadClassMaterial(classId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadRequest(`/api/classes/${classId}/materials`, formData)
}

export async function fetchMaterialFile(classId, materialId, download = false) {
  const query = download ? '?download=true' : ''
  const url = `${API_BASE_URL}/api/classes/${classId}/materials/${materialId}/file${query}`
  const token = getToken()
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.blob()
}

export async function fetchMaterialPreview(classId, materialId) {
  const url = `${API_BASE_URL}/api/classes/${classId}/materials/${materialId}/preview`
  const token = getToken()
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.blob()
}
