import process from 'node:process'
import { JSDOM } from 'jsdom'

let source = ''
process.stdin.setEncoding('utf8')
for await (const chunk of process.stdin) source += chunk

const dom = new JSDOM('<!doctype html><html><body></body></html>')
globalThis.window = dom.window
globalThis.document = dom.window.document
Object.defineProperty(globalThis, 'navigator', {
  value: dom.window.navigator,
  configurable: true,
})
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.SVGElement = dom.window.SVGElement

const mermaid = (await import('mermaid')).default
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
})

try {
  const valid = await mermaid.parse(source.trim(), { suppressErrors: true })
  process.exit(valid ? 0 : 1)
} catch {
  process.exit(1)
}
