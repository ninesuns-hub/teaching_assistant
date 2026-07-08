import { request } from './httpClient'

export async function sendCode(email) {
  return request('/api/auth/send-code', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function register(payload) {
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function login(payload) {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function selectRole(role) {
  return request('/api/auth/select-role', {
    method: 'POST',
    body: JSON.stringify({ role }),
  })
}

export async function getMe() {
  return request('/api/auth/me')
}
