# HEMIS Integration — OpenAPI Audit va Phase 10 Reja

**Manba:** https://student.xiuedu.uz/rest/docs.json
**OpenAPI:** 3.0.0 — HEMIS UNIVERSITY API v1.3
**Cached snapshot:** `hemis_openapi.json` (379 KB)
**Audit sanasi:** 2026-05-21
**Endpoint serverlari:**
- `https://student.xiuedu.uz/rest/` — XIU univetsiteti instance
- `https://student.hemis.uz/rest/` — markaziy HEMIS

---

## 1. Umumiy xulosa

HEMIS — O'zbekiston Vazirlar Mahkamasi tomonidan tasdiqlangan oliy ta'lim ma'lumotlar tizimi.
559-son qaror (2026-05-21 sanasiga ko'ra) talabiga muvofiq, har bir OTM o'z LMS'ini HEMIS bilan
integratsiya qilishi shart.

**Statistika:**
- 254 ta endpoint
- 91 ta schema
- 6 ta tag: Student API, Tutor API, Backend API, Public API, Fast API, Stat

**Bizning hozirgi muammo:**
1. ❌ Talaba/o'qituvchi `email` ustun primary identifier sifatida ishlatilmoqda.
   HEMIS'da `id` (integer) primary, `email` `nullable`.
2. ❌ Login `email + parol` orqali. Aslida HEMIS `student_id_number` (PINFL/talaba ID
   raqami) orqali login qiladi.
3. ⚠️ `HemisLoginView.vue` mavjud, lekin u proxy login form — talaba bizning UI'da
   HEMIS credential terib qoldi. Bu suboptimal: HEMIS-da haqiqiy SSO mexanizmi bor.
4. ❌ HEMIS API'dan ma'lumot sync (subjects, schedule, grades) — hozir mock.

---

## 2. Autentifikatsiya mexanizmlari

### 2.1 Student auth (oddiy)

```http
POST /v1/auth/login
Content-Type: application/json
{ "login": "999211100073", "password": "DD7777777" }

→ 200 OK
{ "success": true, "data": { "token": "uap4X5Bd7078lxIFvxAflcG..." } }
```

- `login` = `student_id_number` (talaba bilet raqami, **NOT email**)
- `token` — JWT, har keyingi so'rovda `Authorization: Bearer <token>`
- Refresh: `POST /v1/auth/refresh-token` (cookie-based)

### 2.2 Tutor auth (reCAPTCHA bilan)

```http
POST /ver1/tutor/auth/login
{ "login": "tutor_login", "password": "...", "reCaptcha": "03AF6jDq15..." }

→ { "data": { "token": "...", "refresh_token": "..." } }
```

`refresh_token` request body orqali qaytariladi — student auth'dan farqli o'laroq.

### 2.3 SSO (Single Sign-On) — **eng muhim**

HEMIS LMS uchun OAuth-stilidagi SSO mexanizmini taklif qiladi:

```http
GET /v1/sso/targets
Authorization: Bearer <student-jwt>

→ 200 OK
{ "data": [
    { "code": "career", "name": "Career.edu.uz", "description": "Karyera markazi" },
    { "code": "lms",    "name": "XIU LMS",      "description": "..." }
] }
```

```http
GET /v1/sso/get-redirect-url?target=lms
Authorization: Bearer <student-jwt>

→ 200 OK
{ "data": {
    "redirect_url": "https://lms.xiuedu.uz/auth/sso/callback?sso_token=eyJ...",
    "target": "lms",
    "expires_in": 300
} }
```

**Flow:**
1. Talaba HEMIS portalida login qilgan
2. HEMIS portalda "XIU LMS" tugmasini bosgan
3. HEMIS `/v1/sso/get-redirect-url?target=lms` chaqiradi → token+URL oladi
4. Talabani `redirect_url`-ga yo'naltiradi
5. Bizning callback `?sso_token=...`-ni qabul qiladi
6. Biz tokenni HEMIS API-ga validate qilamiz (`GET /v1/account/me` SSO-token bilan)
7. Bizning session/JWT yaratiladi

⚠️ **Kerak:** HEMIS administratoridan `target=lms` ro'yxatdan o'tkazish + signing key.

### 2.4 Backend API auth (admin sync uchun)

`bearerAuth` scheme — odatda OTM admin tomonidan olingan static API token. Universitet
butun talabalar/o'qituvchilar ro'yxatini sync qilish uchun. Endpoint'lar: `/v1/data/*`.

---

## 3. Schema xaritalash (HEMIS → bizning DB)

### 3.1 Student → User

HEMIS `Student` schema (91 ta atribut):

| HEMIS field           | Tur                 | Bizning hozirgi field            | Holat                              |
|-----------------------|---------------------|----------------------------------|------------------------------------|
| `id`                  | integer **primary** | `users.hemis_id` (yo'q)          | ❌ qo'shilishi kerak                |
| `student_id_number`   | string nullable     | `users.hemis_login` (yo'q)       | ❌ qo'shilishi kerak                |
| `passport_pin`        | string (PINFL)      | `users.pinfl` (yo'q)             | ❌ qo'shilishi kerak                |
| `first_name`          | string              | `profiles.first_name`            | ✅ bor                              |
| `second_name`         | string (familiya)   | `profiles.last_name`             | ✅ bor                              |
| `third_name`          | string (otasining)  | `profiles.middle_name`           | ✅ bor                              |
| `full_name`           | string              | `users.full_name`                | ✅ bor                              |
| `birth_date`          | int (unix timestamp)| `profiles.birth_date` (date)     | ✅ bor                              |
| `email`               | string **nullable** | `users.email` **NOT NULL UNIQUE**| ❌ optional qilish kerak           |
| `image`               | url string          | `users.avatar_url`               | ✅ bor                              |
| `address`             | string nullable     | `profiles.address`               | ⚠️ tekshirish                       |
| `group.id/.name`      | Group               | (yangi `groups` table?)          | ❌ qo'shilish mumkin                |
| `faculty.id/.code`    | Department          | `academic.Faculty.hemis_id`      | ❌ FK qo'shilishi kerak             |
| `specialty`           | Classifier          | `academic.Specialty.hemis_code`  | ❌ qo'shilishi kerak                |
| `semester.id/.code`   | Semester            | (yangi field)                    | ❌                                  |
| `educationLang`       | Classifier          | `users.preferred_language`       | ⚠️ map kerak (`uz-lat`/`uz-cyr`/`ru`/`en`) |
| `educationForm`       | Classifier          | (yangi: kunduzgi/sirtqi/kechki)  | ❌                                  |
| `educationType`       | Classifier          | (bakalavr/magistr — bor)         | ✅ bor                              |
| `paymentForm`         | Classifier          | (yangi: kontrakt/grand/davlat)   | ❌                                  |
| `studentStatus`       | Classifier          | (yangi: faol/akademik/...)       | ❌                                  |
| `country/province/district` | Classifier × 3 | `profiles.country/region/district`| ⚠️ tekshirish              |
| `socialCategory`      | Classifier nullable | (yangi: nogiron/yetim/...)       | ❌                                  |
| `hash`                | sha256              | `users.hemis_data_hash`          | ❌ qo'shilishi kerak (drift detection) |

### 3.2 Employee → User (o'qituvchi)

HEMIS `Employee` minimal: `{ id, name }`. To'liq ma'lumot `GET /v1/data/employee-list`
(Backend API) orqali olinadi: `birth_date`, `passport_pin`, `phone`, `email`, `gender`,
`employmentForm`, `employmentStaff`, `staffPosition`, `department`, va h.k.

### 3.3 Faculty → Department

HEMIS `Department`:
- `id`, `code`, `name`, `parent` (parent department), `active`, `structureType`, `localityType`

Bizning `academic.Faculty` schema'da `hemis_id`, `hemis_code` kerak.

### 3.4 Group (yangi entity)

Bizda kurs/akademik guruh modeli yo'q. HEMIS'da har talaba `group` ga biriktirilgan.
Yangi `groups` table kerak (`id`, `hemis_id`, `name`, `education_lang`, `faculty_id`).

### 3.5 Semester, Specialty, Curriculum

HEMIS'da `Semester`, `Specialty`, `Curriculum`, `CurriculumSubject` to'liq strukturalar.
Bizda `Specialty` va `Curriculum` bor lekin HEMIS sync yo'q. Sync uchun:
- `academic.Specialty.hemis_code`
- `academic.Curriculum.hemis_id`
- Curriculum sync — `GET /v1/data/curriculum-list` + `/curriculum-subject-list`

---

## 4. Endpoint kategoriyalari (kerakliligi bo'yicha)

### 4.1 KERAK — Phase 10 da ulanadi (35+ endpoint)

**Auth:**
- `POST /v1/auth/login` — proxy login
- `POST /v1/auth/refresh-token`
- `POST /ver1/tutor/auth/login` — tutor login
- `GET /v1/sso/get-redirect-url?target=lms` — SSO
- `GET /v1/sso/targets`

**Talaba ma'lumotlari:**
- `GET /v1/account/me` — login'dan keyin profil + faculty + group + semester
- `GET /v1/account/refresh` — re-sync
- `POST /v1/account/update` — agar biz tahrirlasak

**Ta'lim:**
- `GET /v1/education/subject-list` — talabaga biriktirilgan fanlar + grades
- `GET /v1/education/schedule` — dars jadvali (LMS ham tutash uchun)
- `GET /v1/education/exam-table` — imtihon jadvali
- `GET /v1/education/gpa-list` — GPA tarixi
- `GET /v1/education/performance` — kunlik baholar
- `GET /v1/education/attendance` — davomat
- `GET /v1/education/resources` — elektron resurslar (kitob, video)
- `GET /v1/education/semesters` — semestrlar

**Backend API (admin sync):**
- `GET /v1/data/student-list` — barcha talabalar
- `GET /v1/data/employee-list` — barcha o'qituvchilar
- `GET /v1/data/department-list` — fakultetlar
- `GET /v1/data/group-list` — guruhlar
- `GET /v1/data/curriculum-list` — o'quv rejalar
- `GET /v1/data/curriculum-subject-list` — fanlar
- `GET /v1/data/exam-list` — DAK imtihonlari (bizdan HEMIS'ga POST/upload mexanizmi?)

**Tutor API (pedagog):**
- `POST /ver1/tutor/auth/login` — pedagog login
- `GET /ver1/tutor/profile/index` — profil
- `GET /ver1/tutor/profile/groups` — biriktirilgan guruhlar
- `GET /ver1/tutor/group/students` — guruh talabalari
- `GET /ver1/tutor/grade/student` — talaba baholari
- `GET /ver1/tutor/attendance/by-subject` — davomat
- `POST /ver1/tutor/message/send` — xabar (LMS ichida ham bor — Phase 11)

### 4.2 MUMKIN — keyingi fazada qo'shiladi

- `GET /v1/plagiarism/*` — HEMIS'ning antiplagiat tizimi (bizda Phase 9e pure-Python TF-IDF)
- `POST /v1/exam/*` — HEMIS exam mexanizmi (bizda Phase 6 da o'z exam moduli)
- `GET /v1/social-activity/*` — Talaba reyting/ijtimoiy faollik
- `POST /v1/student/qr-attendance` — QR davomat
- `GET /v1/student/contract` — kontraktlar (Phase 11 billing)
- `GET /v1/grant-application/*` — Grand arizalar
- `POST /v1/fast/*` — AI suhbat (bizning Phase 9 AI o'rniga)

### 4.3 KERAK EMAS

- Bunday endpoint'lar yo'q — hammasi LMS biznes mantig'i bilan bog'liq.

---

## 5. Login flow — yangilangan

### 5.1 Hozirgi (suboptimal)

```
[Talaba] → [Bizning LMS login form] (email + parol)
        → Backend "if email in users: ..." (faqat bizning DB)
        → Cookie auth o'rnatilgan
```

`HemisLoginView.vue` mavjud, lekin u alternative form sifatida ishlaydi.

### 5.2 Yangi — HEMIS SSO (asosiy yo'l)

```
[Talaba HEMIS portalida login qilgan]
   → HEMIS portalda "LMS'ga o'tish" tugmasi
   → HEMIS → GET /v1/sso/get-redirect-url?target=lms (server-side, JWT bilan)
   → HEMIS → 302 redirect to https://lms.xiuedu.uz/auth/sso/callback?sso_token=eyJ...
   → Bizning frontend → callback page yuklanadi
   → Frontend → POST /api/v1/auth/hemis-sso { sso_token } bizning backend'ga
   → Backend → GET /v1/account/me HEMIS'ga (sso_token bilan)
   → Backend → user bo'lmasa yaratadi (hemis_id primary), bo'lsa update qiladi
   → Backend → LMS JWT chiqaradi, cookie/header'ga
   → Frontend → redirect to /app/dashboard
```

### 5.3 Yangi — HEMIS API login (fallback, agar SSO ishlamasa)

```
[Talaba bizning LMS login sahifasi] → "HEMIS hisobim bilan kirish" tab
   → Talaba HEMIS student ID + parol kiritadi (NOT email)
   → Frontend → POST /api/v1/auth/hemis-login { hemis_login, password }
   → Backend → POST /v1/auth/login HEMIS'ga proxy
   → Backend → GET /v1/account/me HEMIS'ga (qaytgan tokenni ishlatib)
   → Backend → user create/update + LMS JWT chiqarish
   → Frontend → redirect
```

### 5.4 Email/parol kirishni saqlash kerakmi?

**Saqlanadi** lekin:
- Faqat XIU `staff` (admin, dekan) uchun (HEMIS-da login bo'lmaganlar)
- Talaba/pedagog email orqali login qila olmaydi (faqat HEMIS)
- Email field optional bo'ladi

---

## 6. Migratsiya rejasi (DB)

### Yangi yoki o'zgartiriladigan ustunlar (`users`):

```sql
-- Phase 10b migration
ALTER TABLE users
  ADD COLUMN hemis_id            INTEGER UNIQUE,                -- HEMIS primary ID
  ADD COLUMN hemis_login         VARCHAR(50) UNIQUE,            -- student_id_number / employee login
  ADD COLUMN pinfl               VARCHAR(14) UNIQUE,            -- passport_pin (14 raqam)
  ADD COLUMN hemis_data_hash     VARCHAR(64),                   -- drift detection
  ADD COLUMN hemis_last_synced_at TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN email DROP NOT NULL,                              -- email endi optional
  ALTER COLUMN email DROP UNIQUE;                                -- bir nechta NULL ruxsat

-- Email unique cheklov faqat NOT NULL holatda:
CREATE UNIQUE INDEX ux_users_email_notnull ON users(email) WHERE email IS NOT NULL;

CREATE INDEX ix_users_hemis_id ON users(hemis_id);
CREATE INDEX ix_users_hemis_login ON users(hemis_login);
CREATE INDEX ix_users_pinfl ON users(pinfl);
```

### Yangi jadval (`groups`):

```sql
CREATE TABLE academic_groups (
  id              BIGSERIAL PRIMARY KEY,
  hemis_id        INTEGER UNIQUE NOT NULL,
  name            VARCHAR(50) NOT NULL,
  education_lang  VARCHAR(20),
  faculty_id      BIGINT REFERENCES faculties(id),
  specialty_id    BIGINT REFERENCES specialties(id),
  semester_id     INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `faculties`, `specialties`, `curricula` ga `hemis_*`:

```sql
ALTER TABLE faculties ADD COLUMN hemis_id INTEGER UNIQUE, ADD COLUMN hemis_code VARCHAR(50);
ALTER TABLE specialties ADD COLUMN hemis_code VARCHAR(50);
ALTER TABLE curricula ADD COLUMN hemis_id INTEGER UNIQUE;
```

### Backend service refactor:

- `app/modules/auth/service.py` — `authenticate_by_email()` → `authenticate_by_hemis_login()` + fallback
- `app/modules/users/service.py` — `get_or_create_from_hemis(student_data)` helper
- `app/integrations/hemis/client.py` — yangi `student_login()`, `account_me()`, `subject_list()`
- `app/api/v1/auth.py` — yangi `POST /auth/hemis-sso { sso_token }` endpoint
- `app/api/v1/auth.py` — `POST /auth/hemis-login` HEMIS API'ni proxy qiladi (hozir mock)

---

## 7. Phase 10 sub-fazalar (kengaytirilgan)

### 10a — HEMIS audit + dokumentatsiya ✅ (shu MD fayl)

### 10b — Models refactor (HEMIS-first identity)

- `users` migration: `hemis_id`, `hemis_login`, `pinfl`, `hemis_data_hash`, email optional
- `groups` table
- `faculties/specialties/curricula` ga `hemis_*` kolonkalar
- Pydantic schemalar: `UserCreate.email: str | None`, `UserPublic.hemis_id`
- Service: get_by_email + get_by_hemis_id + get_or_create_from_hemis_student

### 10c — HEMIS API client to'liq qayta yozish

- `app/integrations/hemis/client.py` — async HTTP wrapper (httpx)
- Endpoint'lar: 35 ta (4.1 ro'yxatdagi)
- JWT cache + auto refresh
- Audit log integration (HemisSyncLog — Phase 7e da bor)
- Mock mode + real mode (env switch)

### 10d — HEMIS Login (proxy) + LMS JWT bridging

- `POST /api/v1/auth/hemis-login` — HEMIS API'ga forward, JWT olib LMS user yaratish
- Frontend `HemisLoginView.vue` qayta dizayn (login field hemis_login bo'lishi, NOT email)
- HEMIS JWT'ni LMS session ichida saqlash (background sync uchun)

### 10e — HEMIS SSO callback

- HEMIS administratoridan `target=lms` ro'yxatdan o'tish (manual step)
- `POST /api/v1/auth/hemis-sso { sso_token }` endpoint
- Frontend `/auth/sso/callback?sso_token=...` page → backend'ga POST
- SSO token validate qilish (HEMIS `/v1/account/me`-ni sso_token bilan chaqirib tekshirish)

### 10f — HEMIS data sync (admin scheduler)

- Celery beat (yoki APScheduler) — har 24 soatda barcha entity'larni sync:
  - student_list → users
  - employee_list → users
  - department_list → faculties
  - group_list → groups
  - curriculum-list → curricula
- Conflict resolution: HEMIS authoritative, agar `hemis_data_hash` o'zgarsa update
- Sync dashboard (admin HemisSyncLog UI'da Phase 8f da bor)

### 10g — Tutor API integration

- Pedagog login `/ver1/tutor/auth/login` orqali
- Pedagog dashboard: HEMIS guruh ro'yxati, davomat, baholar
- reCaptcha integration (Google reCAPTCHA v3 frontend)

### 10h — E-IMZO (elektron imzo)

- `e-imzo.uz` PKCS#11 integration (browser plugin yoki Java applet)
- Hujjat imzolash (diplom, sertifikat, ariza)

### 10i — OTJBAT (Oliy ta'lim jurnal)

- Resursi tahlil qilish kerak — alohida tekshirish

### 10j — TSDIN

- Resursi tahlil qilish kerak

### 10k — Click to'lov

- Click API (https://docs.click.uz/) — kontrakt to'lash

### 10l — Payme to'lov

- Payme API (https://help.paycom.uz/) — kontrakt to'lash

---

## 8. Reja: navbat

1. **10a** — bu MD ✅
2. **10b** — DB models + migration (1-2 kun)
3. **10c** — HEMIS client + auth proxy (2-3 kun)
4. **10d** — Login UI refactor (1 kun)
5. **10e** — SSO callback (1 kun, agar HEMIS administrator tasdiqlasa)
6. **10f** — Data sync (2 kun)
7. **10g** — Tutor API (2 kun)
8. **10h-l** — E-IMZO, OTJBAT, TSDIN, Click, Payme — keyingi iteratsiya

**Boshlash:** 10b (models refactor) — barcha keyingi ish shundan boshlanadi.

---

## 9. Risks va savollar

- **R1:** HEMIS administratorga murojaat — `target=lms` SSO ro'yxati va backend API token uchun.
  Bularsiz 10e/10f/10g yarim qoladi.
- **R2:** HEMIS API rate limit — hujjat ko'rsatmaydi. Real sync paytida tekshirish kerak.
- **R3:** Talaba HEMIS-da kunduzgi/sirtqi/kechki shaklini bizning `Specialty.education_form`
  bilan moslashtirish. Classifier code'lar bizning ENUM'larga moslashishi kerak.
- **R4:** PINFL 14 raqamli — passport. Mavjud talabalarning passportlari migration paytida
  to'ldirilmagan bo'lsa, sync'da to'ldiriladi.
- **R5:** Email NOT NULL → NULLABLE migratsiya — production'da uzilish bo'lmasligi uchun
  ehtiyot bilan: avval default 'NULL' qabul qilish, keyin NOT NULL constraint'ni olib tashlash.

---

## 10. Manbalar

- OpenAPI spec: `md_files/hemis_integration/hemis_openapi.json`
- 559-son qaror: `md_files/xiu_lms_tz_md/lms_tz_xiuedu/docs/00-559-qaror.md`
- HEMIS markaziy portal: https://hemis.uz/
- XIU instance: https://student.xiuedu.uz/
