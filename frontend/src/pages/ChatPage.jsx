import MarkdownMessage from '../components/MarkdownMessage'
import logoImg from '../assets/logo.png'
import SceneSwitcher from '../components/scenes/SceneSwitcher'
import { AuthImage, MessageActionIcon } from '../components/chat/MessageParts'

export default function ChatPage({ model }) {
  const { SCENE_OPTIONS, activeQuote, activeSceneKey, canChat, chatOpacity, chatPlaceholder, composerInputRef, dialRotation, handleCopyMessage, handleExampleSelect, handleFeedback, handleKeyDown, handleMouseDown, handlePickImage, handleRefreshExamples, handleSend, imageInputRef, input, isDragging, isSending, language, messages, messagesEndRef, pendingImage, quoteOpacity, setInput, setPendingImage, t, visibleExamplePrompts, welcomeContent, welcomeLoading, welcomeText } = model

  return (
    <section id="section-chat" className="section section-chat">
          <div className={`chat-shell ${messages.length > 0 ? 'active-chat' : 'empty-chat'}`}>
            <div className="chat-title">
              <img src={logoImg} alt="Logo" className="logo-img logo-img-lg" />
              <h1>{t.title}</h1>
            </div>
            <div className={`messages-list ${messages.length > 0 ? 'has-messages' : 'welcome-state'}`}>
              {messages.length === 0 && (
                <div className="welcome-card">
                  {welcomeContent ? (
                    <MarkdownMessage content={welcomeContent} />
                  ) : welcomeLoading ? (
                    <div className="thinking-indicator" aria-live="polite">
                      <span />
                      <span />
                      <span />
                      <em>{language === 'zh' ? '正在准备介绍' : 'Preparing intro'}</em>
                    </div>
                  ) : (
                    <p>{welcomeText}</p>
                  )}
                </div>
              )}
              {messages.length === 0 && canChat && visibleExamplePrompts.length > 0 && (
                <section className="example-prompts" aria-label={t.exampleQuestions}>
                  <div className="example-prompts-header">
                    <span>{t.exampleQuestions}</span>
                    <button
                      type="button"
                      className="refresh-examples-btn"
                      onClick={handleRefreshExamples}
                      aria-label={t.refreshExamples}
                    >
                      <span aria-hidden="true">↻</span>
                      {t.refreshExamples}
                    </button>
                  </div>
                  <div className="example-prompts-grid">
                    {visibleExamplePrompts.map(prompt => (
                      <button key={prompt} type="button" className="example-prompt-card" onClick={() => handleExampleSelect(prompt)}>
                        {prompt}
                      </button>
                    ))}
                  </div>
                </section>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`message-item ${msg.role}`}>
                  <div className="message-content">
                    {(msg.imagePreview || msg.imagePath) && (
                      <AuthImage path={msg.imagePath} previewUrl={msg.imagePreview} />
                    )}
                    {msg.content && msg.content !== '[图片]' && msg.content !== '[Image]' && (
                      msg.role === 'assistant' ? (
                        <MarkdownMessage content={msg.content} />
                      ) : (
                        <p className="message-text">{msg.content}</p>
                      )
                    )}
                    {msg.content && (msg.content === '[图片]' || msg.content === '[Image]') && !(msg.imagePreview || msg.imagePath) && (
                      <p className="message-text">{msg.content}</p>
                    )}
                    {msg.role === 'assistant' && !msg.content && (
                      <div className="thinking-indicator" aria-live="polite">
                        <span />
                        <span />
                        <span />
                        <em>{language === 'zh' ? '正在思考' : 'Thinking'}</em>
                      </div>
                    )}
                    {msg.role === 'assistant' && msg.id && msg.content && (
                      <>
                        <div className="message-actions">
                          <button
                            type="button"
                            className="feedback-btn"
                            title={t.auth.feedbackCopy}
                            aria-label={t.auth.feedbackCopy}
                            onClick={() => handleCopyMessage(msg.content)}
                          >
                            <MessageActionIcon type="copy" />
                          </button>
                          <button
                            type="button"
                            className={`feedback-btn ${msg.feedback === 'positive' ? 'active' : ''}`}
                            title={t.auth.feedbackHelpful}
                            aria-label={t.auth.feedbackHelpful}
                            onClick={() => handleFeedback(idx, 'positive')}
                          >
                            <MessageActionIcon type="up" />
                          </button>
                          <button
                            type="button"
                            className={`feedback-btn ${msg.feedback === 'negative' ? 'active' : ''}`}
                            title={t.auth.feedbackUnhelpful}
                            aria-label={t.auth.feedbackUnhelpful}
                            onClick={() => handleFeedback(idx, 'negative')}
                          >
                            <MessageActionIcon type="down" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            {pendingImage && (
              <div className="image-preview-bar">
                <img src={pendingImage.previewUrl} alt="" className="image-preview-thumb" />
                <button type="button" className="image-preview-remove" onClick={() => setPendingImage(null)}>×</button>
              </div>
            )}
            <form className="composer" onSubmit={handleSend}>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                hidden
                onChange={handlePickImage}
              />
              <textarea
                ref={composerInputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
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
              <button type="submit" disabled={!canChat || (!input.trim() && !pendingImage) || isSending}>
                {isSending ? t.sending : t.send}
              </button>
            </form>
          </div>

          <SceneSwitcher
            scenes={SCENE_OPTIONS}
            activeScene={activeSceneKey}
            rotation={dialRotation}
            dragging={isDragging}
            opacity={chatOpacity}
            onMouseDown={handleMouseDown}
          />
          <footer className="scene-quote-footer" style={{
            opacity: messages.length > 0 ? 0 : quoteOpacity,
            visibility: messages.length > 0 ? 'hidden' : 'visible',
            pointerEvents: 'none'
          }}>
            <blockquote className="scene-quote">
              <p>{activeQuote.text}</p>
              <cite>- {activeQuote.author}</cite>
            </blockquote>
          </footer>

        </section>
  )
}
