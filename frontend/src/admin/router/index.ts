import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { matches } from '@shared/composables/usePermissions'
import { useAuthStore } from '@shared/stores/auth'

const ADMIN_ROLES = ['super_admin', 'dean', 'department_head', 'support']

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      const t = localStorage.getItem('lms.access_token')
      return t ? { name: 'admin-dashboard' } : { name: 'admin-login' }
    },
  },

  // Auth (admin login)
  {
    path: '/',
    component: () => import('@admin/layouts/AuthLayout.vue'),
    meta: { redirectIfAuth: true },
    children: [
      {
        path: 'login',
        name: 'admin-login',
        component: () => import('@admin/views/auth/AdminLoginView.vue'),
      },
    ],
  },

  // Admin app
  {
    path: '/',
    component: () => import('@admin/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdminRole: true },
    children: [
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('@admin/views/dashboard/AdminDashboardView.vue'),
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('@admin/views/users/UsersListView.vue'),
        meta: { permission: 'users.read' },
      },
      {
        path: 'roles',
        name: 'admin-roles',
        component: () => import('@admin/views/users/RolesListView.vue'),
        meta: { permission: 'users.read' },
      },
      {
        path: 'university',
        name: 'admin-university',
        component: () => import('@admin/views/academic/UniversitySettingsView.vue'),
        meta: { permission: 'org.read' },
      },
      {
        path: 'faculties',
        name: 'admin-faculties',
        component: () => import('@admin/views/academic/FacultiesView.vue'),
        meta: { permission: 'faculty.read' },
      },
      {
        path: 'departments',
        name: 'admin-departments',
        component: () => import('@admin/views/academic/DepartmentsView.vue'),
        meta: { permission: 'department.read' },
      },
      {
        path: 'specialties',
        name: 'admin-specialties',
        component: () => import('@admin/views/academic/SpecialtiesView.vue'),
        meta: { permission: 'specialty.read' },
      },
      {
        path: 'subjects',
        name: 'admin-subjects',
        component: () => import('@admin/views/academic/SubjectsView.vue'),
        meta: { permission: 'subject.read' },
      },
      {
        path: 'curricula',
        name: 'admin-curricula',
        component: () => import('@admin/views/academic/CurriculaView.vue'),
        meta: { permission: 'curriculum.read' },
      },
      {
        path: 'calendars',
        name: 'admin-calendars',
        component: () => import('@admin/views/academic/AcademicCalendarsView.vue'),
        meta: { permission: 'calendar.read' },
      },
      {
        path: 'courses',
        name: 'admin-courses',
        component: () => import('@admin/views/courses/AdminCoursesView.vue'),
        meta: { permission: 'course.read' },
      },
      {
        path: 'courses/:id',
        name: 'admin-course-detail',
        component: () => import('@admin/views/courses/AdminCourseDetailView.vue'),
        meta: { permission: 'course.read' },
      },
      {
        path: 'content',
        name: 'admin-content',
        component: () => import('@admin/views/content/AdminContentView.vue'),
        meta: { permission: 'content.read' },
      },
      {
        path: 'live',
        name: 'admin-live',
        component: () => import('@admin/views/live/AdminLiveSessionsView.vue'),
        meta: { permission: 'live.read' },
      },
      {
        path: 'reports',
        name: 'admin-reports',
        component: () => import('@admin/views/reports/AdminReportsView.vue'),
        meta: { permission: 'exam.create' },
      },
      {
        path: 'hemis-sync',
        name: 'admin-hemis-sync',
        component: () => import('@admin/views/integrations/HemisSyncLogView.vue'),
        meta: { permission: 'exam.create' },
      },
      {
        path: 'settings',
        name: 'admin-settings',
        component: () => import('@admin/views/settings/AdminSettingsView.vue'),
        meta: { permission: 'org.manage' },
      },
    ],
  },

  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'admin-not-found',
    component: () => import('@admin/views/NotFoundView.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (auth.accessToken && !auth.user) {
    await auth.fetchMe()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'admin-login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdminRole && !ADMIN_ROLES.some((r) => auth.roles.includes(r))) {
    auth.logout()
    return { name: 'admin-login' }
  }

  if (to.meta.permission) {
    const required = to.meta.permission as string
    const ok = auth.permissions.some((g) => matches(g, required))
    if (!ok) return { name: 'admin-dashboard' }
  }

  if (to.meta.redirectIfAuth && auth.isAuthenticated) {
    return { name: 'admin-dashboard' }
  }
})

window.addEventListener('lms:logout', () => {
  router.push({ name: 'admin-login' })
})
