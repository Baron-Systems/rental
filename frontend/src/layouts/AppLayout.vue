<template>
  <div class="app-layout flex h-screen bg-ivory-200" dir="rtl">
    <!-- Mobile overlay -->
    <transition name="fade">
      <div
        v-if="mobileOpen"
        class="fixed inset-0 bg-navy-950/60 backdrop-blur-sm z-30 lg:hidden"
        @click="mobileOpen = false"
      />
    </transition>

    <!-- Sidebar -->
    <aside
      class="fixed lg:static inset-y-0 right-0 w-[260px] flex flex-col z-40 transform transition-transform duration-300 lg:translate-x-0 print:hidden"
      :class="mobileOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'"
      style="background: #012350;"
    >
      <!-- Logo / Brand — unified 76px height to align with Topbar bottom border -->
      <div class="h-[76px] flex items-center px-6 border-b border-white/[0.06]">
        <div class="flex items-center gap-3">
          <img
            src="/images/albaron-logo.png"
            alt="ALBaron Systems"
            class="object-contain w-[52px] h-auto shrink-0"
          />
          <div>
            <h1 class="text-base font-bold text-white tracking-tight">نظام الإيجار</h1>
            <p v-if="session.state.account" class="text-[11px] text-gold-400/70 font-medium mt-0.5 truncate max-w-[160px]">
              {{ session.state.account.account_name }}
            </p>
          </div>
        </div>
      </div>

      <!-- Nav — 16px gap above first link from the divider -->
      <nav class="flex-1 px-3 pt-4 pb-2 space-y-1 overflow-y-auto">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="sidebar-item"
          :class="{ 'sidebar-item-active': isActive(item) }"
          @click="mobileOpen = false"
        >
          <svg class="w-[18px] h-[18px] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" :d="item.icon"/>
          </svg>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- User section -->
      <div class="px-4 py-4 border-t border-white/[0.06]">
        <div class="flex items-center gap-3 px-2 py-2 rounded-xl bg-white/[0.03] mb-2">
          <div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-navy-900 shrink-0" style="background: #b38942;">
            {{ userInitial }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ session.state.user }}</p>
            <p class="text-[11px] text-white/40">مستخدم</p>
          </div>
        </div>
        <button
          class="w-full text-sm text-white/50 hover:text-white flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/[0.04] transition-colors"
          @click="handleLogout"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
          تسجيل الخروج
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Bar (sticky, all viewports — matches original DashboardLayout header, print:hidden) -->
      <header class="sticky top-0 z-30 flex h-[76px] shrink-0 items-center justify-between border-b border-ivory-300/30 bg-white px-4 lg:px-6 print:hidden">
        <div class="flex items-center gap-3">
          <!-- Mobile menu button -->
          <button
            class="flex items-center justify-center rounded-[10px] p-2 text-navy-400 hover:bg-ivory-200 lg:hidden"
            @click="mobileOpen = true"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
          </button>

          <!-- Breadcrumbs -->
          <div class="flex items-center gap-1.5 text-sm">
            <template v-if="breadcrumbs.length > 1">
              <span v-for="(crumb, i) in breadcrumbs" :key="crumb.href" class="flex items-center gap-1.5">
                <svg v-if="i > 0" class="h-3 w-3 text-ivory-300/60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                <router-link
                  :to="crumb.href"
                  :class="i === breadcrumbs.length - 1 ? 'font-medium text-navy-900' : 'text-navy-400 hover:text-navy-900'"
                >
                  {{ crumb.label }}
                </router-link>
              </span>
            </template>
            <template v-else-if="route.path === '/'">
              <span class="flex items-center gap-1.5">
                <span class="text-navy-400">الرئيسية</span>
                <svg class="h-3 w-3 text-ivory-300/60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                <span class="font-medium text-navy-900">لوحة التحكم</span>
              </span>
            </template>
            <template v-else>
              <span class="flex items-center gap-1.5">
                <router-link to="/" class="text-navy-400 hover:text-navy-900">الرئيسية</router-link>
                <svg class="h-3 w-3 text-ivory-300/60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                <span class="font-medium text-navy-900">{{ currentLabel }}</span>
              </span>
            </template>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Notifications Bell -->
          <div class="relative" ref="notificationsRef">
            <button
              class="relative flex h-10 w-10 items-center justify-center rounded-[10px] bg-ivory-200/50 text-navy-400 transition-colors hover:bg-ivory-200 hover:text-navy-900"
              @click="toggleNotifications"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
              <span
                v-if="notificationsCount > 0"
                class="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white"
              />
            </button>

            <!-- Notifications dropdown -->
            <div
              v-if="notificationsOpen"
              class="absolute left-0 top-full mt-2 w-80 sm:w-96 rounded-[14px] border border-ivory-300 bg-white shadow-soft-lg z-50 overflow-hidden"
            >
              <!-- Header -->
              <div class="flex items-center justify-between border-b border-ivory-300 px-4 py-3">
                <h3 class="text-sm font-semibold text-navy-900">الإشعارات</h3>
                <span
                  v-if="notificationsCount > 0"
                  class="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600"
                >
                  {{ notificationsCount }}
                </span>
              </div>

              <!-- Body -->
              <div class="max-h-[60vh] overflow-y-auto">
                <!-- Loading -->
                <div v-if="loadingNotifications" class="flex flex-col items-center justify-center gap-3 py-8 text-center">
                  <div class="w-6 h-6 border-2 border-navy-200 border-t-navy-600 rounded-full animate-spin"></div>
                  <p class="text-sm font-medium text-navy-400">جاري تحميل الإشعارات...</p>
                </div>

                <!-- Empty -->
                <div
                  v-else-if="notifications.length === 0"
                  class="flex flex-col items-center justify-center gap-3 py-8 text-center"
                >
                  <div class="flex h-12 w-12 items-center justify-center rounded-full bg-ivory-200">
                    <svg class="h-6 w-6 text-navy-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"/>
                    </svg>
                  </div>
                  <h3 class="text-base font-semibold text-navy-700">لا توجد إشعارات</h3>
                  <p class="text-sm text-navy-400 max-w-xs">ستظهر هنا التنبيهات المهمة عند توفرها.</p>
                </div>

                <!-- Notifications list -->
                <div v-else class="divide-y divide-ivory-300">
                  <router-link
                    v-for="n in notifications"
                    :key="n.id"
                    :to="n.link"
                    class="flex items-start gap-3 px-4 py-3 hover:bg-ivory-200/60 transition-colors"
                    @click="notificationsOpen = false"
                  >
                    <div
                      class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
                      :class="n.priority === 'high' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'"
                    >
                      <!-- Calendar icon for upcoming_due, FileWarning for contracts -->
                      <svg v-if="n.type === 'upcoming_due'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                      </svg>
                      <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                      </svg>
                    </div>
                    <div class="min-w-0 flex-1">
                      <p class="text-sm font-medium text-navy-900">{{ n.title }}</p>
                      <p class="text-xs text-navy-400 mt-0.5 leading-relaxed">{{ n.message }}</p>
                    </div>
                  </router-link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main class="flex-1 overflow-auto">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSession } from '@/composables/useSession'
