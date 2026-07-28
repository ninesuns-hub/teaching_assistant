import { request } from './httpClient'

function queryString(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const value = query.toString()
  return value ? `?${value}` : ''
}

export const fetchAdminUsers = params => request(`/api/admin/users${queryString(params)}`)
export const fetchAdminUser = userId => request(`/api/admin/users/${userId}`)
export const fetchAdminClasses = () => request('/api/admin/classes')
export const fetchAdminAuditLogs = params => request(`/api/admin/audit-logs${queryString(params)}`)
export const updateAdminUserProfile = (userId, payload) => request(`/api/admin/users/${userId}/profile`, { method: 'PATCH', body: JSON.stringify(payload) })
export const updateAdminUserRole = (userId, payload) => request(`/api/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify(payload) })
export const updateAdminUserStatus = (userId, payload) => request(`/api/admin/users/${userId}/status`, { method: 'PATCH', body: JSON.stringify(payload) })
export const updateAdminAccess = (userId, payload) => request(`/api/admin/users/${userId}/admin-access`, { method: 'PATCH', body: JSON.stringify(payload) })
export const addAdminClassMembership = (userId, payload) => request(`/api/admin/users/${userId}/class-memberships`, { method: 'POST', body: JSON.stringify(payload) })
export const removeAdminClassMembership = (userId, classId, reason = '') => request(`/api/admin/users/${userId}/class-memberships/${classId}${queryString({ reason })}`, { method: 'DELETE' })
export const transferAdminClass = (classId, payload) => request(`/api/admin/classes/${classId}/transfer`, { method: 'POST', body: JSON.stringify(payload) })
