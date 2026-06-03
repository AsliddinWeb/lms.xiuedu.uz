import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@shared/stores/auth'

/**
 * Sahifa kirish boshqaruvi (Phase 4 update — 2026-05-10):
 *
 *   meta.requiresAuth        → token majburiy
 *   meta.redirectIfAuth      → loginga kelib login qilgan user dashboard'ga
 *   meta.requiresPermission  → bitta permission talab qiladi (matches() bilan)
 *                              yetishmasa /app/dashboard'ga yo'naltiriladi
 *
 * Permission-page xaritasi md_files/role-access-matrix.md da to'liq yozilgan.
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      const t = localStorage.getItem('lms.access_token')
      return t ? { name: 'dashboard' } : { name: 'login' }
    },
  },

  // Auth (login qilmagan) — login bo'lganlar dashboard'ga
  {
    path: '/',
    component: () => import('@user/layouts/AuthLayout.vue'),
    meta: { redirectIfAuth: true },
    children: [
      { path: 'login', name: 'login', component: () => import('@user/views/auth/LoginView.vue') },
      {
        path: 'register',
        name: 'register',
        component: () => import('@user/views/auth/RegisterView.vue'),
      },
      {
        path: 'forgot-password',
        name: 'forgot-password',
        component: () => import('@user/views/auth/ForgotPasswordView.vue'),
      },
    ],
  },

  // Token-orqali (login holati ahamiyatsiz)
  {
    path: '/',
    component: () => import('@user/layouts/AuthLayout.vue'),
    children: [
      {
        path: 'reset-password',
        name: 'reset-password',
        component: () => import('@user/views/auth/ResetPasswordView.vue'),
      },
      {
        path: 'verify-email',
        name: 'verify-email',
        component: () => import('@user/views/auth/VerifyEmailView.vue'),
      },
      // Phase 10e — HEMIS SSO callback (eski oqim, hozircha qoldirilgan)
      {
        path: 'auth/sso/callback',
        name: 'sso-callback',
        component: () => import('@user/views/auth/SsoCallbackView.vue'),
      },
      // Phase 15 — HEMIS OAuth2 callback (standart oqim)
      {
        path: 'auth/hemis/callback',
        name: 'hemis-oauth-callback',
        component: () => import('@user/views/auth/HemisOAuthCallbackView.vue'),
      },
    ],
  },

  // Authenticated app
  {
    path: '/app',
    component: () => import('@user/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      // ---- Hamma authenticated user ko'radi ----
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@user/views/dashboard/DashboardView.vue'),
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@user/views/profile/ProfileView.vue'),
      },
      {
        path: 'security',
        name: 'security',
        component: () => import('@user/views/profile/SecurityView.vue'),
      },

      // ==========================================================
      // PEDAGOG (course.create) — kurs yaratish va boshqarish
      // ==========================================================
      {
        path: 'courses',
        name: 'my-courses',
        component: () => import('@user/views/courses/MyCoursesView.vue'),
        meta: { requiresPermission: 'course.create' },
      },
      {
        path: 'courses/:id',
        name: 'course-builder',
        component: () => import('@user/views/courses/CourseBuilderView.vue'),
        meta: { requiresPermission: 'course.create' },
      },
      {
        path: 'grading',
        name: 'grading-inbox',
        component: () => import('@user/views/grading/TeacherInboxView.vue'),
        meta: { requiresPermission: 'assignment.grade' },
      },
      {
        path: 'grading/:id',
        name: 'grade-submission',
        component: () => import('@user/views/grading/SubmissionGradeView.vue'),
        meta: { requiresPermission: 'assignment.grade' },
      },
      {
        path: 'rubrics',
        name: 'my-rubrics',
        component: () => import('@user/views/rubrics/RubricsListView.vue'),
        meta: { requiresPermission: 'rubric.manage' },
      },
      {
        path: 'appeals',
        name: 'appeals-inbox',
        component: () => import('@user/views/grading/AppealsInboxView.vue'),
        meta: { requiresPermission: 'appeal.review' },
      },

      // ==========================================================
      // TALABA (enrollment.self) — kurs katalog, o'qish, topshiriq
      // ==========================================================
      {
        path: 'learning',
        name: 'my-learning',
        component: () => import('@user/views/courses/MyLearningView.vue'),
        meta: { requiresPermission: 'enrollment.self' },
      },
      {
        path: 'catalog',
        name: 'course-catalog',
        component: () => import('@user/views/courses/CourseCatalogView.vue'),
        meta: { requiresPermission: 'enrollment.self' },
      },
      {
        path: 'course/:id',
        name: 'course-detail',
        component: () => import('@user/views/courses/CourseDetailView.vue'),
        meta: { requiresPermission: 'enrollment.self' },
      },
      {
        path: 'assignments',
        name: 'my-assignments',
        component: () => import('@user/views/assignments/MyAssignmentsView.vue'),
        meta: { requiresPermission: 'assignment.submit' },
      },
      {
        path: 'assignments/:id',
        name: 'assignment-detail',
        component: () => import('@user/views/assignments/AssignmentDetailView.vue'),
        meta: { requiresPermission: 'assignment.submit' },
      },
      {
        path: 'peer-reviews',
        name: 'my-peer-reviews',
        component: () => import('@user/views/peer_review/PeerReviewListView.vue'),
        meta: { requiresPermission: 'peer.review' },
      },
      {
        path: 'peer-reviews/:id',
        name: 'peer-review-submit',
        component: () => import('@user/views/peer_review/PeerReviewSubmitView.vue'),
        meta: { requiresPermission: 'peer.review' },
      },

      // ==========================================================
      // LIVE (Phase 5) — host (pedagog), student (talaba), shared room
      // ==========================================================
      {
        path: 'live',
        name: 'live-host',
        component: () => import('@user/views/live/MyLiveSessionsView.vue'),
        meta: { requiresPermission: 'live.host' },
      },
      {
        path: 'live/upcoming',
        name: 'live-upcoming',
        component: () => import('@user/views/live/StudentLiveListView.vue'),
        meta: { requiresPermission: 'live.join' },
      },
      {
        path: 'live/:id/lobby',
        name: 'live-lobby',
        component: () => import('@user/views/live/LiveLobbyView.vue'),
        meta: { requiresPermission: 'live.read' },
      },
      {
        path: 'live/:id',
        name: 'live-room',
        component: () => import('@user/views/live/LiveRoomView.vue'),
        meta: { requiresPermission: 'live.read' },
      },

      // Grades (Phase 6 backend, hozir mock UI)
      {
        path: 'grades',
        name: 'grades',
        component: () => import('@user/views/grades/GradesView.vue'),
        // Permission yo'q — barcha authenticated user ko'radi (mock)
      },

      // Notifications (Phase 7d)
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('@user/views/notifications/NotificationsView.vue'),
      },

      // Communications (Phase 11b) — chat + forum
      {
        path: 'chat',
        name: 'chat',
        component: () => import('@user/views/chat/ChatView.vue'),
      },
      // Sertifikatlar (Phase 11d)
      {
        path: 'certificates',
        name: 'my-certificates',
        component: () => import('@user/views/certificates/MyCertificatesView.vue'),
      },
      // Yutuqlar (Phase 11e — badge + leaderboard)
      {
        path: 'achievements',
        name: 'achievements',
        component: () => import('@user/views/achievements/AchievementsView.vue'),
      },
      {
        path: 'forum/courses/:courseId',
        name: 'forum-course',
        component: () => import('@user/views/forum/ForumCourseView.vue'),
      },
      {
        path: 'forum/threads/:threadId',
        name: 'forum-thread',
        component: () => import('@user/views/forum/ForumThreadView.vue'),
      },

      // Exam lobby + result (Phase 6d / 6e — taking view o'z shell'iga ega, pastda)
      {
        path: 'exams',
        name: 'my-exams',
        component: () => import('@user/views/exams/MyExamsView.vue'),
        meta: { requiresPermission: 'exam.attempt' },
      },
      {
        path: 'exams/:id/lobby',
        name: 'exam-lobby',
        component: () => import('@user/views/exams/ExamLobbyView.vue'),
        meta: { requiresPermission: 'exam.attempt' },
      },
      {
        path: 'exams/:id/result/:attemptId',
        name: 'exam-result',
        component: () => import('@user/views/exams/ExamResultView.vue'),
        meta: { requiresPermission: 'exam.attempt' },
      },
      {
        path: 'exams/:id/attempts',
        name: 'exam-attempts',
        component: () => import('@user/views/exams/ExamAttemptsListView.vue'),
        meta: { requiresPermission: 'exam.create' },
      },
      {
        path: 'exams/:id/attempts/:attemptId/review',
        name: 'attempt-review',
        component: () => import('@user/views/exams/AttemptReviewView.vue'),
        meta: { requiresPermission: 'exam.create' },
      },
    ],
  },

  // Exam taking — fullscreen shell (Phase 6e)
  {
    path: '/exams/:id/take/:attemptId',
    name: 'exam-take',
    component: () => import('@user/views/exams/ExamTakingView.vue'),
    meta: { requiresAuth: true, requiresPermission: 'exam.attempt' },
  },

  // Fullscreen lesson player (wireframe 07) — own shell, no app sidebar
  {
    path: '/learn/:id',
    name: 'course-player',
    component: () => import('@user/views/courses/CoursePlayerView.vue'),
    meta: { requiresAuth: true, requiresPermission: 'enrollment.self' },
  },

  // Phase 11a — SCORM player (fullscreen, no sidebar)
  {
    path: '/scorm/:packageId',
    name: 'scorm-player',
    component: () => import('@user/views/scorm/ScormPlayerView.vue'),
    meta: { requiresAuth: true, requiresPermission: 'course.read' },
  },

  // Phase 11d — PUBLIC sertifikat verifikatsiya (autentifikatsiyasiz)
  {
    path: '/verify/:code',
    name: 'verify-certificate',
    component: () => import('@user/views/certificates/VerifyCertificateView.vue'),
  },
  {
    path: '/verify',
    name: 'verify-certificate-empty',
    component: () => import('@user/views/certificates/VerifyCertificateView.vue'),
  },

  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@user/views/NotFoundView.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ---------- Guards ----------

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Token bor lekin user yuklanmagan → /me chaqirish
  if (auth.accessToken && !auth.user) {
    await auth.fetchMe()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Permission-based gating: foydalanuvchida kerakli permission bo'lmasa
  // dashboard'ga qaytaramiz (ruxsatsiz sahifa direct-URL'dan ham ochilmaydi)
  const required = to.meta.requiresPermission as string | undefined
  if (required && auth.isAuthenticated && !auth.hasPermission(required)) {
    return { name: 'dashboard' }
  }

  if (to.meta.redirectIfAuth && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

// ---------- Refresh xatosi → login sahifasiga ----------

window.addEventListener('lms:logout', () => {
  router.push({ name: 'login' })
})
