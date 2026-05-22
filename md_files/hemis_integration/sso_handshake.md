# HEMIS SSO — administrator handshake instruktsiyasi

**Phase 10e** texnik tomondan to'liq tayyor. Production'da ishlash uchun HEMIS
markaziy admin tomonidan quyidagi konfiguratsiya bajarilishi kerak.

## 1. Talab qilinadigan ma'lumotlar

XIU LMS'ni HEMIS SSO partner sifatida ro'yxatga olish uchun HEMIS admin'iga
quyidagi ma'lumotlarni yuboring:

| Parametr | Qiymat |
|----------|--------|
| **Target code** | `lms` |
| **Display name** | `XIU LMS — Masofaviy ta'lim platformasi` |
| **Callback URL** | `https://lms.xiuedu.uz/auth/sso/callback` |
| **Token validation method** | Server-to-server: `GET /v1/account/me` with `Authorization: Bearer <sso_token>` |
| **Token TTL** | 300 sekund (HEMIS taqdim qiladi, biz tekshirmaymiz) |
| **Allowed referrer domains** | `student.xiuedu.uz`, `hemis.uz` (HEMIS portal) |

## 2. HEMIS administratoriga so'rov maktubi (namuna)

```
Mavzu: HEMIS SSO target ro'yxatdan o'tkazish — XIU LMS

Hurmatli HEMIS administratsiyasi,

Xalqaro Innovatsiya Universiteti (XIU) o'zining masofaviy ta'lim platformasini
HEMIS bilan to'liq integratsiya qilish maqsadida SSO partner sifatida
ro'yxatdan o'tishni so'raydi.

Texnik parametrlar:
  - Target identifier: lms
  - Display name: "XIU LMS"
  - Callback URL: https://lms.xiuedu.uz/auth/sso/callback
  - Token validation: GET /v1/account/me (Authorization: Bearer <sso_token>)

Talabalar HEMIS portalida login bo'lib turib, "LMS'ga o'tish" tugmasi orqali
bizning platformaga avtomatik kirishlari uchun:
  1. HEMIS-da `target=lms` ro'yxatdan o'tkazish
  2. /v1/sso/targets API natijalariga "lms" entry qo'shish
  3. /v1/sso/get-redirect-url?target=lms ishlay boshlashi

So'rovingizga javob bering yoki tegishli hujjatni yuboring.

Hurmat bilan,
XIU LMS Texnik jamoasi
```

## 3. HEMIS-side flow (qaytarib eslatma)

```
Talaba portal.hemis.uz da login bo'lgan
   ↓
"XIU LMS'ga o'tish" tugmasi
   ↓
HEMIS server: GET /v1/sso/get-redirect-url?target=lms
   (Auth: Bearer student_jwt)
   ↓
HEMIS qaytaradi:
   {
     "data": {
       "redirect_url": "https://lms.xiuedu.uz/auth/sso/callback?sso_token=<JWT>",
       "target": "lms",
       "expires_in": 300
     }
   }
   ↓
HEMIS browser'ni 302 redirect qiladi redirect_url-ga
   ↓
Bizning frontend: /auth/sso/callback?sso_token=<JWT> sahifa
   ↓
Frontend: POST /api/v1/auth/sso/hemis { sso_token }
   ↓
Backend: GET https://student.xiuedu.uz/rest/v1/account/me
   (Authorization: Bearer <sso_token>)
   ↓
HEMIS Student profili qaytaradi (id, full_name, group, faculty, ...)
   ↓
Backend: upsert_student(profile) — User+Profile yaratiladi/yangilanadi
   ↓
Backend: LMS JWT chiqaradi va frontend'ga qaytaradi
   ↓
Frontend: tokenni saqlaydi, /app/dashboard ga redirect
```

## 4. Test scenariolari (handshake-dan keyin)

### 4.1 Happy path
1. Talaba `https://student.xiuedu.uz` ga login qiladi (HEMIS portal)
2. HEMIS portalda "LMS'ga o'tish" tugmasi (HEMIS UI'da admin tomonidan qo'shilgan)
3. Bosadi → bizga 302 redirect bilan keladi `?sso_token=...`
4. **Kutilgan:** 2-3 sekund ichida `/app/dashboard` ochiladi, talaba login bo'lgan

### 4.2 Token expire
1. Tokenni saqlab, 5+ daqiqa kutgandan keyin URL'ga kirish
2. **Kutilgan:** "HEMIS SSO token yaroqsiz yoki muddati o'tgan" xato

### 4.3 Token tampered
1. URL'dagi `sso_token`-ni 1 belgi bilan o'zgartirish
2. **Kutilgan:** "HEMIS rad qildi: Token yaroqsiz" xato

### 4.4 Re-login
1. Birinchi marta SSO orqali kirgan talaba
2. Ikkinchi marta kelganda — `upsert_student` mavjud userni topadi va yangilaydi
3. **Kutilgan:** ortiqcha user yaratilmaydi, bir xil `user.id`

## 5. Production checklist

- [ ] HEMIS admin `target=lms` ro'yxatga olgan
- [ ] HEMIS portal UI'da "XIU LMS" tugmasi qo'shilgan
- [ ] `HEMIS_API_URL` env: `https://student.xiuedu.uz/rest`
- [ ] `HEMIS_MODE=real` (mock emas!)
- [ ] HTTPS aktiv `lms.xiuedu.uz` da (callback URL HTTPS bo'lishi shart)
- [ ] CORS settings'da `origin: https://student.hemis.uz, https://student.xiuedu.uz` qo'shilgan
- [ ] Backend `cors_origins_list` env'da bor
- [ ] Test scenariolari (4.1-4.4) muvaffaqiyatli o'tdi
- [ ] HemisSyncLog admin viewer (Phase 8f.4)'da test sync yozuvlari ko'rinadi

## 6. Fallback flow (agar SSO ishlamasa)

Talaba SSO orqali kira olmasa, eski "HEMIS proxy login" yo'li mavjud:

```
LMS login sahifa → "Sign in with HEMIS" tugmasi → /auth/login/hemis
   → Talaba HEMIS ID + parol kiritadi (NOT email)
   → Backend → HEMIS API → JWT olib upsert_student → LMS JWT
```

Bu Phase 10d-da tayyor (10e bilan parallel).

## 7. Phase 10e — texnik tafsilotlar

### Backend
- Endpoint: `POST /api/v1/auth/sso/hemis { sso_token }`
- Service: `app/modules/auth/hemis_login.py::login_via_hemis_sso`
- Token validation: `HemisClient.account_me(sso_token)` (mock yoki real)
- User upsert: `upsert_student` (Phase 10b)
- Token cache: `HemisTokenCache.set_student` (Phase 10c)
- Default role: `student` (idempotent)

### Frontend
- Route: `/auth/sso/callback`
- View: `src/user/views/auth/SsoCallbackView.vue`
- Store method: `useAuthStore().ssoHemis(ssoToken)`
- API client: `authApi.ssoHemis(ssoToken)`

### Tests
- Unit: `tests/unit/test_hemis_client.py::test_sso_token_validates_via_account_me`
- E2E (manual): `node sso-debug.mjs` puppeteer script
