<template>
  <AppLayout>
    <div class="p-6 lg:p-8 space-y-6 animate-fade-in" dir="rtl">
      <!-- Page Header — balanced, tight, quiet actions -->
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-[28px] font-bold tracking-tight text-navy-900">لوحة التحكم</h1>
          <p class="mt-0.5 text-sm text-navy-400">نظرة عامة على إدارة العقارات والمستأجرين</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <router-link
            v-for="action in quickActions"
            :key="action.label"
            :to="action.href"
            class="inline-flex items-center justify-center gap-2 rounded-[10px] text-sm font-medium transition-all duration-150 h-[42px] px-6"
            :class="action.primary
              ? 'btn-gold'
              : 'btn-outline hover:bg-ivory-100'"
          >
            <component :is="action.icon" class="h-[18px] w-[18px]" />
            <span>{{ action.label }}</span>
          </router-link>
        </div>
      </div>

      <!-- Loading -->
      <DashboardSkeleton v-if="loading" />

      <!-- Error -->
      <div
        v-else-if="!stats"
        class="flex flex-col items-center justify-center gap-3 py-20 text-center"
      >
        <div class="flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
          <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <p class="text-sm font-medium text-navy-400">تعذر تحميل لوحة التحكم</p>
        <button class="btn-premium btn-outline" @click="retry">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          إعادة المحاولة
        </button>
      </div>

      <template v-else>
        <!-- KPI Cards — 4 primary metrics in a single row -->
        <div class="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-4 rounded-[14px] border border-ivory-300 bg-white overflow-hidden">
          <div
            v-for="(card, i) in kpiCards"
            :key="card.label"
            class="p-5 sm:p-6"
            :class="i < kpiCards.length - 1 && 'border-b border-ivory-300/30 sm:border-b-0 sm:border-l border-l-0'"
          >
            <router-link :to="card.href" class="block">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium text-navy-400 leading-tight">{{ card.label }}</p>
                  <p class="text-[28px] font-bold tracking-tight mt-2 leading-none text-navy-900">
                    {{ card.value }}
                  </p>
                  <div v-if="card.trendLabel" class="flex items-center gap-1 mt-2">
                    <span
                      class="text-xs font-medium leading-tight"
                      :class="card.trend === 'up' ? 'text-emerald-600' : card.trend === 'down' ? 'text-red-600' : 'text-navy-400'"
                    >
                      {{ card.trendLabel }}
                    </span>
                  </div>
                </div>
                <component :is="card.icon" class="h-5 w-5 shrink-0 mt-0.5" :class="card.iconClass" />
              </div>
            </router-link>
          </div>
        </div>

        <!-- Secondary Stats — single strip, uniform, lighter dividers -->
        <div class="rounded-[14px] border border-ivory-300 bg-white px-4 py-5 sm:px-6">
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
            <div
              v-for="(stat, i) in summaryStats"
              :key="stat.label"
              class="flex items-center justify-center"
              :class="i < summaryStats.length - 1 && 'lg:border-l lg:border-ivory-300/30'"
            >
              <router-link :to="stat.href" class="block">
                <div class="flex items-center gap-2.5 min-w-0">
                  <component :is="stat.icon" class="h-[18px] w-[18px] shrink-0 text-navy-400" />
                  <div class="min-w-0">
                    <p class="text-xs font-medium text-navy-400 leading-tight">{{ stat.label }}</p>
                    <p class="text-lg font-bold leading-tight text-navy-900">{{ stat.value }}</p>
                  </div>
                </div>
              </router-link>
            </div>
          </div>
        </div>

        <!-- Charts — Area + Donut -->
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <!-- Area Chart -->
          <div class="card-premium p-5 lg:col-span-2">
            <div class="flex items-start justify-between gap-4 mb-4">
              <div class="flex-1 min-w-0">
                <h2 class="text-base font-semibold text-navy-900">التدفقات المالية</h2>
                <p class="mt-1 text-sm text-navy-400">
                  المستحقات مقابل صافي التحصيل (آخر 6 أشهر)
                  <span v-if="trendCurrency" class="text-navy-300"> · {{ trendCurrency }}</span>
                </p>
              </div>
              <!-- Account selector — System Manager with multiple accounts only -->
              <select
                v-if="showAccountSelector"
                v-model="selectedTrendAccount"
                @change="fetchTrend"
                class="rounded-[8px] border border-ivory-300 bg-white px-3 py-1.5 text-sm text-navy-900 focus:outline-none focus:ring-1 focus:ring-navy-400"
              >
                <option value="" disabled>اختر حسابًا</option>
                <option v-for="a in trendAccounts" :key="a.name" :value="a.name">
                  {{ a.account_name || a.name }} ({{ a.currency || '—' }})
                </option>
              </select>
            </div>
            <!-- No account selected (System Manager) -->
            <div v-if="showAccountSelector && !selectedTrendAccount" class="flex items-center justify-center py-16 text-sm text-navy-400">
              اختر حسابًا لعرض التدفقات المالية
            </div>
            <!-- Loading trend -->
            <div v-else-if="trendLoading" class="flex items-center justify-center py-16">
              <div class="h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-600"></div>
            </div>
            <!-- Chart -->
            <AreaChart v-else :data="trendData" :colors="chartColors" :currency="trendCurrency || currency" />
          </div>

          <!-- Donut Chart -->
          <div class="card-premium p-5">
            <div class="flex items-start justify-between gap-4 mb-4">
              <div class="flex-1 min-w-0">
                <h2 class="text-base font-semibold text-navy-900">حالة الوحدات</h2>
                <p class="mt-1 text-sm text-navy-400">نسبة الوحدات المؤجرة والفارغة والمحجوزة</p>
              </div>
            </div>
            <DonutChart :data="occupancyData" />
          </div>
        </div>

        <!-- Collection Performance — compact, clear progress bar -->
        <div class="rounded-[14px] border border-ivory-300 bg-white p-4 sm:p-5">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h2 class="text-base font-semibold text-navy-900">أداء التحصيل</h2>
              <p class="text-sm text-navy-400">نسبة التحصيل من إجمالي المستحقات</p>
            </div>
            <div class="text-left">
              <span class="text-2xl font-bold text-navy-900">{{ collectionRate }}%</span>
            </div>
          </div>

          <div class="h-2.5 w-full rounded-full bg-ivory-200 overflow-hidden">
            <div
              class="h-full rounded-full bg-emerald-500 transition-all duration-500"
              :style="{ width: collectionRate + '%' }"
            />
          </div>

        </div>
      </template>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import AreaChart from '@/components/ui/AreaChart.vue'
