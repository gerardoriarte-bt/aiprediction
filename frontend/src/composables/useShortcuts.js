import { onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

/**
 * Registers global keyboard shortcuts.
 *
 * - Cmd/Ctrl+K           → calls onCmdK()
 * - Esc                  → calls onEscape()
 * - ?                    → /help
 * - G then C             → /
 * - G then M             → /manual
 * - G then H             → /help
 * - G then O / X / T / R / S → client tab (overview / context / tests / reports / settings)
 *
 * Shortcuts are no-ops when an input/textarea is focused or a contenteditable
 * element has focus. The "G then X" prefix expires after 1.2s.
 */
export function useShortcuts({ onCmdK, onEscape } = {}) {
  const router = useRouter()
  const route = useRoute()

  let gPressed = false
  let gTimer = null

  const clientId = computed(() => {
    const m = (route.path || '').match(/^\/clients\/([^\/]+)/)
    return m ? m[1] : ''
  })

  const isTyping = (target) => {
    if (!target) return false
    const tag = (target.tagName || '').toLowerCase()
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return true
    if (target.isContentEditable) return true
    return false
  }

  const navigate = (key) => {
    const cid = clientId.value
    switch (key) {
      case 'c':
        router.push('/')
        return true
      case 'm':
        router.push('/manual')
        return true
      case 'h':
        router.push('/help')
        return true
      case 'o':
        if (cid) router.push(`/clients/${cid}/overview`)
        return !!cid
      case 'x':
        if (cid) router.push(`/clients/${cid}/context`)
        return !!cid
      case 't':
        if (cid) router.push(`/clients/${cid}/tests`)
        return !!cid
      case 'r':
        if (cid) router.push(`/clients/${cid}/reports`)
        return !!cid
      case 's':
        if (cid) router.push(`/clients/${cid}/settings`)
        return !!cid
      default:
        return false
    }
  }

  const handler = (e) => {
    if (isTyping(e.target)) return

    // Cmd / Ctrl + K
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault()
      onCmdK && onCmdK()
      return
    }

    if (e.key === 'Escape') {
      onEscape && onEscape()
      return
    }

    // ? → /help
    if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
      e.preventDefault()
      router.push('/help')
      return
    }

    if (e.metaKey || e.ctrlKey || e.altKey) return

    const key = (e.key || '').toLowerCase()
    if (gPressed) {
      // Resolve second key.
      if (navigate(key)) {
        e.preventDefault()
      }
      gPressed = false
      if (gTimer) { clearTimeout(gTimer); gTimer = null }
      return
    }

    if (key === 'g') {
      gPressed = true
      if (gTimer) clearTimeout(gTimer)
      gTimer = setTimeout(() => { gPressed = false }, 1200)
      return
    }
  }

  onMounted(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', handler)
    }
  })
  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handler)
    }
    if (gTimer) clearTimeout(gTimer)
  })
}
