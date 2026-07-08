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

export default function MarkdownMessage({ content }) {
  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code: MarkdownCode,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
