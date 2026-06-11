import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import Badge from '../Badge.vue'

describe('Badge', () => {
  it('renders label prop as text', () => {
    const wrapper = mount(Badge, { props: { label: 'Draft' } })
    expect(wrapper.text()).toBe('Draft')
  })

  it('renders slot content over label', () => {
    const wrapper = mount(Badge, {
      props: { label: 'ignored' },
      slots: { default: 'Slotted' },
    })
    expect(wrapper.text()).toBe('Slotted')
  })

  it('adds no extra class for default variant', () => {
    const wrapper = mount(Badge, { props: { variant: 'default' } })
    expect(wrapper.classes()).not.toContain('default')
  })

  it.each(['solid', 'signal', 'ok', 'warn', 'bad', 'brand', 'plum'])(
    'applies %s class for variant="%s"',
    (variant) => {
      const wrapper = mount(Badge, { props: { variant } })
      expect(wrapper.classes()).toContain(variant)
    }
  )

  it('always renders a <span>', () => {
    const wrapper = mount(Badge)
    expect(wrapper.element.tagName).toBe('SPAN')
  })
})
