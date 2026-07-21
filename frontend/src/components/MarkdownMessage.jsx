import { useEffect, useId, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import mermaid from 'mermaid'
import 'katex/dist/katex.min.css'

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'dark',
  themeVariables: {
    background: 'transparent',
    primaryColor: '#202124',
    primaryTextColor: '#f5f6fa',
    primaryBorderColor: '#b8bbc6',
    lineColor: '#c8cbd4',
    secondaryColor: '#2b2d31',
    tertiaryColor: '#17181b',
  },
})

function MermaidDiagram({ chart }) {
  const reactId = useId()
  const diagramId = useMemo(
    () => `mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, '')}`,
    [reactId],
  )
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function renderDiagram() {
      try {
        const result = await mermaid.render(diagramId, chart)
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
  }, [chart, diagramId])

  if (error) {
    return (
      <div className="mermaid-fallback">
        <div className="mermaid-error">Mermaid 图表渲染失败，已显示源码。</div>
        <pre><code>{chart}</code></pre>
      </div>
    )
  }

  return (
    <div
      className="mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

function MarkdownCode({ inline, className, children, ...props }) {
  const languageMatch = /language-(\w+)/.exec(className || '')
  const language = languageMatch?.[1]
  const code = String(children).replace(/\n$/, '')

  if (!inline && language === 'mermaid') {
    return <MermaidDiagram chart={code} />
  }

  return (
    <code className={className} {...props}>
      {children}
    </code>
  )
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

export default function MarkdownMessage({ content }) {
  const normalized = useMemo(() => normalizeMathContent(content), [content])

  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
        components={{
          code: MarkdownCode,
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  )
}
