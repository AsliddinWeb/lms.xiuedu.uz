# 08.03. Claude Code uchun vazifalar

## Maqsad

Loyihani VS Code'da Claude Code yordamida bosqichma-bosqich qurish uchun aniq, bajariladigan vazifalar to'plami.

## Qanday foydalanish

1. VS Code'ni oching
2. Yangi loyiha papkasini yarating: `lms-platform/`
3. Bu `tz_md/` papkasini loyihaga ko'chiring
4. Claude Code'ni ishga tushiring
5. Quyidagi vazifalardan birini Claude'ga bering (har birini alohida)

> **Maslahat:** Har bir vazifani alohida chat'da bajaring. Bu Claude'ga kontekstni toza tutishga yordam beradi.

---

## TASK 1: Loyiha skeleton

```
@docs/02-architecture/02-tech-stack.md
@docs/02-architecture/03-folder-structure.md
@docs/07-devops/01-docker.md

Yuqoridagi hujjatlarga asoslanib, loyiha skeleton'ini yarat:

1. Monorepo struktura yarat (backend/, frontend/, infra/)
2. Backend uchun:
   - pyproject.toml (Poetry)
   - app/ papkasi
   - app/main.py (FastAPI hello world)
   - app/core/config.py (Settings via pydantic-settings)
   - .env.example
   - Dockerfile
3. Frontend uchun:
   - package.json (pnpm)
   - Vue 3 + Vite + TypeScript + Tailwind
   - src/main.ts, src/App.vue
   - tsconfig.json
   - tailwind.config.ts
   - Dockerfile
4. Root'da docker-compose.yml (postgres, redis, minio, backend, frontend)
5. README.md

Faqat skeleton — biznes logika kerak emas.
```

---

## TASK 2: Database modellar va migrations

```
@docs/05-database/01-schema.md
@docs/05-database/03-models.md

Backend uchun barcha SQLAlchemy modellarini yarat:

1. app/models/base.py — BaseModel (id, created_at, updated_at)
2. app/models/user.py — User, Role, Permission, UserRole
3. app/models/academic.py — Otm, Faculty, Department, Specialty
4. app/models/course.py — Course, Module, Lesson
5. app/models/enrollment.py — Enrollment, AcademicYear, Semester
6. app/models/content.py — File, Video, ScormPackage
7. app/models/assignment.py — Assignment, Submission, Grade
8. app/models/exam.py — Exam, Question, Answer, ExamAttempt
9. app/models/payment.py — Contract, Payment, Transaction

Har bir modelda:
- SQLAlchemy 2.0 syntax (Mapped, mapped_column)
- Type hints
- Relationships
- Indexes (kerak bo'lganda)

Alembic'ni sozla va birinchi migration'ni yarat:
- alembic init -t async migrations
- alembic.ini'ni database URL bilan to'ldir
- alembic revision --autogenerate -m "initial"
```

---

## TASK 3: Authentication

```
@docs/03-modules/01-auth.md
@docs/07-devops/04-security.md

Auth modulini to'liq amalga oshir:

1. app/core/security.py:
   - password_hash, verify_password (Argon2)
   - create_access_token, create_refresh_token
   - decode_token

2. app/services/auth_service.py:
   - register_user
   - authenticate
   - refresh_token
   - reset_password

3. app/api/v1/auth.py:
   - POST /auth/register
   - POST /auth/login
   - POST /auth/refresh
   - POST /auth/logout
   - POST /auth/forgot-password
   - POST /auth/reset-password

4. app/api/dependencies.py:
   - get_current_user dependency

5. Pydantic schemalar (app/schemas/auth.py):
   - UserRegister, UserLogin, TokenResponse, etc.

6. Brute force himoyasi (Redis bilan)
7. Rate limiting

Test'lar yoz (tests/test_auth.py)
```

---

## TASK 4: RBAC

```
@docs/03-modules/02-users-rbac.md
@docs/01-overview/04-roles.md

RBAC tizimini amalga oshir:

1. Default rollar va ruxsatlarni seed qilish
2. require_permission decorator
3. require_role decorator
4. Permission tekshiruvi service
5. Frontend uchun permissions composable (Vue)

10 ta rolni yarat:
- super_admin, otm_admin, faculty_admin, department_head
- teacher, student, methodist, accountant
- proctor, support

Permission'lar 10-table.md'dagi RBAC matritsasiga mos kelishi kerak.
```

---

## TASK 5: OneID integratsiyasi

```
@docs/04-integrations/03-oneid.md
@docs/03-modules/01-auth.md

OneID OAuth flow'ni amalga oshir:

1. app/services/oneid_service.py:
   - get_authorization_url
   - exchange_code_for_token
   - get_user_info
   - link_or_create_user

2. app/api/v1/auth.py'ga qo'sh:
   - GET /auth/oneid/login
   - GET /auth/oneid/callback

3. Frontend:
   - OneID login tugmasi (LoginPage.vue)
   - Callback sahifasi

4. State validation (CSRF himoyasi)
5. Test'lar (mock OneID API)
```

---

## TASK 6: HEMIS integratsiyasi

