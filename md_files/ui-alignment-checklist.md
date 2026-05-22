# UI Wireframe Alignment Checklist

> S0–S4 sprint yakunidagi har sahifa holati. Phase 6 ga o'tish sharti: barcha holatlar ✅.
> Last updated: 2026-05-12 (S4 closing)

---

## Tushuntirish

- **Wireframe** — `md_files/ui_wireframes/lms_ui/pages/NN-*.html`
- **Holat:** ✅ wireframe'ga mos · ⏳ qisman / kichik polish kerak · ❌ mos kelmaydi yoki yo'q
- **Quirks** — qaror izohi yoki keyingi Phase'ga qoldirilgan element

---

## 1. AUTH + PUBLIC (S1)

| # | Wireframe | Sahifa | Kod fayl | Holat | Quirks |
|---|---|---|---|---|---|
| 01 | `01-login.html` | Login | [LoginView.vue](../frontend/src/user/views/auth/LoginView.vue) | ✅ | UiAuthLayout 50/50 split + stats grid + OneID/HEMIS |
| 02 | `02-register.html` | Register | [RegisterView.vue](../frontend/src/user/views/auth/RegisterView.vue) | ✅ | 3-step indicator + PINFL + password strength |
| 03 | `03-forgot-password.html` | Forgot Password | [ForgotPasswordView.vue](../frontend/src/user/views/auth/ForgotPasswordView.vue) | ✅ | Info card + SMS button |
| — | (derived) | HemisLogin | [HemisLoginView.vue](../frontend/src/user/views/auth/HemisLoginView.vue) | ✅ | HEMIS variant |
| — | (derived) | ResetPassword | [ResetPasswordView.vue](../frontend/src/user/views/auth/ResetPasswordView.vue) | ✅ | Minimal split |
| — | (derived) | VerifyEmail | [VerifyEmailView.vue](../frontend/src/user/views/auth/VerifyEmailView.vue) | ✅ | Pending/ok/error states |
| — | (derived) | AdminLogin | [AdminLoginView.vue](../frontend/src/admin/views/auth/AdminLoginView.vue) | ✅ | Admin variant |

---

## 2. TALABA (S2)

| # | Wireframe | Sahifa | Kod fayl | Holat | Quirks |
|---|---|---|---|---|---|
| 04 | `04-student-dashboard.html` | Dashboard | [DashboardView.vue](../frontend/src/user/views/dashboard/DashboardView.vue) | ✅ | isStudent/isTeacher branch |
| 05 | `05-courses-list.html` | Catalog | [CourseCatalogView.vue](../frontend/src/user/views/courses/CourseCatalogView.vue) | ✅ | Filter chips + 3-col UiCourseCard |
| 05 | `05-courses-list.html` | My Learning | [MyLearningView.vue](../frontend/src/user/views/courses/MyLearningView.vue) | ✅ | Progress'li UiCourseCard |
| 06 | `06-course-detail.html` | Course Detail | [CourseDetailView.vue](../frontend/src/user/views/courses/CourseDetailView.vue) | ✅ | **Yangi** sahifa — hero + meta strip + tabs + modules accordion |
| 07 | `07-lesson-player.html` | Lesson Player | [CoursePlayerView.vue](../frontend/src/user/views/courses/CoursePlayerView.vue) | ✅ | Fullscreen `/learn/:id`, 320px sidebar + dark player + `?lesson=` deep-link |
| 08 | `08-assignments.html` | My Assignments | [MyAssignmentsView.vue](../frontend/src/user/views/assignments/MyAssignmentsView.vue) | ✅ | 4-stat grid + UiTabs + filter row |
| 08 | `08-assignments.html` (detail) | Assignment Detail | [AssignmentDetailView.vue](../frontend/src/user/views/assignments/AssignmentDetailView.vue) | ✅ | 2-col + UiCard sidebar |
| 09 | `09-exam-page.html` | Exam | — | ⏳ | **Phase 6** — proctoring bilan |
| 10 | `10-grades.html` | Grades | [GradesView.vue](../frontend/src/user/views/grades/GradesView.vue) | ✅ | **Yangi** sahifa — dark GPA card + chart + UiTabs (mock, Ph.6+ real data) |
| 11 | `11-payments.html` | Payments | — | ⏳ | **Phase 8** — to'lov integratsiyasi |
| — | (form pattern) | Profile | [ProfileView.vue](../frontend/src/user/views/profile/ProfileView.vue) | ✅ | i18n + breadcrumb |
| — | (form pattern) | Security | [SecurityView.vue](../frontend/src/user/views/profile/SecurityView.vue) | ✅ | 2FA setup + parol o'zgartirish |
| — | (08/14 derivation) | Peer Review list | [PeerReviewListView.vue](../frontend/src/user/views/peer_review/PeerReviewListView.vue) | ✅ | Breadcrumb + filter chips |
| — | (08/14 derivation) | Peer Review submit | [PeerReviewSubmitView.vue](../frontend/src/user/views/peer_review/PeerReviewSubmitView.vue) | ✅ | 2-col anon submission + grade form |

