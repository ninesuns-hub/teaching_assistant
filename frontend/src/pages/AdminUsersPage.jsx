import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  addAdminClassMembership,
  fetchAdminAuditLogs,
  fetchAdminClasses,
  fetchAdminUser,
  fetchAdminUsers,
  removeAdminClassMembership,
  transferAdminClass,
  updateAdminAccess,
  updateAdminUserProfile,
  updateAdminUserRole,
  updateAdminUserStatus,
} from '../api/admin'

const EMPTY_FILTERS = { search: '', role: '', status: '', class_id: '' }
const ROLE_LABELS = { student: '学生', teacher: '教师' }
const ACTION_LABELS = {
  'user.profile.update': '修改基本资料',
  'user.role.update': '修改业务身份',
  'user.status.update': '修改账号状态',
  'user.admin_access.update': '修改管理员权限',
  'user.class_membership.add': '添加班级成员关系',
  'user.class_membership.remove': '移除班级成员关系',
  'class.owner.transfer': '转交班级',
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function Overview({ value = {} }) {
  const metrics = [
    ['班级', value.class_count ?? 0],
    ['会话', value.conversation_count ?? 0],
    ['作业提交', value.submission_count ?? 0],
    ['学情报告', value.report_count ?? 0],
  ]
  return <div className="admin-metrics">{metrics.map(([label, count]) => <div key={label}><strong>{count}</strong><span>{label}</span></div>)}</div>
}

export default function AdminUsersPage({ currentUser, onCurrentUserRefresh }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [result, setResult] = useState({ items: [], total: 0, pages: 0 })
  const [classes, setClasses] = useState([])
  const [teachers, setTeachers] = useState([])
  const [selected, setSelected] = useState(null)
  const [auditLogs, setAuditLogs] = useState([])
  const [nameDraft, setNameDraft] = useState('')
  const [membershipClassId, setMembershipClassId] = useState('')
  const [transferTeachers, setTransferTeachers] = useState({})
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setResult(await fetchAdminUsers({ ...appliedFilters, page, page_size: 20 }))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [appliedFilters, page])

  useEffect(() => { loadUsers() }, [loadUsers])
  useEffect(() => {
    Promise.all([fetchAdminClasses(), fetchAdminUsers({ role: 'teacher', status: 'active', page_size: 100 })])
      .then(([classRows, teacherRows]) => { setClasses(classRows); setTeachers(teacherRows.items) })
      .catch(err => setError(err.message))
  }, [])

  const openUser = async (userId) => {
    setBusy(`open:${userId}`)
    setError('')
    try {
      const [detail, logs] = await Promise.all([fetchAdminUser(userId), fetchAdminAuditLogs({ target_user_id: userId, page_size: 20 })])
      setSelected(detail)
      setNameDraft(detail.name)
      setAuditLogs(logs.items)
      setMembershipClassId('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const refreshSelected = async (userId = selected?.id) => {
    await Promise.all([loadUsers(), userId ? openUser(userId) : Promise.resolve()])
    if (userId === currentUser.id) await onCurrentUserRefresh()
  }

  const runAction = async (key, operation, confirmation) => {
    if (busy) return
    if (confirmation && !window.confirm(confirmation)) return
    setBusy(key)
    setError('')
    try {
      await operation()
      await refreshSelected()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const availableMembershipClasses = useMemo(() => {
    const ids = new Set((selected?.classes || []).map(item => item.id))
    return classes.filter(item => !ids.has(item.id))
  }, [classes, selected])

  return (
    <section className="section-admin">
      <div className="admin-container">
        <header className="admin-heading"><div><span>ADMIN CONSOLE</span><h1>用户管理</h1><p>维护账号、身份和班级关系，查看学习活动概览。</p></div><strong>{result.total} 位用户</strong></header>
        {error && <div className="admin-alert" role="alert">{error}</div>}
        <form className="admin-filters" onSubmit={event => { event.preventDefault(); setPage(1); setAppliedFilters(filters) }}>
          <input aria-label="搜索用户" placeholder="搜索姓名或学校邮箱" value={filters.search} onChange={event => setFilters(value => ({ ...value, search: event.target.value }))} />
          <select aria-label="身份筛选" value={filters.role} onChange={event => setFilters(value => ({ ...value, role: event.target.value }))}><option value="">全部身份</option><option value="student">学生</option><option value="teacher">教师</option></select>
          <select aria-label="状态筛选" value={filters.status} onChange={event => setFilters(value => ({ ...value, status: event.target.value }))}><option value="">全部状态</option><option value="active">正常</option><option value="disabled">已停用</option></select>
          <select aria-label="班级筛选" value={filters.class_id} onChange={event => setFilters(value => ({ ...value, class_id: event.target.value }))}><option value="">全部班级</option>{classes.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
          <button className="action-btn action-btn-primary" type="submit">筛选</button>
          <button className="action-btn action-btn-soft" type="button" onClick={() => { setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS); setPage(1) }}>重置</button>
        </form>
        <div className="admin-table-wrap">
          <table className="admin-table"><thead><tr><th>用户</th><th>身份</th><th>状态</th><th>权限</th><th>学习概览</th><th>最近活动</th></tr></thead><tbody>
            {!loading && !result.items.length && <tr><td colSpan="6" className="admin-empty">没有符合条件的用户</td></tr>}
            {result.items.map(item => <tr key={item.id} tabIndex="0" onClick={() => openUser(item.id)} onKeyDown={event => { if (event.key === 'Enter') openUser(item.id) }} className={busy === `open:${item.id}` ? 'is-busy' : ''}><td><strong>{item.name}</strong><small>{item.email}</small></td><td>{ROLE_LABELS[item.role] || '待选择'}</td><td><span className={`admin-status is-${item.status}`}>{item.status === 'active' ? '正常' : '已停用'}</span></td><td>{item.effective_admin ? '管理员' : '普通用户'}</td><td>{item.learning_overview.class_count} 班 / {item.learning_overview.conversation_count} 会话 / {item.learning_overview.submission_count} 提交</td><td>{formatDate(item.learning_overview.last_activity_at)}</td></tr>)}
          </tbody></table>
          {loading && <div className="admin-loading">正在加载用户…</div>}
        </div>
        <div className="admin-pagination"><button disabled={page <= 1 || loading} onClick={() => setPage(value => value - 1)}>上一页</button><span>第 {page} / {Math.max(result.pages, 1)} 页</span><button disabled={page >= result.pages || loading} onClick={() => setPage(value => value + 1)}>下一页</button></div>
      </div>

      {selected && <div className="admin-drawer-backdrop" onClick={() => setSelected(null)}><aside className="admin-drawer" role="dialog" aria-modal="true" aria-label="用户详情" onClick={event => event.stopPropagation()}>
        <button className="admin-drawer-close" onClick={() => setSelected(null)} aria-label="关闭">×</button>
        <div className="admin-drawer-title"><span>用户 #{selected.id}</span><h2>{selected.name}</h2><p>{selected.email}</p></div>
        <Overview value={selected.learning_overview} />
        <section className="admin-detail-section"><h3>基本资料</h3><div className="admin-inline-form"><input value={nameDraft} maxLength="100" onChange={event => setNameDraft(event.target.value)} /><button disabled={Boolean(busy) || !nameDraft.trim()} onClick={() => runAction('profile', () => updateAdminUserProfile(selected.id, { name: nameDraft.trim() }))}>保存姓名</button></div><dl><div><dt>注册时间</dt><dd>{formatDate(selected.created_at)}</dd></div><div><dt>最后登录</dt><dd>{formatDate(selected.last_login_at)}</dd></div><div><dt>最近活动</dt><dd>{formatDate(selected.learning_overview.last_activity_at)}</dd></div></dl></section>
        <section className="admin-detail-section"><h3>身份与账号</h3><div className="admin-control-grid"><label>业务身份<select value={selected.role || ''} disabled={Boolean(busy)} onChange={event => runAction('role', () => updateAdminUserRole(selected.id, { role: event.target.value }), `确认将 ${selected.name} 的身份改为${ROLE_LABELS[event.target.value]}？`)}><option value="" disabled>待选择</option><option value="student">学生</option><option value="teacher">教师</option></select></label><label>账号状态<select value={selected.status} disabled={Boolean(busy) || selected.id === currentUser.id} onChange={event => runAction('status', () => updateAdminUserStatus(selected.id, { status: event.target.value }), event.target.value === 'disabled' ? `确认停用 ${selected.name}？其现有登录会立即失效。` : `确认启用 ${selected.name}？`)}><option value="active">正常</option><option value="disabled">已停用</option></select></label></div><button className="admin-danger-action" disabled={Boolean(busy) || selected.is_bootstrap_admin || selected.id === currentUser.id} onClick={() => runAction('admin', () => updateAdminAccess(selected.id, { is_admin: !selected.is_admin }), selected.is_admin ? `确认撤销 ${selected.name} 的管理员权限？` : `确认授予 ${selected.name} 管理员权限？`)}>{selected.effective_admin ? '撤销管理员权限' : '授予管理员权限'}</button>{selected.is_bootstrap_admin && <small className="admin-help">该账号由 ADMIN_EMAILS 授权，不能在页面中撤权。</small>}</section>
        <section className="admin-detail-section"><h3>班级关系</h3>{selected.role === 'student' && <div className="admin-inline-form"><select value={membershipClassId} onChange={event => setMembershipClassId(event.target.value)}><option value="">选择要加入的班级</option>{availableMembershipClasses.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button disabled={!membershipClassId || Boolean(busy)} onClick={() => runAction('membership:add', () => addAdminClassMembership(selected.id, { class_id: Number(membershipClassId) }))}>添加</button></div>}<div className="admin-class-list">{!selected.classes.length && <p>暂无班级关系</p>}{selected.classes.map(item => <article key={`${item.relation}:${item.id}`}><div><strong>{item.name}</strong><small>{item.relation === 'owner' ? '负责教师' : '班级成员'}</small></div>{item.relation === 'member' ? <button disabled={Boolean(busy)} onClick={() => runAction(`membership:${item.id}`, () => removeAdminClassMembership(selected.id, item.id), `确认将 ${selected.name} 移出 ${item.name}？`)}>移出</button> : <div className="admin-transfer"><select value={transferTeachers[item.id] || ''} onChange={event => setTransferTeachers(value => ({ ...value, [item.id]: event.target.value }))}><option value="">选择接收教师</option>{teachers.filter(teacher => teacher.id !== selected.id).map(teacher => <option key={teacher.id} value={teacher.id}>{teacher.name}</option>)}</select><button disabled={!transferTeachers[item.id] || Boolean(busy)} onClick={() => runAction(`transfer:${item.id}`, () => transferAdminClass(item.id, { teacher_id: Number(transferTeachers[item.id]) }), `确认转交班级 ${item.name}？`)}>转交</button></div>}</article>)}</div></section>
        <section className="admin-detail-section"><h3>最近审计记录</h3><div className="admin-audit-list">{!auditLogs.length && <p>暂无操作记录</p>}{auditLogs.map(log => <article key={log.id}><strong>{ACTION_LABELS[log.action] || log.action}</strong><span>{log.actor_name || `管理员 ${log.actor_user_id}`} · {formatDate(log.created_at)}</span>{log.reason && <p>{log.reason}</p>}</article>)}</div></section>
      </aside></div>}
    </section>
  )
}
