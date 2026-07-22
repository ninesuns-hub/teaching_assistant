import { NavLink } from 'react-router-dom'
import logoImg from '../../assets/logo.png'

export default function Topbar({
  t,
  user,
  isTeacher,
  language,
  settingsOpen,
  setLanguage,
  setSettingsOpen,
  onNavigate,
  onLogout,
  onOpenAuth,
}) {
  const navClass = ({ isActive }) => `nav-link ${isActive ? 'active' : ''}`

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-left">
        <div className="brand">
          <img src={logoImg} alt="Logo" className="logo-img" />
          <span className="brand-text">{t.brand}</span>
        </div>
        <nav className="topbar-nav" aria-label="Primary">
          <NavLink className={navClass} to="/chat" onClick={() => onNavigate('chat')}>
            {t.navChat}
          </NavLink>
          {user && (
            <>
              <NavLink className={navClass} to="/resources" onClick={() => onNavigate('resources')}>
                {isTeacher ? t.navClasses : t.navResources}
              </NavLink>
              <NavLink className={navClass} to="/homework" onClick={() => onNavigate('homework')}>
                {t.navHomework}
              </NavLink>
              <button type="button" className="nav-link nav-link-more" disabled title={language === 'zh' ? '即将推出' : 'Coming soon'}>
                {t.navMore}
              </button>
            </>
          )}
        </nav>
        </div>
        <div className="topbar-actions">
        <div className="settings-wrap">
          <button type="button" className="ghost-btn" onClick={() => setSettingsOpen(!settingsOpen)}>
            {t.settings}
          </button>
          {settingsOpen && (
            <div className="settings-menu">
              <div className="settings-item">
                <span>{t.language}</span>
                <div className="lang-switch">
                  <button className={language === 'en' ? 'active' : ''} onClick={() => setLanguage('en')}>EN</button>
                  <button className={language === 'zh' ? 'active' : ''} onClick={() => setLanguage('zh')}>中文</button>
                </div>
              </div>
            </div>
          )}
        </div>
        {user ? (
          <>
            <span className="user-badge">{user.name} ({user.role === 'teacher' ? t.auth.teacher : user.role === 'student' ? t.auth.student : '...'})</span>
            <button type="button" className="ghost-btn" onClick={onLogout}>{t.auth.logout}</button>
          </>
        ) : (
          <>
            <button type="button" className="ghost-btn" onClick={() => onOpenAuth('login')}>{t.login}</button>
            <button type="button" className="solid-btn" onClick={() => onOpenAuth('signup')}>{t.signup}</button>
          </>
        )}
        </div>
      </div>
    </header>
  )
}
