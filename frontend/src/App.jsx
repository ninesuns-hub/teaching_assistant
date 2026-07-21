import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import './App.css'
import { sendChatMessage, sendWelcomeMessage } from './api/chat'
import { sendCode, register, login, selectRole } from './api/auth'
import { fetchMyClasses, createClass, joinClass, fetchClassMaterials, uploadClassMaterial, fetchMaterialFile, fetchMaterialPreview } from './api/classes'
import { fetchConversations, fetchConversationMessages, deleteConversation, submitConversationFeedback } from './api/conversations'
import {
  fetchClassStudents,
  addClassStudent,
  removeClassStudent,
  generateStudentReport,
  generateMyReport,
  generateClassFeedback,
  fetchStudentReports,
  fetchLearningAssistantStatus,
} from './api/learning'
import {
  fetchHomeworks,
  createHomework,
  deleteHomework,
  submitHomework,
  fetchHomeworkSubmissions,
  downloadHomeworkAttachment,
  downloadSubmissionFile,
} from './api/homework'
import { getStoredUser, setAuth, clearAuth, getToken } from './api/httpClient'
import MarkdownMessage from './components/MarkdownMessage'
import LearningMascot, { LearningReportDrawer } from './components/LearningMascot'
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

const MessageActionIcon = ({ type }) => {
  if (type === 'copy') return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" />
    </svg>
  )
  if (type === 'up') return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 10v11" />
      <path d="M15 5.5 14 10h5.2a2 2 0 0 1 1.95 2.44l-1.45 6.4A3 3 0 0 1 16.77 21H7" />
      <path d="M7 10 12 3a2 2 0 0 1 3 2.5" />
    </svg>
  )
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 14V3" />
      <path d="M15 18.5 14 14h5.2a2 2 0 0 0 1.95-2.44L19.7 5.16A3 3 0 0 0 16.77 3H7" />
      <path d="M7 14 12 21a2 2 0 0 0 3-2.5" />
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
    scrollDownStudent: 'Scroll down for learning resources',
    scrollDownTeacher: 'Scroll down to manage classes',
    resourcesTitle: 'Learning Resources',
    teacherPageTitle: 'My Classes',
    navChat: 'Chat',
    navResources: 'Resources',
    navClasses: 'Classes',
    navHomework: 'Homework',
    navMore: 'More',
    exampleQuestions: 'Example questions',
    refreshExamples: 'Try another set',
    homeworkPageTitle: 'Homework',
    view: 'View',
    download: 'Download',
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
      email: 'School Email',
      emailHint: 'Format: 1234567@tongji.edu.cn',
      code: 'Verification Code',
      sendCode: 'Send Code',
      name: 'Name',
      password: 'Password',
      confirmPassword: 'Confirm Password',
      loginBtn: 'Login',
      signupBtn: 'Sign up',
      loggingIn: 'Logging in…',
      signingUp: 'Creating account…',
      serviceUnavailable: 'The service is not responding. Please try again shortly.',
      noAccount: "Don't have an account?",
      hasAccount: 'Already have an account?',
      backToHome: 'Back to Home',
      roleTitle: 'Are you a student or a teacher?',
      student: 'Student',
      teacher: 'Teacher',
      confirmRole: 'Confirm',
      logout: 'Logout',
      createClass: 'Create Class',
      joinClass: 'Join Class',
      className: 'Class Name',
      inviteCode: 'Invite Code',
      myClasses: 'My Classes',
      uploadMaterial: 'Upload Material',
      noClasses: 'No classes yet',
      joinSuccess: 'Joined successfully',
      inviteCodeLabel: 'Invite Code',
      selectClassHint: 'Select a class to view materials',
      studentNoClassHint: 'Join a class with invite code to access materials',
      teacherNoClassHint: 'Create a class to start uploading materials',
      learningTitle: 'Learning Analytics',
      generateMyReport: 'Generate My Report',
      classStudents: 'My Students',
      generateReport: 'Generate Report',
      viewReport: 'View Report',
      generateClassFeedback: 'Generate Class Feedback',
      viewFeedback: 'View Feedback',
      generating: 'Generating...',
      messagesCount: 'Meaningful learning exchanges',
      noStudents: 'No students in class yet',
      expandStudents: 'Expand',
      collapseStudents: 'Collapse',
      addStudent: 'Add student',
      studentEmail: 'Student email',
      removeStudent: 'Remove',
      feedbackHelpful: 'Helpful',
      feedbackUnhelpful: 'Not helpful',
      feedbackCopy: 'Copy',
      welcomeGuest: 'Welcome! Please log in to start chatting.',
      welcomeRolePending: 'Please choose your identity before you start.',
      welcomeStudent: 'Hello! I am your discrete math tutor. I can help explain concepts and answer questions.',
      welcomeTeacher: 'Hello, teacher! I can help answer student questions and support class management.',
      reportTitle: 'Learning Report',
      feedbackTitle: 'Class Feedback',
      newChat: 'New Chat',
      historyTitle: 'History',
      noHistory: 'No conversations yet',
      today: 'Today',
      attachImage: 'Image',
      deleteChat: 'Delete',
      deleteChatConfirm: 'Delete this conversation?',
      homeworkTitle: 'Homework',
      publishHomework: 'Publish Homework',
      homeworkName: 'Title',
      homeworkDesc: 'Description (optional)',
      homeworkDue: 'Due date',
      homeworkAttach: 'Attachment (optional)',
      noHomework: 'No homework yet',
      submitHomework: 'Submit',
      resubmitHomework: 'Resubmit',
      submissionNote: 'Note (optional)',
      uploadSubmission: 'Upload file',
      viewSubmissions: 'Submissions',
      hideSubmissions: 'Hide',
      submitted: 'Submitted',
      notSubmitted: 'Not submitted',
      deleteHomework: 'Delete',
      deleteHomeworkConfirm: 'Delete this homework?',
      downloadAttachment: 'Attachment',
      submissionCount: 'submissions',
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
    scrollDownStudent: '向下滑动查看学习资源',
    scrollDownTeacher: '向下滑动管理班级',
    resourcesTitle: '学习资源',
    teacherPageTitle: '我的班级',
    navChat: '对话',
    navResources: '学习资源',
    navClasses: '我的班级',
    navHomework: '作业',
    navMore: '更多',
    exampleQuestions: '示例问题',
    refreshExamples: '换一换',
    homeworkPageTitle: '作业',
    view: '查看',
    download: '下载',
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
      email: '学校邮箱',
      emailHint: '格式：7位学号@tongji.edu.cn',
      code: '验证码',
      sendCode: '获取验证码',
      name: '姓名',
      password: '密码',
      confirmPassword: '确认密码',
      loginBtn: '登录',
      signupBtn: '注册',
      loggingIn: '登录中…',
      signingUp: '正在创建账号…',
      serviceUnavailable: '服务暂时无响应，请稍后再试。',
      noAccount: '还没有账号？',
      hasAccount: '已有账号？',
      backToHome: '返回首页',
      roleTitle: '请问你是学生还是教师？',
      student: '学生',
      teacher: '教师',
      confirmRole: '确认',
      logout: '退出登录',
      createClass: '创建班级',
      joinClass: '加入班级',
      className: '班级名称',
      inviteCode: '邀请码',
      myClasses: '我的班级',
      uploadMaterial: '上传资料',
      noClasses: '暂无班级',
      joinSuccess: '加入成功',
      inviteCodeLabel: '邀请码',
      selectClassHint: '选择班级查看资料',
      studentNoClassHint: '输入邀请码加入班级后即可查看学习资料',
      teacherNoClassHint: '创建班级后即可上传和管理学习资料',
      learningTitle: '学情分析',
      generateMyReport: '生成我的学情报告',
      classStudents: '我的学生',
      generateReport: '生成学情报告',
      viewReport: '查看报告',
      generateClassFeedback: '生成班级学情反馈',
      viewFeedback: '查看班级反馈',
      generating: '生成中...',
      messagesCount: '有效学习交流',
      noStudents: '班级暂无学生',
      expandStudents: '展开',
      collapseStudents: '收起',
      addStudent: '添加学生',
      studentEmail: '学生邮箱',
      removeStudent: '移除',
      feedbackHelpful: '满意',
      feedbackUnhelpful: '不满意',
      feedbackCopy: '复制',
      welcomeGuest: '欢迎使用离散数学助教，请先登录后开始提问。',
      welcomeRolePending: '请先完成身份选择，再开始使用助手。',
      welcomeStudent: '你好，同学！我是你的离散数学助教，可以帮你解答问题并查看学习资料。',
      welcomeTeacher: '你好，老师！我是离散数学助教，可以帮助你解答学生问题，并支持班级管理。',
      reportTitle: '学情报告',
      feedbackTitle: '班级学情反馈',
      newChat: '新对话',
      historyTitle: '历史会话',
      noHistory: '暂无历史会话',
      today: '今天',
      attachImage: '图片',
      deleteChat: '删除',
      deleteChatConfirm: '确定删除这条对话吗？',
      homeworkTitle: '作业',
      publishHomework: '发布作业',
      homeworkName: '作业标题',
      homeworkDesc: '作业说明（可选）',
      homeworkDue: '截止日期',
      homeworkAttach: '附件（可选）',
      noHomework: '暂无作业',
      submitHomework: '提交作业',
      resubmitHomework: '重新提交',
      submissionNote: '文字说明（可选）',
      uploadSubmission: '上传文件',
      viewSubmissions: '查看提交',
      hideSubmissions: '收起',
      submitted: '已提交',
      notSubmitted: '未提交',
      deleteHomework: '删除',
      deleteHomeworkConfirm: '确定删除这份作业吗？',
      downloadAttachment: '下载附件',
      submissionCount: '份提交',
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
const EXAMPLE_PROMPT_GROUPS = {
  zh: {
    student: [
      [
        '为什么蕴含命题只有在前件为真、后件为假时才是假命题？请结合具体例子说明。',
        '如何用反证法证明：若 n² 是偶数，则 n 是偶数？',
        '给定一个二元关系后，怎样依次判断它是否具有自反性、对称性和传递性？',
      ],
      [
        '如何用真值表判断 `(p→q)↔(¬q→¬p)` 是否为重言式？',
        '数学归纳法中的基础步骤和归纳步骤分别起什么作用？缺少其中一步会怎样？',
        '等价关系如何将一个集合划分为等价类？请用模 3 同余关系说明。',
      ],
      [
        '判断一个函数是单射、满射还是双射时，分别需要检查哪些条件？请配合例子说明。',
        '一个连通图在什么条件下存在欧拉通路或欧拉回路？应该如何快速判断？',
        '什么时候应该使用加法原理、乘法原理、排列或组合？请结合具体情形对比说明。',
      ],
    ],
    teacher: [
      ['设计一节“命题逻辑”课的教学流程', '生成一道图论练习题并给出评分要点', '总结学生学习数学归纳法时的常见误区'],
      ['设计集合与关系章节的课堂活动', '生成一道真值表练习并给出参考答案', '设计一组由基础到进阶的组合计数题'],
      ['给出讲解“等价关系”的课堂案例', '设计图论章节的课堂讨论问题', '制定离散数学阶段测验的知识点分布'],
    ],
  },
  en: {
    student: [
      [
        'Why is an implication false only when its premise is true and its conclusion is false? Explain with a concrete example.',
        'How can contradiction prove that if n² is even, then n is even?',
        'For a binary relation, how can reflexivity, symmetry, and transitivity be checked step by step?',
      ],
      [
        'How can a truth table show whether `(p→q)↔(¬q→¬p)` is a tautology?',
        'What roles do the base case and inductive step play in induction, and what fails if either is missing?',
        'How does an equivalence relation partition a set into equivalence classes? Use congruence modulo 3 as an example.',
      ],
      [
        'What conditions distinguish injective, surjective, and bijective functions? Explain with examples.',
        'When does a connected graph have an Euler path or Euler circuit, and how can this be checked quickly?',
        'When should the addition rule, multiplication rule, permutations, or combinations be used? Compare concrete cases.',
      ],
    ],
    teacher: [
      ['Design a lesson flow for propositional logic', 'Create a graph theory exercise with a scoring rubric', 'Summarize common misconceptions about mathematical induction'],
      ['Design a classroom activity for sets and relations', 'Create a truth-table exercise with a reference answer', 'Design a progression of counting problems from basic to advanced'],
      ['Give a classroom example for teaching equivalence relations', 'Design discussion questions for a graph theory lesson', 'Plan the topic distribution for a discrete mathematics assessment'],
    ],
  },
}
const CODE_COOLDOWN_SEC = 60
const CODE_COOLDOWN_KEY = 'verify_code_cooldown'
const TONGJI_EMAIL_RE = /^[0-9]{7}@tongji\.edu\.cn$/

