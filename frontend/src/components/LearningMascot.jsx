import { useEffect } from 'react'
import mascotRiseGif from '../assets/learning-mascot-clean.gif'
import mascotIdlePng from '../assets/learning-mascot-idle.png'
import './LearningMascot.css'

const copy = {
  zh: {
    teacherTitle: '小离的学情笔记', studentTitle: '小离的学习笔记',
    loading: '我正在翻看最近的学习记录...',
    classLoading: '正在后台整理…',
    background: '报告会在后台继续整理，你可以先关闭这张学习笔记',
    noClass: '先选一个班级吧。这样我才能分清课程，也不会把不同班级的学习记录混在一起。',
    goClass: '去选择班级', start: '开始和我聊聊', continue: '继续和我聊聊',
    generate: '帮我整理学情报告', update: '把报告更新一下', view: '看看上次的报告',
    retry: '重新整理一次',
    generateClass: '帮我整理班级学情', updateClass: '更新班级学情', viewClass: '看看上次的班级反馈',
    noData: '我们还没有留下学习记录。以后遇到课程问题，随时来找我。',
    enough: '最近聊到的内容已经比较丰富了，我可以帮你整理成一份学情报告。',
    current: '上次的学情报告已经整理好了。想回顾时，我随时可以拿给你看。',
    changed: '上次报告之后，我们又聊了一些新内容。需要的话，我可以重新整理。',
    accumulating: '已记录 {count} 次有效学习交流。再进行一些讨论，我就能更准确地分析知识点掌握情况。',
    classNone: '班里暂时还没有学生。添加学生后，我会在这里帮你留意大家的学习轨迹。',
    classQuiet: '班里有 {total} 位同学，目前还没有留下学习交流。可以先鼓励大家在课后向我提问。',
    classActive: '班里有 {total} 位同学，其中 {active} 位已经留下学习记录。',
    classReady: '有 {ready} 位同学的学习轨迹已经比较完整，可以进一步整理。',
    classGrowing: '大家的学习轨迹还在慢慢积累，我先替你留意着。',
    recentTrails: '最近的学习轨迹', effective: '{count} 次有效学习交流', messages: '{count} 条对话记录',
    reportReady: '可以查看报告', reportPending: '还在积累',
    syncing: '正在同步', close: '关闭', report: '学情报告', feedback: '班级学情反馈', generatedAt: '整理于',
    summary: '小离的观察', topics: '聊到的知识点', weak: '值得再练一练', suggestions: '接下来可以这样学',
    contextFirst: '先告诉我是哪门课', newHint: '有新的学情提示', mascotLabel: '打开学情笔记',
  },
  en: {
    teacherTitle: "Xiaoli's class notes", studentTitle: "Xiaoli's learning notes",
    loading: 'Organizing in the background…',
    classLoading: 'Organizing in the background…',
    background: 'The report will keep running in the background. You can close these notes.',
    noClass: 'Choose a class first so I can keep each course and its learning records separate.',
    goClass: 'Choose a class', start: 'Start a conversation', continue: 'Keep learning with me',
    generate: 'Organize my learning report', update: 'Update my report', view: 'View the last report',
    retry: 'Try organizing again',
    generateClass: 'Organize class learning', updateClass: 'Update class learning', viewClass: 'View the last class note',
    noData: 'We have not left a learning trail yet. Come talk to me whenever a course question comes up.',
    enough: 'We have discussed enough material for me to organize a learning report.',
    current: 'Your last learning report is ready whenever you want to revisit it.',
    changed: 'We have discussed something new since the last report. I can organize an updated version.',
    accumulating: '{count} meaningful learning interactions recorded. A little more discussion will help me understand your mastery more accurately.',
    classNone: 'There are no students in this class yet. Once they join, I will keep an eye on their learning trails here.',
    classQuiet: 'There are {total} students, but no learning conversations yet. Encourage them to ask me questions after class.',
    classActive: '{active} of {total} students have started a learning trail.',
    classReady: '{ready} students now have enough context for a closer look.',
    classGrowing: 'Their learning trails are still growing. I will keep watching quietly.',
    recentTrails: 'Recent learning trails', effective: '{count} meaningful exchanges', messages: '{count} conversation messages',
    reportReady: 'Report ready', reportPending: 'Still growing',
    syncing: 'Syncing', close: 'Close', report: 'Learning report', feedback: 'Class learning feedback', generatedAt: 'Organized',
    summary: "Xiaoli's observation", topics: 'Topics discussed', weak: 'Worth practicing', suggestions: 'What to try next',
    contextFirst: 'Tell me which class first', newHint: 'New learning update', mascotLabel: 'Open learning notes',
  },
}

