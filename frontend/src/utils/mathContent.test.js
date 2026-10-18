import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareMathContent } from './mathContent.js'

test('normalizes complete alternate delimiters and preserves matrix rows', () => {
  const source = String.raw`行内 \(x+1\)，矩阵 \[\begin{bmatrix}1&0\\0&1\end{bmatrix}\]`
  const result = prepareMathContent(source)
  assert.equal(result.incomplete, false)
  assert.ok(result.content.includes('$x+1$'))
  assert.ok(result.content.includes(String.raw`1&0\\0&1`))
})
test('does not transform inline code or fenced diagram JSON', () => {
  const source = '`$x$ \\(x\\)`\n```math-diagram\n{"label":"$x$"}\n```'
  assert.equal(prepareMathContent(source).content, source)
})
test('holds incomplete formulas during streaming without inventing their content', () => {
  assert.equal(prepareMathContent('结论：$\\langle 2,1', true).content, '结论：')
  assert.match(prepareMathContent('结论：$\\langle 2,1').content, /公式未完整生成/)
  assert.equal(prepareMathContent('结论：$\\langle 2,1\\rangle$。').incomplete, false)
})