```
@docs/04-integrations/01-hemis.md

HEMIS API client va sinxronizatsiyani yarat:

1. app/integrations/hemis/client.py:
   - HemisClient klassi
   - get_students, get_specialties, get_groups
   - export_attendance, export_grades

2. app/services/hemis_sync_service.py:
   - sync_students() — har kuni 02:00 da
   - sync_specialties()
   - sync_curricula()

3. app/tasks/hemis_tasks.py (Celery):
   - sync_students_task
   - export_attendance_task

4. Admin panel'da HEMIS sync history sahifasi
5. Manual sync tugmasi

Talab: 559-qaror 29-modda — HEMIS bilan to'liq integratsiya
```

---

## TASK 7: Akademik struktura

```
@docs/03-modules/03-academic.md

Akademik strukturani amalga oshir:

1. CRUD endpointlar:
   - /api/v1/otm
   - /api/v1/faculties
   - /api/v1/departments
   - /api/v1/specialties
   - /api/v1/curricula
   - /api/v1/groups

2. Validation:
   - Bakalavr — max 300 talaba (559-qaror 26-modda)
   - Magistratura — max 30 talaba

3. Frontend:
   - Admin panel sahifalari
   - OTM tree view
   - Mutaxassislik form'i
```

---

## TASK 8: Kontent yuklash

```
@docs/03-modules/05-content.md

Kontent yuklash tizimini yarat:

1. app/services/file_service.py:
   - upload_file (chunked, max 5GB)
   - MinIO integratsiyasi

2. app/services/video_service.py:
   - FFmpeg pipeline
   - Multi-resolution (240p, 480p, 720p, 1080p)
   - HLS playlist generation
   - Celery task

3. SCORM:
   - app/services/scorm_service.py
   - ZIP extract va validation
   - manifest.xml parser
   - SCORM 1.2 va 2004 qo'llab-quvvatlash

4. xAPI endpoint:
   - POST /api/v1/xapi/statements

5. Frontend:
   - File upload component (drag-drop)
   - Video player (HLS.js)
   - SCORM player (iframe)
```

---

## TASK 9: Kurslar

```
@docs/03-modules/06-courses.md

Kurs tizimini amalga oshir:

1. Modellar: Course, Module, Lesson
2. CRUD endpointlar
3. Talaba uchun:
   - Mening kurslarim
   - Kurs sahifasi (modullar, darslar)
   - Progress tracking
4. O'qituvchi uchun:
   - Kurs yaratish wizard
   - Modul/dars qo'shish
5. Sertifikat generatsiya (PDF)
```

---

## TASK 10: Topshiriqlar

```
@docs/03-modules/07-assignments.md

Topshiriqlar va baholash tizimi:

1. Modellar va CRUD
2. Antiplag.uz integratsiyasi
3. Fayl yuklash (talaba)
4. Baholash UI (o'qituvchi)
5. Rubrikalar
6. Deadline va kechikish jarimasi
```

---

## TASK 11: Live darslar (Zoom)

```
@docs/04-integrations/02-zoom.md
@docs/03-modules/08-live-classes.md

Zoom integratsiyasi:

1. app/integrations/zoom/client.py:
   - S2S OAuth
   - Meeting CRUD
   - Recording API

2. app/api/v1/webhooks/zoom.py:
   - Webhook handler
   - Signature validation

3. app/services/live_class_service.py:
   - Schedule meeting
   - Auto-create from course
   - Davomatni yozib olish

4. Frontend:
   - Live dars jadvali
   - "Qo'shilish" tugmasi
   - Yozuvlarni ko'rish
```

---

## TASK 12: Imtihonlar va proctoring

```
@docs/03-modules/09-exams-proctoring.md

DIQQAT: Bu CRITICAL modul (559-qaror 10-modda)

1. Imtihon engine:
   - Savol turlarining 8 xili
   - Random selection
   - Vaqt limiti
   - Avtomatik baholash

2. Avtoproctoring (frontend):
   - Webcam access
   - MediaPipe face detection
   - Eye tracking (gaze direction)
   - Tab switch detection
   - Browser fullscreen
   - Suspicious behavior detection

3. Backend:
   - Webcam recordingni MinIO'ga yuklash
   - Suspicious events log
   - Proctor uchun monitoring dashboard

4. Yakuniy attestatsiya:
   - 559-qaror 21-modda — kompyuter sinflarida
   - Maxsus marker
```

---

## TASK 13: To'lov tizimlari

```
@docs/03-modules/10-payments.md
@docs/04-integrations/04-payment-gateways.md

Click va Payme integratsiyasi:

1. Click:
   - app/integrations/click/client.py
   - Prepare endpoint
   - Complete endpoint
   - MD5 signature validation

2. Payme:
   - app/integrations/payme/client.py
   - JSON-RPC 2.0
   - CheckPerformTransaction, CreateTransaction, etc.

3. Shartnoma:
   - PDF generatsiya (WeasyPrint)
   - E-IMZO bilan imzolash
   - MinIO'da saqlash

4. Frontend:
   - To'lov sahifasi
   - Click/Payme tanlash
   - Tranzaksiyalar tarixi
```

