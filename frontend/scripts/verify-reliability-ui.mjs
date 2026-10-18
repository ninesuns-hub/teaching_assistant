// Optional browser regression check. Use PLAYWRIGHT_MODULE_PATH for a bundled runtime.
import { createRequire } from 'node:module'
import fs from 'node:fs'
import process from 'node:process'

const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const browser = await chromium.launch({ headless: true, channel: 'chrome' })
const errors = []
const conv = '11111111-1111-4111-8111-111111111111'
const now = Math.floor(Date.now() / 1000)
const session = { expires_at: now + 28800, idle_expires_at: now + 1800 }
const profile = { id: 999, name: '界面验证', email: 'ui-test@tongji.edu.cn', role: 'student', needs_role_selection: false, is_admin: false, status: 'active', ...session }
const token = `test.${Buffer.from(JSON.stringify({ sub: profile.email, sid: 'ui-test', exp: session.expires_at })).toString('base64url')}.test`
const diagram = { version: 1, kind: 'graph', directed: true, nodes: ['a', 'b', 'c', 'd'].map(id => ({ id, label: id })), edges: [['a', 'a'], ['a', 'b'], ['a', 'b'], ['a', 'd'], ['c', 'b'], ['d', 'c'], ['c', 'd']].map(([from, to], index) => ({ from, to, label: `e${index + 1}` })), annotations: ['自环和两条平行边分别绘制。', '图中只包含真实存在的边。'] }
const answer = '关系：$R=\\{(1,1),(2,2),(3,3)\\}$。\n\n```math-diagram\n' + JSON.stringify(diagram) + '\n```\n\n```mermaid\nflowchart LR\nA["开始"] -->|判断条件| B["结束"]\n```'
const context = await browser.newContext({ viewport: { width: 1280, height: 950 } })
await context.addInitScript(({ profile, token, session }) => {
  localStorage.setItem('access_token', token)
  localStorage.setItem('user', JSON.stringify(profile))
  localStorage.setItem('auth_session', JSON.stringify(session))
}, { profile, token, session })
await context.route('**/api/**', async route => {
  const path = new URL(route.request().url()).pathname
  if (!path.startsWith('/api/')) { await route.continue(); return }
  let data = []
  if (path === '/api/auth/me') data = profile
  else if (path === '/api/auth/activity') data = session
  else if (path === '/api/test-expiry') { await route.fulfill({ status: 401, json: { detail: 'expired' } }); return }
  else if (path.endsWith('/retry')) { await route.fulfill({ headers: { 'X-Chat-Stream-Protocol': 'sse-v1', 'Access-Control-Expose-Headers': 'X-Chat-Stream-Protocol' }, body: 'event: content\ndata: {"delta":"未完成的新草稿"}\n\nevent: error\ndata: {"message":"测试回答中断","code":"STREAM_INCOMPLETE"}\n\n' }); return }
  else if (path === '/api/conversations') data = [{ id: conv, title: '界面验证', class_id: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() }]
  else if (path.endsWith('/messages')) data = [{ id: 1, role: 'user', content: '请绘制这个关系图' }, { id: 2, role: 'assistant', content: answer, can_retry: true, variant_count: 1, variant_index: 1 }]
  else if (path === '/api/memory/settings') data = { enabled: false }
  else if (path.includes('assistant-status')) data = { students: [], student_count: 0 }
  else if (path === '/api/chat/welcome') { await route.fulfill({ headers: { 'X-Chat-Stream-Protocol': 'sse-v1', 'Access-Control-Expose-Headers': 'X-Chat-Stream-Protocol' }, body: 'event: content\ndata: {"delta":"你好"}\n\nevent: done\ndata: {}\n\n' }); return }
  await route.fulfill({ json: data })
})
const page = await context.newPage()
page.on('pageerror', error => errors.push(error.message))
fs.mkdirSync('dist/qa', { recursive: true })
try {
  await page.goto(`${process.env.VITE_TEST_BASE_URL || 'http://127.0.0.1:5173/teaching_assistant/'}#/chat/${conv}`)
  await page.locator('.math-diagram-svg').waitFor({ timeout: 20000 })
  await page.locator('.mermaid-diagram svg').waitFor({ timeout: 30000 })
  if (await page.locator('.math-diagram-edge').count() !== 7) throw Error('Wrong graph edge count')
  if (await page.locator('.katex').count() < 1) throw Error('Math was not rendered')
  for (const [label, scene] of [['碧水蓝天', 'day'], ['黄昏', 'sunset'], ['星空黑夜', 'night']]) {
    await page.getByRole('button', { name: label, exact: true }).click()
    await page.waitForTimeout(1000)
    if (await page.locator('main').getAttribute('data-scene') !== scene) throw Error('Scene mismatch')
    await page.locator('.message-item.assistant').screenshot({ path: `dist/qa/${scene}.png` })
    console.log('SCENE_OK', scene, await page.locator('.mermaid-diagram .edgeLabel').first().evaluate(el => getComputedStyle(el).color))
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(300)
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw Error('Mobile horizontal overflow')
  await page.screenshot({ path: 'dist/qa/mobile.png' })
  await page.getByRole('button', { name: '重新生成回答', exact: true }).click()
  await page.getByText('测试回答中断', { exact: true }).waitFor()
  if (await page.locator('.math-diagram-svg').count() !== 1) throw Error('Failed retry replaced the original answer')
  console.log('FAILED_RETRY_PRESERVES_ANSWER_OK')
  const otherPage = await context.newPage()
  await otherPage.goto(`${process.env.VITE_TEST_BASE_URL || 'http://127.0.0.1:5173/teaching_assistant/'}#/chat/${conv}`)
  await otherPage.locator('.math-diagram-svg').waitFor()
  await page.evaluate(async () => {
    const api = await import('/teaching_assistant/src/api/httpClient.js')
    try { await api.request('/api/test-expiry') } catch { /* expected */ }
  })
  await page.getByText('登录已过期，请重新登录', { exact: true }).waitFor()
  await otherPage.getByText('登录已过期，请重新登录', { exact: true }).waitFor()
  if (await page.evaluate(() => localStorage.getItem('access_token')) !== null) throw Error('Token retained after 401')
  console.log('AUTH_401_EXIT_OK')
  console.log('CROSS_TAB_EXIT_OK')
  if (errors.length) throw Error(JSON.stringify(errors))
} catch (error) {
  console.error('PAGE_ERRORS', JSON.stringify(errors))
  console.error('PAGE_TEXT', (await page.locator('body').innerText()).slice(0, 1600))
  await page.screenshot({ path: 'dist/qa/failure.png', fullPage: true })
  throw error
} finally { await browser.close() }
