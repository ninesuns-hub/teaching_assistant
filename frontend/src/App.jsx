import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import './App.css'
import { sendChatMessage } from './api/chat'
import logoImg from './assets/logo.png'

const SCENE_OPTIONS = [
  { key: 'night', label: { en: 'Starry Night', zh: '星空黑夜' }, angle: 0 },
  { key: 'day', label: { en: 'Blue Sky', zh: '碧水蓝天' }, angle: 120 },
  { key: 'sunset', label: { en: 'Sunset', zh: '落日余晖' }, angle: 240 },
]

const LineIcon = ({ type }) => {
  if (type === 'day') return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  )
  if (type === 'sunset') return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <path d="M17 18a5 5 0 0 0-10 0M2 18h20M2 22h20M8 22h8" />
      <path d="M12 2v3M4.93 4.93l1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  )
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  )
}

const TRANSLATIONS = {
  en: {
    brand: 'Discrete Tutor',
    settings: 'Settings',
    login: 'Login',
    signup: 'Sign up',
    title: 'Discrete Math Tutor',
    placeholder: 'Ask your discrete math question...',
    send: 'Send',
    sending: '...',
    scrollDown: 'Scroll down for resources',
    resourcesTitle: 'Learning Resources',
    view: 'View',
    language: 'Language',
    currentScene: 'Current scene',
    resourceChapter: 'Discrete Math Chapter 1',
    resourceDesc: 'Comprehensive overview of fundamental concepts and proofs.',
    filters: {
      All: 'All',
      Slides: 'Slides',
      Notes: 'Notes',
      Practice: 'Practice',
      Books: 'Books'
    },
    auth: {
      loginTitle: 'Welcome Back',
      signupTitle: 'Create Account',
      email: 'Email',
      password: 'Password',
      confirmPassword: 'Confirm Password',
      loginBtn: 'Login',
      signupBtn: 'Sign up',
      noAccount: "Don't have an account?",
      hasAccount: 'Already have an account?',
      backToHome: 'Back to Home'
    }
  },
  zh: {
    brand: '离散数学助教',
    settings: '设置',
    login: '登录',
    signup: '注册',
    title: '离散数学助教',
    placeholder: '输入你的离散数学问题...',
    send: '发送',
    sending: '...',
    scrollDown: '向下滑动查看资源',
    resourcesTitle: '学习资源',
    view: '查看',
    language: '语言',
    currentScene: '当前场景',
    resourceChapter: '离散数学 第一章',
    resourceDesc: '涵盖基本概念与证明方法的全面概述。',
    filters: {
      All: '全部',
      Slides: '课件',
      Notes: '笔记',
      Practice: '练习',
      Books: '书籍'
    },
    auth: {
      loginTitle: '欢迎回来',
      signupTitle: '创建账号',
      email: '邮箱',
      password: '密码',
      confirmPassword: '确认密码',
      loginBtn: '登录',
      signupBtn: '注册',
      noAccount: '还没有账号？',
      hasAccount: '已有账号？',
      backToHome: '返回首页'
    }
  }
}

const SCENE_QUOTES = {
  day: {
    en: { text: 'All of mathematics... finds the most secret truths and puts them in the right light.', author: 'Leonhard Euler' },
    zh: { text: '所有的数学……都能发现最隐秘的真理，并将其置于正确的光线下。', author: '欧拉' }
  },
  night: {
    en: { text: 'There are faint stars in the night sky that you can see, but only if you look to the side of where they shine... Maybe truth is just like that.', author: 'Kurt Godel' },
    zh: { text: '夜空中有些微弱的星光，只有当你侧过头去看它们时才能看见……也许真理也是如此。', author: '哥德尔' }
  },
  sunset: {
    en: { text: 'Thought is only a flash between two long nights, but this flash is everything.', author: 'Henri Poincare' },
    zh: { text: '思想只是两次漫漫长夜之间的一道闪电，但这道闪电就是一切。', author: '亨利·庞加莱' }
  },
}

const RESOURCE_FILTERS = ['All', 'Slides', 'Notes', 'Practice', 'Books']

function getBeijingHour() {
  const hourPart = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    hour12: false,
  })
    .formatToParts(new Date())
    .find((part) => part.type === 'hour')

  return Number(hourPart?.value ?? 0)
}

function getSceneByHour(hour) {
  if (hour >= 6 && hour < 17) return 'day'
  if (hour >= 17 && hour < 20) return 'sunset'
  return 'night'
}

