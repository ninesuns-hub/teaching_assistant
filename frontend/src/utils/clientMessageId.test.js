import assert from 'node:assert/strict'
import test from 'node:test'

import { createClientMessageId } from './clientMessageId.js'

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

test('prefers the native randomUUID implementation when available', () => {
  const expected = '123e4567-e89b-42d3-a456-426614174000'
  let fallbackCalled = false
  const cryptoApi = {
    randomUUID: () => expected,
    getRandomValues: () => {
      fallbackCalled = true
    },
  }

  assert.equal(createClientMessageId(cryptoApi), expected)
  assert.equal(fallbackCalled, false)
})

test('generates an RFC 4122 version 4 UUID with getRandomValues', () => {
  const cryptoApi = {
    getRandomValues: bytes => {
      bytes.set([
        0x00, 0x11, 0x22, 0x33,
        0x44, 0x55,
        0xff, 0x77,
        0xff, 0x99,
        0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
      ])
      return bytes
    },
  }

  const id = createClientMessageId(cryptoApi)

  assert.equal(id, '00112233-4455-4f77-bf99-aabbccddeeff')
  assert.match(id, UUID_V4_PATTERN)
})

test('returns different identifiers when the random bytes differ', () => {
  let sequence = 0
  const cryptoApi = {
    getRandomValues: bytes => {
      bytes.fill(sequence)
      sequence += 1
      return bytes
    },
  }

  const first = createClientMessageId(cryptoApi)
  const second = createClientMessageId(cryptoApi)

  assert.notEqual(first, second)
  assert.match(first, UUID_V4_PATTERN)
  assert.match(second, UUID_V4_PATTERN)
})

test('reports a clear error when secure randomness is unavailable', () => {
  assert.throws(
    () => createClientMessageId({}),
    /当前浏览器不支持安全随机数，请升级浏览器后重试/,
  )
})
