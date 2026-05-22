# 03. OneID Integratsiyasi

## Maqsad

OneID — O'zbekistondagi yagona identifikatsiya tizimi. Foydalanuvchilar OneID akkaunti orqali tezda kira oladi.

## Texnik tafsilotlar

- Protokol: **OAuth 2.0** + **OpenID Connect**
- Endpoint: `https://sso.egov.uz` (yoki test: `https://sso-test.egov.uz`)
- Grant type: Authorization Code

## Sozlash

### 1. OneID'da ariza
- Texnik direktorlik orqali ariza topshiriladi
- `client_id` va `client_secret` olinadi
- Redirect URI ro'yxatdan o'tkaziladi

### 2. Atributlar (scope)
- `id` — yagona ID
- `pinfl` — JSHSHIR
- `passport_no`, `passport_serial`
- `birth_date`
- `full_name`
- `gender`
- `phone`
- `email`
- `address`

### 3. Maxfiy ma'lumotlar (.env)

```env
ONEID_CLIENT_ID=xxx
ONEID_CLIENT_SECRET=xxx
ONEID_REDIRECT_URI=https://lms.xiuedu.uz/auth/oneid/callback
ONEID_BASE_URL=https://sso.egov.uz
```

## Implementatsiya

### Auth flow

```
1. Talaba "Login with OneID" tugmasini bosadi
2. → Bizning backend `/auth/oneid/login` redirect qiladi
3. → OneID sahifasi → talaba kiradi
4. → OneID `code` bilan bizning `/auth/oneid/callback` ga redirect
5. Bizning backend `code` ni `access_token` ga almashtiradi
6. `access_token` orqali user info olinadi
7. JWT yaratiladi va frontend'ga qaytariladi
```

### Client

```python
# app/integrations/oneid/client.py
import httpx
from urllib.parse import urlencode
from app.core.config import settings


class OneIdClient:
    BASE_URL = settings.ONEID_BASE_URL
    
    def __init__(self):
        self.client_id = settings.ONEID_CLIENT_ID
        self.client_secret = settings.ONEID_CLIENT_SECRET
        self.redirect_uri = settings.ONEID_REDIRECT_URI
    
    def get_authorize_url(self, state: str) -> str:
        """Talabani bu URL'ga redirect qilamiz"""
        params = {
            "response_type": "one_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid profile email",
            "state": state,
        }
        return f"{self.BASE_URL}/sso/oauth/Authorization.do?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> dict:
        """Code → Access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/sso/oauth/Authorization.do",
                data={
                    "grant_type": "one_authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
            )
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict:
        """User ma'lumotlari"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/sso/oauth/Authorization.do",
                data={
                    "grant_type": "one_access_token_identify",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "access_token": access_token,
                    "scope": "openid profile email",
                },
            )
            return response.json()
```

### Endpoints

```python
# app/api/v1/auth/oneid.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
import secrets
import urllib.parse

router = APIRouter(prefix="/auth/oneid", tags=["auth"])


@router.get("/login")
async def oneid_login(request: Request):
    """OneID'ga redirect"""
    # CSRF himoyasi uchun state
    state = secrets.token_urlsafe(32)
    request.session["oneid_state"] = state
    
    client = OneIdClient()
    auth_url = client.get_authorize_url(state)
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oneid_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Callback handler"""
    if error:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error={error}"
        )
    
    # State tekshirish
    saved_state = request.session.get("oneid_state")
    if not saved_state or saved_state != state:
        raise HTTPException(400, "Invalid state")
    
    if not code:
        raise HTTPException(400, "No code provided")
    
    # Code → Access token
    client = OneIdClient()
    token_data = await client.exchange_code(code)
    access_token = token_data.get("access_token")
    
    if not access_token:
        raise HTTPException(401, "Failed to get access token")
    
    # User info
    user_info = await client.get_user_info(access_token)
    
    # User'ni topish yoki yaratish
    user = await find_or_create_user_by_oneid(user_info)
    
    # JWT yaratish
    jwt_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)
    
    # Frontend'ga redirect (token bilan)
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}&refresh={refresh_token}"
    )


async def find_or_create_user_by_oneid(info: dict) -> User:
    """OneID ma'lumotlari asosida user topish/yaratish"""
    pinfl = info.get("pin")  # PINFL
    
    # Avval PINFL bo'yicha topish
    user = await db.execute(
        select(User).join(Profile).where(Profile.pinfl == pinfl)
    ).scalar_one_or_none()
    
    if user:
        # Avtomatik tasdiqlash
        if not user.is_verified:
            user.is_verified = True
            await db.commit()
        return user
    
    # Yangi user yaratish
    user = User(
        email=info.get("email") or f"{pinfl}@oneid.local",
        full_name=info.get("full_name", ""),
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    
    # Profile
    profile = Profile(
        user_id=user.id,
        pinfl=pinfl,
        passport_series=info.get("pport_issue_place"),
        passport_number=info.get("pport_no"),
        birthdate=parse_date(info.get("birth_date")),
        gender=info.get("sex"),
    )
    db.add(profile)
    await db.commit()
    
    # OneID linkini saqlash
    oneid_link = OneIdLink(
        user_id=user.id,
        oneid_id=info.get("user_id"),
    )
    db.add(oneid_link)
    await db.commit()
    
    return user
```

## Database

```sql
-- OneID bog'lanish
CREATE TABLE oneid_links (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    oneid_id VARCHAR(100) UNIQUE NOT NULL,
    pinfl VARCHAR(14),
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Frontend

```vue
<!-- views/auth/LoginView.vue (qisman) -->
<template>
  <div class="space-y-4">
    <Button @click="loginWithOneId" variant="outline" class="w-full">
      <img src="/icons/oneid.svg" class="w-5 h-5 mr-2" />
      OneID orqali kirish
    </Button>
  </div>
</template>

<script setup lang="ts">
function loginWithOneId() {
  window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/oneid/login`
}
</script>
```

## Acceptance kriteriyalar

- [ ] OAuth flow ishlaydi
- [ ] Foydalanuvchi avtomatik yaratiladi
- [ ] PINFL bo'yicha mavjud user'ni topadi
- [ ] State (CSRF) himoyasi
- [ ] Test va production muhitlar
- [ ] Xatolarni handle qilish
- [ ] Test coverage ≥ 70%