import DonutChart from '@/components/ui/DonutChart.vue'
import DashboardSkeleton from '@/components/ui/DashboardSkeleton.vue'
import { callApi, formatMoney, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'

const session = useSession()
const toast = useToast()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const stats = ref(null)
const loading = ref(true)

// ---- Icons (lucide-equivalent inline SVG components) ----
const makeIcon = (pathD) => (props, { attrs }) => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  ...attrs,
  class: props?.class || attrs?.class,
}, [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: pathD })])

const IconReceipt = makeIcon('M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z')
const IconBanknote = makeIcon('M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z')
const IconAlertCircle = makeIcon('M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z')
const IconTrendingUp = makeIcon('M13 7h8m0 0v8m0-8l-8 8-4-4-6 6')
const IconBuilding = makeIcon('M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4')
const IconHome = makeIcon('M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6')
const IconUsers = makeIcon('M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-8 0 4 4 0 008 0zm6 0a4 4 0 11-8 0 4 4 0 018 0z')
const IconFileText = makeIcon('M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z')
const IconBookmark = makeIcon('M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z')
const IconFileSignature = makeIcon('M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z')
const IconWallet = makeIcon('M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z')

// ---- Chart colors (mapped to new project palette, same semantics as original) ----
const chartColors = {
  dues: '#012350',      // deep navy
  receipts: '#16885a',  // success green
  rented: '#059669',    // success green
  empty: '#94a3b8',     // muted (original: #73777F)
  reserved: '#b38942',  // gold accent
  border: '#e8e4d9',    // ivory-300 border
  graphite: '#486fb0',  // navy-400 (original: #4A4E55)
}

// ---- Quick actions (header buttons) ----
const quickActions = [
  { label: '+ مستأجر جديد', href: '/tenants/new', icon: IconUsers, primary: true },
  { label: 'عقد جديد', href: '/contracts/new', icon: IconFileSignature, primary: false },
  { label: 'استحقاق', href: '/dues', icon: IconWallet, primary: false },
  { label: 'دفعة', href: '/receipts', icon: IconBanknote, primary: false },
]

// ---- Balance display helpers ----
const balanceValue = computed(() => stats.value?.totalBalance ?? 0)
const balanceLabel = computed(() => {
  const v = balanceValue.value
  if (v > 0) return 'على المستأجر'
  if (v < 0) return 'لصالح المستأجر'
  return 'لا يوجد رصيد'
})
const balanceDisplayValue = computed(() =>
  formatMoney(Math.abs(balanceValue.value), currency.value)
)
const balanceColorClass = computed(() => {
  const v = balanceValue.value
  if (v > 0) return 'text-navy-900'
  if (v < 0) return 'text-blue-600'
  return 'text-navy-400'
})

