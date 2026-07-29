import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatFileSize,
  getFileCategory,
  getFileExtension,
  getPreviewKind,
} from './fileTypes.js'

test('normalizes declared and filename extensions', () => {
  assert.equal(getFileExtension({ file_type: '.PDF' }), 'pdf')
  assert.equal(getFileExtension({ filename: 'report.Final.DOCX' }), 'docx')
})

test('maps common files to semantic icon categories', () => {
  assert.equal(getFileCategory({ filename: 'paper.pdf' }), 'pdf')
  assert.equal(getFileCategory({ filename: 'report.docx' }), 'word')
  assert.equal(getFileCategory({ filename: 'slides.pptx' }), 'presentation')
  assert.equal(getFileCategory({ filename: 'photo.jpg' }), 'image')
  assert.equal(getFileCategory({ filename: 'source.zip' }), 'archive')
})

test('classifies inline preview support', () => {
  assert.equal(getPreviewKind({ filename: 'paper.pdf' }), 'pdf')
  assert.equal(getPreviewKind({ filename: 'photo.png' }), 'image')
  assert.equal(getPreviewKind({ filename: 'slides.pptx' }), 'html')
  assert.equal(getPreviewKind({ filename: 'legacy.doc' }), 'unsupported')
  assert.equal(getPreviewKind({ filename: 'source.zip' }), 'unsupported')
})

test('formats attachment sizes for compact display', () => {
  assert.equal(formatFileSize(0), '')
  assert.equal(formatFileSize(512), '1 KB')
  assert.equal(formatFileSize(2 * 1024 * 1024), '2.00 MB')
})
