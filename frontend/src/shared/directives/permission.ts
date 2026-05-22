import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@shared/stores/auth'
import { matches } from '@shared/composables/usePermissions'

type PermissionValue = string | string[]
type Modifiers = { any?: boolean; all?: boolean }

function check(value: PermissionValue | undefined, mods: Modifiers): boolean {
  const auth = useAuthStore()
  const granted = auth.permissions
  if (!value) return false
  const required = Array.isArray(value) ? value : [value]
  if (required.length === 0) return true
  const test = (perm: string) => granted.some((g) => matches(g, perm))
  if (mods.all) return required.every(test)
  // default: any
  return required.some(test)
}

function apply(el: HTMLElement, binding: DirectiveBinding<PermissionValue>): void {
  const ok = check(binding.value, binding.modifiers as Modifiers)
  el.style.display = ok ? '' : 'none'
}

/**
 * `v-permission` directive — element ko'rinishini permission'larga qarab boshqaradi.
 *
 * Foydalanish:
 *   <button v-permission="'users.manage'">Yangi</button>
 *   <button v-permission="['users.manage', 'users.read']">Yangi</button>     // .any (default)
 *   <button v-permission.all="['users.manage', 'users.read']">Yangi</button> // hammasi kerak
 *
 * IZOH: element DOM'da qoladi, faqat `display: none` bo'ladi. Sezgir element
 * (masalan, "O'chirish" tugmasi) uchun `v-if` bilan birga ishlatish ham mumkin.
 */
export const vPermission: Directive<HTMLElement, PermissionValue> = {
  mounted: apply,
  updated: apply,
}
