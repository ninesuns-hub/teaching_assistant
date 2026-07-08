export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function getToken() {
  return localStorage.getItem('access_token')
}

export function setAuth(token, user) {
  localStorage.setItem('access_token', token)
  if (user) localStorage.setItem('user', JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
}

export function getStoredUser() {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
}

export async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
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
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (response.status === 204) return null
  return response.json()
}

export async function uploadRequest(path, formData) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()
  const response = await fetch(url, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  if (!response.ok) {
    let detail = `Upload failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}
