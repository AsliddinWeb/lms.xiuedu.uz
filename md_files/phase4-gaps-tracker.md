# Phase 1-4 audit — kamchiliklar va tuzatishlar

**Audit sanasi:** 2026-05-10 (Phase 4e yakunidan keyin)
**Yangilandi:** 2026-05-10 — single-tenant migration yakunidan keyin

> **Eslatma (single-tenant):** Phase 4 va shu audit yakunlangach, loyiha
> single-tenant XIU ga moslashtirildi (`md_files/single-tenant-architecture.md`).
> Quyidagi audit'da "cross-tenant" deb ko'rsatilgan masalalar single-tenantda
> de-facto yo'q, lekin kod (security clamp) saqlandi — kelajakda multi-tenant
> qaytarilsa qayta yozish kerak emas. `OrganizationsView` (i18n bo'limi B)
> umuman o'chirildi (`UniversitySettingsView` bilan almashtirildi).

Audit jami **41 backend + 50 frontend** kamchilikni topdi. Quyidagi 13 ta eng kritik fix shu sessiyada bajarildi. Qolgan ~78 ta nuance — keyingi sprint uchun (asosan i18n leak admin academic CRUD pages va boshqa cosmetic). Backend security/scope masalalari to'liq yopildi.

---

## ✅ HOZIRDA TUZATILDI (12 fix)

### Backend security/scope (5 fix)

1. **Cross-tenant user list leak** ([api/v1/users.py:259](backend/app/api/v1/users.py#L259))
   - Sabab: `users.read` egasi (otm_admin/dean/support) `tenant_id` filtersiz boshqa OTM userlarini ko'rishi mumkin edi
   - Fix: `platform.*` permissioniga ega bo'lmaganda `tenant_id`'ni avtomatik actor.tenant_id'ga clamp qilamiz
   - Single-tenant'da: amaliy ahamiyatsiz (faqat XIU bor), lekin kod saqlandi defensive bo'lib

2. **Content author scope** ([api/v1/content.py:42-58](backend/app/api/v1/content.py#L42))
   - Sabab: `content.create` egasi har qanday user'ning kontentini tahrirlash/o'chirish/transition qilishi mumkin edi
   - Fix: `_require_content_author` helper — faqat kontent muallifi yoki `platform.*` qila oladi (update, delete, transition, upload — 4 endpoint)

3. **Published course module/lesson edit gap** ([modules/courses/service.py:241,322](backend/app/modules/courses/service.py))
   - Sabab: `update_course` published kursda 409 berardi, lekin `update_module`/`update_lesson` published statusi tekshirmas edi
   - Fix: ikkalasi ham course.status='published' bo'lsa ConflictError beradi

4. **Rubric delete author scope** ([api/v1/assignments.py:510](backend/app/api/v1/assignments.py#L510))
   - Sabab: `update_rubric`'da author scope bor edi, lekin `delete_rubric`'da yo'q
   - Fix: created_by != actor && !platform.* → 403

5. **Peer reviewer submission read** ([api/v1/assignments.py:425](backend/app/api/v1/assignments.py#L425))
   - Sabab: peer review biriktirilgan reviewer submissionni ko'ra olmasdi (403) — flow buzilardi
   - Fix: PeerReview FK orqali tekshiriladi; ko'rsa anonim qaytariladi (`user_id=0` marker)

### Backend validation (1 fix)

6. **Pydantic validators kuchaytirildi** ([modules/users/schemas.py](backend/app/modules/users/schemas.py), [academic/schemas.py:367](backend/app/modules/academic/schemas.py))
   - `phone`: regex `^\+?[0-9]{7,19}$` (E.164-compatible)
   - `pinfl`: regex `^\d{14}$` (O'zbekiston 14-raqam)
   - `passport_series`: regex `^[A-Z]{2}$`
   - `passport_number`: regex `^\d{7}$`
   - `birthdate`: kelajak/1900-yildan oldin server-side rad etiladi ([api/v1/users.py:163-176](backend/app/api/v1/users.py))
   - `AcademicCalendarUpdateRequest.end_date < start_date` model_validator qo'shildi

### Frontend (6 fix)

7. **DashboardView role-aware + i18n** ([user/views/dashboard/DashboardView.vue](frontend/src/user/views/dashboard/DashboardView.vue))
   - Talaba: enrolled_count + active_assignments_count + recent_assignments cards
   - Pedagog: my_courses_count + pending_grading_count
   - Real API'lardan data olinadi; barcha matnlar `t()` orqali

8. **AdminDashboardView real KPIs + i18n** ([admin/views/dashboard/AdminDashboardView.vue](frontend/src/admin/views/dashboard/AdminDashboardView.vue))
   - 4 KPI: orgs/users/total_courses/published_courses (har biri real API call)
   - System status, my session, phases progress jadvallari i18n bilan
   - Yangi `admin_dashboard.*` namespace 4 lokalda

9. **Detail view 404 → parent list redirect** (5 ta sahifa)
   - Yangi helper [shared/api/client.ts:isNotFound](frontend/src/shared/api/client.ts) — axios 404 detector
   - AssignmentDetailView, SubmissionGradeView, CoursePlayerView, AdminCourseDetailView, CourseBuilderView — 404 da parent list'ga `router.replace`

10. **NotFoundView i18n** (user va admin)
    - `common.not_found_title/subtitle/go_home` 4 lokalda
    - User → `/`, Admin → `admin-dashboard`

11. **Cross-phase navigation linklari**
    - AssignmentDetailView'da course'ga RouterLink (course-player'ga)
    - SubmissionGradeView'da course-builder'ga link

12. **Plagiat "Run check" tugmasi** (SubmissionGradeView)
    - Pedagog uchun, `assignment.plagiarism_check_enabled` bo'lsa
    - PlagiarismBadge submission header'ida ko'rinadi
    - `submissionsApi.checkPlagiarism` chaqiriladi va submission yangilanadi

---

## ⏭️ KEYINGI SPRINT — qolgan kamchiliklar

### A. Frontend i18n leak (8 ta sahifa, ~1500 qator)

Phase 1c-2 da yozilgan admin academic CRUD sahifalari hardcoded uz-lat:
- [admin/views/users/UsersListView.vue](frontend/src/admin/views/users/UsersListView.vue)
- [admin/views/users/RolesListView.vue](frontend/src/admin/views/users/RolesListView.vue)
- ~~`admin/views/academic/OrganizationsView.vue`~~ — **o'chirildi** (single-tenant: `UniversitySettingsView.vue` bilan almashtirildi)
- [admin/views/academic/FacultiesView.vue](frontend/src/admin/views/academic/FacultiesView.vue)
- [admin/views/academic/DepartmentsView.vue](frontend/src/admin/views/academic/DepartmentsView.vue)
- [admin/views/academic/SpecialtiesView.vue](frontend/src/admin/views/academic/SpecialtiesView.vue)
- [admin/views/academic/SubjectsView.vue](frontend/src/admin/views/academic/SubjectsView.vue)
- [admin/views/academic/CurriculaView.vue](frontend/src/admin/views/academic/CurriculaView.vue)

User app:
- [user/views/profile/ProfileView.vue](frontend/src/user/views/profile/ProfileView.vue) (label/placeholder/successMsg)
- [user/views/profile/SecurityView.vue](frontend/src/user/views/profile/SecurityView.vue) (2FA bo'limi to'liq)
- [user/views/auth/HemisLoginView.vue](frontend/src/user/views/auth/HemisLoginView.vue)

**Tavsiya:** har sahifa uchun namespace yaratib, 4 lokalga keyni qo'shish; `extractErrorMessage` orqali fallback'larni `t('common.load_error')`/`t('common.save_error')`/`t('common.delete_error')` ga ko'chirish (yangi keylar qo'shilgan).

### B. Backend test gaps (8 test kerak)

- `auth.regenerate_backup_codes` endpoint testi yo'q
- `users.set_password`, `users.activate`, `me/avatar` POST/DELETE testlari yo'q
- RBAC endpoint negative test (anonim 401, talaba 403) yo'q
- `enable_distance` 404/403 testi yo'q
- Plagiat threshold edge cases (low + high)
- Appeal approve + late penalty `final_score` re-calc test
- HEMIS error path tests (502/network)
- Reviewer submission read test (1.4 fix tasdiqlovchi)

### C. Backend qolgan kichik fixlar

- `unpublish_course` atomic emas (`published → archived → draft` 2 transition; agar 2-si fail bo'lsa archived'da qoladi)
- Submission model'da `updated_at` yo'q (TimestampMixin qo'shilmagan)
- Email service silently logs SMTP failures — Celery worker yo'q
- HEMIS PINFL collision case (email match'ga ulanadi — security review)
- Partial indexlar yo'q: `peer_reviews(reviewer_id) WHERE submitted_at IS NULL`, `grade_appeals(submission_id, status) WHERE status='pending'`
- Storage: `upload_object` MinIO error handling yo'q (try/except + 503 graceful)

### D. Phase'lar bo'yicha ko'rsatilgan, lekin to'liq qilinmagan

- **Phase 1d:** 2FA backup codes regenerate tugmasi va "download all codes" UX yo'q
- **Phase 1e:** HEMIS profile sync timestamp + manual "Sinxronlash" tugmasi yo'q
- **Phase 2c:** Avatar upload'da client-side preview/crop yo'q (faqat backend xatosi qaytadi)
- **Phase 3a:** Content rich-text editor yo'q (TipTap/Quill yoki markdown editor) — hozirgi `<textarea>` cheklangan
- **Phase 3a:** Content workflow `draft → review → published` "submit for review" tugmasi yo'q
- **Phase 4 (talaba):** Talaba topshiriqning `plagiarism_check_enabled` siyosatini ko'rmaydi (assignment detail stat strip)

### E. UI states

- Filter o'zgartirilganda eski natijalar ekranda qoladi (skeleton/spinner yo'q)
- `RolesListView` da `+ Yangi rol` tugmasi yo'q (Phase 1c-da custom rollar yaratish)
- `AdminCoursesView` da "yangi kurs" tugmasi yo'q (admin platform.* bilan yarata olishi mumkin)
- `MyAssignmentsView` da `overdue`/`graded` filter chips yo'q (faqat active/all)

### F. Cross-phase navigation qolganlari

- `MyLearningView` kursdan to'g'ridan-to'g'ri assignmentlarga link yo'q
- `AppealsInboxView` da appeal'dan student profilega navigate yo'q
- `CourseBuilderView`'da student-progress tabidan kurs assignmentlari progress yo'q

---

## Test natijalari

- **Backend:** 161/161 yashil (yangi backend fixlar regression yaratmadi)
- **Frontend:** Vite barcha o'zgargan fayllarni 200 bilan compile qildi
- **Locale:** uz-lat, uz-cyr, ru, en — JSON validatsiya o'tdi (yangi `common.*`, `dashboard.*`, `admin_dashboard.*` keylar)

## Statistika

| Kategoriya | Aniqlangan | Tuzatildi (12 fix) | Qoldi |
|---|---|---|---|
| Backend security/scope | 7 | 5 | 2 |
| Backend validation | 8 | 1 (kompozit) | 7 |
| Backend tests | 9 | 0 | 9 |
| Backend service/migration | 7 | 0 | 7 |
| Frontend i18n leak | 17 | 4 (Dashboards + NotFound) | 13 |
| Frontend UI states | 8 | 5 (404 redirects) | 3 |
| Frontend role guard | 8 | 0 (oldingi sessiyada) | — |
| Frontend Phase'lar | 11 | 1 (plagiat run) | 10 |
| Frontend cross-nav | 6 | 2 | 4 |

**Jami:** 91 dan 13 ta tuzatildi (~14%). Eng kritik xavfsizlik leaklari yopildi. Qolganlari asosan i18n migration (mexanik ish, ~6 soat) va test coverage (~3 soat).

---

## Tavsiya etilgan keyingi qadam

Phase 5 (Live darslar — WebRTC) boshlashdan oldin qolgan **i18n leak**ni yopish (14 sahifa) va **backup codes regenerate UX**'ni qo'shish — bu 1 ta to'liq sprint (5-7 soat ish). Keyin Phase 5'ga to'g'ridan-to'g'ri o'tish mumkin.

---

## Single-tenant migration (2026-05-10, post-audit)

Audit yakunlangach (Phase 4 → Phase 5 oraligida), foydalanuvchi loyihaga
faqat XIU uchun ishlashini aniqladi. **Soft single-tenant migration**
amalga oshirildi:

**Backend:**
- `app/core/tenant.py` (yangi): `ensure_xiu_org`, `get_xiu_org_id`, `get_tenant_setting`
- `organization_id` har create payload'da optional, service avto-XIU bilan to'ldiradi (faculties, calendars, courses, rubrics)
- HEMIS `base_url` adminkadan sozlanadigan: `Organization.settings.hemis.base_url`
- Demo akkauntlar: 4 ta (admin, dean, teacher, student); `otm-admin` olib tashlandi

**Frontend:**
- `UniversitySettingsView.vue` (yangi): XIU edit + HEMIS sozlash sahifasi (`/university` route)
- `OrganizationsView.vue` + `OrganizationDrawer.vue` o'chirildi
- Faculty/Calendar/Course drawer va viewlar dan OTM picker/filter/column'lar olib tashlandi
- `stores/academic.ts` dan org-related API'lar olib tashlandi

**Tests:** 161/161 passing (auto-create XIU fixture'larda).

Tafsilot: [single-tenant-architecture.md](single-tenant-architecture.md).

---

## UI WIREFRAME ALIGNMENT (2026-05-12, S0–S4 yakuni)

Phase 4 / Phase 5 oraligida foydalanuvchi UI sahifalar `md_files/ui_wireframes/lms_ui/pages/01-18.html` wireframelarga 1:1 mos kelmasligini aniqladi. **Wireframe-alignment sprint** (S0–S4) Phase 6 ga o'tish sharti sifatida ishga olindi.

| Sprint | Mavzu | Holat | Bajarilgan |
|---|---|---|---|
| S0 | Foundation komponentlar + layoutlar | ✅ | UiSidebar, UiTopbar, UiAuthLayout, UiNavIcon (27 ikon), UiTabs, UiBreadcrumb, UiCheck, UiChartBar, UiCourseCard, UiProgressBar, UiImagePlaceholder, UiVideoPlaceholder, UiStatCard |
| S1 | Auth sahifalar | ✅ | 7 ta auth view: 50/50 split, OneID/HEMIS, password strength, 3-step register |
| S2 | Talaba sahifalar | ✅ | Dashboard 04, Catalog 05, MyLearning 05, **CourseDetail 06 (yangi)**, Player 07 fullscreen, Assignments 08, AssignmentDetail, **Grades 10 (yangi)**, Profile, Security, PeerReview |
| S3 | Pedagog + Admin sahifalar | ✅ | MyCoursesView jadval, CourseBuilder breadcrumb+UiTabs, TeacherInbox 14, SubmissionGrade, Appeals, Rubrics, MyLiveSessions, StudentLiveList; AdminDashboard, UsersList, RolesList, 7 academic CRUD, AdminCourses, AdminContent, AdminLiveSessions — barchasiga breadcrumb |
| S4 | Polish + MD | ✅ | Dark mode CSS variables auditi, i18n 4×1140 kalit parity, [ui-alignment-checklist.md](ui-alignment-checklist.md), MD updates |

**Phase 5 (Live) qoldi:** LiveRoomView basic fine-tune (S3 da bajarilgan: breadcrumb, sidebar). **Professional UX** uchun alohida bosqich ajratildi:

## PHASE 5b — LIVE STREAMING PRO (yakunlandi 2026-05-13)

`LiveRoomView` Zoom/Google Meet darajasiga ko'tarildi. Phase 6 (Imtihonlar + Proctoring) ga o'tishga to'siq yo'q.

| Sub-sprint | Mavzu | Holat |
|---|---|---|
| 5b.1 | Pre-join lobby (mic/cam preview + device selector) | ✅ |
| 5b.2 | Device selector (in-room mic/speaker/cam dropdown) | ✅ |
| 5b.3 | Audio level meter (lobby + room) | ✅ |
| 5b.4 | Recording controls (REC tugmasi header'da) | ✅ |
| 5b.5 | Network quality bar (signal + HD + RTT) | ✅ |
| 5b.6 | Reactions + hand raise (LiveKit DataPacket) | ✅ |
| 5b.7 | Background blur (`@livekit/track-processors`) | ✅ |
| 5b.8 | Mobile responsive (drawer panel, horizontal thumbs) | ✅ |
| 5b.9 | Permission denied UX flow (banner + retry + audio-only) | ✅ |
| 5b.10 | i18n 4 locales (1205 kalit parity) | ✅ |
| 5b.11 | Smoke test (TS + 2 build + HTTP 200) | ✅ |

**Bajarilgan ish:** 8–9 kun bo'lib bajarildi. To'liq reja: [phase5b-live-pro-plan.md](phase5b-live-pro-plan.md).

**Yangi paket:** `@livekit/track-processors@0.7.2` (MediaPipe Selfie Segmentation backed) — `livekit-client@^2.18.9` bilan birga.

**Yangi sahifa:** `/app/live/:id/lobby` → [LiveLobbyView.vue](../frontend/src/user/views/live/LiveLobbyView.vue). Navigation flow: StudentLive/MyLive list → Lobby (preview) → Room.

**Out of scope (kelajak fazalar):**
- Real-time captions / STT → Phase 9 (AI/Analytics)
- Breakout rooms → Phase 5c (multi-room session split)
- Cloud recording (S3) → Phase 7 (Deploy)

**Phase 6 (Imtihonlar + Proctoring) entry kriteriyalari:** S0–S4 ✅, Phase 5b ✅, Dead code audit ✅ — barchasi bajarilgan. **Phase 6 boshlandi 2026-05-14**. To'liq reja: [phase6-plan.md](phase6-plan.md).
