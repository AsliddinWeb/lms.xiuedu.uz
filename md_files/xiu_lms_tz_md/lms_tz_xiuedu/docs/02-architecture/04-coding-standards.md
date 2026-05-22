# 04. Kod Standartlari (Coding Standards)

## Umumiy tamoyillar

1. **DRY** (Don't Repeat Yourself)
2. **KISS** (Keep It Simple, Stupid)
3. **YAGNI** (You Aren't Gonna Need It)
4. **SOLID** prinsiplar
5. **Self-documenting code** > kommentariyalar
6. **Test first** (TDD ixtiyoriy, lekin test majburiy)

## Backend (Python) standartlari

### Format va lint

```bash
# Format
black app/ tests/

# Lint
ruff check app/ tests/ --fix

# Type check
mypy app/
```

### Naming konvensiyalar

```python
# Klass nomlari — PascalCase
class UserRepository:
    pass

# Funksiya va o'zgaruvchilar — snake_case
def get_user_by_id(user_id: int) -> User:
    return user

# Konstantalar — UPPER_SNAKE_CASE
MAX_LOGIN_ATTEMPTS = 5
DEFAULT_PAGE_SIZE = 20

# Maxfiy (private) — _underscore prefix
def _internal_helper():
    pass

# Type aliaslar
UserId = int
type UserList = list[User]  # Python 3.12+
```

### Type hints majburiy

```python
# ❌ YOMON
def get_user(id):
    return db.query(User).filter(User.id == id).first()

# ✅ YAXSHI
async def get_user(user_id: int, db: AsyncSession) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

### Async/await majburiy (I/O uchun)

```python
# ❌ YOMON — sync DB chaqiruv
@router.get("/users/{user_id}")
def get_user(user_id: int):
    return db.query(User).get(user_id)

# ✅ YAXSHI — async
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user
```

### Pydantic sxemalari

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    full_name: str = Field(min_length=2, max_length=200)

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Repository pattern

```python
# app/modules/users/repository.py
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.db.add(user)
        await self.db.flush()
        return user
```

### Service pattern (business logic)

```python
# app/modules/users/service.py
class UserService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    async def register(self, data: UserCreate) -> User:
        # Business validatsiya
        if await self.repo.get_by_email(data.email):
            raise UserAlreadyExistsError()
        
        # Parolni hash qilish
        data.password = hash_password(data.password)
        
        # Saqlash
        user = await self.repo.create(data)
        
        # Email yuborish (async task)
        send_welcome_email.delay(user.id)
        
        return user
```

### Dependency injection

```python
# app/api/v1/deps.py
async def get_user_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> UserService:
    return UserService(UserRepository(db), redis)

# Endpoint
@router.post("/register")
async def register(
    data: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return await service.register(data)
```

### Error handling

```python
# Custom exceptions
class AppException(Exception):
    """Base exception"""
    status_code = 500
    detail = "Internal error"

class UserAlreadyExistsError(AppException):
    status_code = 409
    detail = "User with this email already exists"

# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

## Frontend (TypeScript) standartlari

### Format va lint

```bash
# Format
prettier --write src/

# Lint
eslint src/ --fix

# Type check
vue-tsc --noEmit
```

### Naming konvensiyalar

```typescript
// Komponent fayllari — PascalCase
// UserProfile.vue, LoginForm.vue

// Composable fayllari — camelCase, "use" prefiks
// useAuth.ts, usePermissions.ts

// Boshqa fayllar — kebab-case
// user-utils.ts, auth-api.ts

// Type/Interface — PascalCase
interface User {
  id: number
  fullName: string
}

type UserRole = 'student' | 'teacher' | 'admin'

// Variable, function — camelCase
const currentUser = ref<User | null>(null)
function getUserById(id: number): User { ... }

// Constants — UPPER_SNAKE_CASE
const MAX_FILE_SIZE = 5 * 1024 * 1024
```

### Vue 3 Composition API

```vue
<!-- ✅ YAXSHI — Composition API + <script setup> -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'

interface Props {
  userId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  saved: [user: User]
  cancelled: []
}>()

const { user, login } = useAuth()
const isLoading = ref(false)

const userName = computed(() => user.value?.fullName ?? 'Mehmon')

onMounted(async () => {
  // ...
})
</script>

<template>
  <div class="p-4">
    <h1>{{ userName }}</h1>
    <button @click="emit('cancelled')">Bekor</button>
  </div>
</template>
```

### Pinia store

```typescript
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  
  const isAuthenticated = computed(() => !!token.value)
  
  async function login(email: string, password: string) {
    const res = await api.auth.login({ email, password })
    user.value = res.user
    token.value = res.token
    localStorage.setItem('token', res.token)
  }
  
  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }
  
  return { user, token, isAuthenticated, login, logout }
})
```

### API klient

```typescript
// api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore().logout()
    }
    return Promise.reject(err)
  }
)

export default api
```

## Git konvensiyalari

### Branch strategiyasi (Git Flow yengillashtirilgan)

```
main             — production (himoyalangan)
develop          — keyingi release uchun
feature/xxx      — yangi funksiya
bugfix/xxx       — bug tuzatish
hotfix/xxx       — production xatolari
```

### Commit xabarlar (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Misollar:**
```
feat(auth): add 2FA via TOTP
fix(exam): correct timer drift on long exams
docs(api): update OpenAPI examples
refactor(users): extract repository pattern
test(courses): add integration tests for enrollment
chore(deps): upgrade FastAPI to 0.110
```

**Type'lar:**
- `feat` — yangi funksiya
- `fix` — bug tuzatish
- `docs` — hujjatlash
- `style` — formatlash
- `refactor` — refaktoring
- `test` — testlar
- `chore` — texnik ishlar
- `perf` — performance
- `ci` — CI/CD

### PR talablari

- Title: Conventional commit formati
- Description: nima qilindi, nima uchun
- Linked issue
- Screenshot (UI o'zgarishi bo'lsa)
- Tests: o'tdi
- Code review: kamida 1 approval
- No conflicts with target branch

## Test standartlari

### Backend testlar

```python
# tests/unit/users/test_service.py
import pytest
from app.modules.users.service import UserService

@pytest.mark.asyncio
async def test_register_creates_user(user_service, sample_user_data):
    # Arrange
    data = sample_user_data
    
    # Act
    user = await user_service.register(data)
    
    # Assert
    assert user.email == data.email
    assert user.id is not None

@pytest.mark.asyncio
async def test_register_duplicate_email_raises(user_service, existing_user):
    with pytest.raises(UserAlreadyExistsError):
        await user_service.register(UserCreate(
            email=existing_user.email,
            password="password123",
            full_name="Test"
        ))
```

### Frontend testlar

```typescript
// tests/unit/Button.spec.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '@/components/ui/Button.vue'

describe('Button', () => {
  it('emits click event', async () => {
    const wrapper = mount(Button, { slots: { default: 'Click' } })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
```

## Hujjatlash

### Backend — docstrings

```python
async def register(self, data: UserCreate) -> User:
    """
    Yangi foydalanuvchi ro'yxatdan o'tkazadi.
    
    Args:
        data: Foydalanuvchi ma'lumotlari
    
    Returns:
        Yaratilgan User obyekti
    
    Raises:
        UserAlreadyExistsError: Bu email bilan foydalanuvchi mavjud
    """
    ...
```

### Frontend — JSDoc

```typescript
/**
 * Foydalanuvchini autentifikatsiyalaydi
 * @param email - Email manzil
 * @param password - Parol (min 10 belgi)
 * @returns User obyekti va token
 * @throws AuthError — noto'g'ri credentials
 */
async function login(email: string, password: string): Promise<AuthResult> {
  // ...
}
```

## Code review checklist

- [ ] Kod ishlaydi (testlar o'tdi)
- [ ] Type hints to'liq
- [ ] Naming konvensiyalariga mos
- [ ] DRY — takrorlanish yo'q
- [ ] Error handling bor
- [ ] Tests qo'shilgan
- [ ] OpenAPI/JSDoc yangilangan
- [ ] No console.log / print
- [ ] No commented-out code
- [ ] Performance — N+1 query yo'q
- [ ] Security — SQL inject, XSS himoyasi
- [ ] i18n — hardcoded strings yo'q (frontend)
