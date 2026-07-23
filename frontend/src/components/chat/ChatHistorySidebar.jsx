import { formatConvDate } from '../../utils/appUtils'

export default function ChatHistorySidebar({ model }) {
  const { conversationId, conversations, handleDeleteConversation, handleNewChat, handleSelectConversation, setSidebarOpen, sidebarOpen, t, user } = model
  if (!user) return null

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
            <div key={conversation.id} className={`sidebar-item ${conversationId === conversation.id ? 'active' : ''}`} aria-current={conversationId === conversation.id ? 'true' : undefined} onClick={() => handleSelectConversation(conversation.id)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handleSelectConversation(conversation.id) } }}>
              <div className="sidebar-item-main"><span className="sidebar-item-title">{conversation.title}</span><span className="sidebar-item-date">{formatConvDate(conversation.updated_at, t.auth.today)}</span></div>
              <button type="button" className="sidebar-delete-btn" title={t.auth.deleteChat} aria-label={t.auth.deleteChat} onClick={(event) => handleDeleteConversation(event, conversation.id)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="M7 7l1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13" /><path d="M10 11v6M14 11v6" /></svg>
              </button>
            </div>
          ))}
        </div>
      </div>
    </aside>
  </>
}
