# 02. Pages (Sahifalar)

## Maqsad

Frontend ilovaning barcha sahifalari, yo'naltirilishi (router) va wireframe tavsiflari.

## Routerstuktura

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // Public
  { path: '/', component: () => import('@/views/landing/HomeView.vue') },
  { path: '/about', component: () => import('@/views/landing/AboutView.vue') },
  { path: '/courses', component: () => import('@/views/landing/PublicCoursesView.vue') },
  { path: '/login', component: () => import('@/views/auth/LoginView.vue') },
  { path: '/register', component: () => import('@/views/auth/RegisterView.vue') },
  { path: '/forgot-password', component: () => import('@/views/auth/ForgotPasswordView.vue') },
  { path: '/auth/callback', component: () => import('@/views/auth/CallbackView.vue') },
  
  // Authenticated layout
  {
    path: '/app',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      // Dashboard
      { path: 'dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
      
      // Courses
      { path: 'courses', component: () => import('@/views/courses/CoursesListView.vue') },
      { path: 'courses/:id', component: () => import('@/views/courses/CourseDetailView.vue') },
      { path: 'courses/:id/lessons/:lessonId', component: () => import('@/views/courses/LessonView.vue') },
      
      // Assignments
      { path: 'assignments', component: () => import('@/views/assignments/AssignmentsListView.vue') },
      { path: 'assignments/:id', component: () => import('@/views/assignments/AssignmentDetailView.vue') },
      { path: 'assignments/:id/submit', component: () => import('@/views/assignments/SubmitView.vue') },
      
      // Live
      { path: 'live', component: () => import('@/views/live/LiveSessionsListView.vue') },
      { path: 'live/:id', component: () => import('@/views/live/LiveSessionView.vue') },
      
      // Exams
      { path: 'exams', component: () => import('@/views/exams/ExamsListView.vue') },
      { path: 'exams/:id', component: () => import('@/views/exams/ExamDetailView.vue') },
      { path: 'exams/:id/take', component: () => import('@/views/exams/ExamTakeView.vue') },
      
      // Grades
      { path: 'grades', component: () => import('@/views/grades/GradesView.vue') },
      
      // Payments
      { path: 'payments', component: () => import('@/views/payments/PaymentsView.vue') },
      { path: 'payments/contract', component: () => import('@/views/payments/ContractView.vue') },
      
      // Communications
      { path: 'chat', component: () => import('@/views/chat/ChatView.vue') },
      { path: 'forum/:courseId', component: () => import('@/views/forum/ForumView.vue') },
      { path: 'notifications', component: () => import('@/views/notifications/NotificationsView.vue') },
      
      // Profile
      { path: 'profile', component: () => import('@/views/profile/ProfileView.vue') },
      { path: 'profile/settings', component: () => import('@/views/profile/SettingsView.vue') },
      { path: 'profile/security', component: () => import('@/views/profile/SecurityView.vue') },
    ],
  },
  
  // Teacher
  {
    path: '/teacher',
    component: () => import('@/layouts/TeacherLayout.vue'),
    meta: { requiresAuth: true, role: 'teacher' },
    children: [
      { path: 'courses', component: () => import('@/views/teacher/MyCoursesView.vue') },
      { path: 'courses/:id/edit', component: () => import('@/views/teacher/CourseEditorView.vue') },
      { path: 'submissions', component: () => import('@/views/teacher/SubmissionsView.vue') },
      { path: 'submissions/:id/grade', component: () => import('@/views/teacher/GradingView.vue') },
      { path: 'analytics', component: () => import('@/views/teacher/AnalyticsView.vue') },
    ],
  },
  
  // Admin
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: 'dashboard', component: () => import('@/views/admin/AdminDashboardView.vue') },
      { path: 'organizations', component: () => import('@/views/admin/OrganizationsView.vue') },
      { path: 'users', component: () => import('@/views/admin/UsersView.vue') },
      { path: 'students', component: () => import('@/views/admin/StudentsView.vue') },
      { path: 'specialties', component: () => import('@/views/admin/SpecialtiesView.vue') },
      { path: 'courses', component: () => import('@/views/admin/AdminCoursesView.vue') },
      { path: 'reports', component: () => import('@/views/admin/ReportsView.vue') },
      { path: 'settings', component: () => import('@/views/admin/SettingsView.vue') },
      { path: 'audit-logs', component: () => import('@/views/admin/AuditLogsView.vue') },
    ],
  },
  
  // 404
  { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else if (to.meta.role && !auth.hasRole(to.meta.role)) {
    next({ path: '/app/dashboard' })
  } else {
    next()
  }
})

