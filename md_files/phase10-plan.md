# Phase 10 — Davlat integratsiyalari (yangilangan reja)

**Status:** Planning (Phase 1-9 + 8 polish yakunlangan, hozir bu)
**Boshlanish:** 2026-05-21
**559-son qaror talabi:** HEMIS, OTJBAT, TSDIN MAJBURIY

## Hozirgi muammo

1. **Email-first identity** — `users.email NOT NULL UNIQUE`. HEMIS-da `id` primary, `email` optional.
2. **Mock HEMIS** — `app/integrations/hemis/client.py` faqat skeleton, real API chaqirmaydi.
3. **HemisLoginView** — bizning UI'da HEMIS credential terish (proxy). Aslida HEMIS SSO mavjud
   (`GET /v1/sso/get-redirect-url?target=lms`).
4. **Data sync yo'q** — talaba, guruh, fakultet, fan ma'lumotlari HEMIS-dan kelmaydi.

## Yechim — HEMIS-first arxitektura

Hammasi `md_files/hemis_integration/` papkasidagi 3 ta hujjatga asoslangan:
- `README.md` — auth flow + overview
- `endpoints.md` — 255 endpoint reference
- `schema_mapping.md` — DB migratsiya rejasi

## Sub-fazalar

### ✅ 10a — Audit + dokumentatsiya (yakunlangan)

- HEMIS OpenAPI yuklab olish (379KB JSON)
- 3 ta MD hujjat yozish
- 255 endpoint kategoriyalash

### 10b — Models refactor (HEMIS-first identity) ← **boshlanadi**

**DB Migration:**
- `users`: `hemis_id` (UQ+IDX), `hemis_login` (UQ), `pinfl` (UQ), `hemis_data_hash`, `hemis_last_synced_at`
- `users.email` → NULLABLE + partial unique index (`WHERE email IS NOT NULL`)
- `users`: `group_id`, `current_semester_id`, `education_form`, `payment_form`, `student_status`
- `profiles`: `social_category`, `poverty_level`, `accommodation`, `academic_degree`, `academic_title`, `country`, `region`, `district`
- Yangi jadval: `academic_groups` (HEMIS Group)
- Yangi jadval: `academic_semesters`
- Yangi jadval: `hemis_classifiers` (kichik registr)
- `faculties` ga `hemis_id`, `hemis_code`, `hemis_parent_id`, `structure_type`, `locality_type`
- `specialties` ga `hemis_code`
- `curricula` ga `hemis_id`, `specialty_hemis_code`

**Service refactor:**
- `app/modules/auth/service.py` — `authenticate_by_hemis_login()` primary, email fallback
- `app/modules/users/service.py` — `get_or_create_from_hemis_student(data)`, `get_or_create_from_hemis_employee(data)`
- `app/modules/users/service.py` — lookup order: hemis_id → hemis_login → pinfl → email
- Pydantic: `UserCreateRequest.email: str | None = None`, `UserPublic.hemis_id`

**Tests:**
- Email-less user yaratish
- HEMIS hash drift detection
- Old user email migration (existing users get HEMIS sync)

**Vaqt:** 1-2 kun.

### 10c — HEMIS API client to'liq qayta yozish

**`app/integrations/hemis/client.py`:**
- Async httpx wrapper (real + mock mode env switch)
- 35+ endpoint method: `student_login()`, `account_me()`, `subject_list(student_id)`, `schedule()`, `gpa_list()`, `attendance()`, `employee_list()`, `student_list()`, `department_list()`, `group_list()`, `curriculum_list()`, etc.
- JWT cache (Redis) + auto refresh on 401
- Audit log integration (HemisSyncLog model — Phase 7e da bor)
- Retry (exponential backoff) — Phase 7e retry.py allaqachon bor
- Rate limit handling (429 ga sabr)

**Tests:**
- Mock responses (vcrpy yoki pytest-httpx)
- Real-mode smoke (.env.local sozlanganda)

**Vaqt:** 2-3 kun.

### 10d — HEMIS Login (proxy) + LMS JWT bridging

**Backend:**
- `POST /api/v1/auth/hemis-login { hemis_login, password }` — HEMIS API `/v1/auth/login` ga proxy
- Tokenni cookie/session-da saqlamaymiz — faqat keyingi sync uchun (Redis-da TTL 30min)
- LMS JWT yaratish + return

**Frontend:**
- `HemisLoginView.vue` qayta dizayn — field `hemis_login` (NOT email), placeholder
  "Talaba bilet raqami" yoki "PINFL"
- Default login sahifa: 2 ta tab — "HEMIS hisobim" va "Email/parol" (admin uchun)
- Email login faqat platform admin/dean uchun ko'rinadi

**Tests:**
- Mock HEMIS response 200 → LMS user create
- 401 HEMIS → 401 LMS
- Existing email-user → HEMIS sync (merge)

**Vaqt:** 1-2 kun.

### 10e — HEMIS SSO callback

Talaba HEMIS portalida bo'lib, "LMS'ga o'tish" tugmasini bosadi. HEMIS bizga
`?sso_token=...` bilan redirect qiladi.

**Backend:**
- `POST /api/v1/auth/hemis-sso { sso_token }` — sso_token-ni `/v1/account/me` chaqirib validate
- Token muddati 300s — fail bo'lsa 401
- User get_or_create_from_hemis_student → LMS JWT

**Frontend:**
- `/auth/sso/callback?sso_token=...` route — yangi view
- Token URL query-dan o'qiydi, backend'ga POST, JWT olib `/app/dashboard`-ga redirect

