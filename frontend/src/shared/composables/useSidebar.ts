/**
 * Sidebar holatini boshqarish — Phase 17.
 *
 * Desktop'da collapse/expand (icon-only 64px <-> full 260px).
 * Mobile'da drawer toggle (overlay).
 *
 * Collapse holati localStorage'da saqlanadi — refresh'da yo'qolmaydi.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const STORAGE_KEY = 'lms.sidebar.collapsed'

// Module-level singletons — barcha komponentlar yagona state bilan ishlaydi
const collapsed = ref<boolean>(false)
const mobileOpen = ref<boolean>(false)
let initialized = false

function load() {
  if (initialized) return
  initialized = true
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw !== null) collapsed.value = raw === '1'
  } catch {
    // SSR yoki private mode'da localStorage yo'q
  }
}

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, collapsed.value ? '1' : '0')
  } catch {
    // ignore
  }
}

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  persist()
}

function toggleMobile() {
  mobileOpen.value = !mobileOpen.value
}

function closeMobile() {
  mobileOpen.value = false
}

export function useSidebar() {
  load()
  return {
    collapsed,
    mobileOpen,
    toggleCollapsed,
    toggleMobile,
    closeMobile,
  }
}

/**
 * Esc tugmasi bilan mobile drawer yopish.
 * Faqat sidebar komponentida bir marta ulanadi.
 */
export function useSidebarEscClose() {
  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && mobileOpen.value) {
      closeMobile()
    }
  }
  onMounted(() => {
    document.addEventListener('keydown', onKeydown)
  })
  onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKeydown)
  })
}
