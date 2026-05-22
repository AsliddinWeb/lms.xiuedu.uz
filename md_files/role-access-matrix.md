# XIU LMS — Rol va sahifa kirish matritsasi

**Versiya:** Phase 4 + single-tenant migration (2026-05-10)
**Manba:** `frontend/src/user/router/index.ts` + `frontend/src/admin/router/index.ts` + `backend/app/db/seed.py`

> **Single-tenant XIU:** Loyiha faqat bitta universitet (XIU) uchun. `Organization`
> jadvali bitta yozuv saqlaydi. Schema o'zgarmagan, lekin servicelar barcha
> `organization_id` ni avto-XIU bilan to'ldiradi. `otm_admin` roli demo
> akkauntdan olib tashlandi (super_admin bilan teng bo'lganligi uchun).
> Ko'proq: `md_files/single-tenant-architecture.md`.

Ushbu hujjat har bir rol qaysi sahifalarni ko'ra olishini va qaysi sahifalar
qaysi domain (subdomain) ostida ochilishini umumlashtiradi. **Manbada o'zgarish
bo'lsa, bu fayl ham yangilanishi shart.** (Frontend `meta.requiresPermission` →
backend `permissions` bilan teng turishi kerak.)

---

## 1. Rollar va asosiy permissionlari

10 ta rol — `app/db/seed.py` dan:

