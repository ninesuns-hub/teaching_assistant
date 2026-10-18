import { useId, useMemo } from 'react'
import { edgeGeometry, layoutMathDiagram, validateMathDiagram } from '../utils/mathDiagram'

export default function MathDiagram({ source }) {
  const marker = `math-arrow-${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  const result = useMemo(() => {
    try {
      if (source.length > 20000) throw new Error('图形数据过长')
      const data = validateMathDiagram(JSON.parse(source))
      return { data, ...layoutMathDiagram(data) }
    } catch (error) { return { error: error.message } }
  }, [source])
  if (result.error) return <div className="math-diagram-error" role="status">数学图暂时无法显示，请使用回答下方的重试按钮重新生成。<details><summary>查看原因</summary>{result.error}</details></div>
  const { data, positions, width, height } = result
  const directed = data.kind === 'graph' && data.directed
  return (
    <figure className="math-diagram-figure">
      <div className="math-diagram-scroll">
        <svg className="math-diagram-svg" viewBox={`0 0 ${width} ${height}`} style={{ minWidth: Math.min(width, 700) }} role="img" aria-label={data.kind === 'hasse' ? 'Hasse图' : '数学关系示意图'}>
          <defs><marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" /></marker></defs>
          {data.edges.map((edge, index) => {
            const geometry = edgeGeometry(edge, index, data, positions)
            return <g key={index} className="math-diagram-edge"><path d={geometry.path} fill="none" markerEnd={directed ? `url(#${marker})` : undefined} />{edge.label && <text x={geometry.x} y={geometry.y} textAnchor="middle" className="math-diagram-edge-label">{edge.label}</text>}</g>
          })}
          {data.nodes.map(node => <g key={node.id} transform={`translate(${positions[node.id].x} ${positions[node.id].y})`} className="math-diagram-node"><title>{node.label}</title><circle r="28" /><text textAnchor="middle" dominantBaseline="central" fontSize={node.label.length > 5 ? 11 : 17}>{node.label.length > 10 ? node.label.slice(0, 9)+'…' : node.label}</text></g>)}
        </svg>
      </div>
      {data.annotations?.length > 0 && <figcaption><ul>{data.annotations.map((note, index) => <li key={index}>{note}</li>)}</ul></figcaption>}
    </figure>
  )
}
