import { Children, isValidElement, memo, useEffect, useId, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import 'katex/dist/katex.min.css'
import { repairMermaidDiagram } from '../api/chat'

const MERMAID_SCENE_THEMES = {
  day: {
    primaryColor: '#2e6f9e',
    primaryTextColor: '#f7fbfe',
    primaryBorderColor: '#245a80',
    lineColor: '#526d82',
    secondaryColor: '#dcecf6',
    secondaryTextColor: '#17324b',
    tertiaryColor: '#f3f9fc',
    tertiaryTextColor: '#17324b',
    edgeLabelBackground: '#f3f9fc',
  },
  sunset: {
    primaryColor: '#a2594b',
    primaryTextColor: '#fff8f4',
    primaryBorderColor: '#81453b',
    lineColor: '#6d5559',
    secondaryColor: '#ead6d3',
    secondaryTextColor: '#30282a',
    tertiaryColor: '#f3e8e2',
    tertiaryTextColor: '#30282a',
    edgeLabelBackground: '#f3e8e2',
  },
  night: {
    primaryColor: '#91a9ff',
    primaryTextColor: '#0b1020',
    primaryBorderColor: '#b7c5ff',
    lineColor: '#a8b4cc',
    secondaryColor: '#26304c',
    secondaryTextColor: '#f2f5fa',
    tertiaryColor: '#151d34',
    tertiaryTextColor: '#f2f5fa',
    edgeLabelBackground: '#151d34',
  },
}

let mermaidRenderQueue = Promise.resolve()
let mermaidModulePromise
const mermaidRenderCache = new Map()
const MERMAID_CACHE_LIMIT = 30

function loadMermaid() {
  if (!mermaidModulePromise) {
    mermaidModulePromise = import('mermaid').then(module => module.default)
  }
  return mermaidModulePromise
}

function renderMermaidDiagram(diagramId, chart, scene) {
  const cacheKey = `${scene}\u0000${chart}`
  const cachedRender = mermaidRenderCache.get(cacheKey)
  if (cachedRender) return cachedRender

  const themeVariables = MERMAID_SCENE_THEMES[scene] || MERMAID_SCENE_THEMES.night
  const renderTask = mermaidRenderQueue.then(async () => {
    const mermaid = await loadMermaid()
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      fontFamily: 'Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif',
      themeVariables: {
        background: 'transparent',
        mainBkg: themeVariables.primaryColor,
        nodeBorder: themeVariables.primaryBorderColor,
        clusterBkg: themeVariables.tertiaryColor,
        clusterBorder: themeVariables.primaryBorderColor,
        ...themeVariables,
      },
    })
    return mermaid.render(diagramId, chart)
  })

  mermaidRenderCache.set(cacheKey, renderTask)
  if (mermaidRenderCache.size > MERMAID_CACHE_LIMIT) {
    mermaidRenderCache.delete(mermaidRenderCache.keys().next().value)
  }
  renderTask.catch(() => mermaidRenderCache.delete(cacheKey))
  mermaidRenderQueue = renderTask.catch(() => undefined)
  return renderTask
}

