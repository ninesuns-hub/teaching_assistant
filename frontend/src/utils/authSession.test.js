import test from 'node:test'
import assert from 'node:assert/strict'
import { authenticatedFetch, getToken, isAuthExpired, setAuth } from '../api/httpClient.js'

function setup() {
  const storage = () => {
    const data = new Map()
    return {getItem:key=>data.get(key)??null,setItem:(key,value)=>data.set(key,String(value)),removeItem:key=>data.delete(key)}
  }
  globalThis.localStorage=storage()
  globalThis.sessionStorage=storage()
  globalThis.window=new EventTarget()
  const future=Math.floor(Date.now()/1000)+28800
  const token=`header.${btoa(JSON.stringify({sid:'test-session',exp:future}))}.signature`
  setAuth(token,{email:'test@tongji.edu.cn'},{expires_at:future,idle_expires_at:Math.floor(Date.now()/1000)+1800})
  return token
}
test('idle and absolute deadlines both expire authentication', () => {
  setup()
  assert.equal(isAuthExpired(),false)
  assert.equal(isAuthExpired(Date.now()+1801_000),true)
  const future=Math.floor(Date.now()/1000)+100
  localStorage.setItem('auth_session',JSON.stringify({expires_at:future,idle_expires_at:future+900}))
  assert.equal(isAuthExpired(Date.now()+101_000),true)
})
test('401 clears credentials and emits one expiry event', async () => {
  setup()
  let events=0
  window.addEventListener('auth:expired',()=>events++)
  const originalFetch=globalThis.fetch
  globalThis.fetch=async()=>new Response('{}',{status:401})
  try { await authenticatedFetch('/api/conversations') } finally { globalThis.fetch=originalFetch }
  assert.equal(getToken(),null)
  assert.equal(localStorage.getItem('user'),null)
  assert.equal(events,1)
})
test('503 does not sign out a valid session', async () => {
  const token=setup()
  const originalFetch=globalThis.fetch
  globalThis.fetch=async()=>new Response('{}',{status:503})
  try { await authenticatedFetch('/api/conversations') } finally { globalThis.fetch=originalFetch }
  assert.equal(getToken(),token)
})
