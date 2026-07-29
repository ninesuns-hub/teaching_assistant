export const PREVIEWABLE_EXTENSIONS = new Set([
  'pdf',
  'png',
  'jpg',
  'jpeg',
  'pptx',
  'ppsx',
  'docx',
])

export function getFileExtension(file = {}) {
  const declared = String(file.file_type || '').toLowerCase().replace(/^\./, '')
  if (declared) return declared
  const filename = String(file.filename || '')
  const dotIndex = filename.lastIndexOf('.')
  return dotIndex >= 0 ? filename.slice(dotIndex + 1).toLowerCase() : ''
}

export function getFileCategory(file) {
  const extension = getFileExtension(file)
  if (extension === 'pdf') return 'pdf'
  if (['doc', 'docx'].includes(extension)) return 'word'
  if (['ppt', 'pptx', 'ppsx'].includes(extension)) return 'presentation'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(extension)) return 'image'
  if (['zip', 'rar', '7z'].includes(extension)) return 'archive'
  return 'file'
}

export function getPreviewKind(file) {
  const extension = getFileExtension(file)
  if (!PREVIEWABLE_EXTENSIONS.has(extension)) return 'unsupported'
  if (extension === 'pdf') return 'pdf'
  if (['png', 'jpg', 'jpeg'].includes(extension)) return 'image'
  return 'html'
}

export function formatFileSize(bytes = 0) {
  const value = Number(bytes) || 0
  if (value <= 0) return ''
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`
  return `${(value / 1024 / 1024).toFixed(2)} MB`
}
