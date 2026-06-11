import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ScoreBar from '../ScoreBar.vue'

describe('ScoreBar', () => {
  it('renders fill at 100% when value equals max', () => {
    const wrapper = mount(ScoreBar, { props: { value: 100, max: 100 } })
    expect(wrapper.find('.fill').attributes('style')).toContain('width: 100%')
  })

  it('renders fill at 50% for value=50/max=100', () => {
    const wrapper = mount(ScoreBar, { props: { value: 50, max: 100 } })
    expect(wrapper.find('.fill').attributes('style')).toContain('width: 50%')
  })

  it('clamps below 0 to 0%', () => {
    const wrapper = mount(ScoreBar, { props: { value: -10, max: 100 } })
    expect(wrapper.find('.fill').attributes('style')).toContain('width: 0%')
  })

  it('clamps above max to 100%', () => {
    const wrapper = mount(ScoreBar, { props: { value: 200, max: 100 } })
    expect(wrapper.find('.fill').attributes('style')).toContain('width: 100%')
  })

  it('applies custom color via style', () => {
    const wrapper = mount(ScoreBar, { props: { value: 40, max: 100, color: '#ff0000' } })
    expect(wrapper.find('.fill').attributes('style')).toContain('#ff0000')
  })

  it('accepts string value', () => {
    const wrapper = mount(ScoreBar, { props: { value: '75', max: '100' } })
    expect(wrapper.find('.fill').attributes('style')).toContain('width: 75%')
  })

  it('sets aria-label from prop', () => {
    const wrapper = mount(ScoreBar, { props: { value: 60, ariaLabel: 'Score: 60' } })
    expect(wrapper.attributes('aria-label')).toBe('Score: 60')
  })
})
