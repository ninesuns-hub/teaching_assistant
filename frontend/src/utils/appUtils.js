export const CODE_COOLDOWN_SEC = 60
const CODE_COOLDOWN_KEY = 'verify_code_cooldown'
export const TONGJI_EMAIL_RE = /^[0-9]{7}@tongji\.edu\.cn$/

export function getRemainingCooldown(email) {
  try {
    const raw = sessionStorage.getItem(CODE_COOLDOWN_KEY)
    if (!raw) return 0
    const { email: savedEmail, expiresAt } = JSON.parse(raw)
    if (savedEmail !== email.trim().toLowerCase()) return 0
    return Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))
  } catch {
    return 0
  }
}

export function saveCooldown(email) {
  sessionStorage.setItem(CODE_COOLDOWN_KEY, JSON.stringify({
    email: email.trim().toLowerCase(),
    expiresAt: Date.now() + CODE_COOLDOWN_SEC * 1000,
  }))
}

export function getBeijingHour() {
  const hourPart = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    hour12: false,
  })
    .formatToParts(new Date())
    .find((part) => part.type === 'hour')

  return Number(hourPart?.value ?? 0)
}

export function getSceneByHour(hour) {
  if (hour >= 6 && hour < 17) return 'day'
  if (hour >= 17 && hour < 20) return 'sunset'
  return 'night'
}

export function formatConvDate(iso, todayLabel) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return todayLabel
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function getMaterialCategory(material) {
  const filename = (material.filename || '').toLowerCase()
  const extType = (material.file_type || '').toLowerCase()
  if (filename.includes('practice') || filename.includes('exercise') || filename.includes('homework') || filename.includes('quiz')) {
    return 'Practice'
  }
  if (filename.includes('book') || filename.includes('textbook')) {
    return 'Books'
  }
  if (extType === 'pptx' || filename.endsWith('.pptx') || filename.endsWith('.ppsx')) {
    return 'Slides'
  }
  return 'Notes'
}
