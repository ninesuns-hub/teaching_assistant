const ID = /^[A-Za-z0-9_-]{1,32}$/

export function validateMathDiagram(data) {
  if (!data || data.version !== 1 || !['graph', 'tree', 'hasse'].includes(data.kind)) throw new Error('不支持的数学图格式')
  if (!Array.isArray(data.nodes) || data.nodes.length < 1 || data.nodes.length > 30 || !Array.isArray(data.edges) || data.edges.length > 80) throw new Error('数学图规模超出限制')
  const ids = new Set()
  for (const node of data.nodes) {
    if (typeof node.id !== 'string' || !ID.test(node.id) || ids.has(node.id) || typeof node.label !== 'string' || !node.label.length || node.label.length > 32) throw new Error('节点ID或标签无效')
    ids.add(node.id)
  }
  if (data.directed !== undefined && typeof data.directed !== 'boolean') throw new Error('方向设置无效')
  const degree = Object.fromEntries([...ids].map(id => [id, 0]))
  for (const edge of data.edges) {
    if (!ids.has(edge.from) || !ids.has(edge.to) || typeof (edge.label ?? '') !== 'string' || (edge.label || '').length > 48) throw new Error('边端点或标签无效')
    degree[edge.to]++
  }
  if (data.kind !== 'graph') {
    const roots = [...ids].filter(id => degree[id] === 0)
    if (data.kind === 'tree' && (roots.length !== 1 || Object.values(degree).some(n => n > 1))) throw new Error('树结构无效')
    const queue = [...roots]
    let visited = 0
    while (queue.length) {
      const id = queue.shift()
      visited++
      for (const edge of data.edges.filter(e => e.from === id)) if (--degree[edge.to] === 0) queue.push(edge.to)
    }
    if (visited !== ids.size) throw new Error('分层图不能包含环')
  }
  if (data.annotations !== undefined && (!Array.isArray(data.annotations) || data.annotations.length > 12 || data.annotations.some(x => typeof x !== 'string' || x.length > 240))) throw new Error('图外说明无效')
  return data
}

export function layoutMathDiagram(data) {
  validateMathDiagram(data)
  const positions = {}
  if (data.kind === 'graph') {
    const count = data.nodes.length
    const radius = count === 1 ? 0 : Math.max(100, count * 22)
    const size = radius * 2 + 180
    data.nodes.forEach((node, index) => {
      const angle = -Math.PI / 2 + index * 2 * Math.PI / count
      positions[node.id] = { x: size / 2 + radius * Math.cos(angle), y: size / 2 + radius * Math.sin(angle) }
    })
    return { positions, width: Math.max(size, 300), height: Math.max(size, 220) }
  }
  const levels = Object.fromEntries(data.nodes.map(node => [node.id, 0]))
  for (let pass = 0; pass < data.nodes.length; pass++) for (const edge of data.edges) levels[edge.to] = Math.max(levels[edge.to], levels[edge.from] + 1)
  const layers = []
  data.nodes.forEach(node => { (layers[levels[node.id]] ||= []).push(node) })
  const width = Math.max(340, ...layers.map(layer => layer.length * 150 + 80))
  const height = Math.max(240, layers.length * 130 + 60)
  layers.forEach((layer, level) => layer.forEach((node, index) => {
    const y = 65 + level * 130
    positions[node.id] = { x: width * (index + 1) / (layer.length + 1), y: data.kind === 'hasse' ? height - y : y }
  }))
  return { positions, width, height }
}

export function edgeGeometry(edge, index, data, positions) {
  const a = positions[edge.from], b = positions[edge.to]
  if (edge.from === edge.to) {
    const loops = data.edges.slice(0, index).filter(e => e.from === edge.from && e.to === edge.to).length
    const reach = 60 + loops * 26
    return { path: `M ${a.x-16} ${a.y-22} C ${a.x-reach} ${a.y-reach-38}, ${a.x+reach} ${a.y-reach-38}, ${a.x+16} ${a.y-22}`, x: a.x, y: a.y-reach-10 }
  }
  const group = data.edges.map((e, i) => ({ ...e, index: i })).filter(e => (e.from === edge.from && e.to === edge.to) || (e.from === edge.to && e.to === edge.from))
  const ordinal = group.findIndex(e => e.index === index)
  const canonical = edge.from < edge.to ? 1 : -1
  const offset = (ordinal - (group.length - 1) / 2) * 54 * canonical
  const dx = b.x-a.x, dy = b.y-a.y, length = Math.hypot(dx, dy)
  const cx = (a.x+b.x)/2 - dy/length*offset, cy = (a.y+b.y)/2 + dx/length*offset
  const d1 = Math.hypot(cx-a.x, cy-a.y), d2 = Math.hypot(cx-b.x, cy-b.y)
  const sx = a.x+(cx-a.x)*30/d1, sy=a.y+(cy-a.y)*30/d1
  const ex = b.x+(cx-b.x)*34/d2, ey=b.y+(cy-b.y)*34/d2
  return { path: `M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}`, x:(sx+2*cx+ex)/4, y:(sy+2*cy+ey)/4-9 }
}