function getRemainingCooldown(email) {
  try {
    const raw = sessionStorage.getItem(CODE_COOLDOWN_KEY)
    if (!raw) return 0
    const { email: savedEmail, expiresAt } = JSON.parse(raw)
    if (savedEmail !== email.trim().toLowerCase()) return 0
    return Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))
  } catch {
    return 0
  }
}

function saveCooldown(email) {
  sessionStorage.setItem(CODE_COOLDOWN_KEY, JSON.stringify({
    email: email.trim().toLowerCase(),
    expiresAt: Date.now() + CODE_COOLDOWN_SEC * 1000,
  }))
}

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

function formatConvDate(iso, todayLabel) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return todayLabel
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function getMaterialCategory(material) {
  const filename = (material.filename || '').toLowerCase()
  const extType = (material.file_type || '').toLowerCase()
  if (filename.includes('practice') || filename.includes('exercise') || filename.includes('homework') || filename.includes('quiz')) {
    return 'Practice'
  }
  if (filename.includes('book') || filename.includes('textbook')) {
    return 'Books'
  }
  if (extType === 'pptx' || filename.endsWith('.pptx') || filename.endsWith('.ppsx')) {
    return 'Slides'
  }
  return 'Notes'
}

function AuthImage({ path, previewUrl }) {
  const [src, setSrc] = useState(previewUrl || null)

  useEffect(() => {
    if (previewUrl) {
      setSrc(previewUrl)
      return
    }
    if (!path) return undefined

    let cancelled = false
    let objectUrl = null
    const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
    const url = path.startsWith('http') ? path : `${API_BASE}${path}`
    const token = getToken()

    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(res => {
        if (!res.ok) throw new Error('load failed')
        return res.blob()
      })
      .then(blob => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setSrc(null)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [path, previewUrl])

  if (!src) return null
  return <img src={src} className="message-image" alt="" />
}

function App() {
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
  const [activeSection, setActiveSection] = useState('chat')
  const [exampleGroupIndex, setExampleGroupIndex] = useState(0)
  
  const [dialRotation, setDialRotation] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef({ startX: 0, startRot: 0 })
  const messagesEndRef = useRef(null)
  const composerInputRef = useRef(null)

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
    setActiveSection(target)
    setSidebarOpen(false)
    setSettingsOpen(false)
    setLearningAssistantOpen(false)
  }, [])

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
  }

  const handleSignup = async (e) => {
    e.preventDefault()
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
  }

  const handleLogin = async (e) => {
    e.preventDefault()
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
  }

  const handleSelectRole = async (role) => {
    try {
      const data = await selectRole(role)
      const nextUser = { ...user, role: data.role, needs_role_selection: false }
      setAuth(data.access_token, nextUser)
      setUser(nextUser)
      setExampleGroupIndex(0)
      setRoleModalOpen(false)
    } catch (err) {
      setAuthError(err.message)
    }
  }

  const handleLogout = () => {
    clearAuth()
    setActiveSection('chat')
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
  }

  const handleViewStudentReport = async (studentId) => {
    if (!activeClassId) return
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
  }

  const handleGenerateMyReport = async () => {
    if (!activeClassId || generatingLearning) return
    setGeneratingLearning(true)
    try {
      const report = await generateMyReport(activeClassId)
      setReportModal(report)
    } catch (err) {
      alert(err.message)
    } finally {
      setGeneratingLearning(false)
    }
  }

  const handleGenerateClassFeedback = async () => {
    if (!activeClassId || generatingLearning) return
    setGeneratingLearning(true)
    try {
      const feedback = await generateClassFeedback(activeClassId)
      setFeedbackModal(feedback)
    } catch (err) {
      alert(err.message)
    } finally {
      setGeneratingLearning(false)
    }
  }

  const handleLearningAssistantToggle = () => {
    const nextOpen = !learningAssistantOpen
    setLearningAssistantOpen(nextOpen)
    if (nextOpen && activeClassId) loadLearningAssistantStatus(activeClassId)
  }

  const handleAssistantGenerate = async () => {
    if (!activeClassId || generatingLearning) return
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
  }

  const handleAddStudent = async () => {
    if (!activeClassId || !studentEmailInput.trim() || studentBusy) return
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
  }

  const handleRemoveStudent = async (studentId) => {
    if (!activeClassId || studentBusy) return
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
  }

  const handleCreateClass = async () => {
    if (!classForm.name.trim()) return
    try {
      await createClass(classForm.name.trim())
      setClassForm(prev => ({ ...prev, name: '' }))
      loadClasses()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleJoinClass = async () => {
    if (!classForm.inviteCode.trim()) return
    try {
      await joinClass(classForm.inviteCode.trim())
      setClassForm(prev => ({ ...prev, inviteCode: '' }))
      loadClasses()
      alert(t.auth.joinSuccess)
    } catch (err) {
      alert(err.message)
    }
  }

  const handleUploadMaterial = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !activeClassId) return
    try {
      await uploadClassMaterial(activeClassId, file)
      loadMaterials(activeClassId)
    } catch (err) {
      alert(err.message)
    } finally {
      e.target.value = ''
    }
  }

  const openMaterialFile = async (material, download = false) => {
    if (!activeClassId) return
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
  }

  const handleDeleteHomework = async (homeworkId) => {
    if (!window.confirm(t.auth.deleteHomeworkConfirm)) return
    try {
      await deleteHomework(homeworkId)
      setHomeworks(prev => prev.filter(h => h.id !== homeworkId))
      if (expandedHomeworkId === homeworkId) setExpandedHomeworkId(null)
    } catch (err) {
      alert(err.message)
    }
  }

  const handleSubmitHomework = async (homeworkId) => {
    if (homeworkBusy) return
    const draft = submitDrafts[homeworkId] || {}
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
  }

  const handleToggleSubmissions = async (homeworkId) => {
    if (expandedHomeworkId === homeworkId) {
      setExpandedHomeworkId(null)
      return
    }
    try {
      const rows = await fetchHomeworkSubmissions(homeworkId)
      setHomeworkSubmissions(prev => ({ ...prev, [homeworkId]: rows }))
      setExpandedHomeworkId(homeworkId)
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDownloadAttachment = async (hw) => {
    try {
      const blob = await downloadHomeworkAttachment(hw.id)
      downloadBlobFile(blob, hw.attachment_name || 'attachment')
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDownloadSubmission = async (sub) => {
    try {
      const blob = await downloadSubmissionFile(sub.id)
      downloadBlobFile(blob, sub.filename || 'submission')
    } catch (err) {
      alert(err.message)
    }
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
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend(e)
    }
  }

  return (
    <div className="app-container">
      {user && activeSection === 'chat' && (
        <>
          {sidebarOpen && (
            <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
          )}
          <button
            type="button"
            className={`sidebar-tab ${sidebarOpen ? 'open' : ''}`}
            onClick={() => setSidebarOpen(o => !o)}
            aria-label={t.auth.historyTitle}
            aria-expanded={sidebarOpen}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="sidebar-tab-arrow" aria-hidden="true">
              <path d="M9 6l6 6-6 6" />
            </svg>
            {!sidebarOpen && (
              <span className="sidebar-tab-label">{t.auth.historyTitle}</span>
            )}
          </button>
          <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`} aria-hidden={!sidebarOpen}>
            <div className="sidebar-inner">
              <div className="sidebar-header">
                <h3>{t.auth.historyTitle}</h3>
                <button type="button" className="sidebar-new-btn" onClick={handleNewChat}>
                  + {t.auth.newChat}
                </button>
              </div>
              <div className="sidebar-list">
                {conversations.length === 0 ? (
                  <p className="sidebar-empty">{t.auth.noHistory}</p>
                ) : conversations.map(c => (
                  <div
                    key={c.id}
                    className={`sidebar-item ${conversationId === c.id ? 'active' : ''}`}
                    onClick={() => handleSelectConversation(c.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleSelectConversation(c.id)
                      }
                    }}
                  >
                    <div className="sidebar-item-main">
                      <span className="sidebar-item-title">{c.title}</span>
                      <span className="sidebar-item-date">{formatConvDate(c.updated_at, t.auth.today)}</span>
                    </div>
                    <button
                      type="button"
                      className="sidebar-delete-btn"
                      title={t.auth.deleteChat}
                      aria-label={t.auth.deleteChat}
                      onClick={(e) => handleDeleteConversation(e, c.id)}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M4 7h16" />
                        <path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                        <path d="M7 7l1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13" />
                        <path d="M10 11v6M14 11v6" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </>
      )}

      <main className={`page scene-${activeSceneKey}`}>
        {SCENE_OPTIONS.map(opt => (
          <div key={opt.key} className={`scene-layer scene-${opt.key}`} style={{ opacity: sceneOpacities[opt.key] }}>
            <div className="scene-halo" aria-hidden="true" />
            <div className="scene-motion" aria-hidden="true" />
            <div className="scene-motion-secondary" aria-hidden="true" />
            {opt.key === 'night' && <div className="scene-meteor" aria-hidden="true" />}
          </div>
        ))}

        <header className="topbar">
          <div className="topbar-left">
            <div className="brand">
              <img src={logoImg} alt="Logo" className="logo-img" />
              <span className="brand-text">{t.brand}</span>
            </div>
            <nav className="topbar-nav" aria-label="Primary">
              <button type="button" className={`nav-link ${activeSection === 'chat' ? 'active' : ''}`} onClick={() => handleSectionChange('chat')} aria-current={activeSection === 'chat' ? 'page' : undefined}>
                {t.navChat}
              </button>
              {user && (
                <>
                  <button type="button" className={`nav-link ${activeSection === 'resources' ? 'active' : ''}`} onClick={() => handleSectionChange('resources')} aria-current={activeSection === 'resources' ? 'page' : undefined}>
                    {isTeacher ? t.navClasses : t.navResources}
                  </button>
                  <button type="button" className={`nav-link ${activeSection === 'homework' ? 'active' : ''}`} onClick={() => handleSectionChange('homework')} aria-current={activeSection === 'homework' ? 'page' : undefined}>
                    {t.navHomework}
                  </button>
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
                <button type="button" className="ghost-btn" onClick={handleLogout}>{t.auth.logout}</button>
              </>
            ) : (
              <>
                <button type="button" className="ghost-btn" onClick={() => setAuthModal('login')}>{t.login}</button>
                <button type="button" className="solid-btn" onClick={() => setAuthModal('signup')}>{t.signup}</button>
              </>
            )}
          </div>
        </header>

        <section id="section-chat" className="section section-chat" hidden={activeSection !== 'chat'}>
          <div className={`chat-shell ${messages.length > 0 ? 'active-chat' : 'empty-chat'}`}>
            <div className="chat-title">
              <img src={logoImg} alt="Logo" className="logo-img logo-img-lg" />
              <h1>{t.title}</h1>
            </div>
            <div className={`messages-list ${messages.length > 0 ? 'has-messages' : 'welcome-state'}`}>
              {messages.length === 0 && (
                <div className="welcome-card">
                  {welcomeContent ? (
                    <MarkdownMessage content={welcomeContent} />
                  ) : welcomeLoading ? (
                    <div className="thinking-indicator" aria-live="polite">
                      <span />
                      <span />
                      <span />
                      <em>{language === 'zh' ? '正在准备介绍' : 'Preparing intro'}</em>
                    </div>
                  ) : (
                    <p>{welcomeText}</p>
                  )}
                </div>
              )}
              {messages.length === 0 && canChat && visibleExamplePrompts.length > 0 && (
                <section className="example-prompts" aria-label={t.exampleQuestions}>
                  <div className="example-prompts-header">
                    <span>{t.exampleQuestions}</span>
                    <button
                      type="button"
                      className="refresh-examples-btn"
                      onClick={handleRefreshExamples}
                      aria-label={t.refreshExamples}
                    >
                      <span aria-hidden="true">↻</span>
                      {t.refreshExamples}
                    </button>
                  </div>
                  <div className="example-prompts-grid">
                    {visibleExamplePrompts.map(prompt => (
                      <button key={prompt} type="button" className="example-prompt-card" onClick={() => handleExampleSelect(prompt)}>
                        {prompt}
                      </button>
                    ))}
                  </div>
                </section>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`message-item ${msg.role}`}>
                  <div className="message-content">
                    {(msg.imagePreview || msg.imagePath) && (
                      <AuthImage path={msg.imagePath} previewUrl={msg.imagePreview} />
                    )}
                    {msg.content && msg.content !== '[图片]' && msg.content !== '[Image]' && (
                      msg.role === 'assistant' ? (
                        <MarkdownMessage content={msg.content} />
                      ) : (
                        <p className="message-text">{msg.content}</p>
                      )
                    )}
                    {msg.content && (msg.content === '[图片]' || msg.content === '[Image]') && !(msg.imagePreview || msg.imagePath) && (
                      <p className="message-text">{msg.content}</p>
                    )}
                    {msg.role === 'assistant' && !msg.content && (
                      <div className="thinking-indicator" aria-live="polite">
                        <span />
                        <span />
                        <span />
                        <em>{language === 'zh' ? '正在思考' : 'Thinking'}</em>
                      </div>
                    )}
                    {msg.role === 'assistant' && msg.id && msg.content && (
                      <>
                        <div className="message-actions">
                          <button
                            type="button"
                            className="feedback-btn"
                            title={t.auth.feedbackCopy}
                            aria-label={t.auth.feedbackCopy}
                            onClick={() => handleCopyMessage(msg.content)}
                          >
                            <MessageActionIcon type="copy" />
                          </button>
                          <button
                            type="button"
                            className={`feedback-btn ${msg.feedback === 'positive' ? 'active' : ''}`}
                            title={t.auth.feedbackHelpful}
                            aria-label={t.auth.feedbackHelpful}
                            onClick={() => handleFeedback(idx, 'positive')}
                          >
                            <MessageActionIcon type="up" />
                          </button>
                          <button
                            type="button"
                            className={`feedback-btn ${msg.feedback === 'negative' ? 'active' : ''}`}
                            title={t.auth.feedbackUnhelpful}
                            aria-label={t.auth.feedbackUnhelpful}
                            onClick={() => handleFeedback(idx, 'negative')}
                          >
                            <MessageActionIcon type="down" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            {pendingImage && (
              <div className="image-preview-bar">
                <img src={pendingImage.previewUrl} alt="" className="image-preview-thumb" />
                <button type="button" className="image-preview-remove" onClick={() => setPendingImage(null)}>×</button>
              </div>
            )}
            <form className="composer" onSubmit={handleSend}>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                hidden
                onChange={handlePickImage}
              />
              <textarea
                ref={composerInputRef}
                value={input} 
                onChange={(e) => setInput(e.target.value)} 
                onKeyDown={handleKeyDown}
                placeholder={chatPlaceholder} 
                disabled={!canChat || isSending}
                rows={1} 
              />
              <button
                type="button"
                className="attach-image-btn"
                title={t.auth.attachImage}
                disabled={!canChat || isSending}
                onClick={() => imageInputRef.current?.click()}
                aria-label={t.auth.attachImage}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21.44 11.05l-8.49 8.49a5.25 5.25 0 0 1-7.42-7.42l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95l-9.2 9.19a1.75 1.75 0 0 1-2.47-2.47l8.49-8.48" />
                </svg>
              </button>
              <button type="submit" disabled={!canChat || (!input.trim() && !pendingImage) || isSending}>
                {isSending ? t.sending : t.send}
              </button>
            </form>
          </div>

          <div className="scene-dial-wrap" style={{ opacity: chatOpacity }}>
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

          <footer className="scene-quote-footer" style={{ 
            opacity: messages.length > 0 ? 0 : quoteOpacity, 
            visibility: messages.length > 0 ? 'hidden' : 'visible',
            pointerEvents: 'none'
          }}>
            <blockquote className="scene-quote">
              <p>{activeQuote.text}</p>
              <cite>- {activeQuote.author}</cite>
            </blockquote>
          </footer>

        </section>

        <section id="section-resources" className={`section section-resources ${isTeacher ? 'section-teacher' : 'section-student'}`} hidden={activeSection !== 'resources'}>
          <div className="resources-container">
            <div className="resources-header" id={isTeacher ? 'section-classes' : undefined}>
              <h2>{secondPageTitle}</h2>
              {!isTeacher && user && classes.length > 0 && (
                <div className="filter-bar">
                  {RESOURCE_FILTERS.map(filter => (
                    <button
                      key={filter}
                      type="button"
                      className={`filter-btn ${activeFilter === filter ? 'active' : ''}`}
                      onClick={() => setActiveFilter(filter)}
                    >
                      {t.filters[filter]}
                    </button>
                  ))}
                </div>
              )}
              {!user && <p className="muted">{t.login}</p>}
            </div>

            {isTeacher && user && (
              <div className="class-panel teacher-panel">
                <div className="class-actions">
                  <input
                    value={classForm.name}
                    onChange={e => setClassForm(p => ({ ...p, name: e.target.value }))}
                    placeholder={t.auth.className}
                  />
                  <button type="button" className="action-btn action-btn-primary" onClick={handleCreateClass}>
                    {t.auth.createClass}
                  </button>
                </div>
                {classes.length === 0 ? (
                  <p className="muted">{t.auth.teacherNoClassHint}</p>
                ) : (
                  <>
                    <div className="class-tabs">
                      {classes.map(c => (
                        <button
                          key={c.id}
                          type="button"
                          className={`filter-btn ${activeClassId === c.id ? 'active' : ''}`}
                          onClick={() => {
                            setActiveClassId(c.id)
                            setStudentsOpen(false)
                          }}
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                    {activeClassId && (
                      <p className="invite-code-display">
                        {t.auth.inviteCodeLabel}: <strong>{classes.find(c => c.id === activeClassId)?.invite_code}</strong>
                      </p>
                    )}
                    {activeClassId && (
                      <label className="upload-btn">
                        {t.auth.uploadMaterial}
                        <input type="file" accept=".pdf,.pptx,.ppsx" hidden onChange={handleUploadMaterial} />
                      </label>
                    )}
                    {activeClassId && (
                      <div className="learning-panel">
                        <h3>{t.auth.learningTitle}</h3>
                        <div className="learning-actions">
                          <button
                            type="button"
                            className="solid-btn"
                            disabled={generatingLearning}
                            onClick={handleGenerateClassFeedback}
                          >
                            {generatingLearning ? t.auth.generating : t.auth.generateClassFeedback}
                          </button>
                        </div>
                        <button
                          type="button"
                          className={`students-fold-toggle ${studentsOpen ? 'open' : ''}`}
                          onClick={() => setStudentsOpen(o => !o)}
                          aria-expanded={studentsOpen}
                        >
                          <span className="students-fold-label">
                            {t.auth.classStudents}
                            <span className="students-fold-count">{students.length}</span>
                          </span>
                          <span className="students-fold-meta">
                            {studentsOpen ? t.auth.collapseStudents : t.auth.expandStudents}
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M6 9l6 6 6-6" />
                            </svg>
                          </span>
                        </button>
                        {studentsOpen && (
                          <div className="student-list students-fold-body">
                            <div className="student-manage-row">
                              <input
                                value={studentEmailInput}
                                onChange={(e) => setStudentEmailInput(e.target.value)}
                                placeholder={t.auth.studentEmail}
                              />
                              <button type="button" className="action-btn action-btn-primary" disabled={studentBusy} onClick={handleAddStudent}>
                                {t.auth.addStudent}
                              </button>
                            </div>
                            {students.length === 0 ? (
                              <p className="muted">{t.auth.noStudents}</p>
                            ) : students.map(s => (
                              <div key={s.id} className="student-row">
                                <div>
                                  <strong>{s.name}</strong>
                                  <span className="muted-inline">{t.auth.messagesCount}: {s.effective_question_count ?? s.message_count}</span>
                                </div>
                                <div className="card-actions">
                                  <button type="button" className="download-btn" onClick={() => handleViewStudentReport(s.id)}>
                                    {t.auth.viewReport}
                                  </button>
                                  <button
                                    type="button"
                                    className="download-btn"
                                    disabled={generatingLearning}
                                    onClick={() => handleGenerateStudentReport(s.id)}
                                  >
                                    {t.auth.generateReport}
                                  </button>
                                  <button type="button" className="download-btn danger" disabled={studentBusy} onClick={() => handleRemoveStudent(s.id)}>
                                    {t.auth.removeStudent}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {isStudent && user && (
              <div className="class-panel student-panel">
                {classes.length === 0 ? (
                  <>
                    <p className="muted">{t.auth.studentNoClassHint}</p>
                    <div className="class-actions">
                      <input
                        value={classForm.inviteCode}
                        onChange={e => setClassForm(p => ({ ...p, inviteCode: e.target.value }))}
                        placeholder={t.auth.inviteCode}
                      />
                      <button type="button" className="action-btn action-btn-primary" onClick={handleJoinClass}>
                        {t.auth.joinClass}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="muted">{t.auth.selectClassHint}</p>
                    <div className="class-tabs">
                      {classes.map(c => (
                        <button
                          key={c.id}
                          type="button"
                          className={`filter-btn ${activeClassId === c.id ? 'active' : ''}`}
                          onClick={() => setActiveClassId(c.id)}
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                    <div className="class-actions join-more">
                      <input
                        value={classForm.inviteCode}
                        onChange={e => setClassForm(p => ({ ...p, inviteCode: e.target.value }))}
                        placeholder={t.auth.inviteCode}
                      />
                      <button type="button" className="action-btn action-btn-soft" onClick={handleJoinClass}>
                        {t.auth.joinClass}
                      </button>
                    </div>
                    {activeClassId && (
                      <div className="learning-panel">
                        <button
                          type="button"
                          className="solid-btn"
                          disabled={generatingLearning}
                          onClick={handleGenerateMyReport}
                        >
                          {generatingLearning ? t.auth.generating : t.auth.generateMyReport}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {(isStudent || isTeacher) && user && classes.length > 0 && (
              <>
                {isTeacher && (
                  <div className="resource-library-header">
                    <h3>{t.resourcesTitle}</h3>
                    <div className="filter-bar">
                      {RESOURCE_FILTERS.map(filter => (
                        <button
                          key={filter}
                          type="button"
                          className={`filter-btn ${activeFilter === filter ? 'active' : ''}`}
                          onClick={() => setActiveFilter(filter)}
                        >
                          {t.filters[filter]}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              <div className="resources-grid">
                {visibleMaterials.length === 0 ? (
                  <div className="resource-card muted-card">
                    <p className="muted">{materials.length === 0 ? t.auth.noClasses : (language === 'zh' ? '该分类下暂无资料' : 'No resources in this category')}</p>
                  </div>
                ) : visibleMaterials.map(m => (
                  <div key={m.id} className="resource-card">
                    <div className="card-type">{t.filters[getMaterialCategory(m)]}</div>
                    <h3>{m.filename}</h3>
                    <p>{(m.file_size / 1024 / 1024).toFixed(2)} MB</p>
                    <div className="card-footer">
                      <span>{m.uploaded_at?.slice(0, 10)}</span>
                      <div className="card-actions">
                        <button type="button" className="download-btn" onClick={() => openMaterialFile(m, false)}>
                          {t.view}
                        </button>
                        <button type="button" className="download-btn" onClick={() => openMaterialFile(m, true)}>
                          {t.download}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              </>
            )}
          </div>
        </section>

        {user && (isTeacher || isStudent) && (
          <section id="section-homework" className="section section-homework" hidden={activeSection !== 'homework'}>
            <div className="resources-container">
              <div className="resources-header">
                <h2>{t.homeworkPageTitle}</h2>
              </div>

              <div className="homework-panel">
                {isTeacher && activeClassId && (
                  <div className="homework-publish">
                    <input
                      value={homeworkForm.title}
                      onChange={e => setHomeworkForm(p => ({ ...p, title: e.target.value }))}
                      placeholder={t.auth.homeworkName}
                    />
                    <textarea
                      value={homeworkForm.description}
                      onChange={e => setHomeworkForm(p => ({ ...p, description: e.target.value }))}
                      placeholder={t.auth.homeworkDesc}
                      rows={3}
                    />
                    <div className="homework-publish-row">
                      <input
                        type="datetime-local"
                        value={homeworkForm.dueAt}
                        onChange={e => setHomeworkForm(p => ({ ...p, dueAt: e.target.value }))}
                        aria-label={t.auth.homeworkDue}
                      />
                      <label className="upload-btn soft">
                        {homeworkFile ? homeworkFile.name : t.auth.homeworkAttach}
                        <input
                          type="file"
                          accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                          hidden
                          onChange={e => setHomeworkFile(e.target.files?.[0] || null)}
                        />
                      </label>
                      <button
                        type="button"
                        className="action-btn action-btn-primary"
                        disabled={homeworkBusy || !homeworkForm.title.trim()}
                        onClick={handlePublishHomework}
                      >
                        {t.auth.publishHomework}
                      </button>
                    </div>
                  </div>
                )}

                {!activeClassId ? (
                  <p className="muted">{t.auth.noClasses}</p>
                ) : homeworks.length === 0 ? (
                  <p className="muted">{t.auth.noHomework}</p>
                ) : (
                  <div className="homework-list">
                    {homeworks.map(hw => {
                      const draft = submitDrafts[hw.id] || {}
                      const subs = homeworkSubmissions[hw.id] || []
                      return (
                        <div key={hw.id} className="homework-card">
                          <div className="homework-card-top">
                            <div>
                              <h4>{hw.title}</h4>
                              {hw.description && <p className="homework-desc">{hw.description}</p>}
                              <div className="homework-meta">
                                {hw.due_at && <span>{t.auth.homeworkDue}: {hw.due_at.slice(0, 16).replace('T', ' ')}</span>}
                                {isTeacher && <span>{hw.submission_count} {t.auth.submissionCount}</span>}
                                {isStudent && (
                                  <span className={hw.my_submission ? 'status-done' : 'status-pending'}>
                                    {hw.my_submission ? t.auth.submitted : t.auth.notSubmitted}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="homework-card-actions">
                              {hw.has_attachment && (
                                <button type="button" className="download-btn" onClick={() => handleDownloadAttachment(hw)}>
                                  {t.auth.downloadAttachment}
                                </button>
                              )}
                              {isTeacher && (
                                <>
                                  <button type="button" className="download-btn" onClick={() => handleToggleSubmissions(hw.id)}>
                                    {expandedHomeworkId === hw.id ? t.auth.hideSubmissions : t.auth.viewSubmissions}
                                  </button>
                                  <button type="button" className="download-btn danger" onClick={() => handleDeleteHomework(hw.id)}>
                                    {t.auth.deleteHomework}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>

                          {isStudent && (
                            <div className="homework-submit">
                              <textarea
                                value={draft.content || ''}
                                onChange={e => setSubmitDrafts(prev => ({
                                  ...prev,
                                  [hw.id]: { ...draft, content: e.target.value },
                                }))}
                                placeholder={t.auth.submissionNote}
                                rows={2}
                              />
                              <div className="homework-publish-row">
                                <label className="upload-btn soft">
                                  {draft.file ? draft.file.name : t.auth.uploadSubmission}
                                  <input
                                    type="file"
                                    accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                                    hidden
                                    onChange={e => setSubmitDrafts(prev => ({
                                      ...prev,
                                      [hw.id]: { ...draft, file: e.target.files?.[0] || null },
                                    }))}
                                  />
                                </label>
                                <button
                                  type="button"
                                  className="action-btn action-btn-primary"
                                  disabled={homeworkBusy}
                                  onClick={() => handleSubmitHomework(hw.id)}
                                >
                                  {hw.my_submission ? t.auth.resubmitHomework : t.auth.submitHomework}
                                </button>
                              </div>
                              {hw.my_submission?.filename && (
                                <p className="muted-inline">{hw.my_submission.filename}</p>
                              )}
                            </div>
                          )}

                          {isTeacher && expandedHomeworkId === hw.id && (
                            <div className="submission-list">
                              {subs.length === 0 ? (
                                <p className="muted">{t.auth.noHomework}</p>
                              ) : subs.map(sub => (
                                <div key={sub.id} className="submission-row">
                                  <div>
                                    <strong>{sub.student_name}</strong>
                                    {sub.content && <p className="homework-desc">{sub.content}</p>}
                                    <span className="muted-inline">{sub.submitted_at?.slice(0, 16).replace('T', ' ')}</span>
                                  </div>
                                  {sub.has_file && (
                                    <button type="button" className="download-btn" onClick={() => handleDownloadSubmission(sub)}>
                                      {sub.filename || t.download}
                                    </button>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      {user && activeSection === 'chat' && (
        <LearningMascot
          role={user.role}
          activeClass={activeClass}
          open={learningAssistantOpen}
          loading={learningAssistantLoading}
          status={learningAssistantStatus}
          generating={generatingLearning}
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

      {/* Report / Feedback Modals */}
      {reportModal && (
        <div className="auth-overlay" onClick={() => setReportModal(null)}>
          <div className="report-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setReportModal(null)}>&times;</button>
            <h2>{t.auth.reportTitle}{reportModal.student_name ? ` - ${reportModal.student_name}` : ''}</h2>
            <div className="report-content">{reportModal.summary}</div>
          </div>
        </div>
      )}

      {feedbackModal && (
        <div className="auth-overlay" onClick={() => setFeedbackModal(null)}>
          <div className="report-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setFeedbackModal(null)}>&times;</button>
            <h2>{t.auth.feedbackTitle}</h2>
            <div className="report-content">{feedbackModal.summary}</div>
          </div>
        </div>
      )}

      {/* Auth Modals */}
      {authModal && (
        <div className="auth-overlay" onClick={() => setAuthModal(null)}>
          <div className="auth-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setAuthModal(null)}>&times;</button>
            <div className="auth-header">
              <img src={logoImg} alt="Logo" className="logo-img" />
              <h2>{authModal === 'login' ? t.auth.loginTitle : t.auth.signupTitle}</h2>
            </div>
            
            <form className="auth-form" onSubmit={authModal === 'login' ? handleLogin : handleSignup}>
              <div className="form-group">
                <label>{t.auth.email}</label>
                <input
                  type="email"
                  placeholder="2131445@tongji.edu.cn"
                  value={authForm.email}
                  onChange={e => setAuthForm(p => ({ ...p, email: e.target.value }))}
                />
                <small>{t.auth.emailHint}</small>
              </div>
              {authModal === 'signup' && (
                <>
                  <div className="form-group code-row">
                    <label>{t.auth.code}</label>
                    <div className="code-input-wrap">
                      <input
                        type="text"
                        value={authForm.code}
                        onChange={e => setAuthForm(p => ({ ...p, code: e.target.value }))}
                      />
                      <button
                        type="button"
                        disabled={codeCooldown > 0 || sendingCode}
                        onClick={handleSendCode}
                      >
                        {sendingCode
                          ? '...'
                          : codeCooldown > 0
                            ? `${codeCooldown}s`
                            : t.auth.sendCode}
                      </button>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>{t.auth.name}</label>
                    <input
                      type="text"
                      value={authForm.name}
                      onChange={e => setAuthForm(p => ({ ...p, name: e.target.value }))}
                    />
                  </div>
                </>
              )}
              <div className="form-group">
                <label>{t.auth.password}</label>
                <input
                  type="password"
                  value={authForm.password}
                  onChange={e => setAuthForm(p => ({ ...p, password: e.target.value }))}
                />
              </div>
              {authModal === 'signup' && (
                <div className="form-group">
                  <label>{t.auth.confirmPassword}</label>
                  <input
                    type="password"
                    value={authForm.confirmPassword}
                    onChange={e => setAuthForm(p => ({ ...p, confirmPassword: e.target.value }))}
                  />
                </div>
              )}
              {authError && <p className="auth-error">{authError}</p>}
              <button type="submit" className="auth-submit" disabled={authLoading} aria-busy={authLoading}>
                {authLoading
                  ? authModal === 'login' ? t.auth.loggingIn : t.auth.signingUp
                  : authModal === 'login' ? t.auth.loginBtn : t.auth.signupBtn}
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

      {roleModalOpen && (
        <div className="auth-overlay">
          <div className="auth-modal" onClick={e => e.stopPropagation()}>
            <div className="auth-header">
              <img src={logoImg} alt="Logo" className="logo-img" />
              <h2>{t.auth.roleTitle}</h2>
            </div>
            <div className="role-actions">
              <button type="button" className="solid-btn" onClick={() => handleSelectRole('student')}>{t.auth.student}</button>
              <button type="button" className="ghost-btn" onClick={() => handleSelectRole('teacher')}>{t.auth.teacher}</button>
            </div>
            {authError && <p className="auth-error">{authError}</p>}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