// ---- KPI cards (4 primary metrics) ----
const kpiCards = computed(() => [
  {
    label: 'إجمالي المستحقات',
    value: formatMoney(stats.value?.totalDues ?? 0, currency.value),
    icon: IconReceipt,
    href: '/dues',
    iconClass: 'text-navy-600',
    trend: 'up',
    trendLabel: 'حتى اليوم',
  },
  {
    label: 'صافي التحصيل',
    value: formatMoney(stats.value?.netCollections ?? 0, currency.value),
    icon: IconBanknote,
    href: '/receipts',
    iconClass: 'text-emerald-600',
    trend: 'up',
    trendLabel: 'التحصيل الفعلي',
  },
  {
    label: 'الرصيد المستحق',
    value: balanceDisplayValue.value,
    icon: IconAlertCircle,
    href: '/tenants',
    iconClass: balanceColorClass.value,
    trend: 'neutral',
    trendLabel: balanceLabel.value,
  },
  {
    label: 'نسبة الإشغال',
    value: `${stats.value?.occupancyRate ?? 0}%`,
    icon: IconTrendingUp,
    href: '/buildings',
    iconClass: 'text-navy-600',
    trend: 'neutral',
    trendLabel: `${stats.value?.rentedUnitsCount ?? 0} من ${stats.value?.unitsCount ?? 0} وحدات`,
  },
])

// ---- Secondary stats (compact variant) ----
const summaryStats = computed(() => [
  { label: 'العقارات', value: stats.value?.buildingsCount ?? 0, icon: IconBuilding, href: '/buildings' },
  { label: 'الوحدات', value: stats.value?.unitsCount ?? 0, icon: IconHome, href: '/buildings' },
  { label: 'المستأجرون', value: stats.value?.tenantsCount ?? 0, icon: IconUsers, href: '/tenants' },
  { label: 'العقود', value: stats.value?.activeContractsCount ?? 0, icon: IconFileText, href: '/contracts' },
  { label: 'فارغة', value: stats.value?.emptyUnitsCount ?? 0, icon: IconHome, href: '/buildings' },
  { label: 'محجوزة', value: stats.value?.reservedUnitsCount ?? 0, icon: IconBookmark, href: '/buildings' },
  { label: 'عليهم رصيد', value: stats.value?.tenantsWithBalanceCount ?? 0, icon: IconAlertCircle, href: '/tenants' },
])

// ---- Occupancy donut data ----
const occupancyData = computed(() => [
  { name: 'مؤجرة', value: stats.value?.rentedUnitsCount ?? 0, fill: chartColors.rented },
  { name: 'فارغة', value: stats.value?.emptyUnitsCount ?? 0, fill: chartColors.empty },
  { name: 'محجوزة', value: stats.value?.reservedUnitsCount ?? 0, fill: chartColors.reserved },
])

// ---- Financial trend (real data from backend) ----
const trendData = ref([])
const trendCurrency = ref('')
const trendLoading = ref(false)

// Account selector — System Manager with multiple accounts only
const trendAccounts = ref([])
const selectedTrendAccount = ref('')

const showAccountSelector = computed(() =>
  session.state.account?.is_system_admin === true && trendAccounts.value.length > 1
)

// ---- Collection performance ----
const collectionRate = computed(() => {
  const dues = stats.value?.totalDues ?? 0
  const netCollections = stats.value?.netCollections ?? 0
  return dues > 0 ? Math.round((netCollections / dues) * 100) : 0
})

// ---- Data fetching ----
async function fetchDashboard() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.dashboard.get_dashboard')
    stats.value = res?.stats ?? null
  } catch (e) {
    stats.value = null
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function fetchTrendAccounts() {
  // Only System Manager needs the account list (regular user has one account)
  if (session.state.account?.is_system_admin !== true) return
  try {
    const res = await callApi('rental.rental.api.account.list_rental_accounts')
    trendAccounts.value = res?.accounts ?? []
  } catch {
    trendAccounts.value = []
  }
}

async function fetchTrend() {
  // For System Manager with multiple accounts, wait for a selection
  if (showAccountSelector.value && !selectedTrendAccount.value) {
    trendData.value = []
    trendCurrency.value = ''
    return
  }
  trendLoading.value = true
  try {
    const params = {}
    if (selectedTrendAccount.value) params.account = selectedTrendAccount.value
    const res = await callApi('rental.rental.api.dashboard.get_financial_trend', params)
    trendData.value = (res?.months ?? []).map(m => ({
      name: m.name,
      dues: m.dues,
      receipts: m.netCollections,
    }))
    trendCurrency.value = res?.currency ?? ''
  } catch (e) {
    trendData.value = []
    trendCurrency.value = ''
    toast.error(extractError(e))
  } finally {
    trendLoading.value = false
  }
}

function retry() {
  window.location.reload()
}

onMounted(async () => {
  await fetchDashboard()
  await fetchTrendAccounts()
  await fetchTrend()
})
</script>
