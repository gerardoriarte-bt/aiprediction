import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import Button from '../Button.vue'

// Stub router-link so tests don't need a real router
const RouterLinkStub = { name: 'RouterLink', template: '<a><slot /></a>', props: ['to'] }

describe('Button', () => {
  it('renders a <button> by default', () => {
    const wrapper = mount(Button)
    expect(wrapper.element.tagName).toBe('BUTTON')
  })

  it('renders label prop', () => {
    const wrapper = mount(Button, { props: { label: 'Save' } })
    expect(wrapper.text()).toContain('Save')
  })

  it('renders slot content', () => {
    const wrapper = mount(Button, { slots: { default: 'Click me' } })
    expect(wrapper.text()).toContain('Click me')
  })

  it('applies primary class for variant=primary', () => {
    const wrapper = mount(Button, { props: { variant: 'primary' } })
    expect(wrapper.classes()).toContain('primary')
  })

  it('applies sm class for size=sm', () => {
    const wrapper = mount(Button, { props: { size: 'sm' } })
    expect(wrapper.classes()).toContain('sm')
  })

  it('does not apply size class for default md', () => {
    const wrapper = mount(Button, { props: { size: 'md' } })
    expect(wrapper.classes()).not.toContain('md')
  })

  it('emits click when enabled', async () => {
    const wrapper = mount(Button)
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('does not emit click when disabled', async () => {
    const wrapper = mount(Button, { props: { disabled: true } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeFalsy()
  })

  it('renders an <a> tag when href is provided', () => {
    const wrapper = mount(Button, { props: { href: 'https://example.com' } })
    expect(wrapper.element.tagName).toBe('A')
  })

  it('renders router-link when to is provided', () => {
    const wrapper = mount(Button, {
      props: { to: '/home' },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    expect(wrapper.find('a').exists()).toBe(true)
  })
})
