import { useEffect, useState } from 'react'
import { getToken } from '../../api/httpClient'

export function MessageActionIcon({ type }) {
  if (type === 'copy') return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" /></svg>
  if (type === 'up') return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11" /><path d="M15 5.5 14 10h5.2a2 2 0 0 1 1.95 2.44l-1.45 6.4A3 3 0 0 1 16.77 21H7" /><path d="M7 10 12 3a2 2 0 0 1 3 2.5" /></svg>
  if (type === 'retry') return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6v5h-5" /><path d="M19 11a8 8 0 1 0 1 5" /></svg>
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 14V3" /><path d="M15 18.5 14 14h5.2a2 2 0 0 0 1.95-2.44L19.7 5.16A3 3 0 0 0 16.77 3H7" /><path d="M7 14 12 21a2 2 0 0 0 3-2.5" /></svg>
}

export function AuthImage({ path, previewUrl }) {
  const [src, setSrc] = useState(previewUrl || null)
  useEffect(() => {
    if (previewUrl) { setSrc(previewUrl); return undefined }
    if (!path) return undefined
    let cancelled = false
    let objectUrl = null
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
    const url = path.startsWith('http') ? path : `${apiBase}${path}`
    const token = getToken()
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((response) => { if (!response.ok) throw new Error('load failed'); return response.blob() })
      .then((blob) => { if (!cancelled) { objectUrl = URL.createObjectURL(blob); setSrc(objectUrl) } })
      .catch(() => { if (!cancelled) setSrc(null) })
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [path, previewUrl])
  return src ? <img src={src} className="message-image" alt="" /> : null
}
