import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Chatbox from './Chatbox.vue'

vi.mock('./categorizedQuestions.json', () => ({
  default: {
    "General": ["How are you?", "What is this?"],
    "Technical": ["How to install?"]
  }
}))


describe('Chatbox.vue', () => {
  const jsonResponse = (data, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'Content-Type': 'application/json' }),
    json: () => Promise.resolve(data),
  })

  // The history request on mount goes to its own mock, so the other tests can queue responses for their own requests.
  const mockFetch = vi.fn()
  const historyFetch = vi.fn()
  vi.stubGlobal('fetch', (url, options) =>
    String(url).includes('/history?') ? historyFetch(url, options) : mockFetch(url, options))

  beforeEach(() => {
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token: 'mock-token-123' }),
    })
    historyFetch.mockReset()
    historyFetch.mockResolvedValue(jsonResponse({ conversationId: null, messages: [] }))
  })

  // Waits for the session and history loading on mount, as sending is blocked until then.
  const createWrapper = async (provide = {}) => {
    const wrapper = mount(Chatbox, {
      global: {
        provide: {
          token: 'initial-token',
          projectId: 1,
          ...provide
        }
      }
    })
    await flushPromises()
    return wrapper
  }

  it('renders the initial greeting message', async () => {
    const wrapper = await createWrapper()
    expect(wrapper.text()).toContain('Greetings. How may I be of assistance?')
  })

  it('shows categories initially and switches to questions on click', async () => {
    const wrapper = await createWrapper()
    
    const categories = wrapper.findAll('.category-chip')
    expect(categories[0].text()).toBe('General')

    await categories[0].trigger('click')

    expect(wrapper.text()).toContain('How are you?')
    expect(wrapper.find('.back-chip').exists()).toBe(true)
  })

  it('updates the input field when typing', async () => {
    const wrapper = await createWrapper()
    const input = wrapper.find('input')
    
    await input.setValue('Hello Bot')
    expect(wrapper.vm.input).toBe('Hello Bot')
  })

  it('disables input and buttons when loading is true', async () => {
    const wrapper = await createWrapper()
    await wrapper.find('input').setValue('Hello')
    
    let resolveFetch;
    mockFetch.mockReturnValue(new Promise((res) => { resolveFetch = res; }))

    const sendButton = wrapper.find('.input-area button')
    await sendButton.trigger('click')
    
    expect(wrapper.find('input').attributes()).toHaveProperty('disabled')
    expect(sendButton.attributes()).toHaveProperty('disabled')

    resolveFetch({ ok: true, body: null })
  })

  it('returns to categories when "Go back" is clicked', async () => {
    const wrapper = await createWrapper()
    
    await wrapper.find('.category-chip').trigger('click')
    expect(wrapper.find('.back-chip').exists()).toBe(true)

    await wrapper.find('.back-chip').trigger('click')
    
    expect(wrapper.find('.category-chip').exists()).toBe(true)
  })
	
	const streamResponse = (events) => {
		const encoder = new TextEncoder()
		const chunks = events.map(([event, data]) => encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
		return {
			ok: true,
			status: 200,
			body: {
				getReader: () => ({
					read: () => Promise.resolve(chunks.length ? { value: chunks.shift(), done: false } : { done: true }),
				}),
			},
		}
	}

	const ask = async (wrapper, text = 'When is the test plan due?') => {
		await wrapper.find('input').setValue(text)
		await wrapper.find('.input-area button').trigger('click')
		await flushPromises()
	}

	it('sends requests to the address from data-api-url', async () => {
		const wrapper = await createWrapper({ apiUrl: 'https://ai.example.test' })
		mockFetch.mockResolvedValueOnce(streamResponse([]))

		await ask(wrapper)

		expect(mockFetch.mock.calls.at(-1)[0]).toBe('https://ai.example.test/chat')
	})

	it('renews the token after a 401 and sends the question again', async () => {
		const wrapper = await createWrapper({ refreshUrl: '/chatbot/refresh-token' })
		mockFetch
			.mockResolvedValueOnce({ ok: false, status: 401 })
			.mockResolvedValueOnce(jsonResponse({ token: 'refreshed-token-xyz' }))
			.mockResolvedValueOnce(streamResponse([['token', { text: 'Answer' }], ['done', { message_id: 'm1' }]]))

		await ask(wrapper)

		const calls = mockFetch.mock.calls
		expect(calls.at(-3)[1].headers.Authorization).toBe('initial-token')
		expect(calls.at(-2)).toEqual(['/chatbot/refresh-token', { credentials: 'same-origin' }])
		expect(calls.at(-1)[0]).toMatch(/\/chat$/)
		expect(calls.at(-1)[1].headers.Authorization).toBe('refreshed-token-xyz')
		expect(wrapper.findAll('.chatbox-message.bot').at(-1).text()).toContain('Answer')
	})

	it.each([
		['is refused', { ok: false, status: 403, headers: new Headers({ 'Content-Type': 'application/json' }), json: () => Promise.resolve({}) }],
		['redirects to the login page', { ok: true, status: 200, headers: new Headers({ 'Content-Type': 'text/html' }), json: () => Promise.reject(new Error('not JSON')) }],
	])('shows the session ended text when the token refresh %s', async (_, refreshResponse) => {
		const wrapper = await createWrapper({ refreshUrl: '/chatbot/refresh-token' })
		mockFetch
			.mockResolvedValueOnce({ ok: false, status: 401 })
			.mockResolvedValueOnce(refreshResponse)

		await ask(wrapper)

		expect(mockFetch).toHaveBeenCalledTimes(2)
		expect(wrapper.findAll('.chatbox-message.bot').at(-1).text()).toContain('Your session has ended')
	})

	it('renews the token from /start_session when running on its own', async () => {
		const wrapper = await createWrapper()
		mockFetch
			.mockResolvedValueOnce({ ok: false, status: 401 })
			.mockResolvedValueOnce(jsonResponse({ token: 'dev-token' }))
			.mockResolvedValueOnce(streamResponse([['token', { text: 'Answer' }]]))

		await ask(wrapper)

		const calls = mockFetch.mock.calls
		expect(calls.at(-2)[0]).toBe('http://localhost:8000/start_session')
		expect(calls.at(-1)[1].headers.Authorization).toBe('dev-token')
	})

	it('explains when the backend has AUTH_DEV_MODE off', async () => {
		mockFetch.mockResolvedValueOnce(jsonResponse({ detail: 'Not found' }, 404))
		const wrapper = await createWrapper({ token: '' })
		await flushPromises()

		expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/start_session')
		expect(wrapper.findAll('.chatbox-message.bot').at(-1).text()).toContain('AUTH_DEV_MODE is off')
	})

	it('explains AUTH_DEV_MODE when renewing the token on its own fails', async () => {
		const wrapper = await createWrapper()
		mockFetch
			.mockResolvedValueOnce({ ok: false, status: 401 })
			.mockResolvedValueOnce(jsonResponse({ detail: 'Not found' }, 404))

		await ask(wrapper)

		expect(wrapper.findAll('.chatbox-message.bot').at(-1).text()).toContain('AUTH_DEV_MODE is off')
	})

	it('does not call /start_session inside MMT', async () => {
		await createWrapper({ token: '', refreshUrl: '/chatbot/refresh-token' })
		expect(mockFetch).not.toHaveBeenCalled()
	})

	it('streams the answer from events and sends the conversation ID with the next question', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([
			['start', { conversation_id: 'c1' }],
			['status', { text: 'Reading the course material…' }],
			['token', { text: 'Due **30.10.2026**' }],
			['token', { text: ', see the Schedule page.' }],
			['done', { message_id: 'm1' }],
		]))

		await ask(wrapper)

		const bot = wrapper.findAll('.chatbox-message.bot').at(-1)
		expect(bot.html()).toContain('<strong>30.10.2026</strong>, see the Schedule page.')
		expect(bot.find('.chatbox-status').exists()).toBe(false)
		expect(bot.findAll('.chatbox-feedback button')).toHaveLength(2)

		mockFetch.mockResolvedValueOnce(streamResponse([['done', { message_id: 'm2' }]]))
		await ask(wrapper, 'And the test report?')
		const body = JSON.parse(mockFetch.mock.calls.at(-1)[1].body)
		expect(body.conversation_id).toBe('c1')
	})

	it('shows the status text until the first token arrives', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([['status', { text: 'Reading the course material…' }]]))

		await ask(wrapper)

		expect(wrapper.find('.chatbox-status').text()).toBe('Reading the course material…')
	})

	it('sends feedback for an answer', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([['token', { text: 'Answer' }], ['done', { message_id: 'm1' }]]))
		await ask(wrapper)

		mockFetch.mockResolvedValueOnce({ ok: true, status: 204 })
		await wrapper.findAll('.chatbox-feedback button')[1].trigger('click')
		await flushPromises()

		const [url, options] = mockFetch.mock.calls.at(-1)
		expect(url).toMatch(/\/feedback$/)
		expect(JSON.parse(options.body)).toEqual({ message_id: 'm1', rating: -1 })
		expect(wrapper.findAll('.chatbox-feedback button')[1].classes()).toContain('selected')
	})

	it('shows the error event and no feedback buttons when the answer fails', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([['error', { text: 'Sorry, I could not answer.', message_id: 'm1' }]]))

		await ask(wrapper)

		const bot = wrapper.findAll('.chatbox-message.bot').at(-1)
		expect(bot.classes()).toContain('error')
		expect(bot.text()).toContain('Sorry, I could not answer.')
		expect(bot.find('.chatbox-feedback').exists()).toBe(false)
	})

	it('removes scripts and event handlers from answers', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([
			['token', { text: 'Risk: <img src=x onerror="alert(1)"><script>alert(2)</script>' }],
			['done', { message_id: 'm1' }],
		]))

		await ask(wrapper)

		const html = wrapper.findAll('.chatbox-message.bot').at(-1).html()
		expect(html).not.toContain('onerror')
		expect(html).not.toContain('<script')
	})

	it('shows user messages as plain text', async () => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce(streamResponse([]))

		await ask(wrapper, '<b>bold?</b>')

		const user = wrapper.findAll('.chatbox-message.user').at(-1)
		expect(user.text()).toBe('<b>bold?</b>')
		expect(user.find('b').exists()).toBe(false)
	})

	it.each([
		[403, "You don't have access"],
		[429, 'Please wait a minute'],
	])('explains HTTP %i errors', async (status, text) => {
		const wrapper = await createWrapper()
		mockFetch.mockResolvedValueOnce({ ok: false, status })

		await ask(wrapper)

		expect(wrapper.findAll('.chatbox-message.bot').at(-1).text()).toContain(text)
	})

	it('restores the latest conversation on mount and continues it', async () => {
		historyFetch.mockResolvedValueOnce(jsonResponse({
			conversationId: 'c1',
			messages: [
				{ id: 'u1', role: 'user', content: 'When is the test plan due?', rating: null },
				{ id: 'm1', role: 'assistant', content: 'Due **30.10.2026**', rating: 1 },
			],
		}))
		const wrapper = await createWrapper()

		const [url, options] = historyFetch.mock.calls[0]
		expect(url).toBe('http://localhost:8000/history?project_id=1')
		expect(options.method).toBe('GET')
		expect(options.headers.Authorization).toBe('initial-token')
		expect(options).not.toHaveProperty('body')

		expect(wrapper.text()).not.toContain('Greetings')
		expect(wrapper.find('.chatbox-message.user').text()).toBe('When is the test plan due?')
		const bot = wrapper.find('.chatbox-message.bot')
		expect(bot.html()).toContain('<strong>30.10.2026</strong>')
		expect(bot.findAll('.chatbox-feedback button')[0].classes()).toContain('selected')

		mockFetch.mockResolvedValueOnce(streamResponse([['done', { message_id: 'm2' }]]))
		await ask(wrapper, 'And the test report?')
		expect(JSON.parse(mockFetch.mock.calls.at(-1)[1].body).conversation_id).toBe('c1')
	})

	it.each([
		['there is no earlier conversation', () => Promise.resolve(jsonResponse({ conversationId: null, messages: [] }))],
		['the history request fails', () => Promise.resolve(jsonResponse({ detail: 'Internal error' }, 500))],
		['the backend cannot be reached', () => Promise.reject(new TypeError('Failed to fetch'))],
	])('keeps the greeting and allows sending when %s', async (_, response) => {
		historyFetch.mockImplementationOnce(response)
		const wrapper = await createWrapper()

		expect(wrapper.text()).toContain('Greetings. How may I be of assistance?')
		expect(wrapper.find('input').attributes()).not.toHaveProperty('disabled')
	})

	it('blocks sending until the history has loaded', async () => {
		let resolveHistory
		historyFetch.mockReturnValueOnce(new Promise((res) => { resolveHistory = res }))
		const wrapper = mount(Chatbox, { global: { provide: { token: 'initial-token', projectId: 1 } } })
		await flushPromises()

		expect(wrapper.find('input').attributes()).toHaveProperty('disabled')

		resolveHistory(jsonResponse({ conversationId: null, messages: [] }))
		await flushPromises()
		expect(wrapper.find('input').attributes()).not.toHaveProperty('disabled')
	})

	it('does not ask for history without a token', async () => {
		await createWrapper({ token: '', refreshUrl: '/chatbot/refresh-token' })
		expect(historyFetch).not.toHaveBeenCalled()
	})

})
