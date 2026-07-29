import { useEffect, useRef } from 'react'

import FileTypeIcon from './FileTypeIcon'
import { formatFileSize } from '../utils/fileTypes'

export default function AttachmentPreviewModal({
  language,
  onClose,
  onDownload,
  preview,
  scene,
}) {
  const closeButtonRef = useRef(null)
  const modalRef = useRef(null)
  const previousFocusRef = useRef(null)
  const isOpen = Boolean(preview)

  useEffect(() => {
    if (!isOpen) return undefined
    previousFocusRef.current = document.activeElement
    closeButtonRef.current?.focus()
    const handleKeyDown = event => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = modalRef.current?.querySelectorAll(
        'button:not(:disabled), a[href], iframe, object, [tabindex]:not([tabindex="-1"])',
      )
      if (!focusable?.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      previousFocusRef.current?.focus?.()
    }
  }, [isOpen, onClose])

  if (!preview) return null
  const zh = language === 'zh'

  return (
    <div className="attachment-preview-overlay" data-scene={scene} onMouseDown={onClose}>
      <section
        ref={modalRef}
        className="attachment-preview-modal"
        role="dialog"
        aria-modal="true"
        aria-label={zh ? '附件预览' : 'Attachment preview'}
        onMouseDown={event => event.stopPropagation()}
      >
        <header className="attachment-preview-header">
          <FileTypeIcon file={preview} size="large" />
          <div className="attachment-preview-title">
            <strong>{preview.filename}</strong>
            {formatFileSize(preview.file_size) && <span>{formatFileSize(preview.file_size)}</span>}
          </div>
          <div className="attachment-preview-actions">
            <button type="button" className="download-btn" onClick={onDownload}>
              {zh ? '下载' : 'Download'}
            </button>
            <button
              ref={closeButtonRef}
              type="button"
              className="attachment-preview-close"
              aria-label={zh ? '关闭预览' : 'Close preview'}
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </header>

        <div className="attachment-preview-body">
          {preview.status === 'loading' && (
            <div className="attachment-preview-state">{zh ? '正在加载预览…' : 'Loading preview…'}</div>
          )}
          {preview.status === 'error' && (
            <div className="attachment-preview-state is-error">
              <strong>{zh ? '预览加载失败' : 'Unable to load preview'}</strong>
              <p>{preview.error}</p>
            </div>
          )}
          {preview.status === 'unsupported' && (
            <div className="attachment-preview-state">
              <FileTypeIcon file={preview} size="large" />
              <strong>{zh ? '该格式暂不支持在线预览' : 'Preview is unavailable for this format'}</strong>
              <p>{zh ? '请使用右上角的下载按钮在本地查看。' : 'Use the download button to open it locally.'}</p>
            </div>
          )}
          {preview.status === 'ready' && preview.previewKind === 'image' && (
            <img className="attachment-preview-image" src={preview.url} alt={preview.filename} />
          )}
          {preview.status === 'ready' && preview.previewKind === 'pdf' && (
            <object className="attachment-preview-document" data={preview.url} type="application/pdf">
              <p>{zh ? '浏览器无法显示PDF，请下载后查看。' : 'This browser cannot display the PDF.'}</p>
            </object>
          )}
          {preview.status === 'ready' && preview.previewKind === 'html' && (
            <iframe
              className="attachment-preview-document"
              src={preview.url}
              sandbox=""
              title={preview.filename}
            />
          )}
        </div>
      </section>
    </div>
  )
}
