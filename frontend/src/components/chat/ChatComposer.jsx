export default function ChatComposer({
  variant,
  canChat,
  chatPlaceholder,
  composerInputRef,
  handleKeyDown,
  handlePickImage,
  handleSend,
  imageInputRef,
  input,
  isSending,
  pendingImage,
  setInput,
  setPendingImage,
  t,
}) {
  return (
    <div className={`composer-block composer-block--${variant}`}>
      {pendingImage && (
        <div className="image-preview-bar">
          <img src={pendingImage.previewUrl} alt="" className="image-preview-thumb" />
          <button type="button" className="image-preview-remove" onClick={() => setPendingImage(null)} aria-label={t.auth.removeImage || 'Remove image'}>&times;</button>
        </div>
      )}
      <form className={`composer composer--${variant}`} onSubmit={handleSend} aria-busy={isSending}>
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="visually-hidden-file-input"
          disabled={!canChat || isSending}
          onChange={handlePickImage}
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
          title={t.auth.attachImage}
          disabled={!canChat || isSending}
          onClick={() => imageInputRef.current?.click()}
          aria-label={t.auth.attachImage}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M21.44 11.05l-8.49 8.49a5.25 5.25 0 0 1-7.42-7.42l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.2 9.19a1.75 1.75 0 0 1-2.47-2.47l8.49-8.48" />
          </svg>
        </button>
        <button type="submit" disabled={!canChat || (!input.trim() && !pendingImage) || isSending} aria-busy={isSending}>
          {isSending ? t.sending : t.send}
        </button>
      </form>
    </div>
  )
}
