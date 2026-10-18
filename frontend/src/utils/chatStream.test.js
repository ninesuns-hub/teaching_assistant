import test from 'node:test'
import assert from 'node:assert/strict'
import { consumeChatStream } from '../api/chat.js'

const response = frames => new Response(frames, {headers:{'X-Chat-Stream-Protocol':'sse-v1'}})
test('requires saved completion event', async () => {
  await assert.rejects(consumeChatStream(response('event: content\ndata: {"delta":"half"}\n\n'),()=>{}), /中断/)
})
test('forwards replacement and continuation then returns done', async () => {
  const events=[]
  const done=await consumeChatStream(response('event: status\ndata: {"stage":"continuing"}\n\nevent: replace\ndata: {"content":"fixed"}\n\nevent: done\ndata: {"message_id":7}\n\n'),e=>events.push(e))
  assert.equal(done.message_id,7)
  assert.equal(events[1].content,'fixed')
})
test('error after partial content preserves structured error', async () => {
  await assert.rejects(consumeChatStream(response('event: content\ndata: {"delta":"part"}\n\nevent: error\ndata: {"message":"回答未完成","code":"ANSWER_TRUNCATED"}\n\n'),()=>{}), error=>error.code==='ANSWER_TRUNCATED')
})
