import { request } from './httpClient'

export async function login(payload) {
  // TODO: 后续对接登录接口
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function register(payload) {
  // TODO: 后续对接注册接口
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
