import { createRouter, createWebHashHistory } from 'vue-router'
import { useSession } from '@/composables/useSession'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/setup',
    name: 'Setup',
    component: () => import('@/pages/SetupPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/buildings',
    name: 'Buildings',
    component: () => import('@/pages/BuildingsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/buildings/:id',
    name: 'BuildingDetail',
    component: () => import('@/pages/BuildingDetailPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/floors',
    name: 'Floors',
    component: () => import('@/pages/FloorsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/floors/new',
    name: 'FloorNew',
    component: () => import('@/pages/NewFloorPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/tenants',
    name: 'Tenants',
    component: () => import('@/pages/TenantsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/tenants/new',
    name: 'TenantNew',
    component: () => import('@/pages/TenantNewPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/tenants/:id/edit',
    name: 'TenantEdit',
    component: () => import('@/pages/TenantEditPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/tenants/:id',
    name: 'TenantDetail',
    component: () => import('@/pages/TenantDetailPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/tenants/:id/statement',
    name: 'TenantStatement',
    component: () => import('@/pages/TenantStatementPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts',
    name: 'Contracts',
    component: () => import('@/pages/ContractsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/new',
    name: 'ContractNew',
    component: () => import('@/pages/ContractFormPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/edit',
    name: 'ContractEdit',
    component: () => import('@/pages/ContractFormPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/preview',
    name: 'ContractPreview',
    component: () => import('@/pages/ContractPreviewPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/print',
    name: 'ContractPrint',
    component: () => import('@/pages/ContractPrintPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/renew',
    name: 'ContractRenew',
    component: () => import('@/pages/ContractRenewPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/evict',
    name: 'ContractEvict',
    component: () => import('@/pages/ContractEvictPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id/settlement',
    name: 'ContractSettlement',
    component: () => import('@/pages/ContractSettlementPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/contracts/:id',
    name: 'ContractDetail',
    component: () => import('@/pages/ContractDetailPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/dues',
    name: 'Dues',
    component: () => import('@/pages/DuesPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/dues/:id',
    name: 'DueDetail',
    component: () => import('@/pages/DueDetailPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/receipts',
    name: 'Receipts',
    component: () => import('@/pages/ReceiptsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/receipts/:id',
    name: 'ReceiptDetail',
    component: () => import('@/pages/ReceiptDetailPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/pages/SettingsPage.vue'),
    meta: { requiresAuth: true, requiresSetup: true },
  },
]

let router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const { state, init, isLoggedIn, needsSetup, isReady } = useSession()

  if (!state.initialized) {
    await init()
  }

  // User with no account linked — only allow Login page
  if (isLoggedIn.value && state.account?.needs_account) {
    if (to.name !== 'Login') {
      return { name: 'Login' }
    }
    return true
  }

  if (to.meta.public) {
    if (isLoggedIn.value && isReady.value) {
      return { name: 'Dashboard' }
    }
    if (isLoggedIn.value && needsSetup.value) {
      return { name: 'Setup' }
    }
    return true
  }

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { name: 'Login' }
  }

  if (to.meta.requiresSetup && !isReady.value) {
    if (needsSetup.value) {
      return { name: 'Setup' }
    }
    return { name: 'Login' }
  }

  if (isLoggedIn.value && needsSetup.value && to.name !== 'Setup') {
    return { name: 'Setup' }
  }

  return true
})

export default router
