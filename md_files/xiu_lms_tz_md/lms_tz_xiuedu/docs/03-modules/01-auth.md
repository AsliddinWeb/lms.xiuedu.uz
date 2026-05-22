# 01. Auth Moduli (Autentifikatsiya)

## Maqsad

Foydalanuvchilarni xavfsiz autentifikatsiyalash, sessiya boshqarish, parol va 2FA boshqaruvi.

## Funksional talablar

### 1. Ro'yxatdan o'tish va kirish usullari

| Usul | Tavsifi |
|------|---------|
| Email + parol | Klassik usul |
| Telefon + SMS OTP | Tez kirish |
| OneID (SSO) | Yagona Identifikatsiya orqali |
| Hemis SSO | Hemis akkaunt orqali |
| Google OAuth | Xorijiy talabalar uchun (ixtiyoriy) |

### 2. Tokenlar (JWT)

**Access Token:**
- Davomiyligi: 15 daqiqa
- Payload: `user_id`, `role`, `permissions`, `tenant_id`, `exp`, `iat`, `jti`
- Algoritm: RS256 (asymmetric)

**Refresh Token:**
- Davomiyligi: 7 kun
- Httpolny secure cookie
- Redis'da saqlanadi (rotatable)
- Bekor qilish (revoke) imkoniyati

### 3. 2FA (Ikki bosqichli autentifikatsiya)

- **TOTP** (Google Authenticator, Authy)
- **SMS OTP** (Eskiz.uz orqali)
- **Backup kodlar** (10 ta, bir martalik)
- Ixtiyoriy yoki majburiy (admin sozlashi)

### 4. Parol boshqaruvi

- Minimum 10 belgi
- Harf + raqam + maxsus belgi
- Bcrypt hashing (cost: 12)
- Parol tarixi: oxirgi 5 ta saqlanadi (qayta ishlatishni taqiqlash)
- Parolni unutdingizmi? — email orqali tiklash (1 marta token)

### 5. Brute-force himoya

- 5 ta noto'g'ri urinish → 15 daqiqa bloklash
- IP-based rate limiting (Redis)
- Captcha (3-urinishdan keyin)

### 6. Sessiya boshqaruvi

- Active session ro'yxati
- Boshqa qurilmadan chiqish ("Logout from all devices")
- Geo va qurilma ma'lumotlari
- Audit log

## API Endpoints

```
POST   /api/v1/auth/register              # Ro'yxatdan o'tish
POST   /api/v1/auth/login                 # Kirish (email/phone + password)
POST   /api/v1/auth/login/oneid           # OneID orqali
POST   /api/v1/auth/login/hemis           # Hemis SSO
POST   /api/v1/auth/refresh               # Token yangilash
POST   /api/v1/auth/logout                # Chiqish
POST   /api/v1/auth/logout-all            # Hamma qurilmadan chiqish

POST   /api/v1/auth/verify-email          # Email tasdiqlash (token)
POST   /api/v1/auth/resend-verification   # Tasdiqlash kodini qayta yuborish

POST   /api/v1/auth/forgot-password       # Parolni unutdim
POST   /api/v1/auth/reset-password        # Parolni tiklash (token)
POST   /api/v1/auth/change-password       # Parolni o'zgartirish (logged-in)

POST   /api/v1/auth/2fa/enable            # 2FA yoqish (TOTP secret)
POST   /api/v1/auth/2fa/verify            # 2FA tasdiqlash
POST   /api/v1/auth/2fa/disable           # 2FA o'chirish
GET    /api/v1/auth/2fa/backup-codes      # Backup kodlar olish
POST   /api/v1/auth/2fa/regenerate        # Backup kodlarni yangilash

GET    /api/v1/auth/sessions              # Active sessions
DELETE /api/v1/auth/sessions/{id}         # Boshqa sessiyani o'chirish

GET    /api/v1/auth/me                    # Joriy foydalanuvchi
```

## Database modellari

