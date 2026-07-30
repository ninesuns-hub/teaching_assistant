import MarkdownMessage from '../components/MarkdownMessage'
import ChatComposer from '../components/chat/ChatComposer'
import { AuthImage, MessageActionIcon } from '../components/chat/MessageParts'
import SceneSwitcher from '../components/scenes/SceneSwitcher'
import FileTypeIcon from '../components/FileTypeIcon'
import { formatFileSize } from '../utils/fileTypes'


const ATTACHMENT_PLACEHOLDERS = new Set([
  '[图片]',
  '[Image]',
  '[文档]',
  '[Documents]',
  '[图片和文档]',
  '[Image and documents]',
])


function ChatAttachmentList({
  attachments,
  language,
  onDownload,
  onPreview,
}) {
  if (!attachments?.length) return null
  return (
    <div className="chat-message-attachments">
      {attachments.map(attachment => (
        <div className="chat-message-attachment" key={attachment.id}>
          <FileTypeIcon file={attachment} />
          <div className="chat-message-attachment-info">
            <strong title={attachment.filename}>{attachment.filename}</strong>
            {formatFileSize(attachment.file_size) && (
              <span>{formatFileSize(attachment.file_size)}</span>
            )}
          </div>
          <div className="chat-message-attachment-actions">
            <button type="button" onClick={() => onPreview(attachment)}>
              {language === 'zh' ? '预览' : 'Preview'}
            </button>
            <button type="button" onClick={() => onDownload(attachment)}>
              {language === 'zh' ? '下载' : 'Download'}
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ChatPage({ model }) {
  const { SCENE_OPTIONS, activeQuote, activeSceneKey, attachmentInputRef, canChat, chatOpacity, chatPlaceholder, composerInputRef, conversationId, conversationLoading, dialRotation, handleAssistantContentUpdate, handleCopyMessage, handleExampleSelect, handleFeedback, handleKeyDown, handleMessagesScroll, handleMouseDown, handleOpenChatAttachment, handlePickAttachment, handleRefreshExamples, handleRemovePendingDocument, handleSceneSelect, handleSend, input, isActionPending, isDragging, isSending, language, messages, messagesEndRef, messagesListRef, pendingDocuments, pendingImage, quoteOpacity, setInput, setPendingImage, t, visibleExamplePrompts, welcomeContent, welcomeLoading, welcomeText } = model
  const statusLabels = {
    understanding: t.chatUnderstanding,
    retrieving: t.chatRetrieving,
    querying_course: t.chatQueryingCourse,
    analyzing_image: t.chatAnalyzingImage,
    analyzing_learning: t.chatAnalyzingLearning,
    organizing: t.chatOrganizing,
    using_tool: t.chatUsingTool,
    generating_visual: t.chatGeneratingVisual,
  }
  const isWelcome = messages.length === 0 && !conversationLoading
  const composerProps = {
    canChat: canChat && !conversationLoading,
    chatPlaceholder: conversationLoading
      ? language === 'zh' ? '正在加载当前对话…' : 'Loading this conversation…'
      : chatPlaceholder,
    composerInputRef,
    handleKeyDown,
    handlePickAttachment,
    handleRemovePendingDocument,
    handleSend,
    attachmentInputRef,
    input,
    isAttachmentUploading: isActionPending('chat:attachment:upload'),
    isSending,
    language,
    pendingDocuments,
    pendingImage,
    setInput,
    setPendingImage,
    t,
  }

  return (
    <section id="section-chat" className="section section-chat">
      <div className={`chat-shell ${isWelcome ? 'empty-chat' : 'active-chat'}`}>
        {isWelcome ? (
          <div className="welcome-flow">
            <div className="welcome-card">
              {welcomeContent ? (
                <MarkdownMessage content={welcomeContent} scene={activeSceneKey} labels={t} />
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

            <ChatComposer variant="hero" {...composerProps} />

            {canChat && visibleExamplePrompts.length > 0 && (
              <section className="example-prompts" aria-label={t.exampleQuestions}>
                <div className="example-prompts-header">
                  <span>{t.exampleQuestions}</span>
                  <button type="button" className="refresh-examples-btn" onClick={handleRefreshExamples} aria-label={t.refreshExamples}>
                    <span aria-hidden="true">↻</span>
                    {t.refreshExamples}
                  </button>
                </div>
                <div className="example-prompts-grid">
                  {visibleExamplePrompts.map((prompt) => (
                    <button key={prompt} type="button" className="example-prompt-card" onClick={() => handleExampleSelect(prompt)}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </section>
            )}
          </div>
        ) : (
          <>
            <div ref={messagesListRef} className="messages-list has-messages" onScroll={handleMessagesScroll}>
              {conversationLoading && (
                <div className="conversation-loading" aria-live="polite">
                  <div className="thinking-indicator">
                    <span />
                    <span />
                    <span />
                    <em>{language === 'zh' ? '正在加载对话' : 'Loading conversation'}</em>
                  </div>
                </div>
              )}
              {messages.map((message, index) => (
                <div key={message.id || index} className={`message-item ${message.role}`}>
                  <div className="message-content">
                    {(message.imagePreview || message.imagePath) && (
                      <AuthImage path={message.imagePath} previewUrl={message.imagePreview} />
                    )}
                    <ChatAttachmentList
                      attachments={message.attachments}
                      language={language}
                      onPreview={attachment => handleOpenChatAttachment(attachment, false)}
                      onDownload={attachment => handleOpenChatAttachment(attachment, true)}
                    />
                    {message.content && !ATTACHMENT_PLACEHOLDERS.has(message.content) && (
                      message.role === 'assistant' ? (
                        <MarkdownMessage
                          content={message.content}
                          scene={activeSceneKey}
                          conversationId={conversationId}
                          messageId={message.id}
                          onContentUpdate={handleAssistantContentUpdate}
                          labels={t}
                        />
                      ) : <p className="message-text">{message.content}</p>
                    )}
                    {message.content && ATTACHMENT_PLACEHOLDERS.has(message.content)
                      && !(message.imagePreview || message.imagePath)
                      && !message.attachments?.length && (
                      <p className="message-text">{message.content}</p>
                    )}
                    {message.role === 'assistant' && !message.content && (
                      <div className="thinking-indicator" aria-live="polite">
                        <span />
                        <span />
                        <span />
                        <em>{statusLabels[message.statusStage] || t.chatUnderstanding}</em>
                      </div>
                    )}
                    {message.role === 'assistant' && message.id && message.content && (
                      <>
                      {message.memoryContextCount > 0 && (
                        <button type="button" className="memory-context-note" onClick={model.onOpenMemory}>
                          {language === 'zh'
                            ? `本次参考了 ${message.memoryContextCount} 条记忆`
                            : `Used ${message.memoryContextCount} memories`}
                        </button>
                      )}
                      <div className="message-actions">
                        <button type="button" className="feedback-btn" title={t.auth.feedbackCopy} aria-label={t.auth.feedbackCopy} onClick={() => handleCopyMessage(message.content)}>
                          <MessageActionIcon type="copy" />
                        </button>
                        <button type="button" className={`feedback-btn ${message.feedback === 'positive' ? 'active' : ''}`} title={t.auth.feedbackHelpful} aria-label={t.auth.feedbackHelpful} aria-pressed={message.feedback === 'positive'} onClick={() => handleFeedback(index, 'positive')}>
                          <MessageActionIcon type="up" />
                        </button>
                        <button type="button" className={`feedback-btn ${message.feedback === 'negative' ? 'active' : ''}`} title={t.auth.feedbackUnhelpful} aria-label={t.auth.feedbackUnhelpful} aria-pressed={message.feedback === 'negative'} onClick={() => handleFeedback(index, 'negative')}>
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
            <ChatComposer variant="compact" {...composerProps} />
          </>
        )}
      </div>

      <SceneSwitcher scenes={SCENE_OPTIONS} activeScene={activeSceneKey} rotation={dialRotation} dragging={isDragging} opacity={chatOpacity} language={language} onMouseDown={handleMouseDown} onSceneSelect={handleSceneSelect} />
      <footer className="scene-quote-footer" style={{ opacity: isWelcome ? quoteOpacity : 0, visibility: isWelcome ? 'visible' : 'hidden', pointerEvents: 'none' }}>
        <blockquote className="scene-quote">
          <p>{activeQuote.text}</p>
          <cite>- {activeQuote.author}</cite>
        </blockquote>
      </footer>
    </section>
  )
}
