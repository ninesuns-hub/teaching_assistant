export const CHAT_ATTACHMENT_LIMITS = Object.freeze({
  maxCount: 3,
  maxImages: 1,
  maxImageBytes: 5 * 1024 * 1024,
  maxDocumentBytes: 20 * 1024 * 1024,
  maxTotalBytes: 50 * 1024 * 1024,
})

const ALLOWED_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
])
const ALLOWED_DOCUMENT_EXTENSIONS = new Set(['pdf', 'docx', 'pptx', 'ppsx'])

function extensionOf(file) {
  return String(file?.name || '').split('.').pop()?.toLowerCase() || ''
}

export function validateChatAttachmentSelection({
  selected,
  pendingDocuments = [],
  pendingImage = null,
}) {
  const files = Array.from(selected || [])
  if (
    pendingDocuments.length
    + (pendingImage ? 1 : 0)
    + files.length
    > CHAT_ATTACHMENT_LIMITS.maxCount
  ) {
    return { error: 'count' }
  }

  const imageFiles = files.filter(file => String(file.type || '').startsWith('image/'))
  const documentFiles = files.filter(file => !String(file.type || '').startsWith('image/'))
  if (
    imageFiles.length > CHAT_ATTACHMENT_LIMITS.maxImages
    || (imageFiles.length && pendingImage)
  ) {
    return { error: 'image_count' }
  }
  if (imageFiles.some(file => (
    !ALLOWED_IMAGE_TYPES.has(file.type)
    || file.size > CHAT_ATTACHMENT_LIMITS.maxImageBytes
  ))) {
    return { error: 'image_format_or_size' }
  }

  for (const file of documentFiles) {
    const extension = extensionOf(file)
    if (extension === 'doc' || extension === 'ppt') {
      return { error: 'legacy_document' }
    }
    if (
      !ALLOWED_DOCUMENT_EXTENSIONS.has(extension)
      || file.size > CHAT_ATTACHMENT_LIMITS.maxDocumentBytes
    ) {
      return { error: 'document_format_or_size' }
    }
  }

  const existingSize = (pendingImage?.file_size || 0)
    + pendingDocuments.reduce((sum, item) => sum + (item.file_size || 0), 0)
  const selectedSize = files.reduce((sum, file) => sum + (file.size || 0), 0)
  if (existingSize + selectedSize > CHAT_ATTACHMENT_LIMITS.maxTotalBytes) {
    return { error: 'total_size' }
  }
  return { imageFiles, documentFiles, error: null }
}