### users
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(200) NOT NULL,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    totp_secret VARCHAR(255),               -- shifrlangan
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    last_login_ip INET,
    tenant_id BIGINT REFERENCES organizations(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_tenant ON users(tenant_id);
```

### user_sessions
```sql
CREATE TABLE user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON user_sessions(refresh_token_hash);
```

### password_reset_tokens
```sql
CREATE TABLE password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### email_verification_tokens
```sql
CREATE TABLE email_verification_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### backup_codes
```sql
CREATE TABLE backup_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    code_hash VARCHAR(255) NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### login_attempts (audit)
```sql
CREATE TABLE login_attempts (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255),
    user_id BIGINT,
    ip_address INET NOT NULL,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_login_attempts_email ON login_attempts(email, created_at DESC);
CREATE INDEX idx_login_attempts_ip ON login_attempts(ip_address, created_at DESC);
```

## Pydantic sxemalar

```python
# app/modules/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=100)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Parolda kamida 1 ta katta harf bo'lishi kerak")
        if not any(c.isdigit() for c in v):
            raise ValueError("Parolda kamida 1 ta raqam bo'lishi kerak")
        if not any(c in "!@#$%^&*()_+-=" for c in v):
            raise ValueError("Parolda kamida 1 ta maxsus belgi bo'lishi kerak")
        return v

class LoginRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str
    totp_code: str | None = None  # 2FA bo'lsa

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    avatar_url: str | None
    is_2fa_enabled: bool
    role: str
    permissions: list[str]
    
    model_config = {"from_attributes": True}
```

## Service implementatsiyasi

```python
# app/modules/auth/service.py
from datetime import datetime, timedelta
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token,
)

class AuthService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis
    
    async def register(self, data: RegisterRequest) -> User:
        # Email mavjudligini tekshirish
        if await self.repo.get_by_email(data.email):
            raise UserAlreadyExistsError()
        
        # Parolni hash qilish
        password_hash = hash_password(data.password)
        
        # Userni yaratish
        user = await self.repo.create(User(
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
            phone=data.phone,
        ))
        
        # Verification email yuborish (Celery task)
        from app.workers.email import send_verification_email
        send_verification_email.delay(user.id)
        
        return user
    
    async def login(
        self, data: LoginRequest, ip: str, user_agent: str
    ) -> TokenResponse:
        # Brute-force tekshiruvi
        await self._check_rate_limit(data.email, ip)
        
        # Userni topish
        user = await self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            await self._record_failed_attempt(data.email, ip)
            raise InvalidCredentialsError()
        
        # 2FA tekshiruvi
        if user.is_2fa_enabled:
            if not data.totp_code:
                raise TwoFactorRequiredError()
            if not self._verify_totp(user.totp_secret, data.totp_code):
                raise InvalidTotpError()
        
        # Tokenlarni yaratish
        access = create_access_token(user.id, user.role)
        refresh = create_refresh_token(user.id)
        
        # Sessiyani saqlash
        await self.repo.create_session(
            user_id=user.id,
            refresh_token=refresh,
            ip=ip,
            user_agent=user_agent,
        )
        
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=15 * 60,
        )
```

## Frontend implementatsiyasi

### Login sahifa

```vue
<!-- src/views/auth/LoginView.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const email = ref('')
const password = ref('')
const totpCode = ref('')
const requires2FA = ref(false)
const isLoading = ref(false)

async function handleLogin() {
  isLoading.value = true
  try {
    await auth.login({
      email: email.value,
      password: password.value,
      totp_code: totpCode.value || undefined,
    })
    router.push('/dashboard')
  } catch (err: any) {
    if (err.response?.data?.code === 'TWO_FACTOR_REQUIRED') {
      requires2FA.value = true
    } else {
      toast.error(err.response?.data?.detail || 'Kirish xatoligi')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-md bg-white p-8 rounded-lg shadow">
      <h1 class="text-2xl font-bold mb-6">Tizimga kirish</h1>
      <form @submit.prevent="handleLogin" class="space-y-4">
        <Input v-model="email" type="email" placeholder="Email" required />
        <Input v-model="password" type="password" placeholder="Parol" required />
        
        <Input
          v-if="requires2FA"
          v-model="totpCode"
          placeholder="2FA kod (6 raqam)"
          maxlength="6"
        />
        
        <Button type="submit" :loading="isLoading" class="w-full">
          Kirish
        </Button>
        
        <div class="text-sm text-center">
          <RouterLink to="/forgot-password" class="text-blue-600">
            Parolni unutdingizmi?
          </RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>
```

## Xavfsizlik talablari

- ✅ Parolni hech qachon plain-text saqlamang
- ✅ JWT secret faqat .env'da
- ✅ HTTPS only (production)
- ✅ HttpOnly + Secure + SameSite cookies
- ✅ CSRF token (form-based requests)
- ✅ Rate limiting (login, register, reset)
- ✅ Audit log barcha auth hodisalari
- ✅ Tokenlarni blacklist (logout)
- ✅ Token rotation (refresh)

## Test stsenariylari

```python
# tests/unit/auth/test_service.py

class TestAuthService:
    async def test_register_success(self): ...
    async def test_register_duplicate_email(self): ...
    async def test_register_weak_password(self): ...
    async def test_login_success(self): ...
    async def test_login_invalid_credentials(self): ...
    async def test_login_locked_account(self): ...
    async def test_login_with_2fa(self): ...
    async def test_login_wrong_totp(self): ...
    async def test_refresh_token(self): ...
    async def test_refresh_token_revoked(self): ...
    async def test_password_reset_flow(self): ...
    async def test_brute_force_protection(self): ...
```

## Acceptance kriteriyalar

- [ ] Register, login, logout ishlaydi
- [ ] JWT tokenlar to'g'ri yaratiladi va yangilanadi
- [ ] 2FA TOTP qo'shilgan va testlangan
- [ ] Brute-force himoyasi ishlaydi (5 urinish → 15 daqiqa)
- [ ] Email verifikatsiya
- [ ] Parolni tiklash flow
- [ ] OneID integratsiyasi
- [ ] Hemis SSO integratsiyasi
- [ ] Audit logi to'liq
- [ ] Frontend login/register sahifalari
- [ ] Test coverage ≥ 90%
- [ ] OpenAPI doc to'liq
