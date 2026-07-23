import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { HashRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { sendChatMessage, sendWelcomeMessage } from '../api/chat'
import { sendCode, register, login, selectRole } from '../api/auth'
import { fetchMyClasses, createClass, joinClass, fetchClassMaterials, uploadClassMaterial, fetchMaterialFile, fetchMaterialPreview } from '../api/classes'
import { fetchConversations, fetchConversationMessages, deleteConversation, submitConversationFeedback } from '../api/conversations'
import {
  fetchClassStudents,
  addClassStudent,
  removeClassStudent,
  generateStudentReport,
  generateMyReport,
  generateClassFeedback,
  fetchStudentReports,
  fetchLearningAssistantStatus,
} from '../api/learning'
import {
  fetchHomeworks,
  createHomework,
  deleteHomework,
  submitHomework,
  fetchHomeworkSubmissions,
  downloadHomeworkAttachment,
  downloadSubmissionFile,
} from '../api/homework'
import { getStoredUser, setAuth, clearAuth } from '../api/httpClient'
import LearningMascot, { LearningReportDrawer } from '../components/LearningMascot'
import Topbar from '../components/layout/Topbar'
import SceneBackdrop from '../components/scenes/SceneBackdrop'
import ChatHistorySidebar from '../components/chat/ChatHistorySidebar'
import AppModals from '../components/modals/AppModals'
import ChatPage from '../pages/ChatPage'
import ResourcesPage from '../pages/ResourcesPage'
import HomeworkPage from '../pages/HomeworkPage'
import { EXAMPLE_PROMPT_GROUPS, SCENE_QUOTES, TRANSLATIONS } from '../config/uiContent'
import { CODE_COOLDOWN_SEC, TONGJI_EMAIL_RE, getBeijingHour, getMaterialCategory, getRemainingCooldown, getSceneByHour, saveCooldown } from '../utils/appUtils'

const SCENE_OPTIONS = [
  { key: 'night', label: { en: 'Starry Night', zh: '星空黑夜' }, angle: 0 },
  { key: 'day', label: { en: 'Blue Sky', zh: '碧水蓝天' }, angle: 120 },
  { key: 'sunset', label: { en: 'Sunset', zh: '落日余晖' }, angle: 240 },
]

function AppController() {
  const location = useLocation()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [welcomeContent, setWelcomeContent] = useState('')
  const [welcomeLoading, setWelcomeLoading] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [authModal, setAuthModal] = useState(null) // null, 'login', 'signup'
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [user, setUser] = useState(() => getStoredUser())
  const [authForm, setAuthForm] = useState({ email: '', code: '', name: '', password: '', confirmPassword: '' })
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [classes, setClasses] = useState([])
  const [activeClassId, setActiveClassId] = useState(null)
  const [materials, setMaterials] = useState([])
  const [homeworks, setHomeworks] = useState([])
  const [homeworkForm, setHomeworkForm] = useState({ title: '', description: '', dueAt: '' })
  const [homeworkFile, setHomeworkFile] = useState(null)
  const [homeworkBusy, setHomeworkBusy] = useState(false)
  const [expandedHomeworkId, setExpandedHomeworkId] = useState(null)
  const [homeworkSubmissions, setHomeworkSubmissions] = useState({})
  const [submitDrafts, setSubmitDrafts] = useState({})
  const [classForm, setClassForm] = useState({ name: '', inviteCode: '' })
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [students, setStudents] = useState([])
  const [studentsOpen, setStudentsOpen] = useState(false)
  const [studentEmailInput, setStudentEmailInput] = useState('')
  const [studentBusy, setStudentBusy] = useState(false)
  const [reportModal, setReportModal] = useState(null)
  const [feedbackModal, setFeedbackModal] = useState(null)
  const [generatingLearning, setGeneratingLearning] = useState(false)
  const [learningAssistantOpen, setLearningAssistantOpen] = useState(false)
  const [learningAssistantStatus, setLearningAssistantStatus] = useState(null)
  const [learningAssistantLoading, setLearningAssistantLoading] = useState(false)
  const [learningAssistantError, setLearningAssistantError] = useState('')
  const [learningDrawer, setLearningDrawer] = useState(null)
  const [pendingImage, setPendingImage] = useState(null)
  const imageInputRef = useRef(null)
  const welcomeRequestRef = useRef(null)
  const [language, setLanguage] = useState('zh')
  const [activeFilter, setActiveFilter] = useState('All')
  const [exampleGroupIndex, setExampleGroupIndex] = useState(0)

  const [dialRotation, setDialRotation] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef({ startX: 0, startRot: 0 })
  const messagesEndRef = useRef(null)
  const composerInputRef = useRef(null)
  const pendingActionsRef = useRef(new Set())
  const [pendingActions, setPendingActions] = useState({})

  const isActionPending = useCallback(
    actionKey => Boolean(pendingActions[actionKey]),
    [pendingActions],
  )

  const runPendingAction = useCallback(async (actionKey, operation) => {
    if (pendingActionsRef.current.has(actionKey)) return undefined
    pendingActionsRef.current.add(actionKey)
    setPendingActions(current => ({ ...current, [actionKey]: true }))
    try {
      return await operation()
    } finally {
      pendingActionsRef.current.delete(actionKey)
      setPendingActions(current => {
        const next = { ...current }
        delete next[actionKey]
        return next
      })
    }
  }, [])

  const t = TRANSLATIONS[language]
  const isTeacher = user?.role === 'teacher'
  const isStudent = user?.role === 'student'
  const secondPageTitle = isTeacher ? t.teacherPageTitle : t.resourcesTitle
  const activeClass = useMemo(
    () => classes.find(c => c.id === activeClassId) || null,
    [classes, activeClassId],
  )
  const canChat = Boolean(user?.role && !user.needs_role_selection)
  const exampleGroups = EXAMPLE_PROMPT_GROUPS[language]?.[user?.role] || []
  const visibleExamplePrompts = exampleGroups[exampleGroupIndex] || []
  const activeSection = location.pathname === '/resources'
    ? 'resources'
    : location.pathname === '/homework'
      ? 'homework'
      : 'chat'

  const welcomeText = useMemo(() => {
    if (!user) return t.auth.welcomeGuest
    if (user.needs_role_selection) return t.auth.welcomeRolePending
    if (isTeacher && !activeClass) {
      return language === 'zh'
        ? '你好，老师！请先创建或选择一个班级，然后我会围绕当前班级协助你进行教学问答、资料与学生管理。'
        : 'Hello, teacher! Create or select a class first, then I can support teaching Q&A, materials, and student management for that class.'
    }
    return isTeacher ? t.auth.welcomeTeacher : isStudent ? t.auth.welcomeStudent : t.auth.welcomeGuest
  }, [user, isTeacher, isStudent, activeClass, language, t])

  const chatPlaceholder = useMemo(() => {
    if (!user) return t.auth.welcomeGuest
    if (user.needs_role_selection) return t.auth.welcomeRolePending
    return t.placeholder
  }, [user, t])
  const visibleMaterials = useMemo(() => {
    if (activeFilter === 'All') return materials
    return materials.filter(m => getMaterialCategory(m) === activeFilter)
  }, [materials, activeFilter])

  const loadClasses = useCallback(async () => {
    if (!user?.role) return
    try {
      const data = await fetchMyClasses()
      setClasses(data)
      if (data.length > 0 && !activeClassId) setActiveClassId(data[0].id)
    } catch (err) {
      console.error(err)
    }
  }, [user?.role, activeClassId])

  const loadMaterials = useCallback(async (classId) => {
    if (!classId) return
    try {
      const data = await fetchClassMaterials(classId)
      setMaterials(data)
    } catch (err) {
      console.error(err)
      setMaterials([])
    }
  }, [])

  const loadHomeworks = useCallback(async (classId) => {
    if (!classId || !user?.role) return
    try {
      const data = await fetchHomeworks(classId)
      setHomeworks(data)
    } catch (err) {
      console.error(err)
      setHomeworks([])
    }
  }, [user?.role])

  useEffect(() => {
    if (user?.role) loadClasses()
  }, [user?.role, loadClasses])

  useEffect(() => {
    if (activeClassId) {
      loadMaterials(activeClassId)
      loadHomeworks(activeClassId)
      setExpandedHomeworkId(null)
    } else {
      setHomeworks([])
    }
  }, [activeClassId, loadMaterials, loadHomeworks])

  const handleSectionChange = useCallback((target) => {
    navigate(`/${target}`)
    setSidebarOpen(false)
    setSettingsOpen(false)
    setLearningAssistantOpen(false)
  }, [navigate])

  const loadConversations = useCallback(async () => {
    if (!user?.role) return []
    try {
      const convs = await fetchConversations()
      setConversations(convs)
      return convs
    } catch (err) {
      console.error(err)
      setConversations([])
      return []
    }
  }, [user?.role])

  const selectConversation = useCallback(async (id) => {
    try {
      setConversationId(id)
      const msgs = await fetchConversationMessages(id)
      setMessages(msgs.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        imagePath: m.image_url || null,
        feedback: m.feedback || null,
      })))
    } catch (err) {
      console.error(err)
    }
  }, [])

  const loadLatestConversation = useCallback(async () => {
    if (!user?.role) return
    const convs = await loadConversations()
    if (convs.length > 0) {
      await selectConversation(convs[0].id)
    } else {
      setConversationId(null)
      setMessages([])
    }
  }, [user?.role, loadConversations, selectConversation])

  const loadStudents = useCallback(async (classId) => {
    if (!classId || user?.role !== 'teacher') return
    try {
      const data = await fetchClassStudents(classId)
      setStudents(data)
    } catch (err) {
      console.error(err)
      setStudents([])
    }
  }, [user?.role])

  const loadLearningAssistantStatus = useCallback(async (classId) => {
    if (!classId || !user?.role) {
      setLearningAssistantStatus(null)
      return
    }
    setLearningAssistantLoading(true)
    setLearningAssistantError('')
    try {
      setLearningAssistantStatus(await fetchLearningAssistantStatus(classId))
    } catch (err) {
      console.error(err)
      if (user?.role === 'teacher') {
        const fallbackStudents = students.map(student => ({
          id: student.id,
          name: student.name,
          effective_question_count: student.effective_question_count ?? 0,
          message_count: student.message_count ?? 0,
          ready: (student.effective_question_count ?? 0) >= 5,
          latest_report: null,
        }))
        setLearningAssistantStatus({
          role: 'teacher',
          class_id: classId,
          student_count: fallbackStudents.length,
          active_students: fallbackStudents.filter(student => student.message_count > 0).length,
          ready_students: fallbackStudents.filter(student => student.ready).length,
          students: fallbackStudents,
          latest_feedback: null,
          fallback: true,
        })
        setLearningAssistantError(language === 'zh' ? '详细学情还在同步，先为你显示班级里的最新记录。' : 'Detailed learning data is syncing. Showing the latest class records for now.')
      } else {
        setLearningAssistantError(language === 'zh' ? '学习记录还在同步，稍后再来看看吧。' : 'Your learning records are still syncing. Please check again shortly.')
      }
    } finally {
      setLearningAssistantLoading(false)
    }
  }, [user?.role, language, students])
  useEffect(() => {
    if (user?.role) loadLatestConversation()
  }, [user?.role, loadLatestConversation])

  useEffect(() => {
    if (!canChat || conversationId || messages.length > 0) return
    const key = `${user?.email || 'user'}:${user?.role || 'none'}:${activeClassId || 'none'}`
    if (welcomeRequestRef.current === key) return

    let cancelled = false
    welcomeRequestRef.current = key
    setWelcomeContent('')
    setWelcomeLoading(true)

    sendWelcomeMessage(activeClassId, (chunk) => {
      if (!cancelled) setWelcomeContent(prev => prev + chunk)
    })
      .catch((err) => {
        console.error(err)
        if (!cancelled) setWelcomeContent('')
      })
      .finally(() => {
        if (!cancelled) setWelcomeLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [canChat, conversationId, messages.length, activeClassId, user?.email, user?.role])

  useEffect(() => {
    if (activeClassId && isTeacher) loadStudents(activeClassId)
  }, [activeClassId, isTeacher, loadStudents])

  useEffect(() => {
    if (isSending) return undefined
    const timer = window.setTimeout(() => {
      if (activeClassId && user?.role) loadLearningAssistantStatus(activeClassId)
      else setLearningAssistantStatus(null)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isSending, activeClassId, user?.role, loadLearningAssistantStatus])
  useEffect(() => {
    if (authModal === 'signup' && authForm.email) {
      setCodeCooldown(getRemainingCooldown(authForm.email))
    }
  }, [authForm.email, authModal])

  useEffect(() => {
    if (codeCooldown <= 0) return
    const timer = setTimeout(() => setCodeCooldown(c => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [codeCooldown])

  const handleAuthSuccess = (data) => {
    const nextUser = {
      email: data.email,
      name: data.name,
      role: data.role,
      needs_role_selection: data.needs_role_selection,
    }
    setAuth(data.access_token, nextUser)
    setUser(nextUser)
    setExampleGroupIndex(0)
    setAuthModal(null)
    if (data.needs_role_selection) setRoleModalOpen(true)
  }

  const handleSendCode = async () => {
    if (codeCooldown > 0 || sendingCode) return

    const email = authForm.email.trim().toLowerCase()
    if (!email) {
      setAuthError(language === 'zh' ? '请先填写学校邮箱' : 'Please enter your school email')
      return
    }
    if (!TONGJI_EMAIL_RE.test(email)) {
      setAuthError(language === 'zh' ? '邮箱格式：7位学号@tongji.edu.cn' : 'Email format: 7-digit ID@tongji.edu.cn')
      return
    }

    return runPendingAction('auth:code', async () => {
    setAuthError('')
    saveCooldown(email)
    setCodeCooldown(CODE_COOLDOWN_SEC)
    setSendingCode(true)

    try {
      await sendCode(email)
    } catch (err) {
      setAuthError(['REQUEST_TIMEOUT', 'SERVICE_UNAVAILABLE'].includes(err.code) ? t.auth.serviceUnavailable : err.message)
    } finally {
      setSendingCode(false)
    }
    })
  }

  const handleSignup = async (e) => {
    e.preventDefault()
    return runPendingAction('auth:signup', async () => {
    setAuthError('')
    setAuthLoading(true)
    try {
      const data = await register({
        email: authForm.email.trim().toLowerCase(),
        code: authForm.code.trim(),
        name: authForm.name.trim(),
        password: authForm.password,
        confirm_password: authForm.confirmPassword,
      })
      handleAuthSuccess(data)
    } catch (err) {
      setAuthError(['REQUEST_TIMEOUT', 'SERVICE_UNAVAILABLE'].includes(err.code) ? t.auth.serviceUnavailable : err.message)
    } finally {
      setAuthLoading(false)
    }
    })
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    return runPendingAction('auth:login', async () => {
    setAuthError('')
    setAuthLoading(true)
    try {
      const data = await login({
        email: authForm.email.trim().toLowerCase(),
        password: authForm.password,
      })
      handleAuthSuccess(data)
    } catch (err) {
      setAuthError(['REQUEST_TIMEOUT', 'SERVICE_UNAVAILABLE'].includes(err.code) ? t.auth.serviceUnavailable : err.message)
    } finally {
      setAuthLoading(false)
    }
    })
  }

  const handleSelectRole = async (role) => {
    return runPendingAction(`auth:role:${role}`, async () => {
    setAuthLoading(true)
    try {
      const data = await selectRole(role)
      const nextUser = { ...user, role: data.role, needs_role_selection: false }
      setAuth(data.access_token, nextUser)
      setUser(nextUser)
      setExampleGroupIndex(0)
      setRoleModalOpen(false)
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
    })
  }

  const handleLogout = () => {
    clearAuth()
    navigate('/chat', { replace: true })
    setUser(null)
    setExampleGroupIndex(0)
    welcomeRequestRef.current = null
    setWelcomeContent('')
    setWelcomeLoading(false)
    setClasses([])
    setMaterials([])
    setHomeworks([])
    setHomeworkForm({ title: '', description: '', dueAt: '' })
    setHomeworkFile(null)
    setExpandedHomeworkId(null)
    setHomeworkSubmissions({})
    setSubmitDrafts({})
    setActiveClassId(null)
    setMessages([])
    setConversationId(null)
    setConversations([])
    setSidebarOpen(false)
    setStudents([])
    setStudentsOpen(false)
    setReportModal(null)
    setFeedbackModal(null)
  }

  const handleNewChat = () => {
    setConversationId(null)
    setMessages([])
    welcomeRequestRef.current = null
    setWelcomeContent('')
    setExampleGroupIndex(0)
  }

  const handleSelectConversation = async (id) => {
    await selectConversation(id)
    setSidebarOpen(false)
  }

  const handleDeleteConversation = async (e, id) => {
    e.stopPropagation()
    if (!window.confirm(t.auth.deleteChatConfirm)) return
    try {
      await deleteConversation(id)
      setConversations(prev => prev.filter(c => c.id !== id))
      if (conversationId === id) {
        setConversationId(null)
        setMessages([])
      }
    } catch (err) {
      alert(err.message || (language === 'zh' ? '删除失败' : 'Delete failed'))
    }
  }

  const handleGenerateStudentReport = async (studentId) => {
    if (!activeClassId || generatingLearning) return
    return runPendingAction(`learning:student:${studentId}`, async () => {
      setGeneratingLearning(true)
      try {
        const report = await generateStudentReport(activeClassId, studentId)
        setReportModal(report)
        loadStudents(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        setGeneratingLearning(false)
      }
    })
  }

  const handleViewStudentReport = async (studentId) => {
    if (!activeClassId) return
    return runPendingAction(`learning:view:${studentId}`, async () => {
      try {
        const reports = await fetchStudentReports(activeClassId, studentId)
        if (reports.length === 0) {
          alert(language === 'zh' ? '暂无学情报告，请先生成' : 'No report yet, please generate first')
          return
        }
        setReportModal(reports[0])
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleGenerateMyReport = async () => {
    if (!activeClassId || generatingLearning) return
    return runPendingAction('learning:self', async () => {
      setGeneratingLearning(true)
      try {
        const report = await generateMyReport(activeClassId)
        setReportModal(report)
      } catch (err) {
        alert(err.message)
      } finally {
        setGeneratingLearning(false)
      }
    })
  }

  const handleGenerateClassFeedback = async () => {
    if (!activeClassId || generatingLearning) return
    return runPendingAction('learning:class', async () => {
      setGeneratingLearning(true)
      try {
        const feedback = await generateClassFeedback(activeClassId)
        setFeedbackModal(feedback)
      } catch (err) {
        alert(err.message)
      } finally {
        setGeneratingLearning(false)
      }
    })
  }

  const handleLearningAssistantToggle = () => {
    const nextOpen = !learningAssistantOpen
    setLearningAssistantOpen(nextOpen)
    if (nextOpen && activeClassId) loadLearningAssistantStatus(activeClassId)
  }

  const handleAssistantGenerate = async () => {
    if (!activeClassId || generatingLearning) return
    return runPendingAction(`learning:assistant:${isTeacher ? 'class' : 'self'}`, async () => {
    setGeneratingLearning(true)
    setLearningAssistantError('')
    try {
      if (isTeacher) {
        const feedback = await generateClassFeedback(activeClassId)
        setLearningDrawer({ type: 'feedback', data: feedback })
      } else {
        const report = await generateMyReport(activeClassId)
        setLearningDrawer({ type: 'report', data: report })
      }
      await loadLearningAssistantStatus(activeClassId)
    } catch (err) {
      setLearningAssistantError(err.message || (language === 'zh' ? '生成失败，请稍后再试' : 'Generation failed. Please try again.'))
    } finally {
      setGeneratingLearning(false)
    }
    })
  }

  const handleAssistantStudentAction = async (student) => {
    if (student.latest_report) {
      setLearningDrawer({ type: 'report', data: student.latest_report })
      return
    }
    if (!student.ready) {
      setLearningAssistantError(language === 'zh' ? `${student.name} 的学习轨迹仍在积累，暂时不做学情判断。` : `${student.name}'s learning trail is still developing.`)
      return
    }
    if (generatingLearning) return
    return runPendingAction(`learning:assistant:student:${student.id}`, async () => {
    setGeneratingLearning(true)
    setLearningAssistantError('')
    try {
      const report = await generateStudentReport(activeClassId, student.id)
      setLearningDrawer({ type: 'report', data: report })
      await loadLearningAssistantStatus(activeClassId)
    } catch (err) {
      setLearningAssistantError(err.message)
    } finally {
      setGeneratingLearning(false)
    }
    })
  }

  const handleAddStudent = async () => {
    if (!activeClassId || !studentEmailInput.trim() || studentBusy) return
    return runPendingAction('student:add', async () => {
      setStudentBusy(true)
      try {
        await addClassStudent(activeClassId, { email: studentEmailInput.trim().toLowerCase() })
        setStudentEmailInput('')
        await loadStudents(activeClassId)
        await loadLearningAssistantStatus(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        setStudentBusy(false)
      }
    })
  }

  const handleRemoveStudent = async (studentId) => {
    if (!activeClassId || studentBusy) return
    return runPendingAction(`student:remove:${studentId}`, async () => {
      setStudentBusy(true)
      try {
        await removeClassStudent(activeClassId, studentId)
        setStudents(prev => prev.filter(s => s.id !== studentId))
        await loadLearningAssistantStatus(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        setStudentBusy(false)
      }
    })
  }

  const handleCreateClass = async () => {
    if (!classForm.name.trim()) return
    return runPendingAction('class:create', async () => {
      try {
        await createClass(classForm.name.trim())
        setClassForm(prev => ({ ...prev, name: '' }))
        loadClasses()
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleJoinClass = async () => {
    if (!classForm.inviteCode.trim()) return
    return runPendingAction('class:join', async () => {
      try {
        await joinClass(classForm.inviteCode.trim())
        setClassForm(prev => ({ ...prev, inviteCode: '' }))
        loadClasses()
        alert(t.auth.joinSuccess)
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleUploadMaterial = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !activeClassId) return
    return runPendingAction('material:upload', async () => {
      try {
        await uploadClassMaterial(activeClassId, file)
        loadMaterials(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        e.target.value = ''
      }
    })
  }

  const openMaterialFile = async (material, download = false) => {
    if (!activeClassId) return
    const actionKey = `material:${download ? 'download' : 'view'}:${material.id}`
    return runPendingAction(actionKey, async () => {
      try {
        const blob = download
          ? await fetchMaterialFile(activeClassId, material.id, true)
          : await fetchMaterialPreview(activeClassId, material.id)
        const url = URL.createObjectURL(blob)

        if (download) {
          const link = document.createElement('a')
          link.href = url
          link.download = material.filename
          document.body.appendChild(link)
          link.click()
          link.remove()
        } else {
          window.open(url, '_blank', 'noopener,noreferrer')
        }

        setTimeout(() => URL.revokeObjectURL(url), 60_000)
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const downloadBlobFile = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename || 'download'
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  const handlePublishHomework = async () => {
    if (!activeClassId || !homeworkForm.title.trim() || homeworkBusy) return
    return runPendingAction('homework:publish', async () => {
      setHomeworkBusy(true)
      try {
        await createHomework(activeClassId, {
          title: homeworkForm.title.trim(),
          description: homeworkForm.description,
          dueAt: homeworkForm.dueAt,
          file: homeworkFile,
        })
        setHomeworkForm({ title: '', description: '', dueAt: '' })
        setHomeworkFile(null)
        await loadHomeworks(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        setHomeworkBusy(false)
      }
    })
  }

  const handleDeleteHomework = async (homeworkId) => {
    if (!window.confirm(t.auth.deleteHomeworkConfirm)) return
    return runPendingAction(`homework:delete:${homeworkId}`, async () => {
      try {
        await deleteHomework(homeworkId)
        setHomeworks(prev => prev.filter(h => h.id !== homeworkId))
        if (expandedHomeworkId === homeworkId) setExpandedHomeworkId(null)
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleSubmitHomework = async (homeworkId) => {
    if (homeworkBusy) return
    const draft = submitDrafts[homeworkId] || {}
    return runPendingAction(`homework:submit:${homeworkId}`, async () => {
      setHomeworkBusy(true)
      try {
        await submitHomework(homeworkId, {
          content: draft.content || '',
          file: draft.file || null,
        })
        setSubmitDrafts(prev => ({ ...prev, [homeworkId]: { content: '', file: null } }))
        await loadHomeworks(activeClassId)
      } catch (err) {
        alert(err.message)
      } finally {
        setHomeworkBusy(false)
      }
    })
  }

  const handleToggleSubmissions = async (homeworkId) => {
    if (expandedHomeworkId === homeworkId) {
      setExpandedHomeworkId(null)
      return
    }
    return runPendingAction(`homework:submissions:${homeworkId}`, async () => {
      try {
        const rows = await fetchHomeworkSubmissions(homeworkId)
        setHomeworkSubmissions(prev => ({ ...prev, [homeworkId]: rows }))
        setExpandedHomeworkId(homeworkId)
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleDownloadAttachment = async (hw) => {
    return runPendingAction(`homework:attachment:${hw.id}`, async () => {
      try {
        const blob = await downloadHomeworkAttachment(hw.id)
        downloadBlobFile(blob, hw.attachment_name || 'attachment')
      } catch (err) {
        alert(err.message)
      }
    })
  }

  const handleDownloadSubmission = async (sub) => {
    return runPendingAction(`submission:download:${sub.id}`, async () => {
      try {
        const blob = await downloadSubmissionFile(sub.id)
        downloadBlobFile(blob, sub.filename || 'submission')
      } catch (err) {
        alert(err.message)
      }
    })
  }

  // 自动滚动到最新消息
  useEffect(() => {
    if (messagesEndRef.current) {
      // 关键：只在消息列表容器内滚动，不影响全局
      messagesEndRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest', // 避免滚动整个页面
        inline: 'start'
      })
    }
  }, [messages])

  // Initialize dial based on current time
  useEffect(() => {
    const currentSceneKey = getSceneByHour(getBeijingHour())
    const targetScene = SCENE_OPTIONS.find(s => s.key === currentSceneKey)
    if (targetScene) {
      setDialRotation(-targetScene.angle)
    }
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

  const chatOpacity = 1
  const quoteOpacity = 1

  const activeQuote = useMemo(() => SCENE_QUOTES[activeSceneKey][language], [activeSceneKey, language])

  const handleMouseDown = (e) => {
    setIsDragging(true)
    dragRef.current = { startX: e.clientX, startRot: dialRotation }
  }

  const handleSceneSelect = useCallback((sceneKey) => {
    const targetScene = SCENE_OPTIONS.find(scene => scene.key === sceneKey)
    if (!targetScene) return
    setDialRotation(currentRotation => {
      const baseRotation = -targetScene.angle
      const nearestTurn = Math.round((currentRotation - baseRotation) / 360)
      return baseRotation + nearestTurn * 360
    })
  }, [])

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

  const handlePickImage = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      alert(language === 'zh' ? '请选择图片文件' : 'Please select an image file')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      alert(language === 'zh' ? '图片不能超过 5MB' : 'Image must be under 5MB')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result
      const base64 = String(dataUrl).split(',')[1]
      setPendingImage({ previewUrl: dataUrl, base64, mime: file.type })
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleFeedback = async (messageIndex, feedbackType) => {
    const targetMessage = messages[messageIndex]
    if (!targetMessage || targetMessage.role !== 'assistant' || !conversationId || !targetMessage.id) return
    try {
      await submitConversationFeedback(conversationId, targetMessage.id, feedbackType)
      setMessages(prev => prev.map((msg, idx) => idx === messageIndex ? { ...msg, feedback: feedbackType } : msg))
    } catch (err) {
      alert(err.message)
    }
  }

  const handleCopyMessage = async (content) => {
    if (!content) return
    try {
      await navigator.clipboard.writeText(content)
    } catch (err) {
      alert(err.message || (language === 'zh' ? '复制失败' : 'Copy failed'))
    }
  }

  const handleExampleSelect = (prompt) => {
    setInput(prompt)
    requestAnimationFrame(() => {
      composerInputRef.current?.focus()
      composerInputRef.current?.setSelectionRange(prompt.length, prompt.length)
    })
  }

  const handleRefreshExamples = () => {
    if (exampleGroups.length < 2) return
    setExampleGroupIndex(current => (current + 1) % exampleGroups.length)
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!canChat) {
      if (!user) setAuthModal('login')
      else if (user.needs_role_selection) setRoleModalOpen(true)
      return
    }
    if ((!input.trim() && !pendingImage) || isSending) return

    return runPendingAction('chat:send', async () => {
    const text = input.trim()
    const displayText = text || (language === 'zh' ? '[图片]' : '[Image]')
    const userMessage = {
      role: 'user',
      content: displayText,
      imagePreview: pendingImage?.previewUrl || null,
    }
    const imagePayload = pendingImage
      ? { image_base64: pendingImage.base64, image_mime: pendingImage.mime }
      : {}

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setPendingImage(null)
    setIsSending(true)

    // 创建一个空的助手消息占位
    const assistantMessage = { role: 'assistant', content: '' }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const newConversationId = await sendChatMessage({
        message: text,
        conversation_id: conversationId,
        class_id: activeClassId,
        ...imagePayload,
      }, (chunk) => {
        setMessages(prev => {
          const lastIndex = prev.length - 1
          if (lastIndex >= 0 && prev[lastIndex].role === 'assistant') {
            // 创建一个全新的数组和全新的消息对象，确保不可变性
            const newMessages = [...prev]
            newMessages[lastIndex] = {
              ...newMessages[lastIndex],
              content: newMessages[lastIndex].content + chunk
            }
            return newMessages
          }
          return prev
        })
      })
      if (newConversationId) {
        setConversationId(newConversationId)
        loadConversations()
        const persistedMessages = await fetchConversationMessages(newConversationId)
        setMessages(persistedMessages.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          imagePath: m.image_url || null,
          feedback: m.feedback || null,
        })))
      }
    } catch (err) {
      console.error(err)
      alert(err.message || '发送失败')
      setMessages(prev => {
        const newMessages = [...prev]
        const lastMsg = newMessages[newMessages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = '抱歉，发生了错误，请稍后再试。'
        }
        return newMessages
      })
    } finally {
      setIsSending(false)
    }
    })
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
  }

  const viewModel = {
    SCENE_OPTIONS,
    authError,
    authForm,
    authLoading,
    authModal,
    activeClassId,
    activeFilter,
    activeQuote,
    activeSceneKey,
    canChat,
    chatOpacity,
    chatPlaceholder,
    classForm,
    classes,
    codeCooldown,
    conversationId,
    conversations,
    composerInputRef,
    dialRotation,
    expandedHomeworkId,
    feedbackModal,
    generatingLearning,
    handleAddStudent,
    handleCopyMessage,
    handleCreateClass,
    handleDeleteHomework,
    handleDownloadAttachment,
    handleDownloadSubmission,
    handleExampleSelect,
    handleFeedback,
    handleGenerateClassFeedback,
    handleGenerateMyReport,
    handleGenerateStudentReport,
    handleJoinClass,
    handleKeyDown,
    handleLogin,
    handleMouseDown,
    handleSceneSelect,
    handleNewChat,
    handlePickImage,
    handlePublishHomework,
    handleRefreshExamples,
    handleRemoveStudent,
    handleDeleteConversation,
    handleSelectConversation,
    handleSelectRole,
    handleSend,
    handleSendCode,
    handleSignup,
    handleSubmitHomework,
    handleToggleSubmissions,
    handleUploadMaterial,
    handleViewStudentReport,
    homeworkBusy,
    homeworkFile,
    homeworkForm,
    homeworks,
    homeworkSubmissions,
    imageInputRef,
    input,
    isDragging,
    isSending,
    isActionPending,
    isStudent,
    isTeacher,
    language,
    materials,
    messages,
    messagesEndRef,
    openMaterialFile,
    pendingImage,
    quoteOpacity,
    reportModal,
    roleModalOpen,
    secondPageTitle,
    setActiveClassId,
    setActiveFilter,
    setAuthForm,
    setAuthModal,
    setClassForm,
    setHomeworkFile,
    setHomeworkForm,
    setInput,
    setPendingImage,
    setFeedbackModal,
    setReportModal,
    setSidebarOpen,
    setStudentEmailInput,
    setStudentsOpen,
    setSubmitDrafts,
    studentBusy,
    studentEmailInput,
    students,
    studentsOpen,
    sendingCode,
    sidebarOpen,
    submitDrafts,
    t,
    user,
    visibleExamplePrompts,
    visibleMaterials,
    welcomeContent,
    welcomeLoading,
    welcomeText,
  }

  return (
    <div className="app-container">
      {activeSection === 'chat' && <ChatHistorySidebar model={viewModel} />}

      <main className="page" data-scene={activeSceneKey}>
        <SceneBackdrop scenes={SCENE_OPTIONS} opacities={sceneOpacities} />

        <Topbar
          t={t}
          user={user}
          isTeacher={isTeacher}
          language={language}
          settingsOpen={settingsOpen}
          setLanguage={setLanguage}
          setSettingsOpen={setSettingsOpen}
          onNavigate={handleSectionChange}
          onLogout={handleLogout}
          onOpenAuth={setAuthModal}
        />

        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={(
        <ChatPage model={viewModel} />
          )} />

          <Route path="/resources" element={canChat ? (
        <ResourcesPage model={viewModel} />
          ) : <Navigate to="/chat" replace />} />

        {user && (isTeacher || isStudent) && (
          <Route path="/homework" element={canChat ? (
          <HomeworkPage model={viewModel} />
          ) : <Navigate to="/chat" replace />} />
        )}
        </Routes>
      </main>

      {user && activeSection === 'chat' && (
        <LearningMascot
          role={user.role}
          activeClass={activeClass}
          open={learningAssistantOpen}
          loading={learningAssistantLoading}
          status={learningAssistantStatus}
          generating={generatingLearning}
          isActionPending={isActionPending}
          error={learningAssistantError}
          language={language}
          onToggle={handleLearningAssistantToggle}
          onClose={() => setLearningAssistantOpen(false)}
          onGenerate={handleAssistantGenerate}
          onViewLatest={(data) => setLearningDrawer({ type: isTeacher ? 'feedback' : 'report', data })}
          onFocusChat={() => {
            setLearningAssistantOpen(false)
            requestAnimationFrame(() => composerInputRef.current?.focus())
          }}
          onGoToClasses={() => {
            setLearningAssistantOpen(false)
            handleSectionChange('resources')
          }}
          onStudentAction={handleAssistantStudentAction}
        />
      )}

      <LearningReportDrawer value={learningDrawer} language={language} onClose={() => setLearningDrawer(null)} />

      <AppModals model={viewModel} />

    </div>
  )
}

export default function App() {
  return (
    <HashRouter>
      <AppController />
    </HashRouter>
  )
}
