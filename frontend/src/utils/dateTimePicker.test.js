import test from 'node:test'
import assert from 'node:assert/strict'

import { showDateTimePicker } from './dateTimePicker.js'

test('opens the native picker when the browser supports it', () => {
  let calls = 0
  const opened = showDateTimePicker({
    showPicker() {
      calls += 1
    },
  })

  assert.equal(opened, true)
  assert.equal(calls, 1)
})

test('falls back without throwing when showPicker is unavailable', () => {
  assert.equal(showDateTimePicker({}), false)
  assert.equal(showDateTimePicker(null), false)
})

test('falls back without throwing when the native picker rejects the call', () => {
  const opened = showDateTimePicker({
    showPicker() {
      throw new Error('not allowed')
    },
  })

  assert.equal(opened, false)
})
