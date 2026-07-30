import FileTypeIcon from '../FileTypeIcon'
import { formatFileSize } from '../../utils/fileTypes'


function attachmentStatus(item, language) {
  const zh = language === 'zh'
  if (item.status === 'ready') {
    return item.truncated
      ? zh ? '已就绪 · 内容较长，已截断' : 'Ready · long content truncated'
      : zh ? '已就绪' : 'Ready'
  }
  if (item.status === 'failed') {
    return item.error_message || (zh ? '解析失败' : 'Parsing failed')
  }
  if (item.status === 'running') {
    const progress = item.progress_total
      ? ` ${item.progress_current || 0}/${item.progress_total}`
      : ''
    return item.requires_ocr
      ? `${zh ? '正在 OCR' : 'OCR in progress'}${progress}`
      : `${zh ? '正在解析' : 'Parsing'}${progress}`
  }
  return zh ? '等待解析' : 'Queued'
}


export default function ChatComposer({
  variant,
  attachmentInputRef,
  canChat,
  chatPlaceholder,
  composerInputRef,
  handleKeyDown,
  handlePickAttachment,
  handleRemovePendingDocument,
  handleSend,
  input,
  isAttachmentUploading,
  isSending,
  language,
  pendingDocuments,
  pendingImage,
  setInput,
  setPendingImage,
  t,
}) {
  const documentsReady = pendingDocuments.every(item => item.status === 'ready')
  const hasAttachments = Boolean(pendingImage || pendingDocuments.length)
  const attachmentLabel = language === 'zh' ? '添加图片或文档' : 'Attach image or document'

  return (
    <div className={`composer-block composer-block--${variant}`}>
      {hasAttachments && (
        <div className="chat-attachment-tray">
          {pendingImage && (
            <div className="chat-pending-attachment is-image">
              <img src={pendingImage.previewUrl} alt="" className="image-preview-thumb" />
              <div className="chat-pending-attachment-info">
                <strong title={pendingImage.filename}>{pendingImage.filename}</strong>
                <span>{formatFileSize(pendingImage.file_size)}</span>
              </div>
              <button
                type="button"
                className="chat-pending-attachment-remove"
                onClick={() => setPendingImage(null)}
                aria-label={t.auth.removeImage || 'Remove image'}
              >
                &times;
              </button>
            </div>
          )}
          {pendingDocuments.map(item => (
            <div
              className={`chat-pending-attachment is-${item.status}`}
              key={item.id}
            >
              <FileTypeIcon file={item} />
              <div className="chat-pending-attachment-info">
                <strong title={item.filename}>{item.filename}</strong>
                <span className={item.status === 'failed' ? 'is-error' : ''}>
                  {formatFileSize(item.file_size)} · {attachmentStatus(item, language)}
                </span>
                {(item.status === 'queued' || item.status === 'running') && (
                  <span className="chat-attachment-progress" aria-hidden="true">
                    <i
                      style={{
                        width: item.progress_total
                          ? `${Math.min(100, ((item.progress_current || 0) / item.progress_total) * 100)}%`
                          : '18%',
                      }}
                    />
                  </span>
                )}
              </div>
              <button
                type="button"
                className="chat-pending-attachment-remove"
                onClick={() => handleRemovePendingDocument(item)}
                aria-label={language === 'zh' ? `移除 ${item.filename}` : `Remove ${item.filename}`}
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
      <form className={`composer composer--${variant}`} onSubmit={handleSend} aria-busy={isSending}>
        <input
          ref={attachmentInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp,image/gif,.pdf,.docx,.pptx,.ppsx"
          className="visually-hidden-file-input"
          disabled={!canChat || isSending || isAttachmentUploading}
          onChange={handlePickAttachment}
        />
        <textarea
          ref={composerInputRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={chatPlaceholder}
          disabled={!canChat || isSending}
          rows={1}
        />
        <button
          type="button"
          className="attach-image-btn"
          title={attachmentLabel}
          disabled={!canChat || isSending || isAttachmentUploading || (pendingDocuments.length + (pendingImage ? 1 : 0) >= 3)}
          onClick={() => attachmentInputRef.current?.click()}
          aria-label={attachmentLabel}
        >
          {isAttachmentUploading ? (
            <span className="attachment-upload-spinner" aria-hidden="true" />
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21.44 11.05l-8.49 8.49a5.25 5.25 0 0 1-7.42-7.42l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.2 9.19a1.75 1.75 0 0 1-2.47-2.47l8.49-8.48" />
            </svg>
          )}
        </button>
        <button
          type="submit"
          disabled={
            !canChat
            || (!input.trim() && !hasAttachments)
            || !documentsReady
            || isAttachmentUploading
            || isSending
          }
          aria-busy={isSending}
        >
          {isSending ? t.sending : t.send}
        </button>
      </form>
    </div>
  )
}