---

## 3. PEDAGOG (S3)

| # | Wireframe | Sahifa | Kod fayl | Holat | Quirks |
|---|---|---|---|---|---|
| 12 | `12-teacher-dashboard.html` | Teacher Dashboard | [DashboardView.vue](../frontend/src/user/views/dashboard/DashboardView.vue) | ✅ | isTeacher branch (S2.2 da) |
| 12 (table) | wireframe excerpt | My Courses | [MyCoursesView.vue](../frontend/src/user/views/courses/MyCoursesView.vue) | ✅ | Card → jadval refaktor (S3.3) |
| 13 | `13-course-builder.html` | Course Builder | [CourseBuilderView.vue](../frontend/src/user/views/courses/CourseBuilderView.vue) | ⏳ | Breadcrumb + UiTabs OK, lekin wireframe 4-step indikator hozircha yo'q (Phase 6 polish) |
| 14 | `14-grade-submissions.html` | Grading Inbox | [TeacherInboxView.vue](../frontend/src/user/views/grading/TeacherInboxView.vue) | ✅ | Wireframe 14 jadval + filter chips |
| 14 (detail) | wireframe excerpt | Submission Grade | [SubmissionGradeView.vue](../frontend/src/user/views/grading/SubmissionGradeView.vue) | ✅ | 2-col submission + rubric grading |
| — | (14 derivation) | Appeals Inbox | [AppealsInboxView.vue](../frontend/src/user/views/grading/AppealsInboxView.vue) | ✅ | Filter chips + jadval |
| — | (05/14 derivation) | Rubrics List | [RubricsListView.vue](../frontend/src/user/views/rubrics/RubricsListView.vue) | ✅ | Breadcrumb + search |
| 15 | `15-live-class.html` | Live Room | [LiveRoomView.vue](../frontend/src/user/views/live/LiveRoomView.vue) | ✅ | Phase 5b da to'liq pro-darajaga ko'tarildi: pre-join lobby, device selector, audio meter, recording indicator, network quality bar, reactions+hand raise, background blur, mobile responsive, permission UX |
| — | (5b.1 yangi) | Live Lobby | [LiveLobbyView.vue](../frontend/src/user/views/live/LiveLobbyView.vue) | ✅ | Pre-join screen: mic/cam preview + device pickers + audio level + session info |
| — | (list pattern) | My Live Sessions | [MyLiveSessionsView.vue](../frontend/src/user/views/live/MyLiveSessionsView.vue) | ✅ | Breadcrumb |
| — | (list pattern) | Student Live List | [StudentLiveListView.vue](../frontend/src/user/views/live/StudentLiveListView.vue) | ✅ | Breadcrumb |

---

## 4. ADMIN (S3)