function fill(template, values) {
  return Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, value), template)
}

function formatDate(value, language) {
  if (!value) return ''
  return new Intl.DateTimeFormat(language === 'zh' ? 'zh-CN' : 'en', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value))
}

function StudentPanel({ text, status, generating, hasError, onGenerate, onViewLatest, onFocusChat }) {
  const count = status?.effective_question_count ?? 0
  const latest = status?.latest_report
  const canCreateOrUpdate = Boolean(
    status?.can_generate
    && (!latest || status?.has_updates || hasError || generating),
  )
  let message = text.noData
  if (count > 0 && !status?.can_generate) message = fill(text.accumulating, { count })
  else if (latest && status?.has_updates) message = text.changed
  else if (latest) message = text.current
  else if (status?.can_generate) message = text.enough

  return (
    <>
      <div className={`learning-assistant-letter ${status?.has_updates ? 'is-fresh' : ''}`}>
        <p>{message}</p>
      </div>
      <div className="learning-assistant-actions">
        {canCreateOrUpdate ? (
          <button className="learning-primary-action" onClick={onGenerate} disabled={generating} aria-busy={generating}>
            {generating ? text.loading : hasError ? text.retry : latest ? text.update : text.generate}
          </button>
        ) : (
          <button className="learning-primary-action" onClick={onFocusChat}>{count ? text.continue : text.start}</button>
        )}
        {latest && <button className="learning-text-action" onClick={() => onViewLatest(latest)}>{text.view}</button>}
      </div>
    </>
  )
}

function TeacherPanel({ text, status, generating, hasError, isActionPending, onGenerate, onViewLatest, onStudentAction }) {
  const total = status?.student_count ?? 0
  const active = status?.active_students ?? 0
  const ready = status?.ready_students ?? 0
  const latest = status?.latest_feedback
  const students = status?.students?.slice(0, 4) ?? []
  let opening = text.classNone
  if (total > 0 && active === 0) opening = fill(text.classQuiet, { total })
  else if (active > 0) opening = fill(text.classActive, { total, active })

  return (
    <>
      <div className="learning-assistant-letter">
        <p>{opening}</p>
        {active > 0 && <p>{ready > 0 ? fill(text.classReady, { ready }) : text.classGrowing}</p>}
      </div>
      {students.length > 0 && (
        <div className="learning-student-signals">
          <h3>{text.recentTrails}</h3>
          {students.map(student => {
            const countText = student.effective_question_count > 0
              ? fill(text.effective, { count: student.effective_question_count })
              : fill(text.messages, { count: student.message_count ?? 0 })
            return (
              <button key={student.id} onClick={() => onStudentAction(student)} disabled={generating || (!student.latest_report && !student.ready)} aria-busy={isActionPending(`learning:assistant:student:${student.id}`)}>
                <span><strong>{student.name}</strong><small>{countText}</small></span>
                <em className={student.latest_report ? 'has-report' : ''}>{student.latest_report ? text.reportReady : text.reportPending}</em>
              </button>
            )
          })}
        </div>
      )}
      <div className="learning-assistant-actions">
        <button className="learning-primary-action" onClick={onGenerate} disabled={generating || !active} aria-busy={generating}>
          {generating ? text.classLoading : hasError ? text.retry : latest ? text.updateClass : text.generateClass}
        </button>
        {latest && <button className="learning-text-action" onClick={() => onViewLatest(latest)}>{text.viewClass}</button>}
      </div>
    </>
  )
}