| Rol | Asosiy domeni | Eng muhim permissionlar |
|---|---|---|
| **super_admin** | Admin (8203) | `platform.*` (hammasi) |
| **otm_admin** | Admin (8203) | (single-tenant'da super_admin bilan teng — demo akkauntdan olib tashlangan, lekin schema'da hali ham mavjud) |
| **dean** | Admin (8203) | `faculty.read/students/curriculum`, `course.read`, `assignment.read`, `appeal.review` (read-only ko'p) |
| **department_head** | Admin + User (8201) | `department.manage`, `subject.manage`, `course.create/publish`, `assignment.manage/grade`, `rubric.manage`, `appeal.review` |
| **teacher** | User (8201) | `course.create/edit/publish`, `assignment.manage/grade`, `rubric.manage`, `content.create/publish`, `appeal.review`, `live.host` |
| **student** | User (8201) | `enrollment.self`, `progress.write`, `assignment.submit`, `peer.review`, `appeal.create`, `content.read`, `live.join` |
| **external_teacher** | User (8201) | `course.read/edit`, `course.content.create`, `enrollment.read`, `progress.read.all`, `content.create`, `live.host` |
| **tsdin_inspector** | Admin (8203) | `monitoring.read.*`, `audit.read.*`, `reports.read.*` (read-only) |
| **support** | Admin (8203) | `users.read`, `tickets.manage`, `password.reset.request` |
| **guest** | — | (hech narsa) |

> **Eslatma:** `course.create` permissioni **pedagog tomoni** belgisi sifatida ishlatiladi (`teacher`, `department_head`, `otm_admin`, `super_admin`'da bor; `student`, `dean`, `external_teacher`, `support`, `guest`'da yo'q). `enrollment.self` esa **talaba tomoni** belgisi (faqat `student`'da).

---

## 2. User app (lms.xiuedu.uz, port 8201)

Ushbu domen — **talaba va pedagog** ishchi maydoni. Sahifalar role bo'yicha
qatiy bo'lingan: route guard `meta.requiresPermission`ga qarab ruxsatsiz user'ni
`/app/dashboard`ga qaytaradi.

### 2.1 Auth (login qilmaganlar uchun)

| Path | Sahifa | Auth | Eslatma |
|---|---|---|---|
| `/login` | LoginView | public | `redirectIfAuth` — login bo'lsa dashboard'ga |
| `/register` | RegisterView | public | Default rol: `student` |
| `/forgot-password` | ForgotPasswordView | public | |
| `/login/hemis` | HemisLoginView | public | HEMIS delegated login (PINFL+parol) |
| `/reset-password` | ResetPasswordView | token | URL'dagi token bilan |
| `/verify-email` | VerifyEmailView | token | URL'dagi token bilan |

### 2.2 Hamma authenticated user

| Path | Sahifa | Permission | Talaba | Pedagog | Admin |
|---|---|---|:---:|:---:|:---:|
| `/app/dashboard` | DashboardView | (faqat `requiresAuth`) | ✅ | ✅ | ✅ |
| `/app/profile` | ProfileView | — | ✅ | ✅ | ✅ |
| `/app/security` | SecurityView (2FA, parol) | — | ✅ | ✅ | ✅ |

### 2.3 PEDAGOG sahifalari (`course.create` / `assignment.grade` / …)

| Path | Sahifa | Permission talab | Talaba | Pedagog |
|---|---|---|:---:|:---:|
| `/app/courses` | MyCoursesView (yaratgan kurslar) | `course.create` | ❌ | ✅ |
| `/app/courses/:id` | CourseBuilderView (4-tab) | `course.create` | ❌ | ✅ |
| `/app/grading` | TeacherInboxView (grading queue) | `assignment.grade` | ❌ | ✅ |
| `/app/grading/:id` | SubmissionGradeView | `assignment.grade` | ❌ | ✅ |
| `/app/rubrics` | RubricsListView (rubric katalog — CRUD) | `rubric.manage` | ❌ | ✅ |
| `/app/appeals` | AppealsInboxView (apellyatsiyalar) | `appeal.review` | ❌ | ✅ |

### 2.4 TALABA sahifalari (`enrollment.self` / `assignment.submit` / `peer.review`)

| Path | Sahifa | Permission talab | Talaba | Pedagog |
|---|---|---|:---:|:---:|
| `/app/catalog` | CourseCatalogView | `enrollment.self` | ✅ | ❌ |
| `/app/learning` | MyLearningView (yozilgan kurslar) | `enrollment.self` | ✅ | ❌ |
| `/app/learn/:id` | CoursePlayerView | `enrollment.self` | ✅ | ❌ |
| `/app/assignments` | MyAssignmentsView (talaba feed) | `assignment.submit` | ✅ | ❌ |
| `/app/assignments/:id` | AssignmentDetailView (submit form) | `assignment.submit` | ✅ | ❌ |
| `/app/peer-reviews` | PeerReviewListView | `peer.review` | ✅ | ❌ |
| `/app/peer-reviews/:id` | PeerReviewSubmitView | `peer.review` | ✅ | ❌ |

### 2.5 Sidebar nav (`AppLayout.vue`)

Sidebar'da nav itemlari ham role-based filtrlanadi (`computed` array):

**Talaba ko'radi:**
1. Dashboard
2. Katalog (`/app/catalog`)
3. Mening kurslarim (`/app/learning` — yozilgan kurslar)
4. Topshiriqlar (`/app/assignments`)
5. Peer review (`/app/peer-reviews`)
6. Profil, Xavfsizlik

**Pedagog ko'radi:**
1. Dashboard
2. Mening kurslarim (`/app/courses` — yaratgan kurslar)
3. Tekshirish (`/app/grading`)
4. Apellyatsiyalar (`/app/appeals`)
5. Rubrik kataloglari (`/app/rubrics`)
6. Profil, Xavfsizlik

**Phase 5+ uchun disabled (ikkalasiga ko'rinadi):** Jadval, Baholar, To'lovlar, Sertifikatlar, Forum, Xabarlar.

---

## 3. Admin app (lms-admin.xiuedu.uz, port 8203)

Ushbu domen **faqat admin role**'lar uchun. `requiresAdminRole` global meta:
`['super_admin', 'otm_admin', 'dean', 'department_head', 'support']` — boshqa
roldagi user (talaba, teacher, external_teacher, guest) login bo'lganida darhol
chiqarib yuboriladi.

### 3.1 Auth

| Path | Sahifa | Auth |
|---|---|---|
| `/login` | AdminLoginView | public |

### 3.2 Asosiy panel — `requiresAuth + requiresAdminRole`

| Path | Sahifa | Permission talab |
|---|---|---|
| `/dashboard` | AdminDashboardView | (yo'q) |
| `/users` | UsersListView | `users.read` |
| `/roles` | RolesListView | `users.read` |
| `/university` | UniversitySettingsView (XIU edit, HEMIS sozlama) | `org.read` |
| `/faculties` | FacultiesView | `faculty.read` |
| `/departments` | DepartmentsView | `department.read` |
| `/specialties` | SpecialtiesView | `specialty.read` |
| `/subjects` | SubjectsView | `subject.read` |
| `/curricula` | CurriculaView | `curriculum.read` |
| `/calendars` | AcademicCalendarsView | `calendar.read` |
| `/courses` | AdminCoursesView | `course.read` |
| `/courses/:id` | AdminCourseDetailView | `course.read` |
| `/content` | AdminContentView | `content.read` |

### 3.3 Sidebar nav guruhlari (`AdminLayout.vue`)

1. **Umumiy** — Dashboard, Analitika (Ph.9 disabled)
2. **Boshqaruv** — Foydalanuvchilar, Rollar, Universitet sozlamalari (XIU), Fakultet, Kafedra, Yo'nalish, Fan, O'quv reja, Akademik kalendar
3. **O'quv jarayoni** — Kurslar, Kontent
4. **Operatsiyalar** — Hisobotlar (Ph.9), Audit (Ph.10), Sozlamalar (Ph.10)

---

## 4. Implementation tafsiloti

### 4.1 Frontend route guard

`frontend/src/user/router/index.ts`:

```ts
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.accessToken && !auth.user) await auth.fetchMe()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Phase 4: permission-based gating
  const required = to.meta.requiresPermission as string | undefined
  if (required && auth.isAuthenticated && !auth.hasPermission(required)) {
    return { name: 'dashboard' }
  }

  if (to.meta.redirectIfAuth && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})
```

`auth.hasPermission()` — `permissions` array ichida `matches()` qiladi
(wildcard `platform.*` super_admin'ni hamma joyga kiritadi).

### 4.2 Sidebar nav reactive

`AppLayout.vue` da `main` array `computed` — har render'da `auth.hasPermission` ni
chaqirib qaysi nav itemlar ko'rinishini hisoblaydi. Sahifaga URL orqali
to'g'ridan kirish ham guard tomonidan blok qilinadi.

### 4.3 Backend permission check

Har endpoint `Depends(require_permission("X"))` orqali tekshiriladi. Frontend
guard faqat UX yordamchi — haqiqiy himoya backend'da. Foydalanuvchi DevTools
orqali frontend bypass qilsa ham, backend 403 qaytaradi.

---

## 5. Demo akkauntlar bilan test

`backend/app/db/seed.py` dagi 4 ta demo (single-tenant: `otm-admin` olib tashlandi —
bitta universitetda super_admin bilan funksional teng bo'lgan):

| Email | Parol | Rol | Login URL | Asosiy panel |
|---|---|---|---|---|
| `admin@xiuedu.uz` | `ChangeMe!2026` | super_admin | http://localhost:8203/login | Admin (hammasi) |
| `dean@xiuedu.uz` | `Dean!2026` | dean | http://localhost:8203/login | Admin (read-only) |
| `teacher@xiuedu.uz` | `Teacher!2026` | teacher | http://localhost:8201/login | User (pedagog) |
| `student@xiuedu.uz` | `Student!2026` | student | http://localhost:8201/login | User (talaba) |

### Test qilish kerak qadamlar (per-role smoke):

**student bilan:**
1. `/app/dashboard` ✅, `/app/catalog` ✅, `/app/learning` ✅
2. `/app/courses` → dashboard'ga redirect (course.create yo'q) ✅
3. `/app/grading` → redirect ✅, `/app/rubrics` → redirect ✅, `/app/appeals` → redirect ✅
4. `/app/assignments` ✅, `/app/peer-reviews` ✅

**teacher bilan:**
1. `/app/dashboard` ✅, `/app/courses` ✅, `/app/grading` ✅
2. `/app/catalog` → dashboard'ga redirect (enrollment.self yo'q) ✅
3. `/app/learning` → redirect ✅, `/app/assignments` → redirect ✅
4. `/app/peer-reviews` → redirect ✅, `/app/rubrics` ✅, `/app/appeals` ✅

**admin bilan:**
1. http://localhost:8203 ga login. Hamma admin sahifalari ✅
2. http://localhost:8201 ga login qila olmaydi (admin login alohida — token shared, lekin nav admin-only).

---

## 6. Phase 5+ uchun yangi sahifalar qo'shilganda

Yangi route qo'shganda quyidagi qadamlarni hammasini bajaring:

1. **Backend:** Kerakli permission yoki yangi permission yarating (`backend/app/db/seed.py`'ga qo'shing).
2. **Frontend route:** `meta: { requiresPermission: '...' }` qo'shing.
3. **Sidebar:** `AppLayout.vue` yoki `AdminLayout.vue` `computed` ichiga shartli qo'shing.
4. **Bu MD fayl:** Tegishli jadvalga (2.3 / 2.4 / 3.2) bitta qator qo'shing.
5. **i18n:** 4 ta locale (`uz-lat`, `uz-cyr`, `ru`, `en`) ga nav label'i qo'shing.
6. **Restart:** `docker compose restart frontend-user frontend-admin` (Vite locale cache).
