# 02. Users & RBAC Moduli

## Maqsad

Foydalanuvchilarni boshqarish, rollar va ruxsatlar tizimi (Role-Based Access Control).

## Funksional talablar

### 1. Profil boshqaruvi
- To'liq ism, telefon, email, manzil
- Avatar yuklash (max 2 MB, jpg/png/webp)
- Til tanlash (uz-lat, uz-cyr, ru, en)
- Vaqt zonasi
- Bildirishnoma sozlamalari

### 2. Rollar tizimi (RBAC)
Tafsilotlar: [01-overview/04-roles.md](../01-overview/04-roles.md)

10 ta asosiy rol:
1. Super Administrator
2. OTM Administrator
3. Dekan / O'quv bo'limi
4. Kafedra mudiri
5. Pedagog
6. Talaba
7. Xorijiy pedagog
8. Tashqi nazoratchi (TSDIN)
9. Texnik qo'llab-quvvatlash
10. Mehmon (Auditor)

### 3. Custom rollar
- OTM administratori o'z OTMda yangi rollar yaratishi mumkin
- Ruxsatlarni granular tanlash (resource.action format)

### 4. Foydalanuvchilar boshqaruvi
- Ro'yxat (filter, sort, search, pagination)
- Yangi qo'shish (manual yoki bulk import)
- Tahrir, faollashtirish/o'chirish
- Rollarni biriktirish/yechib olish
- Ko'p qurilmadan login boshqaruvi
- Audit tarixi

### 5. Bulk amallar
- CSV/Excel orqali bulk import
- Ko'p foydalanuvchini bir vaqtda boshqarish
- Bulk email yuborish

## API Endpoints

```
# Profil
GET    /api/v1/users/me
PATCH  /api/v1/users/me
POST   /api/v1/users/me/avatar
DELETE /api/v1/users/me/avatar
PATCH  /api/v1/users/me/preferences

# Foydalanuvchilar (admin)
GET    /api/v1/users                          # ro'yxat (filter)
POST   /api/v1/users                          # yaratish
GET    /api/v1/users/{id}                     # tafsilot
PATCH  /api/v1/users/{id}                     # tahrir
DELETE /api/v1/users/{id}                     # soft delete
POST   /api/v1/users/{id}/activate
POST   /api/v1/users/{id}/deactivate
POST   /api/v1/users/{id}/reset-password
POST   /api/v1/users/{id}/impersonate         # Super admin only

# Rollar
GET    /api/v1/roles
POST   /api/v1/roles
GET    /api/v1/roles/{id}
PATCH  /api/v1/roles/{id}
DELETE /api/v1/roles/{id}
POST   /api/v1/users/{id}/roles               # rol biriktirish
DELETE /api/v1/users/{id}/roles/{role_id}     # rol yechish

# Ruxsatlar
GET    /api/v1/permissions                    # mavjud ruxsatlar ro'yxati
GET    /api/v1/users/{id}/permissions         # foydalanuvchining barcha ruxsatlari

# Bulk
POST   /api/v1/users/bulk-import              # CSV import
POST   /api/v1/users/bulk-action              # bulk activate/deactivate
GET    /api/v1/users/export                   # CSV/Excel eksport
```

## Database modellari

### profiles
```sql
CREATE TABLE profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    pinfl VARCHAR(14) UNIQUE,                  -- Shaxsiy raqam
    passport_series VARCHAR(2),
    passport_number VARCHAR(7),
    birthdate DATE,
    gender VARCHAR(10),
    nationality VARCHAR(50),
    address TEXT,
    region_id INT,
    district_id INT,
    bio TEXT,
    language VARCHAR(10) DEFAULT 'uz-lat',
    timezone VARCHAR(50) DEFAULT 'Asia/Tashkent',
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### roles
```sql
CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,          -- 'student', 'teacher', etc.
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,           -- Sistem rollar o'chirilmaydi
    tenant_id BIGINT REFERENCES organizations(id), -- NULL = global
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### permissions
```sql
CREATE TABLE permissions (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,         -- 'course.create', 'exam.proctor'
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50)                       -- guruhlash uchun
);
```

