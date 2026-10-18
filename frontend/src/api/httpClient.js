export const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? ''
export const DEFAULT_REQUEST_TIMEOUT_MS = 12_000

export class ServiceUnavailableError extends Error {
  constructor(message = '服务暂时无响应，请稍后再试') {
    super(message)
    this.name = 'ServiceUnavailableError'
    this.code = 'SERVICE_UNAVAILABLE'
  }
}

export class RequestTimeoutError extends ServiceUnavailableError {
  constructor(message) {
    super(message)
    this.name = 'RequestTimeoutError'
    this.code = 'REQUEST_TIMEOUT'
  }
}

async function fetchWithTimeout(url, options = {}, defaultTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS) {
  const { timeoutMs = defaultTimeoutMs, signal: callerSignal, ...fetchOptions } = options
  const controller = new AbortController()
  let timedOut = false
  const forwardAbort = () => controller.abort()

  if (callerSignal?.aborted) controller.abort()
  else callerSignal?.addEventListener('abort', forwardAbort, { once: true })

  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    return await authenticatedFetch(url, { ...fetchOptions, signal: controller.signal })
  } catch (error) {
    if (timedOut) throw new RequestTimeoutError()
    if (error instanceof TypeError) throw new ServiceUnavailableError()
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    callerSignal?.removeEventListener('abort', forwardAbort)
  }
}

export function getToken() {
  const token = localStorage.getItem('access_token')
  if (token && isAuthExpired()) {
    expireAuth()
    return null
  }
  return token
}

export function setAuth(token, user, session) {
  localStorage.setItem('access_token', token)
  if (user) localStorage.setItem('user', JSON.stringify(user))
  sessionStorage.removeItem('auth_expired_notice')
  if (session?.expires_at && session?.idle_expires_at) {
    localStorage.setItem('auth_session', JSON.stringify({
      expires_at: session.expires_at, idle_expires_at: session.idle_expires_at,
    }))
  }
}

export function clearAuth() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
  localStorage.removeItem('auth_session')
}

export function getStoredUser() {
  if (!getToken()) return null
  try { return JSON.parse(localStorage.getItem('user') || 'null') } catch { return null }
}

export function isAuthExpired(now = Date.now()) {
  try {
    const session = JSON.parse(localStorage.getItem('auth_session') || 'null')
    if (session && Math.min(session.expires_at, session.idle_expires_at) * 1000 <= now) return true
    const token = localStorage.getItem('access_token')
    if (!token) return false
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return !payload.sid || !payload.exp || payload.exp * 1000 <= now
  } catch { return true }
}

export function expireAuth() {
  const hadToken = Boolean(localStorage.getItem('access_token'))
  clearAuth()
  if (hadToken) {
    sessionStorage.setItem('auth_expired_notice', '1')
    window.dispatchEvent(new Event('auth:expired'))
  }
}

export async function authenticatedFetch(url, options = {}) {
  const token = getToken()
  const headers = new Headers(options.headers || {})
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(url, { ...options, headers })
  const isLogin = /\/api\/auth\/(login|register|send-code)(?:\?|$)/.test(String(url))
  if (response.status === 401 && !isLogin && token === localStorage.getItem('access_token')) expireAuth()
  return response
}

export async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()

  const response = await fetchWithTimeout(url, {
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
    } catch {
      // Keep the status-based fallback when the response body is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (response.status === 204) return null
  return response.json()
}

export async function uploadRequest(path, formData) {
  const url = `${API_BASE_URL}${path}`
  const token = getToken()
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
    timeoutMs: 60_000,
  }, 60_000)
  if (!response.ok) {
    let detail = `Upload failed: ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || data.message || detail
    } catch {
      // Keep the status-based fallback when the response body is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return response.json()
}