**HEMIS administrator bilan:**
- `target=lms` ro'yxatdan o'tkazish kerak
- Callback URL: `https://lms.xiuedu.uz/auth/sso/callback`
- Signing key (agar mavjud bo'lsa) almashish

**Tests:**
- Mock sso_token + mock HEMIS validate → user create
- Stale token → 401
- Cross-target (boshqa OTM) → 401

**Vaqt:** 1 kun (HEMIS admin tasdig'i kelganidan keyin).

### 10f — HEMIS data sync (admin scheduler)

**Sync job'lar:**
- `sync_students_job` — `/v1/data/student-list` har 24h
- `sync_employees_job` — `/v1/data/employee-list?type=employee` har 24h
- `sync_departments_job` — `/v1/data/department-list` har 7 kun
- `sync_groups_job` — `/v1/data/group-list` har 24h
- `sync_curricula_job` — `/v1/data/curriculum-list` har 7 kun
- `sync_subjects_job` — `/v1/data/curriculum-subject-list` har 7 kun

**Conflict resolution:**
- HEMIS authoritative — `hemis_data_hash` o'zgarsa update
- Local-only fields (LMS-specific) yo'qotilmaydi
- Email mismatch — HEMIS authoritative agar HEMIS'da to'ldirilgan, aks holda local saqlanadi

**Scheduler:**
- APScheduler (Celery overkill bizning kichik scale uchun)
- Yoki `/api/v1/admin/sync/run` endpoint — admin qo'lda trigger qila oladi
- HemisSyncLog'da har sync yozuvi (Phase 7e model)
- Admin UI (Phase 8f HemisSyncLogView) — failed sync'ni Retry tugmasi

**Tests:**
- Sync delta detection (only changed records)
- Concurrent sync lock (Redis lock)
- Error reporting + audit log

**Vaqt:** 2-3 kun.

### 10g — Tutor (pedagog) API integration

Pedagog HEMIS API-dan o'z guruh ma'lumotlarini olishi mumkin.

**Backend:**
- `POST /api/v1/auth/hemis-tutor-login { hemis_login, password, recaptcha }` — `/ver1/tutor/auth/login`-ga proxy
- Pedagog dashboard'da yangi widget'lar:
  - HEMIS guruh ro'yxati (`/ver1/tutor/profile/groups`)
  - Guruh talabalari (`/ver1/tutor/group/students`)
  - Davomat HEMIS-dan (`/ver1/tutor/attendance/by-subject`)
  - GPA HEMIS-dan (`/ver1/tutor/grade/gpa`)
  - HEMIS xabarlar (`/ver1/tutor/message/*`)

**Frontend:**
- reCAPTCHA v3 integration (Google site key kerak)
- Pedagog tabi: "HEMIS ma'lumotlari" — read-only widget'lar

**Vaqt:** 2 kun.

## ✅ Phase 10 — yakunlangan (2026-05-21)

10a–10g barcha sub-fazalar bajarildi. Qolgan integratsiyalar **scope'dan
chiqarildi** (LMS biznes funksiyasi emas yoki XIU yangi OTM uchun
hozircha ahamiyatsiz). Quyidagilar **bekor qilindi**:

### ❌ 10h — Click to'lov
**Sabab (foydalanuvchi qarori):** LMS to'lov bilan shug'ullanmaydi. To'lov alohida
mahsuldorlik tizimida — kontrakt to'lovi XIU buxgalteriya/CRM tomonida yuritiladi.
LMS faqat akademik jarayon.

### ❌ 10i — Payme to'lov
**Sabab:** Click bilan bir xil (yuqorida).

### ❌ E-IMZO
**Sabab:** XIU yangi OTM — bitiruvchi yo'q, diplom muammosi 4 yildan keyin.
Browser plugin UX murakkab. Hozircha qog'oz kontrakt yetarli yuridik kuchga ega.

### ❌ OTJBAT
**Sabab:** Rasmiy API docs hozircha mavjud emas. HEMIS allaqachon Vazirlikka
ma'lumot yetkazadi (HEMIS davlat tizimi). Qo'shimcha integratsiya ortiqcha
qo'shimcha qiymat bermaydi.

### ❌ TSDIN
**Sabab:** Akkreditatsiya jarayoni 5 yilda bir marta. XIU yangi OTM —
birinchi akkreditatsiya 2-3 yil keyin. Real-time API kerak emas.

## Total vaqt

- 10b → 10g: 8-12 kun ✅ **tugagan**
- 10h - 10l: scope'dan chiqarildi (alohida loyiha sifatida ko'rib chiqilishi mumkin)

## Risks

- **R1:** HEMIS administrator tasdig'i — 10e/10f/10g yarim qoladi
- **R2:** HEMIS API rate limit
- **R3:** Production data migration — mavjud email-only user'larni HEMIS bilan merge
- **R4:** E-IMZO browser plugin yoki SDK versiyasi — mac/linux uchun farq

## Boshlash tartibi

**1-bosqich:** 10b → 10c → 10d ✅ tugagan (HEMIS-first identity + API client + proxy login)
**2-bosqich:** 10e → 10f → 10g ✅ tugagan (SSO + data sync + tutor)
**3-bosqich:** ❌ scope'dan chiqarildi (to'lov, e-imzo, OTJBAT, TSDIN)

**Phase 10 to'liq yakunlandi.** Keyingi: **Phase 11** (SCORM, Communications, Sertifikat, Gamification).
