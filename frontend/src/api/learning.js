import { request } from './httpClient'

export async function fetchClassStudents(classId) {
  return request(`/api/learning/classes/${classId}/students`)
}

export async function addClassStudent(classId, payload) {
  return request(`/api/learning/classes/${classId}/students`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function removeClassStudent(classId, studentId) {
  return request(`/api/learning/classes/${classId}/students/${studentId}`, { method: 'DELETE' })
}

export async function generateStudentReport(classId, studentId) {
  return request(`/api/learning/classes/${classId}/students/${studentId}/report`, { method: 'POST' })
}

export async function fetchStudentReports(classId, studentId) {
  return request(`/api/learning/classes/${classId}/students/${studentId}/reports`)
}

export async function generateMyReport(classId) {
  return request(`/api/learning/me/report?class_id=${classId}`, { method: 'POST' })
}

export async function generateClassFeedback(classId) {
  return request(`/api/learning/classes/${classId}/feedback`, { method: 'POST' })
}

export async function fetchClassFeedback(classId) {
  return request(`/api/learning/classes/${classId}/feedback`)
}

export async function fetchReportDetail(reportId) {
  return request(`/api/learning/reports/${reportId}`)
}

export async function fetchFeedbackDetail(feedbackId) {
  return request(`/api/learning/feedback/${feedbackId}`)
}
export async function fetchLearningAssistantStatus(classId) {
  return request(`/api/learning/assistant-status?class_id=${classId}`)
}
