import { createRouter, createWebHistory } from 'vue-router'
import { authService } from '@/api/services/authService'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invoices',
    name: 'InvoiceList',
    component: () => import('@/views/InvoiceListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invoices/:id',
    name: 'InvoiceDetail',
    component: () => import('@/views/InvoiceDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/invoices/:id/preview',
    name: 'InvoicePreview',
    component: () => import('@/views/InvoicePreviewView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/business-partners',
    name: 'BusinessPartnerList',
    component: () => import('@/views/BusinessPartnerListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/business-partners/:id',
    name: 'BusinessPartnerDetail',
    component: () => import('@/views/BusinessPartnerDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/products',
    name: 'ProductList',
    component: () => import('@/views/ProductListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/products/:id',
    name: 'ProductDetail',
    component: () => import('@/views/ProductDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/companies',
    name: 'CompanyList',
    component: () => import('@/views/CompanyListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/companies/:id',
    name: 'CompanyDetail',
    component: () => import('@/views/CompanyDetailView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Navigation Guard für Auth
router.beforeEach((to, from, next) => {
  const isAuthenticated = authService.isAuthenticated()

  // Debug-Logging für Entwicklung
  if (import.meta.env.DEV) {
    console.log('🛡️ Route Guard:', {
      to: to.path,
      requiresAuth: to.meta.requiresAuth,
      isAuthenticated
    })
  }

  if (to.meta.requiresAuth && !isAuthenticated) {
    if (import.meta.env.DEV) {
      console.log('🚫 Access denied - redirecting to login')
    }
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && isAuthenticated) {
    if (import.meta.env.DEV) {
      console.log('✅ Already authenticated - redirecting to dashboard')
    }
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router
