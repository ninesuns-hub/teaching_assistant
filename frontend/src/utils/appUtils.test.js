import assert from 'node:assert/strict'
import test from 'node:test'

import { getSceneByHour } from './appUtils.js'

test('uses the configured Beijing-time scene boundaries', () => {
  assert.equal(getSceneByHour(5), 'night')
  assert.equal(getSceneByHour(6), 'day')
  assert.equal(getSceneByHour(14), 'day')
  assert.equal(getSceneByHour(15), 'sunset')
  assert.equal(getSceneByHour(18), 'sunset')
  assert.equal(getSceneByHour(19), 'night')
})
