import { computed } from 'vue'
import { useAuthStore } from '@shared/stores/auth'

/**
 * Permission tekshiruvi — backend `_matches` mantiqi bilan teng:
 *  - `platform.*` → istalgan ruxsatga to'g'ri keladi (super admin)
 *  - `foo.*` → `foo.bar`, `foo.bar.baz` ga to'g'ri keladi
 *  - aniq mos: `foo.bar` === `foo.bar`
 */
export function matches(granted: string, required: string): boolean {
  if (granted === required) return true
  if (granted === 'platform.*') return true
  if (granted.endsWith('.*')) {
    const prefix = granted.slice(0, -2)
    return required === prefix || required.startsWith(prefix + '.')
  }
  return false
}

export function usePermissions() {
  const auth = useAuthStore()

  const permissions = computed(() => auth.permissions)
  const roles = computed(() => auth.roles)

  function hasPermission(perm: string): boolean {
    return permissions.value.some((g) => matches(g, perm))
  }

  function hasAnyPermission(perms: string[]): boolean {
    return perms.some(hasPermission)
  }

  function hasAllPermissions(perms: string[]): boolean {
    return perms.every(hasPermission)
  }

  function hasRole(code: string): boolean {
    return roles.value.includes(code)
  }

  function hasAnyRole(codes: string[]): boolean {
    return codes.some((c) => roles.value.includes(c))
  }

  return {
    permissions,
    roles,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
  }
}
