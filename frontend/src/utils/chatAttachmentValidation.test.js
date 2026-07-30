import assert from 'node:assert/strict'
import test from 'node:test'

import { validateChatAttachmentSelection } from './chatAttachmentValidation.js'

const mb = value => value * 1024 * 1024
const file = (name, size, type = '') => ({ name, size, type })

test('accepts up to three mixed modern attachments', () => {
  const result = validateChatAttachmentSelection({
    selected: [
      file('question.png', mb(1), 'image/png'),
      file('paper.pdf', mb(10), 'application/pdf'),
      file('slides.pptx', mb(15)),
    ],
  })
  assert.equal(result.error, null)
  assert.equal(result.imageFiles.length, 1)
  assert.equal(result.documentFiles.length, 2)
})

test('rejects count, image, per-file, and total-size violations', () => {
  assert.equal(validateChatAttachmentSelection({
    selected: [file('a.pdf', 1), file('b.pdf', 1), file('c.pdf', 1), file('d.pdf', 1)],
  }).error, 'count')
  assert.equal(validateChatAttachmentSelection({
    selected: [
      file('a.png', 1, 'image/png'),
      file('b.jpg', 1, 'image/jpeg'),
    ],
  }).error, 'image_count')
  assert.equal(validateChatAttachmentSelection({
    selected: [file('large.pdf', mb(21))],
  }).error, 'document_format_or_size')
  assert.equal(validateChatAttachmentSelection({
    selected: [file('new.pdf', mb(11))],
    pendingDocuments: [
      { file_size: mb(20) },
      { file_size: mb(20) },
    ],
  }).error, 'total_size')
})

test('rejects legacy Office formats with a distinct reason', () => {
  assert.equal(validateChatAttachmentSelection({
    selected: [file('legacy.doc', mb(1))],
  }).error, 'legacy_document')
  assert.equal(validateChatAttachmentSelection({
    selected: [file('legacy.ppt', mb(1))],
  }).error, 'legacy_document')
})
