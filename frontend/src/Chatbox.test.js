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
  const mockFetch = vi.fn()
  vi.stubGlobal('fetch', mockFetch)

  beforeEach(() => {
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ token: 'mock-token-123' }),
    })
  })

  const createWrapper = () => mount(Chatbox, {
    global: {
      provide: {
        token: 'initial-token',
        projectId: 1
      }
    }
  })

  it('renders the initial greeting message', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Greetings. How may I be of assistance?')
  })

  it('shows categories initially and switches to questions on click', async () => {
    const wrapper = createWrapper()
    
    const categories = wrapper.findAll('.category-chip')
    expect(categories[0].text()).toBe('General')

    await categories[0].trigger('click')

    expect(wrapper.text()).toContain('How are you?')
    expect(wrapper.find('.back-chip').exists()).toBe(true)
  })

  it('updates the input field when typing', async () => {
    const wrapper = createWrapper()
    const input = wrapper.find('input')
    
    await input.setValue('Hello Bot')
    expect(wrapper.vm.input).toBe('Hello Bot')
  })

  it('disables input and buttons when loading is true', async () => {
    const wrapper = createWrapper()
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
    const wrapper = createWrapper()
    
    await wrapper.find('.category-chip').trigger('click')
    expect(wrapper.find('.back-chip').exists()).toBe(true)

    await wrapper.find('.back-chip').trigger('click')
    
    expect(wrapper.find('.category-chip').exists()).toBe(true)
  })
	
	it('refreshes token and shows notification when API returns 401', async () => {
		const wrapper = createWrapper()
		
		const postMessageSpy = vi.spyOn(window.top, 'postMessage')
		
		mockFetch.mockResolvedValueOnce({
			status: 401,
			ok: false
		})

		await wrapper.find('input').setValue('Hello')
		await wrapper.find('.input-area button').trigger('click')
		
		await flushPromises(); 

		expect(postMessageSpy).toHaveBeenCalledWith("AUTH_EXPIRED_SIGNAL", "*")

		const mockNewToken = 'refreshed-token-xyz'
		window.dispatchEvent(new MessageEvent('message', {
			data: { type: 'NEW_TOKEN', token: mockNewToken }
		}))
		
		await flushPromises()

		expect(wrapper.vm.token).toBe(mockNewToken)
		expect(wrapper.text()).toContain('Token expired and refreshed')
		
		postMessageSpy.mockRestore()
	})

})