### role_permissions
```sql
CREATE TABLE role_permissions (
    role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE,
    permission_id BIGINT REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

### user_roles
```sql
CREATE TABLE user_roles (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role_id BIGINT REFERENCES roles(id) ON DELETE CASCADE,
    scope_type VARCHAR(50),                    -- 'global', 'org', 'faculty', 'department', 'course'
    scope_id BIGINT,                           -- ID of scope (nullable for global)
    granted_by BIGINT REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                      -- ixtiyoriy
    PRIMARY KEY (user_id, role_id, scope_type, scope_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_scope ON user_roles(scope_type, scope_id);
```

## RBAC implementatsiyasi

### Permission decorator (FastAPI)

```python
# app/core/deps.py
from fastapi import Depends, HTTPException, status
from app.modules.auth.service import get_current_user

def require_permission(permission: str):
    async def checker(
        user: User = Depends(get_current_user),
        rbac: RBACService = Depends(get_rbac_service),
    ) -> User:
        if not await rbac.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        return user
    return checker

# Ishlatish
@router.post("/courses")
async def create_course(
    data: CourseCreate,
    user: User = Depends(require_permission("course.create")),
):
    ...
```

### RBAC servisi

```python
# app/modules/rbac/service.py
class RBACService:
    def __init__(self, repo: RBACRepository, redis: Redis):
        self.repo = repo
        self.redis = redis
    
    async def has_permission(
        self,
        user: User,
        permission: str,
        scope_type: str | None = None,
        scope_id: int | None = None,
    ) -> bool:
        # Cache'dan tekshirish
        cache_key = f"perms:{user.id}"
        cached = await self.redis.get(cache_key)
        if cached:
            permissions = json.loads(cached)
        else:
            permissions = await self._load_permissions(user.id)
            await self.redis.set(cache_key, json.dumps(permissions), ex=300)
        
        # Wildcard match
        for p in permissions:
            if self._matches(p, permission):
                return True
        return False
    
    def _matches(self, granted: str, required: str) -> bool:
        """Wildcard match: 'platform.*' matches 'platform.users.create'"""
        if granted == required:
            return True
        if granted.endswith(".*"):
            prefix = granted[:-2]
            return required.startswith(prefix + ".")
        return False
    
    async def get_user_permissions(self, user_id: int) -> list[str]:
        """Foydalanuvchining barcha ruxsatlarini qaytaradi"""
        return await self._load_permissions(user_id)
    
    async def assign_role(
        self, user_id: int, role_id: int, 
        scope_type: str = "global", scope_id: int | None = None,
        granted_by: int | None = None,
    ):
        await self.repo.create_user_role(
            user_id=user_id, role_id=role_id,
            scope_type=scope_type, scope_id=scope_id,
            granted_by=granted_by,
        )
        # Cache'ni tozalash
        await self.redis.delete(f"perms:{user_id}")
```

## Frontend RBAC

### Permission composable

```typescript
// composables/usePermissions.ts
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  const auth = useAuthStore()
  
  const permissions = computed(() => auth.user?.permissions ?? [])
  
  function hasPermission(permission: string): boolean {
    if (!auth.user) return false
    
    // Wildcard match
    return permissions.value.some(p => {
      if (p === permission) return true
      if (p.endsWith('.*')) {
        const prefix = p.slice(0, -2)
        return permission.startsWith(prefix + '.')
      }
      return false
    })
  }
  
  function hasAnyPermission(perms: string[]): boolean {
    return perms.some(p => hasPermission(p))
  }
  
  function hasAllPermissions(perms: string[]): boolean {
    return perms.every(p => hasPermission(p))
  }
  
  return { permissions, hasPermission, hasAnyPermission, hasAllPermissions }
}
```

### v-permission directive

```typescript
// directives/permission.ts
import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

export const vPermission: Directive = {
  mounted(el, binding) {
    const auth = useAuthStore()
    const permission = binding.value as string
    
    const has = auth.user?.permissions.some(p => 
      p === permission || (p.endsWith('.*') && permission.startsWith(p.slice(0, -2)))
    )
    
    if (!has) {
      el.style.display = 'none'
    }
  }
}
```

```vue
<!-- Ishlatish -->
<button v-permission="'course.create'">Yangi kurs</button>
```

### Router guard

```typescript
// router/guards.ts
import { useAuthStore } from '@/stores/auth'

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  
  // Auth required
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }
  
  // Permission required
  if (to.meta.permission) {
    const has = auth.user?.permissions.some(p => 
      p === to.meta.permission
    )
    if (!has) {
      return next({ name: 'forbidden' })
    }
  }
  
  next()
})
```

## Default rollar (seed)

```python
# scripts/seed_roles.py

DEFAULT_ROLES = [
    {
        "code": "super_admin",
        "name": "Super Administrator",
        "permissions": ["platform.*"],
    },
    {
        "code": "otm_admin",
        "name": "OTM Administratori",
        "permissions": [
            "org.*",
            "users.manage",
            "courses.manage",
            "reports.view",
        ],
    },
    {
        "code": "dean",
        "name": "Dekan",
        "permissions": [
            "faculty.read",
            "faculty.students.manage",
            "faculty.curriculum.manage",
            "faculty.reports.view",
        ],
    },
    {
        "code": "department_head",
        "name": "Kafedra mudiri",
        "permissions": [
            "department.read",
            "department.teachers.manage",
            "department.subjects.manage",
        ],
    },
    {
        "code": "teacher",
        "name": "Pedagog",
        "permissions": [
            "course.edit",
            "course.content.create",
            "assignment.grade",
            "exam.create",
            "live.host",
        ],
    },
    {
        "code": "student",
        "name": "Talaba",
        "permissions": [
            "course.read",
            "assignment.submit",
            "exam.attempt",
            "live.join",
            "profile.edit",
            "payment.view",
        ],
    },
    {
        "code": "tsdin_inspector",
        "name": "TSDIN nazoratchisi",
        "permissions": [
            "monitoring.read.*",
            "audit.read.*",
            "reports.read.*",
        ],
    },
]
```

## Acceptance kriteriyalar

- [ ] Profil ko'rish va tahrirlash
- [ ] Avatar yuklash
- [ ] Foydalanuvchilar ro'yxati (filter, search, pagination)
- [ ] Yangi foydalanuvchi yaratish
- [ ] Rollar va ruxsatlar boshqaruvi
- [ ] Custom rollar yaratish (OTM darajasida)
- [ ] Bulk import (CSV)
- [ ] Bulk eksport
- [ ] RBAC backend va frontend
- [ ] 1:50 oqituvchi-talaba nisbati validatsiyasi
- [ ] Audit logi
- [ ] Test coverage ≥ 85%