export default router
```

## Sahifalar tavsifi

### Public

#### `/` — Landing
- Hero: "Onlayn ta'lim platformasi"
- Asosiy xususiyatlar (3-4 cards)
- Mashhur kurslar
- OTM partyorlar
- Statistika (talabalar soni, kurslar)
- CTA: "Ro'yxatdan o'tish"
- Footer

#### `/login` — Kirish
- Email + parol
- "OneID orqali kirish" tugmasi
- "HEMIS orqali kirish" tugmasi
- "Parolni unutdim?" link
- 2FA modal (kerak bo'lsa)

#### `/register` — Ro'yxatdan o'tish
- Step 1: Email + telefon + parol
- Step 2: To'liq ism, PINFL
- Step 3: OTM, mutaxassislik
- Step 4: SMS tasdiqlash

### Talaba

#### `/app/dashboard` — Talaba Dashboard
- KPI cards (GPA, davomat, balans, kurslar)
- Yaqinlashayotgan deadlinelar
- Bugungi live darslar
- Kurslar progressi (chart)
- So'nggi xabarnomalar

#### `/app/courses` — Mening kurslarim
- Cards grid (rasm, sarlavha, progress bar)
- Filter: Joriy / Tugatilgan / Barchasi
- Sort: Sana / Progress / Sarlavha
- Search

#### `/app/courses/:id` — Kurs sahifasi
- Header (cover image, title, description)
- Modullar accordeoni
- Har dars: title, type, duration, status (✓ done)
- Sidebar: progress, sertifikat
- Tabs: Overview / Materiallar / Forum / Davomat

#### `/app/courses/:id/lessons/:lessonId` — Dars
- Video player (yoki SCORM)
- Sidebar: lessons navigation
- Tabs: Video / Materiallar / Topshiriqlar / Izohlar
- "Keyingi dars" tugmasi

#### `/app/exams/:id/take` — Imtihonni topshirish
- Header: vaqt taymeri, qolgan vaqt
- Webcam preview (proktoring)
- Savol panel (1 ta savol bir vaqtda)
- Navigation (savollar listi pastda)
- "Saqlash va davom etish"
- "Tugatish" tugma (modal tasdiqi)

### O'qituvchi

#### `/teacher/courses/:id/edit` — Kurs tahrirlash
- Tabs: Overview / Modullar / Talabalar / Statistika
- Modullar va darslar drag-drop
- Har modul ichida darslar list (CRUD)
- Topshiriq, imtihon yaratish

#### `/teacher/submissions/:id/grade` — Topshiriqni baholash
- Sidebar: talaba info
- Asosiy: javobni ko'rish (PDF preview, video, kod)
- Right panel:
  - Rubric (criterialar bo'yicha ball)
  - Plagiat hisoboti
  - Izoh maydon
  - Audio izoh recorder
  - "Baholash" tugmasi

### Admin

#### `/admin/dashboard` — Admin Dashboard
- Real-time metrikalar
- Foydalanuvchilar grafigi (DAU)
- Tizim holati (uptime, errors)
- Resurs ishlatishi
- Top 5 active courses

#### `/admin/students` — Talabalar
- Jadval (server-side pagination)
- Filterlar: OTM, fakultet, yo'nalish, kurs, status
- Bulk actions
- Export Excel

## Layout komponentlari

### `AppLayout` (talaba)
```
┌──────────────────────────────────────────────┐
│ TopBar: logo, search, notifications, user │
├────────┬─────────────────────────────────────┤
│ Side- │                                      │
│ bar    │           Main content              │
│        │                                      │
│ - Dash │                                      │
│ - Cour │                                      │
│ - Live │                                      │
│ - Pay  │                                      │
└────────┴─────────────────────────────────────┘
```

### `TeacherLayout`
- Sidebar: Mening kurslarim, Topshiriqlar, Statistika

### `AdminLayout`
- Sidebar: Dashboard, OTMlar, Foydalanuvchilar, Hisobotlar, Sozlamalar

## State management (Pinia)

```typescript
// stores/auth.ts
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: localStorage.getItem('access_token') as string | null,
    permissions: [] as string[],
  }),
  
  getters: {
    isAuthenticated: (s) => !!s.token,
    hasRole: (s) => (role: string) => s.user?.roles.includes(role) ?? false,
    can: (s) => (perm: string) => s.permissions.includes(perm),
  },
  
  actions: {
    async login(email: string, password: string) { /* ... */ },
    async logout() { /* ... */ },
    async fetchUser() { /* ... */ },
  },
})
```

## Acceptance kriteriyalar

- [ ] Barcha sahifalar mavjud
- [ ] Router guards (auth, role)
- [ ] Layout komponentlari
- [ ] Pinia stores
- [ ] Lazy-loaded routes (code splitting)
- [ ] 404 sahifasi
- [ ] Loading va error states
- [ ] Mobile-friendly