function App() {
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [authModal, setAuthModal] = useState(null) // null, 'login', 'signup'
  const [language, setLanguage] = useState('en')
  const [activeFilter, setActiveFilter] = useState('All')
  const [scrollPos, setScrollPos] = useState(0)
  
  const [dialRotation, setDialRotation] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef({ startX: 0, startRot: 0 })
  const containerRef = useRef(null)

  const t = TRANSLATIONS[language]

  // Initialize dial based on current time
  useEffect(() => {
    const currentSceneKey = getSceneByHour(getBeijingHour())
    const targetScene = SCENE_OPTIONS.find(s => s.key === currentSceneKey)
    if (targetScene) {
      setDialRotation(-targetScene.angle)
    }
  }, [])

  // Track scroll position
  useEffect(() => {
    const handleScroll = () => {
      if (containerRef.current) {
        const pos = containerRef.current.scrollTop / window.innerHeight
        setScrollPos(pos)
      }
    }
    const container = containerRef.current
    if (container) container.addEventListener('scroll', handleScroll)
    return () => container?.removeEventListener('scroll', handleScroll)
  }, [])

  const sceneOpacities = useMemo(() => {
    return SCENE_OPTIONS.reduce((acc, scene) => {
      let relAngle = (scene.angle + dialRotation) % 360
      while (relAngle < -180) relAngle += 360
      while (relAngle > 180) relAngle -= 360
      const dist = Math.abs(relAngle)
      acc[scene.key] = Math.max(0, 1 - dist / 120)
      return acc
    }, {})
  }, [dialRotation])

  const activeSceneKey = useMemo(() => {
    let maxOpacity = -1, key = 'night'
    Object.entries(sceneOpacities).forEach(([k, v]) => {
      if (v > maxOpacity) { maxOpacity = v; key = k; }
    })
    return key
  }, [sceneOpacities])

  const chatOpacity = useMemo(() => {
    const normalizedRot = ((-dialRotation % 360) + 360) % 360
    const distToSnap = Math.abs((normalizedRot % 120))
    const finalDist = Math.min(distToSnap, 120 - distToSnap)
    // Increased fade range: starts fading much earlier
    const dialOpacity = Math.max(0, 1 - finalDist / 45)
    const scrollFade = Math.max(0, 1 - scrollPos * 2)
    return dialOpacity * scrollFade
  }, [dialRotation, scrollPos])

  const quoteOpacity = useMemo(() => {
    const normalizedRot = ((-dialRotation % 360) + 360) % 360
    const distToSnap = Math.abs((normalizedRot % 120))
    const finalDist = Math.min(distToSnap, 120 - distToSnap)
    // Quote is even more sensitive, stays hidden longer
    const dialOpacity = Math.max(0, 1 - finalDist / 25)
    const scrollFade = Math.max(0, 1 - scrollPos * 2)
    return dialOpacity * scrollFade
  }, [dialRotation, scrollPos])

  const activeQuote = useMemo(() => SCENE_QUOTES[activeSceneKey][language], [activeSceneKey, language])

  const handleMouseDown = (e) => {
    setIsDragging(true)
    dragRef.current = { startX: e.clientX, startRot: dialRotation }
  }

  useEffect(() => {
    if (!isDragging) return
    const handleMouseMove = (e) => {
      const deltaX = e.clientX - dragRef.current.startX
      setDialRotation(dragRef.current.startRot + deltaX * 1.2)
    }
    const handleMouseUp = () => {
      setIsDragging(false)
      setDialRotation(Math.round(dialRotation / 120) * 120)
    }
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, dialRotation])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || isSending) return
    setIsSending(true)
    try {
      await sendChatMessage({ message: input.trim(), history: [] })
      setInput('')
    } catch (err) { console.error(err) } finally { setIsSending(false) }
  }

  return (
    <div className="app-container" ref={containerRef}>
      <main className={`page scene-${activeSceneKey}`}>
        {SCENE_OPTIONS.map(opt => (
          <div key={opt.key} className={`scene-layer scene-${opt.key}`} style={{ opacity: sceneOpacities[opt.key] }}>
            <div className="scene-halo" aria-hidden="true" />
            <div className="scene-motion" aria-hidden="true" />
            <div className="scene-motion-secondary" aria-hidden="true" />
            {opt.key === 'night' && <div className="scene-meteor" aria-hidden="true" />}
          </div>
        ))}

        <header className={`topbar ${scrollPos > 0.5 ? 'topbar-scrolled' : ''}`}>
          <div className="brand">
            <img src={logoImg} alt="Logo" className="logo-img" />
            <span className="brand-text">{t.brand}</span>
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
            <button type="button" className="ghost-btn" onClick={() => setAuthModal('login')}>{t.login}</button>
            <button type="button" className="solid-btn" onClick={() => setAuthModal('signup')}>{t.signup}</button>
          </div>
        </header>

        <section className="section section-chat">
          <div className="chat-shell" style={{ 
            opacity: chatOpacity, 
            transform: `scale(${0.98 + chatOpacity * 0.02}) translateY(${scrollPos * -50}px)` 
          }}>
            <div className="chat-title">
              <img src={logoImg} alt="Logo" className="logo-img logo-img-lg" />
              <h1>{t.title}</h1>
            </div>
            <form className="composer" onSubmit={handleSend}>
              <textarea value={input} onChange={(e) => setInput(e.target.value)} placeholder={t.placeholder} rows={1} />
              <button type="submit" disabled={!input.trim() || isSending}>
                {isSending ? t.sending : t.send}
              </button>
            </form>
          </div>

      <div className="scene-dial-wrap" style={{ opacity: chatOpacity, transform: `translateY(${scrollPos * 100}px)` }}>
            <div className="dial-pointer" aria-hidden="true" />
            <div className="scene-dial" onMouseDown={handleMouseDown} style={{ 
                transform: `rotate(${dialRotation}deg)`,
                cursor: isDragging ? 'grabbing' : 'grab',
                transition: isDragging ? 'none' : 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)'
              }}>
              {/* Internal Dividers */}
              <div className="dial-divider" style={{ transform: 'rotate(60deg)' }} />
              <div className="dial-divider" style={{ transform: 'rotate(180deg)' }} />
              <div className="dial-divider" style={{ transform: 'rotate(300deg)' }} />

              {SCENE_OPTIONS.map((opt, idx) => (
                <div key={opt.key} className={`dial-item ${activeSceneKey === opt.key ? 'active' : ''}`} style={{ 
                    '--idx': idx,
                    transform: `rotate(${idx * 120}deg) translateY(-38px) rotate(${-idx * 120 - dialRotation}deg)`
                  }}>
                  <LineIcon type={opt.key} />
                </div>
              ))}
            </div>
          </div>

          <footer className="scene-quote-footer" style={{ opacity: quoteOpacity, transform: `translateY(${scrollPos * 50}px)` }}>
            <blockquote className="scene-quote">
              <p>{activeQuote.text}</p>
              <cite>- {activeQuote.author}</cite>
            </blockquote>
          </footer>

          <div className="scroll-indicator" style={{ opacity: chatOpacity }}>
            <span>{t.scrollDown}</span>
            <div className="arrow-down" />
          </div>
        </section>

        <section className="section section-resources" style={{ 
          opacity: Math.min(1, (scrollPos - 0.2) * 2),
          transform: `translateY(${(1 - scrollPos) * 100}px)`
        }}>
          <div className="resources-container">
            <div className="resources-header">
              <h2>{t.resourcesTitle}</h2>
              <div className="filter-bar">
                {RESOURCE_FILTERS.map(f => (
                  <button key={f} className={`filter-btn ${activeFilter === f ? 'active' : ''}`} onClick={() => setActiveFilter(f)}>
                    {t.filters[f]}
                  </button>
                ))}
              </div>
            </div>
            <div className="resources-grid">
              <div className="resource-card">
                <div className="card-type">{activeFilter === 'All' ? t.filters.Slides : t.filters[activeFilter]}</div>
                <h3>{t.resourceChapter}</h3>
                <p>{t.resourceDesc}</p>
                <div className="card-footer">
                  <span>2.4 MB</span>
                  <button className="download-btn">{t.view}</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Auth Modals */}
      {authModal && (
        <div className="auth-overlay" onClick={() => setAuthModal(null)}>
          <div className="auth-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setAuthModal(null)}>&times;</button>
            <div className="auth-header">
              <img src={logoImg} alt="Logo" className="logo-img" />
              <h2>{authModal === 'login' ? t.auth.loginTitle : t.auth.signupTitle}</h2>
            </div>
            
            <form className="auth-form" onSubmit={e => e.preventDefault()}>
              <div className="form-group">
                <label>{t.auth.email}</label>
                <input type="email" placeholder="example@email.com" />
              </div>
              <div className="form-group">
                <label>{t.auth.password}</label>
                <input type="password" placeholder="••••••••" />
              </div>
              {authModal === 'signup' && (
                <div className="form-group">
                  <label>{t.auth.confirmPassword}</label>
                  <input type="password" placeholder="••••••••" />
                </div>
              )}
              
              <button type="submit" className="auth-submit">
                {authModal === 'login' ? t.auth.loginBtn : t.auth.signupBtn}
              </button>
            </form>

            <div className="auth-footer">
              {authModal === 'login' ? (
                <p>{t.auth.noAccount} <span onClick={() => setAuthModal('signup')}>{t.auth.signupBtn}</span></p>
              ) : (
                <p>{t.auth.hasAccount} <span onClick={() => setAuthModal('login')}>{t.auth.loginBtn}</span></p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