function MermaidDiagram({
  chart,
  scene,
  conversationId,
  messageId,
  labels = {},
}) {
  const reactId = useId()
  const diagramId = useMemo(
    () => `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, '')}-${scene}`,
    [reactId, scene],
  )
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')
  const [activeChart, setActiveChart] = useState(chart)
  const [copyState, setCopyState] = useState('')
  const [repairing, setRepairing] = useState(false)
  const [repairFeedback, setRepairFeedback] = useState('')

  useEffect(() => {
    setActiveChart(chart)
  }, [chart])

  useEffect(() => {
    let cancelled = false

    async function renderDiagram() {
      try {
        const result = await renderMermaidDiagram(diagramId, activeChart, scene)
        if (!cancelled) {
          setSvg(result.svg)
          setError('')
        }
      } catch (err) {
        if (!cancelled) {
          setSvg('')
          setError(err instanceof Error ? err.message : 'Mermaid render failed')
        }
      }
    }

    renderDiagram()

    return () => {
      cancelled = true
    }
  }, [activeChart, diagramId, scene])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(activeChart)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
  }

  const handleRepair = async () => {
    if (!conversationId || !messageId || repairing) return
    setRepairing(true)
    setRepairFeedback('')
    try {
      const result = await repairMermaidDiagram({
        conversation_id: conversationId,
        message_id: messageId,
        source: chart,
        parse_error: error,
      })
      setActiveChart(result.source)
    } catch (err) {
      setRepairFeedback(err.message || labels.mermaidRepairFailed || '图表重新生成失败')
    } finally {
      setRepairing(false)
    }
  }

  if (error) {
    return (
      <div className="mermaid-surface mermaid-fallback">
        <div className="mermaid-error">
          {labels.mermaidRenderFailed || 'Mermaid 图表渲染失败，已显示源码。'}
        </div>
        <pre><code>{activeChart}</code></pre>
        <div className="mermaid-actions">
          <button type="button" onClick={handleCopy}>
            {copyState === 'copied'
              ? labels.mermaidCopied || '已复制'
              : copyState === 'failed'
                ? labels.mermaidCopyFailed || '复制失败'
                : labels.mermaidCopySource || '复制源码'}
          </button>
          <button
            type="button"
            onClick={handleRepair}
            disabled={repairing || !conversationId || !messageId}
            title={!messageId ? labels.mermaidRepairPending || '回答保存后可重新生成' : undefined}
          >
            {repairing
              ? labels.mermaidRegenerating || '正在重新生成…'
              : labels.mermaidRegenerate || '重新生成图表'}
          </button>
        </div>
        {repairFeedback && <div className="mermaid-repair-feedback">{repairFeedback}</div>}
      </div>
    )
  }

  return (
    <div
      className="mermaid-surface mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

function MarkdownCode({
  inline,
  className,
  children,
  scene,
  conversationId,
  messageId,
  labels,
  ...props
}) {
  const languageMatch = /language-(\w+)/.exec(className || '')
  const language = languageMatch?.[1]
  const code = String(children).replace(/\n$/, '')

  if (!inline && language === 'mermaid') {
    return (
      <MermaidDiagram
        chart={code}
        scene={scene}
        conversationId={conversationId}
        messageId={messageId}
        labels={labels}
      />
    )
  }

  return (
    <code className={className} {...props}>
      {children}
    </code>
  )
}

function MarkdownPre({ children, ...props }) {
  const child = Children.toArray(children)[0]
  const className = isValidElement(child) ? child.props.className || '' : ''

  if (/\blanguage-mermaid\b/.test(className)) {
    return <>{children}</>
  }

  return <pre {...props}>{children}</pre>
}

function normalizeMathContent(content) {
  if (!content) return ''

  // 先保护 fenced code（含 mermaid），避免被公式预处理破坏
  const fences = []
  let text = content.replace(/```[\s\S]*?```/g, (block) => {
    const key = `@@FENCE_${fences.length}@@`
    fences.push(block)
    return key
  })

  text = text
    // \( ... \) → $...$
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, expr) => `$${expr.trim()}$`)
    // \[ ... \] → $$...$$
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, expr) => `\n$$\n${expr.trim()}\n$$\n`)

  // 修复矩阵行分隔：\begin{...}...\end{...} 内的 "\ " → \\
  text = text.replace(
    /(\\begin\{(?:bmatrix|pmatrix|vmatrix|Bmatrix|matrix|array)\}[\s\S]*?\\end\{(?:bmatrix|pmatrix|vmatrix|Bmatrix|matrix|array)\})/g,
    (block) => block
      .replace(/\\\s+(?=\d|\\|[a-zA-Z])/g, '\\\\ ')
      .replace(/\\\n/g, '\\\\\n'),
  )

  // [ ...含 LaTeX 命令... ] → $$...$$（模型常误用方括号）
  text = text.replace(
    /\[\s*([^[\]]*(?:\\begin\{|\\boxed\{|\\frac\{|\\cdot|\\times|\\to|\\rightarrow)[^[\]]*?)\]/g,
    (_, expr) => {
      const trimmed = expr.trim()
      if (!trimmed || trimmed.length > 2000) return `[${expr}]`
      return `\n$$\n${trimmed}\n$$\n`
    },
  )

  // 还原 code fence
  fences.forEach((block, i) => {
    text = text.replace(`@@FENCE_${i}@@`, block)
  })

  return text
}

function MarkdownMessage({
  content,
  scene = 'night',
  conversationId = null,
  messageId = null,
  labels = {},
}) {
  const normalized = useMemo(() => normalizeMathContent(content), [content])
  const markdownComponents = useMemo(
    () => ({
      code: function SceneMarkdownCode(props) {
        return (
          <MarkdownCode
            {...props}
            scene={scene}
            conversationId={conversationId}
            messageId={messageId}
            labels={labels}
          />
        )
      },
      pre: MarkdownPre,
    }),
    [conversationId, labels, messageId, scene],
  )

  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={markdownComponents}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  )
}

export default memo(MarkdownMessage)