export function LearningReportDrawer({ value, language = 'zh', onClose }) {
  const text = copy[language] || copy.zh
  useEffect(() => {
    if (!value) return undefined
    const closeOnEscape = event => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [value, onClose])
  if (!value) return null

  const data = value.data
  const stats = data?.stats || {}
  const topics = stats.topics || stats.common_topics || []
  const weak = stats.weak_points || stats.class_weak_points || []
  const suggestions = stats.suggestions || stats.teaching_suggestions || []
  return (
    <div className="learning-drawer-layer" role="presentation" onClick={onClose}>
      <aside className="learning-report-drawer" role="dialog" aria-modal="true" aria-label={value.type === 'feedback' ? text.feedback : text.report} onClick={event => event.stopPropagation()}>
        <div className="learning-drawer-header">
          <div><span>{text.summary}</span><h2>{value.type === 'feedback' ? text.feedback : text.report}{data.student_name ? ` · ${data.student_name}` : ''}</h2></div>
          <button onClick={onClose} aria-label={text.close}>×</button>
        </div>
        <div className="learning-drawer-meta">
          <span>{text.generatedAt} · {formatDate(data.created_at, language)}</span>
          {data.message_count != null && <span>{data.message_count} 条对话记录</span>}
        </div>
        {topics.length > 0 && <section className="learning-insight-block"><h3>{text.topics}</h3><div className="learning-tag-list">{topics.map(item => <span key={item}>{item}</span>)}</div></section>}
        <section className="learning-report-summary"><h3>{text.summary}</h3><div>{data.summary}</div></section>
        {weak.length > 0 && <section className="learning-insight-block"><h3>{text.weak}</h3><ul>{weak.map(item => <li key={item}>{item}</li>)}</ul></section>}
        {suggestions.length > 0 && <section className="learning-insight-block learning-suggestions"><h3>{text.suggestions}</h3><ol>{suggestions.map(item => <li key={item}>{item}</li>)}</ol></section>}
      </aside>
    </div>
  )
}

export default function LearningMascot({ role, activeClass, open, loading, status, generating, generationReady = false, generationFailed = false, isActionPending, error, language = 'zh', onToggle, onClose, onGenerate, onViewLatest, onFocusChat, onGoToClasses, onStudentAction }) {
  const text = copy[language] || copy.zh
  const title = role === 'teacher' ? text.teacherTitle : text.studentTitle
  const showBadge = generationReady || (role === 'student'
    ? Boolean(status?.has_updates || (status?.can_generate && !status?.latest_report))
    : Boolean(status?.ready_students))

  useEffect(() => {
    if (!open) return undefined
    const closeOnEscape = event => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open, onClose])

  return (
    <div className={`learning-mascot-shell ${open ? 'is-open' : ''}`}>
      {open && (
        <section className="learning-assistant-panel" aria-label={title} aria-live="polite">
          <div className="learning-assistant-header">
            <div className="learning-assistant-avatar">离</div>
            <div className="learning-assistant-heading"><h2>{title}</h2><p>{activeClass?.name || text.contextFirst}</p></div>
            <button onClick={onClose} aria-label={text.close}>×</button>
          </div>
          {error && <p className="learning-sync-note"><span />{error}</p>}
          {generating && <p className="learning-background-note">{text.background}</p>}
          {loading ? <div className="learning-assistant-loading"><i /><i /><i /><span>{text.loading}</span></div>
            : !activeClass ? <><div className="learning-assistant-letter"><p>{text.noClass}</p></div><button className="learning-primary-action" onClick={onGoToClasses}>{text.goClass}</button></>
              : role === 'teacher'
                ? <TeacherPanel text={text} status={status} generating={generating} hasError={generationFailed} isActionPending={isActionPending} onGenerate={onGenerate} onViewLatest={onViewLatest} onStudentAction={onStudentAction} />
                : <StudentPanel text={text} status={status} generating={generating} hasError={generationFailed} onGenerate={onGenerate} onViewLatest={onViewLatest} onFocusChat={onFocusChat} />}
        </section>
      )}
      <button className="learning-mascot-button" onClick={onToggle} aria-expanded={open} aria-label={text.mascotLabel}>
        <span className="learning-mascot-ground" aria-hidden="true" />
        <img key={open ? 'rise' : 'idle'} src={open ? mascotRiseGif : mascotIdlePng} alt="小离学情助手" />
        {showBadge && <span className="learning-mascot-badge" aria-label={text.newHint} />}
        {!open && <span className="learning-mascot-label">{text.mascotLabel}</span>}
      </button>
    </div>
  )
}
