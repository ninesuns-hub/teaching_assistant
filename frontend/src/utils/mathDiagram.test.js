import test from 'node:test'
import assert from 'node:assert/strict'
import { edgeGeometry, layoutMathDiagram, validateMathDiagram } from './mathDiagram.js'

const graph = { version:1, kind:'graph', directed:true, nodes:['a','b','c','d'].map(id=>({id,label:id})), edges:[['a','a'],['a','b'],['a','b'],['b','a'],['d','c'],['c','d']].map(([from,to])=>({from,to})) }
test('loops, parallel and opposite arrows receive distinct, finite geometry', () => {
  const { positions } = layoutMathDiagram(graph)
  const edges = graph.edges.map((edge,index)=>edgeGeometry(edge,index,graph,positions))
  assert.equal(new Set(edges.map(edge=>edge.path)).size, edges.length)
  assert.ok(edges.every(edge=>!edge.path.includes('NaN')))
  assert.ok(edges[0].path.includes(' C '))
})
test('Hasse order increases upward and tree order downward', () => {
  for (const kind of ['hasse','tree']) {
    const data={version:1,kind,nodes:graph.nodes.slice(0,3),edges:[{from:'a',to:'b'},{from:'a',to:'c'}]}
    const {positions}=layoutMathDiagram(data)
    assert.equal(positions.a.y < positions.b.y, kind==='tree')
  }
})
test('rejects missing endpoints, duplicate IDs and cyclic layers', () => {
  assert.throws(()=>validateMathDiagram({...graph,edges:[{from:'a',to:'missing'}]}))
  assert.throws(()=>validateMathDiagram({...graph,nodes:[graph.nodes[0],graph.nodes[0]]}))
  assert.throws(()=>validateMathDiagram({...graph,kind:'hasse'}))
})
