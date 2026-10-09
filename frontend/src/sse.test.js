import { describe, it, expect, vi } from 'vitest'
import { createSseParser } from './sse.js'

describe('createSseParser', () => {
  it('parses complete events', () => {
    const onEvent = vi.fn()
    const parse = createSseParser(onEvent)
    parse('event: token\ndata: {"text": "Hi"}\n\nevent: done\ndata: {"message_id": "m1"}\n\n')
    expect(onEvent.mock.calls).toEqual([
      ['token', { text: 'Hi' }],
      ['done', { message_id: 'm1' }],
    ])
  })

  it('buffers events split across chunks', () => {
    const onEvent = vi.fn()
    const parse = createSseParser(onEvent)
    parse('event: tok')
    parse('en\ndata: {"text": "Hel')
    expect(onEvent).not.toHaveBeenCalled()
    parse('lo"}\n')
    parse('\n')
    expect(onEvent).toHaveBeenCalledWith('token', { text: 'Hello' })
  })

  it('accepts CRLF line endings and skips invalid JSON', () => {
    const onEvent = vi.fn()
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const parse = createSseParser(onEvent)
    parse('event: status\r\ndata: {"text": "Working"}\r\n\r\nevent: token\ndata: {broken\n\n')
    expect(onEvent.mock.calls).toEqual([['status', { text: 'Working' }]])
    errorSpy.mockRestore()
  })
})