| # | Wireframe | Sahifa | Kod fayl | Holat | Quirks |
|---|---|---|---|---|---|
| 16 | `16-admin-dashboard.html` | Admin Dashboard | [AdminDashboardView.vue](../frontend/src/admin/views/dashboard/AdminDashboardView.vue) | ✅ | 4 KPI + system status + phases progress |
| 17 | `17-users-management.html` | Users List | [UsersListView.vue](../frontend/src/admin/views/users/UsersListView.vue) | ✅ | Filter bar + jadval + breadcrumb |
| — | (17 derivation) | Roles List | [RolesListView.vue](../frontend/src/admin/views/users/RolesListView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | University Settings | [UniversitySettingsView.vue](../frontend/src/admin/views/academic/UniversitySettingsView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Faculties | [FacultiesView.vue](../frontend/src/admin/views/academic/FacultiesView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Departments | [DepartmentsView.vue](../frontend/src/admin/views/academic/DepartmentsView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Specialties | [SpecialtiesView.vue](../frontend/src/admin/views/academic/SpecialtiesView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Subjects | [SubjectsView.vue](../frontend/src/admin/views/academic/SubjectsView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Curricula | [CurriculaView.vue](../frontend/src/admin/views/academic/CurriculaView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Academic Calendars | [AcademicCalendarsView.vue](../frontend/src/admin/views/academic/AcademicCalendarsView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Admin Courses | [AdminCoursesView.vue](../frontend/src/admin/views/courses/AdminCoursesView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Admin Course Detail | [AdminCourseDetailView.vue](../frontend/src/admin/views/courses/AdminCourseDetailView.vue) | ⏳ | Header'da slug, breadcrumb yo'q (S4 polish) |
| — | (17 derivation) | Admin Content | [AdminContentView.vue](../frontend/src/admin/views/content/AdminContentView.vue) | ✅ | Breadcrumb |
| — | (17 derivation) | Admin Live Sessions | [AdminLiveSessionsView.vue](../frontend/src/admin/views/live/AdminLiveSessionsView.vue) | ✅ | Breadcrumb |
| 18 | `18-reports.html` | Reports | — | ⏳ | **Phase 9** — analytics modulida |

---

## 5. SHARED INFRA (S0)

| Element | Holat |
|---|---|
| `UiSidebar` (260px wireframe pattern) | ✅ |
| `UiTopbar` (search + actions + `user-menu` slot) | ✅ |
| `UiUserMenu` (dropdown: profile/security/logout) | ✅ |
| `UiAuthLayout` (50/50 dark+light split) | ✅ |
| `UiNavIcon` (27 ta wireframe SVG ikon) | ✅ |
| `UiBreadcrumb`, `UiTabs`, `UiCheck`, `UiChartBar`, `UiCourseCard`, `UiProgressBar`, `UiImagePlaceholder`, `UiVideoPlaceholder`, `UiStatCard` | ✅ |
| CSS variables (`:root` light + `.dark` mode) | ✅ |
| Tailwind + Geist Sans/Mono + Instrument Serif | ✅ |
| i18n 4 locale (uz-lat / uz-cyr / ru / en) — 1148 kalit, parity OK | ✅ |

### 5.1 Sidebar struktura qoidalari (wireframe 04 + 12 + 16 ga **strict** mos)

**Talaba (wireframe 04 strict):**
- ASOSIY: Dashboard, **Kurslar** (=MyLearning), Topshiriqlar, Jadval (Ph.6), Baholar
- BOSHQA: To'lovlar (Ph.8), Sertifikatlar (Ph.10), Forum (Ph.6), Xabarlar (Ph.6)
- (border-top) FOOTER: Yordam (Ph.6), Sozlamalar (Ph.6)
- **Sidebar'da YO'Q (in-page link orqali kiriladi):**
  - **Katalog** → MyLearningView'dagi "Kurs qidirish" tugmasi
  - **Peer Review** → Assignment Detail sahifasidan
  - **Live darslar** → Dashboard widget'dan
- **Profil/Security/Logout sidebar'da YO'Q** — endi topbar `UiUserMenu` dropdown'da.

**Pedagog (wireframe 12 strict + 1 ta deviation):**
- O'QITUVCHI: Dashboard, **Mening kurslarim**, **Topshiriqlar** (grading inbox), Live darslar, **Talabalar (Ph.6)**
- TAHLIL: Statistika (Ph.9), Hisobotlar (Ph.9)
- (border-top) FOOTER: Yordam (Ph.6), Sozlamalar (Ph.6)
- **Sidebar'da YO'Q (in-page link orqali kiriladi):**
  - **Kurs konstruktori** → Mening kurslarim sahifasidagi "+ Yangi kurs" tugmasi (wireframe 12 da sidebar'da bor edi, lekin bizning arxitektura ikkita route emas, bitta MyCoursesView orqali kursni yaratadi/tahrirlaydi — sidebar'da takror item bermayman)
  - **Apellyatsiyalar** → Topshiriqlar (grading) sahifasi ichidagi tab/button orqali
  - **Rubrik kataloglari** → Kurs konstruktori ichidagi tab sifatida
- **Profil/Security/Logout topbar `UiUserMenu` dropdown'da.**

**Admin (wireframe 16):**
- UMUMIY: Dashboard, Analitika (Ph.9)
- BOSHQARUV: Foydalanuvchilar, Rollar, Universitet, Fakultetlar, Kafedralar, Mutaxassisliklar, Fanlar, O'quv rejalar, Akademik kalendar
- TA'LIM: Kurslar, Kontent, Live darslar
- (border-top) OPERATSIYALAR: Hisobotlar (Ph.9), Audit (Ph.10), Sozlamalar (Ph.10)
- **Logout topbar `UiUserMenu` dropdown'da (admin uchun faqat logout — admin profili ayri sahifa yo'q).**

### 5.2 Topbar struktura

Wireframe `.topbar` pattern + qo'shimcha:
- Chap: search input (400px max)
- O'ng (actions slot): UiLocaleToggle → UiThemeToggle → Notifications bell
- O'ng eng oxir (`user-menu` slot): `UiUserMenu` dropdown — avatar + ism + role chevron
  - Bosilganda dropdown ochiladi
  - Dropdown header: user info (ism, email, role)
  - Items: Profil, Xavfsizlik, (divider), Chiqish (qizil)

---

## 6. SMOKE TEST (S2 + S3 yopilishida)

| Test | Holat |
|---|---|
| `vue-tsc -b` type-check | ✅ exit 0 |
| `pnpm build:user` | ✅ exit 0 |
| `pnpm build:admin` | ✅ exit 0 |
| HTTP 25 ta route | ✅ hammasi 200 |
| Locale JSON parity | ✅ 4 × 1140 kalit |

---

## 7. PHASE 6 GA O'TISH STATUSI

**S0–S4 wireframe alignment sprintlari to'liq bajarilgan:**
- [x] S0 Foundation — Komponentlar + layoutlar + CSS variables
- [x] S1 Auth — 7 ta auth sahifa wireframe'ga mos
- [x] S2 Talaba — 11 ta sahifa (2 yangi: CourseDetail + Grades)
- [x] S3 Pedagog + Admin — 20+ sahifa breadcrumb + struktura
- [x] S4 Polish — bu checklist, dark mode audit, i18n parity, MD updates

**Phase 5b — Live Streaming Pro (yakunlandi 2026-05-13):**

`LiveRoomView` Zoom/Google Meet darajasiga ko'tarildi. To'liq reja: [phase5b-live-pro-plan.md](phase5b-live-pro-plan.md).

- [x] 5b.1 Pre-join lobby ([LiveLobbyView.vue](../frontend/src/user/views/live/LiveLobbyView.vue), route `/app/live/:id/lobby`)
- [x] 5b.2 Device selector (in-room mic/cam/speaker dropdown)
- [x] 5b.3 Audio level meter (lobby + room, 5-bar real-time RMS)
- [x] 5b.4 Recording controls (header REC indicator + host toggle)
- [x] 5b.5 Network quality bar (📡 + 4-bar signal + HD + label + RTT)
- [x] 5b.6 Reactions + hand raise (LiveKit DataPacket + floating animation)
- [x] 5b.7 Background blur (`@livekit/track-processors` BackgroundBlur)
- [x] 5b.8 Mobile responsive (drawer panel, horizontal thumbs, 48px controls)
- [x] 5b.9 Permission denied UX (in-room banner + retry + audio-only + listen-only)
- [x] 5b.10 i18n 4 locales (1205 kalit, parity OK)
- [x] 5b.11 Smoke test (type-check `exit 0`, user+admin builds `exit 0`, 4 live route HTTP 200)

**Phase 6 da qo'shiladi (wireframe 09 va keyingilar):**
- `09-exam-page.html` → Exam taking UI + auto-proctoring overlay
- Course Builder 4-step indikator
- Reports module (wireframe 18)
- Payments (wireframe 11) — Phase 8

**Phase 6 ga o'tish to'liq sharti:** S0–S4 ✅ + Phase 5b yopilgan bo'lishi.

---

*Ushbu checklist har sprint oxirida yangilanadi. Yangi sahifa qo'shilganda 1-bo'limga "Holat" ustuni qo'shilishi shart.*
