import assert from 'node:assert/strict'
import test from 'node:test'

import { TONGJI_EMAIL_RE, getSceneByHour } from './appUtils.js'

test('uses the configured Beijing-time scene boundaries', () => {
  assert.equal(getSceneByHour(5), 'night')
  assert.equal(getSceneByHour(6), 'day')
  assert.equal(getSceneByHour(14), 'day')
  assert.equal(getSceneByHour(15), 'sunset')
  assert.equal(getSceneByHour(18), 'sunset')
  assert.equal(getSceneByHour(19), 'night')
})

test('accepts Tongji email addresses with non-numeric local parts', () => {
  assert.equal(TONGJI_EMAIL_RE.test('2452808@tongji.edu.cn'), true)
  assert.equal(TONGJI_EMAIL_RE.test('teacher.name@tongji.edu.cn'), true)
  assert.equal(TONGJI_EMAIL_RE.test('department-user@tongji.edu.cn'), true)
})

test('rejects invalid or deceptive Tongji email addresses', () => {
  assert.equal(TONGJI_EMAIL_RE.test('@tongji.edu.cn'), false)
  assert.equal(TONGJI_EMAIL_RE.test('user@example.com'), false)
  assert.equal(TONGJI_EMAIL_RE.test('user@sub.tongji.edu.cn'), false)
  assert.equal(TONGJI_EMAIL_RE.test('user@tongji.edu.cn.example.com'), false)
  assert.equal(TONGJI_EMAIL_RE.test('user name@tongji.edu.cn'), false)
  assert.equal(TONGJI_EMAIL_RE.test('user@name@tongji.edu.cn'), false)
})
