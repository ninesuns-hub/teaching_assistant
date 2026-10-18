import { useEffect, useRef, useState } from 'react'
import { getMe, reportActivity } from '../api/auth'
import { expireAuth, getToken, isAuthExpired, setAuth } from '../api/httpClient'

export default function useAuthSession(user, onInvalid, onVerified) {
  const callbacks = useRef({ onInvalid, onVerified })
  const [verifiedToken, setVerifiedToken] = useState(null)
  const [notice, setNotice] = useState(() => sessionStorage.getItem('auth_expired_notice') === '1')
  useEffect(() => { callbacks.current = { onInvalid, onVerified } }, [onInvalid, onVerified])
  useEffect(() => {
    let cancelled = false
    let lastActivity = Date.now()
    const invalid = () => {
      setVerifiedToken(null)
      setNotice(true)
      callbacks.current.onInvalid()
    }
    const verify = async () => {
      const token = getToken()
      if (!token) return
      try {
        const profile = await getMe()
        if (!cancelled && token === getToken()) {
          setAuth(token, profile, profile)
          setVerifiedToken(token)
          setNotice(false)
          callbacks.current.onVerified(profile)
        }
      } catch { /* 401 is handled globally; temporary network failure keeps credentials. */ }
    }
    const activity = async (event) => {
      if (!event.isTrusted || document.visibilityState !== 'visible' || Date.now() - lastActivity < 60_000) return
      const token = getToken()
      if (!token) return
      lastActivity = Date.now()
      try {
        const session = await reportActivity()
        if (token === getToken()) setAuth(token, null, session)
      } catch { /* Do not renew locally if the server did not confirm. */ }
    }
    const foreground = () => { if (document.visibilityState === 'visible') verify() }
    const storage = (event) => {
      if (event.key === 'access_token') {
        if (!getToken()) invalid()
        else verify()
      }
    }
    window.addEventListener('auth:expired', invalid)
    window.addEventListener('storage', storage)
    document.addEventListener('visibilitychange', foreground)
    for (const type of ['pointerdown', 'keydown', 'scroll', 'input']) window.addEventListener(type, activity, { capture: true, passive: true })
    const timer = setInterval(() => { if (getToken() && isAuthExpired()) expireAuth() }, 1000)
    verify()
    return () => {
      cancelled = true
      clearInterval(timer)
      window.removeEventListener('auth:expired', invalid)
      window.removeEventListener('storage', storage)
      document.removeEventListener('visibilitychange', foreground)
      for (const type of ['pointerdown', 'keydown', 'scroll', 'input']) window.removeEventListener(type, activity, true)
    }
  }, [user?.email])
  return { authReady: Boolean(verifiedToken), authNotice: notice }
}