import { callApi, extractError } from '@/composables/useApi'

const router = useRouter()
const route = useRoute()
const session = useSession()
const mobileOpen = ref(false)

// ---- Notifications state ----
const notificationsRef = ref(null)
const notificationsOpen = ref(false)
const notifications = ref([])
const notificationsCount = ref(0)
const loadingNotifications = ref(false)
let notificationsInterval = null

const navItems = [
  { to: '/', label: 'لوحة التحكم', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { to: '/buildings', label: 'العقارات', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { to: '/tenants', label: 'المستأجرون', icon: 'M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-8 0 4 4 0 008 0zm6 0a4 4 0 11-8 0 4 4 0 018 0z' },
  { to: '/contracts', label: 'العقود', icon: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z M14 2v6h6 M8 14c.5-.5 1-1 1.5-1s1 1 1.5 1 1-1 1.5-1 1 1 1.5 1 1-1 1.5-1' },
  { to: '/dues', label: 'الالتزامات', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2 M9 5a2 2 0 002 2h2a2 2 0 002-2 M9 5a2 2 0 012-2h2a2 2 0 012 2 M9 12h6 M9 16h6' },
  { to: '/receipts', label: 'سندات القبض', icon: 'M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1z M8 7h8 M8 11h8 M8 15h5' },
  { to: '/settings', label: 'الإعدادات', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z' },
]

// ---- Breadcrumb map (matches original) ----
const breadcrumbMap = {
  '/': 'لوحة التحكم',
  '/buildings': 'العقارات',
  '/tenants': 'المستأجرون',
  '/contracts': 'العقود',
  '/dues': 'الالتزامات',
  '/receipts': 'سندات القبض',
  '/settings': 'الإعدادات',
}

function getBreadcrumbs(pathname) {
  const segments = pathname.split('/').filter(Boolean)
  const breadcrumbs = []
  let path = ''
  for (const segment of segments) {
    path += `/${segment}`
    let label = breadcrumbMap[path]
    if (!label) {
      if (segment === 'new') label = 'جديد'
      else if (segment === 'edit') label = 'تعديل'
      else if (segment === 'preview') label = 'معاينة'
      else if (segment === 'evict') label = 'إخلاء'
      else if (segment === 'renew') label = 'تجديد'
      else if (segment === 'settlement') label = 'تسوية'
      else if (segment === 'statement') label = 'كشف حساب'
      else if (segment === 'print') label = 'طباعة'
      else label = 'تفاصيل'
    }
    breadcrumbs.push({ href: path, label })
  }
  return breadcrumbs
}

const breadcrumbs = computed(() => getBreadcrumbs(route.path))

const currentLabel = computed(() => {
  const item = navItems.find(n => route.path === n.to || (n.to !== '/' && route.path.startsWith(n.to + '/')))
  return item?.label || 'نظام الإيجار'
})

const userInitial = computed(() => {
  const user = session.state.user || ''
  return user.charAt(0).toUpperCase() || 'U'
})

function isActive(item) {
  if (item.to === '/') return route.path === '/'
  return route.path === item.to || route.path.startsWith(item.to + '/')
}

// ---- Notifications ----
async function fetchNotifications() {
  try {
    loadingNotifications.value = true
    const res = await callApi('rental.rental.api.dashboard.get_notifications', {}, { autoToast: false })
    notifications.value = res?.notifications || []
    notificationsCount.value = res?.count || 0
  } catch {
    notifications.value = []
    notificationsCount.value = 0
  } finally {
    loadingNotifications.value = false
  }
}

function toggleNotifications() {
  notificationsOpen.value = !notificationsOpen.value
}

function handleClickOutside(e) {
  if (notificationsRef.value && !notificationsRef.value.contains(e.target)) {
    notificationsOpen.value = false
  }
}

// ---- Lifecycle ----
onMounted(() => {
  fetchNotifications()
  // Refresh every 5 minutes — matches original (300000ms)
  notificationsInterval = setInterval(fetchNotifications, 300000)
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  if (notificationsInterval) clearInterval(notificationsInterval)
  document.removeEventListener('mousedown', handleClickOutside)
})

// Close mobile sidebar on route change — matches original
watch(() => route.path, () => {
  mobileOpen.value = false
})

async function handleLogout() {
  await session.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
