import { useEffect, useState } from 'react'
import { clearMemories, deleteMemory, editMemory, fetchMemories } from '../api/memory'

const TYPE_LABELS = {
  communication_preference: ['沟通偏好', 'Communication preference'],
  learning_preference: ['学习偏好', 'Learning preference'],
  course_learning_state: ['课程学习状态', 'Course learning state'],
  explicit_user_fact: ['明确记忆', 'Explicit memory'],
  unresolved_learning_goal: ['学习目标', 'Learning goal'],
}

export default function MemorySettingsPanel({
  open,
  language,
  setting,
  onClose,
  onSettingChange,
}) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState('')
  const zh = language === 'zh'

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    setLoading(true)
    setError('')
    fetchMemories()
      .then(result => {
        if (!cancelled) setItems(result.items || [])
      })
      .catch(err => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [open, setting?.backfill_status])

  if (!open) return null

  const save = async (item) => {
    try {
      const updated = await editMemory(item.id, draft)
      setItems(current => current.map(value => value.id === item.id ? updated : value))
      setEditingId(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const remove = async (item) => {
    if (!window.confirm(zh ? '删除这条记忆？' : 'Delete this memory?')) return
    try {
      await deleteMemory(item.id)
      setItems(current => current.filter(value => value.id !== item.id))
    } catch (err) {
      setError(err.message)
    }
  }

  const clearAll = async () => {
    if (!window.confirm(zh ? '清空全部长期记忆？此操作无法撤销。' : 'Clear all long-term memories? This cannot be undone.')) return
    try {
      await clearMemories()
      setItems([])
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <section className="memory-panel" role="dialog" aria-modal="true" aria-label={zh ? '个性化记忆' : 'Personal memory'} onClick={event => event.stopPropagation()}>
        <div className="memory-panel-header">
          <div>
            <h2>{zh ? '个性化记忆' : 'Personal memory'}</h2>
            <p>{zh ? '同一会话的上下文始终有效。开启后，小离会整理可跨会话使用的学习偏好。' : 'Conversation context always works. Enable this to retain useful preferences across chats.'}</p>
          </div>
          <button type="button" className="modal-close" aria-label={zh ? '关闭' : 'Close'} onClick={onClose}>&times;</button>
        </div>
        <label className="memory-toggle-row">
          <span>
            <strong>{zh ? '跨会话记忆' : 'Cross-chat memory'}</strong>
            <small>{setting?.enabled
              ? (zh ? `历史整理状态：${setting.backfill_status}` : `History status: ${setting.backfill_status}`)
              : (zh ? '默认关闭，只有你开启后才会整理历史记录' : 'Off by default; history is processed only after you enable it')}</small>
          </span>
          <input type="checkbox" checked={Boolean(setting?.enabled)} onChange={event => onSettingChange(event.target.checked)} />
        </label>
        {error && <p className="auth-error">{error}</p>}
        <div className="memory-list">
          {loading && <p>{zh ? '正在读取记忆...' : 'Loading memories...'}</p>}
          {!loading && !items.length && <p className="memory-empty">{zh ? '暂时没有长期记忆' : 'No long-term memories yet'}</p>}
          {items.map(item => (
            <article className="memory-item" key={item.id}>
              <div className="memory-item-meta">
                <span>{TYPE_LABELS[item.memory_type]?.[zh ? 0 : 1] || item.memory_type}</span>
                <span>{item.class_id ? (zh ? `班级 ${item.class_id}` : `Class ${item.class_id}`) : (zh ? '全局' : 'Global')}</span>
              </div>
              {editingId === item.id ? (
                <textarea value={draft} maxLength={500} onChange={event => setDraft(event.target.value)} />
              ) : <p>{item.content}</p>}
              <div className="memory-item-actions">
                {editingId === item.id ? <>
                  <button type="button" onClick={() => save(item)}>{zh ? '保存' : 'Save'}</button>
                  <button type="button" onClick={() => setEditingId(null)}>{zh ? '取消' : 'Cancel'}</button>
                </> : <>
                  <button type="button" onClick={() => { setEditingId(item.id); setDraft(item.content) }}>{zh ? '修改' : 'Edit'}</button>
                  <button type="button" onClick={() => remove(item)}>{zh ? '删除' : 'Delete'}</button>
                </>}
              </div>
            </article>
          ))}
        </div>
        <div className="memory-panel-footer">
          <button type="button" className="ghost-btn" disabled={!items.length} onClick={clearAll}>{zh ? '清空全部记忆' : 'Clear all memories'}</button>
        </div>
      </section>
    </div>
  )
}