---

## TASK 14: OTJBAT/TSDIN

```
@docs/04-integrations/05-otjbat-tsdin.md

DIQQAT: Majburiy (559-qaror 29-modda)

1. OTJBAT API:
   - Talabalar ma'lumotlarini yuborish
   - O'quv jarayoni hisobotlari
   - Real-time monitoring

2. TSDIN API:
   - Davlat hisobotlari
   - Imtihon natijalari
   - Bitiruv hujjatlari

3. Cron jobs (Celery Beat):
   - Daily report
   - Weekly summary
   - Monthly statistics
```

---

## TASK 15: Hisobotlar va analitika

```
@docs/03-modules/12-reports.md

Hisobotlar moduli:

1. Dashboard'lar (rol bo'yicha):
   - Admin: umumiy statistika
   - O'qituvchi: kurs metrikalar
   - Talaba: progress
   - Methodist: akademik hisobotlar

2. Export formatlari:
   - PDF, Excel, CSV

3. Real-time charts (Chart.js)
4. Custom report builder
```

---

## TASK 16: Aloqa (chat, forum, bot)

```
@docs/03-modules/11-communications.md

Aloqa moduli:

1. Real-time chat:
   - WebSocket (FastAPI)
   - Pinia store
   - Typing indicators
   - Read receipts

2. Forum:
   - Mavzular
   - Javoblar
   - Voting

3. Email:
   - Template engine (Jinja2)
   - SMTP service
   - Async sending (Celery)

4. SMS:
   - Eskiz/PlayMobile
   - Template'lar

5. Telegram bot:
   - python-telegram-bot
   - Commands: /start, /grades, /schedule
   - Bildirishnomalar
```

---

## TASK 17: Frontend — Design system

```
@docs/06-frontend/01-design-system.md
@docs/06-frontend/03-components.md

Design system'ni qur:

1. Tailwind config (rang, font, spacing)
2. Asosiy komponentlar:
   - Button, Input, Select, Checkbox, Radio
   - Card, Modal, Drawer
   - Table, Pagination
   - Tabs, Accordion
   - Toast notifications
   - Form (with validation)

3. Storybook setup (ixtiyoriy)
4. Dark mode qo'llab-quvvatlash
```

---

## TASK 18: Frontend — Sahifalar

```
@docs/06-frontend/02-pages.md

Asosiy sahifalarni yarat:

1. Auth: Login, Register, Forgot Password
2. Dashboard (rol bo'yicha)
3. Profile, Settings
4. Courses (list, detail)
5. Lesson player
6. Assignments
7. Exams
8. Payments
9. Admin panels

Layout va routing'ni Vue Router bilan sozla.
i18n (uz/ru/en) qo'shilsin.
```

---

## TASK 19: DevOps

```
@docs/07-devops/01-docker.md
@docs/07-devops/02-ci-cd.md
@docs/07-devops/03-monitoring.md

Production'ga tayyor qilish:

1. Docker production konfiguratsiyasi
2. GitHub Actions CI/CD
3. Prometheus + Grafana
4. Loki logs
5. Sentry
6. Backup automation
7. SSL sertifikat (Let's Encrypt)
8. Nginx reverse proxy
```

---

## TASK 20: Testing va Documentation

```
Test va dokumentatsiya:

1. Unit testlar (pytest):
   - Coverage ≥ 80%
   - Critical modullarda 90%+

2. Integration testlar:
   - API endpoint'lar
   - Database operatsiyalari

3. E2E testlar (Playwright):
   - Login flow
   - Course enrollment
   - Exam taking
   - Payment

4. API documentation (OpenAPI/Swagger)
5. User documentation
6. Admin documentation
7. Video tutoriallar
```

---

## Maslahatlar

### Vazifalarni qanday berish
- Har bir vazifani alohida chat'da bajaring
- `@docs/...` orqali kerakli hujjatlarni biriktiring
- Aniq natija (deliverable) so'rang

### Kod sifatini saqlash
- Har vazifadan keyin `pytest` ishga tushiring
- Lint va type check qiling
- Code review qiling

### Konteksni boshqarish
- Katta vazifalarni kichik qismlarga bo'ling
- Modul tugagach, yangi chat boshlang
- TZ fayllarini yangilab boring

### Debugging
- Xatolik bo'lsa, log va stack trace'ni Claude'ga ko'rsating
- "Mana shu xatolik chiqyapti, sababi nima?" deb so'rang
- Test natijalarini ulashing

## Yakuniy tekshiruv

Loyiha tugagach quyidagilar bo'lishi kerak:

- [ ] 24 ta sprint tugagan
- [ ] 559-qaror talablari bajarilgan
- [ ] Test coverage ≥ 80%
- [ ] Production deploy bo'lgan
- [ ] HEMIS, OneID, Click, Payme, Zoom, OTJBAT, TSDIN integratsiyalari ishlaydi
- [ ] Avtoproctoring ishlaydi
- [ ] Pilot OTM'da muvaffaqiyatli sinov
- [ ] User docs tayyor
- [ ] Security audit o'tgan

**Omad! 🚀**
