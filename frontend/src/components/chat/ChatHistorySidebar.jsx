import { useState } from 'react'
import { formatConvDate } from '../../utils/appUtils'

export default function ChatHistorySidebar({ model }) {
  const { conversationId, conversations, handleDeleteConversation, handleNewChat, handleRenameConversation, handleSelectConversation, isActionPending, setSidebarOpen, sidebarOpen, t, user } = model
  const [editingId, setEditingId] = useState(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [renameError, setRenameError] = useState('')
  if (!user) return null

  const beginRename = (event, conversation) => {
    event.stopPropagation()
    setEditingId(conversation.id)
    setDraftTitle(conversation.title)
    setRenameError('')
  }

  const cancelRename = (event) => {
    event?.stopPropagation()
    setEditingId(null)
    setDraftTitle('')
    setRenameError('')
  }

  const saveRename = async (event, conversationIdToRename) => {
    event?.preventDefault()
    event?.stopPropagation()
    const title = draftTitle.trim()
    if (!title) {
      setRenameError(t.auth.renameRequired)
      return
    }
    if (title.length > 50) {
      setRenameError(t.auth.renameTooLong)
      return
    }
    try {
      await handleRenameConversation(conversationIdToRename, title)
      cancelRename()
    } catch (error) {
      setRenameError(error.message)
    }
  }

  return <>
    {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-hidden="true" />}
    <button type="button" className={`sidebar-tab ${sidebarOpen ? 'open' : ''}`} onClick={() => setSidebarOpen((open) => !open)} aria-label={t.auth.historyTitle} aria-expanded={sidebarOpen}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="sidebar-tab-arrow" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
      {!sidebarOpen && <span className="sidebar-tab-label">{t.auth.historyTitle}</span>}
    </button>
    <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`} aria-hidden={!sidebarOpen}>
      <div className="sidebar-inner">
        <div className="sidebar-header"><h3>{t.auth.historyTitle}</h3><button type="button" className="sidebar-new-btn" onClick={handleNewChat}>+ {t.auth.newChat}</button></div>
        <div className="sidebar-list">
          {conversations.length === 0 ? <p className="sidebar-empty">{t.auth.noHistory}</p> : conversations.map((conversation) => (
            <div key={conversation.id} className={`sidebar-item ${conversationId === conversation.id ? 'active' : ''} ${editingId === conversation.id ? 'is-editing' : ''}`} aria-current={conversationId === conversation.id ? 'true' : undefined} onClick={() => { if (editingId !== conversation.id) handleSelectConversation(conversation.id) }} role="button" tabIndex={editingId === conversation.id ? -1 : 0} onKeyDown={(event) => { if (editingId !== conversation.id && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); handleSelectConversation(conversation.id) } }}>
              {editingId === conversation.id ? (
                <form className="sidebar-rename-form" onSubmit={(event) => saveRename(event, conversation.id)} onClick={event => event.stopPropagation()}>
                  <input autoFocus value={draftTitle} maxLength={50} aria-label={t.auth.renameChat} aria-invalid={Boolean(renameError)} onChange={event => { setDraftTitle(event.target.value); setRenameError('') }} onKeyDown={event => { if (event.key === 'Escape') cancelRename(event) }} />
                  {renameError && <span className="sidebar-rename-error" role="alert">{renameError}</span>}
                  <div className="sidebar-rename-actions">
                    <button type="submit" disabled={isActionPending(`conversation:rename:${conversation.id}`)} aria-busy={isActionPending(`conversation:rename:${conversation.id}`)}>{t.auth.saveRename}</button>
                    <button type="button" disabled={isActionPending(`conversation:rename:${conversation.id}`)} onClick={cancelRename}>{t.auth.cancelRename}</button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="sidebar-item-main"><span className="sidebar-item-title">{conversation.title}</span><span className="sidebar-item-date">{formatConvDate(conversation.updated_at, t.auth.today)}</span></div>
                  <div className="sidebar-item-actions">
                    <button type="button" className="sidebar-item-action sidebar-rename-btn" title={t.auth.renameChat} aria-label={t.auth.renameChat} onClick={(event) => beginRename(event, conversation)}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z" /></svg>
                    </button>
                    <button type="button" className="sidebar-item-action sidebar-delete-btn" title={t.auth.deleteChat} aria-label={t.auth.deleteChat} onClick={(event) => handleDeleteConversation(event, conversation.id)}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="M7 7l1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13" /><path d="M10 11v6M14 11v6" /></svg>
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </aside>
  </>
}
