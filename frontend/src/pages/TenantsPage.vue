<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <PageHeader title="المستأجرون" description="إدارة المستأجرين ومراقبة أرصدتهم المالية" action-label="مستأجر جديد" @action="router.push({ name: 'TenantNew' })">
        <template #actions>
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="loading || printing" @click="handlePrint">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
            <span>{{ printing ? 'جاري تجهيز الطباعة...' : 'طباعة' }}</span>
          </button>
        </template>
      </PageHeader>

      <!-- Stats cards -->
      <div v-if="stats" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard label="إجمالي المستأجرين" :value="stats.total || 0" icon="users" color="navy" />
        <StatCard label="عليهم رصيد" :value="stats.debt || 0" icon="alert" color="red" />
        <StatCard label="لهم رصيد" :value="stats.credit || 0" icon="banknote" color="green" />
        <StatCard label="الرصيد صفر" :value="stats.zero || 0" icon="card" color="muted" />
      </div>

      <!-- Search + Advanced filters -->
      <Card padding="md" class="mb-4">
        <div class="flex flex-col sm:flex-row gap-3">
          <div class="relative flex-1">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="filters.search" type="text" placeholder="بحث بالاسم أو الهوية أو الهاتف..." class="input-premium pr-10" @input="handleSearchChange" />
          </div>
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" @click="showAdvanced = !showAdvanced">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
            <span>فلاتر إضافية</span>
            <span v-if="activeAdvancedCount" class="inline-flex items-center justify-center w-5 h-5 text-xs font-bold rounded-full bg-gold-500 text-navy-900">{{ activeAdvancedCount }}</span>
          </button>
          <button v-if="activeAdvancedCount" class="btn-premium btn-ghost" @click="clearFilters">مسح الفلاتر</button>
        </div>

        <div v-if="showAdvanced" class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-ivory-300/60">
          <div>
            <label class="block text-xs font-semibold text-navy-500 mb-1">حالة العقد</label>
            <select v-model="filters.contractState" class="input-premium" @change="handleFilterChange">
              <option value="all">كل العقود</option>
              <option value="current">لديه عقد حالي</option>
              <option value="upcoming">لديه عقد قادم</option>
              <option value="none">بدون عقد</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-navy-500 mb-1">العقار</label>
            <div class="relative">
              <select v-model="filters.buildingId" class="input-premium" :class="{ 'pr-8': filters.buildingId }" @change="handleBuildingChange">
                <option value="">كل العقارات</option>
                <option v-for="b in buildings" :key="b.name" :value="b.name">{{ b.building_name }}</option>
              </select>
              <button v-if="filters.buildingId" class="absolute left-2 top-1/2 -translate-y-1/2 text-navy-400 hover:text-navy-700" @click="clearBuilding">✕</button>
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-navy-500 mb-1">الوحدة</label>
            <div class="relative">
              <select v-model="filters.unitId" class="input-premium" :disabled="!filters.buildingId" :class="{ 'pr-8': filters.unitId, 'opacity-50 cursor-not-allowed': !filters.buildingId }" @change="handleFilterChange">
                <option value="">كل الوحدات</option>
                <option v-for="u in units" :key="u.name" :value="u.name">{{ u.unit_number }}</option>
              </select>
              <button v-if="filters.unitId" class="absolute left-2 top-1/2 -translate-y-1/2 text-navy-400 hover:text-navy-700" @click="clearUnit">✕</button>
            </div>
          </div>
        </div>
      </Card>

      <!-- Table -->
      <Card padding="none">
        <div v-if="loading && tenants.length === 0" class="flex items-center justify-center py-16">
          <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <EmptyState v-else-if="tenants.length === 0" title="لا يوجد مستأجرون" description="لم يتم العثور على مستأجرين مطابقين لبحثك." />
        <DataTable v-else :columns="columns">
          <TableRow v-for="t in tenants" :key="t.name" class="cursor-pointer hover:bg-gold-50/30" @click="router.push(`/tenants/${t.name}`)">
            <TableCell>
              <span class="font-semibold text-navy-800">{{ t.full_name }}</span>
            </TableCell>
            <TableCell>
              <div class="flex flex-col">
                <span class="text-sm text-navy-700">{{ t.national_id || '—' }}</span>
                <span v-if="t.phone" class="text-xs text-navy-400 inline-flex items-center gap-1" dir="ltr">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>
                  {{ t.phone }}
                </span>
                <span v-else class="text-xs text-navy-300">—</span>
              </div>
            </TableCell>
            <TableCell>
              <span v-if="t.currentContractsCount > 0" class="text-sm text-navy-700">{{ t.currentContractsCount }} {{ (t.currentContractsCount === 1 || t.currentContractsCount === 2) ? 'عقد' : 'عقود' }}</span>
              <span v-else class="text-navy-300">—</span>
            </TableCell>
            <TableCell><span class="tabular-nums text-red-600">{{ formatMoney(t.totalDues, currency) }}</span></TableCell>
            <TableCell><span class="tabular-nums text-emerald-600">{{ formatMoney(t.totalReceipts, currency) }}</span></TableCell>
            <TableCell>
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold tabular-nums" :class="balanceBadgeClass(t.balance)">
                {{ formatMoney(t.balance, currency) }}
              </span>
            </TableCell>
            <TableCell align="center">
              <div class="flex items-center justify-center gap-1" @click.stop>
                <router-link :to="`/tenants/${t.name}`" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="عرض">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
                <button class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="تعديل" @click="router.push({ name: 'TenantEdit', params: { id: t.name } })">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <button class="w-8 h-8 rounded-lg flex items-center justify-center text-red-500 hover:bg-red-50 transition-colors" title="حذف" @click="handleDelete(t)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            </TableCell>
          </TableRow>
        </DataTable>

        <!-- Pagination footer -->
        <div class="px-4 py-3 border-t border-ivory-300/60 text-xs text-navy-400 flex items-center justify-between">
          <span>إجمالي: {{ pagination.total }} مستأجر</span>
          <span v-if="filters.search">نتائج البحث: "{{ filters.search }}"</span>
        </div>
        <div v-if="pagination && pagination.totalPages > 1" class="flex items-center justify-center gap-3 px-4 py-3 border-t border-ivory-300/60">
          <button class="btn-premium btn-ghost px-2 py-1" :disabled="pagination.page <= 1" @click="onPageChange(pagination.page - 1)">السابق</button>
          <span class="text-sm text-navy-500">صفحة {{ pagination.page }} من {{ pagination.totalPages }}</span>
          <button class="btn-premium btn-ghost px-2 py-1" :disabled="pagination.page >= pagination.totalPages" @click="onPageChange(pagination.page + 1)">التالي</button>
        </div>
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { callApi, formatMoney, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const lessorLogo = computed(() => session.state.account?.settings?.logo || '')
const lessorName = computed(() => session.state.account?.settings?.landlord_name || '')

const columns = [
  { key: 'name', label: 'المستأجر' },
  { key: 'idphone', label: 'الهوية / الهاتف' },
  { key: 'contracts', label: 'العقود الحالية' },
  { key: 'dues', label: 'المستحقات' },
  { key: 'receipts', label: 'الدفعات' },
  { key: 'balance', label: 'الرصيد' },
  { key: 'actions', label: 'إجراءات', align: 'center' },
]

const tenants = ref([])
const loading = ref(true)
const printing = ref(false)
const pagination = ref(null)
const stats = ref(null)
const buildings = ref([])
const units = ref([])
const showAdvanced = ref(false)

const filters = ref({ search: '', contractState: 'all', buildingId: '', unitId: '' })

const activeAdvancedCount = computed(() => {
  let n = 0
  if (filters.value.contractState !== 'all') n++
  if (filters.value.buildingId) n++
  if (filters.value.unitId) n++
  return n
})

function balanceBadgeClass(bal) {
  if (bal > 0) return 'bg-red-50 text-red-700'
  if (bal < 0) return 'bg-emerald-50 text-emerald-700'
  return 'bg-navy-50 text-navy-500'
}

function handleSearchChange() {
  filters.value.page = 1
  fetchTenants(1)
}

function handleFilterChange() {
  fetchTenants(1)
}

async function handleBuildingChange() {
  filters.value.unitId = ''
  await loadUnits()
  fetchTenants(1)
}

function clearBuilding() {
  filters.value.buildingId = ''
  filters.value.unitId = ''
  units.value = []
  fetchTenants(1)
}

function clearUnit() {
  filters.value.unitId = ''
  fetchTenants(1)
}

function clearFilters() {
  filters.value = { search: '', contractState: 'all', buildingId: '', unitId: '' }
  units.value = []
  fetchTenants(1)
}

async function loadBuildings() {
  try {
    const res = await callApi('rental.rental.api.property.get_buildings', { simple: 1, include_inactive: 1 })
    buildings.value = Array.isArray(res) ? res : (res.buildings || [])
  } catch {
    buildings.value = []
  }
}

async function loadUnits() {
  if (!filters.value.buildingId) { units.value = []; return }
  try {
    const res = await callApi('rental.rental.api.property.get_units', { building: filters.value.buildingId, simple: 1, include_inactive: 1 })
    units.value = Array.isArray(res) ? res : (res.units || [])
  } catch {
    units.value = []
  }
}

async function fetchTenants(page = 1) {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.tenant.get_tenants', {
      page,
      search: filters.value.search || undefined,
      contract_state: filters.value.contractState !== 'all' ? filters.value.contractState : undefined,
      building: filters.value.buildingId || undefined,
      unit: filters.value.unitId || undefined,
      limit: 15,
    })
    tenants.value = res.tenants || []
    pagination.value = res.pagination
    stats.value = res.stats
    // Auto-correct page if beyond totalPages
    if (res.pagination && res.pagination.totalPages > 0 && page > res.pagination.totalPages) {
      fetchTenants(res.pagination.totalPages)
    }
  } catch (e) {
    toast.error(extractError(e) || 'حدث خطأ أثناء تحميل المستأجرين')
  } finally {
    loading.value = false
  }
}

function onPageChange(page) { fetchTenants(page) }

async function handleDelete(t) {
  const ok = await confirm({
    title: 'حذف المستأجر',
    message: 'سيتم حذف بيانات المستأجر. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'danger',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.tenant.delete_tenant', { name: t.name })
    fetchTenants(pagination.value?.page || 1)
  } catch (e) {
    toast.error(extractError(e) || 'حدث خطأ أثناء حذف المستأجر')
  }
}

async function handlePrint() {
  if (printing.value) return
  printing.value = true
  try {
    const res = await callApi('rental.rental.api.tenant.get_tenants', {
      print: 1,
      search: filters.value.search || undefined,
      contract_state: filters.value.contractState !== 'all' ? filters.value.contractState : undefined,
      building: filters.value.buildingId || undefined,
      unit: filters.value.unitId || undefined,
    })
    const list = res.tenants || []
    if (!list.length) {
      toast.info('لا يوجد مستأجرون مطابقون للطباعة')
      return
    }
    _openListPrintWindow(list, {}, res.print?.total ?? list.length)
  } catch (e) {
    toast.error(extractError(e) || 'حدث خطأ أثناء تجهيز التقرير')
  } finally {
    printing.value = false
  }
}

function _filterSummary() {
  const parts = []
  if (filters.value.search) parts.push(`البحث: ${filters.value.search}`)
  if (filters.value.contractState !== 'all') {
    const labels = { current: 'لديه عقد حالي', upcoming: 'لديه عقد قادم', none: 'بدون عقد' }
    parts.push(`حالة العقد: ${labels[filters.value.contractState]}`)
  }
  if (filters.value.buildingId) {
    const b = buildings.value.find(x => x.name === filters.value.buildingId)
    if (b) parts.push(`العقار: ${b.building_name}`)
  }
  if (filters.value.unitId) {
    const u = units.value.find(x => x.name === filters.value.unitId)
    if (u) parts.push(`الوحدة: ${u.unit_number}`)
  }
  return parts.join(' | ') || 'جميع المستأجرين'
}

function _openListPrintWindow(tenantsList, _statsObj, total) {
  const w = window.open('', '_blank', 'width=1000,height=700')
  if (!w) { toast.error('يرجى السماح بالنوافذ المنبثقة للطباعة'); return }
  const cur = currency.value
  const summary = _filterSummary()
  const hideContractCol = filters.value.contractState !== 'all'
  const hideUnitCol = !!filters.value.unitId

  const debtTotal = tenantsList.reduce((s, t) => s + (t.balance > 0 ? t.balance : 0), 0)
  const creditTotal = tenantsList.reduce((s, t) => s + (t.balance < 0 ? Math.abs(t.balance) : 0), 0)
  const debtCount = tenantsList.filter(t => t.balance > 0).length
  const creditCount = tenantsList.filter(t => t.balance < 0).length
  const zeroCount = tenantsList.filter(t => t.balance === 0).length

  const hideBuildingInLoc = !!filters.value.buildingId
  const rows = tenantsList.map((t, i) => {
    const loc = t.currentContract
      ? [!hideBuildingInLoc ? (t.currentContract.building_name || '') : '', t.currentContract.unit_number ? `وحدة ${t.currentContract.unit_number}` : ''].filter(Boolean).join(' — ') || '—'
      : '—'
    return `
    <tr>
      <td>${i + 1}</td>
      <td class="bold">${t.full_name}</td>
      <td>${t.national_id || '—'}</td>
      <td dir="ltr">${t.phone || '—'}</td>
      ${hideContractCol ? '' : `<td>${t.currentContract?.contract_number || '—'}</td>`}
      ${hideUnitCol ? '' : `<td>${loc}</td>`}
      <td class="num bold ${t.balance > 0 ? 'red' : t.balance < 0 ? 'green' : ''}">${formatMoney(t.balance, cur)}</td>
    </tr>`
  }).join('')

  w.document.write(`<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
    <title>تقرير المستأجرين</title><style>
      body{font-family:Arial,sans-serif;padding:24px;color:#1a2238}
      .print-header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:8px;margin-bottom:12px}
      .print-header .logo{height:65px;width:auto;object-fit:contain}
      .print-header .name{font-size:17px;font-weight:bold;color:#1a2238}
      .report-title{font-size:22px;font-weight:bold;text-align:center;margin:8px 0 4px;border-bottom:2px solid #1a2238;padding-bottom:8px}
      p.sub{font-size:13px;color:#64748b;margin:0 0 16px;text-align:center}
      table{width:100%;border-collapse:collapse;font-size:12px}
      th,td{border:1px solid #e2e8f0;padding:6px 8px;text-align:right}
      th{background:#f1f5f9} .num{text-align:left} .bold{font-weight:bold}
      .red{color:#dc2626} .green{color:#059669}
      .totals{margin-top:16px;font-size:13px;border-top:2px solid #1a2238;padding-top:12px}
      .totals div{padding:4px 0;margin-bottom:4px}
      .totals .label{color:#1a2238;font-weight:bold}
    </style></head><body>
    <div class="print-header">
      <div>${lessorLogo.value ? `<img src="${lessorLogo.value}" alt="شعار المؤجر" class="logo" />` : ''}</div>
      <div>${lessorName.value ? `<span class="name">${lessorName.value}</span>` : ''}</div>
    </div>
    <h1 class="report-title">تقرير المستأجرين</h1>
    <p class="sub">${summary || 'جميع المستأجرين'}</p>
    <table><thead><tr><th>#</th><th>اسم المستأجر</th><th>رقم الهوية</th><th>الهاتف</th>${hideContractCol ? '' : '<th>العقد الحالي / القادم</th>'}${hideUnitCol ? '' : '<th>العقار / الوحدة</th>'}<th class="num">الرصيد</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <div class="totals">
      <div><span class="label">عدد المستأجرين:</span> <b>${total}</b></div>
      <div><span class="label">عليهم رصيد:</span> <b>${debtCount}</b> مستأجر — <span class="label">إجمالي</span> <b>${formatMoney(debtTotal, cur)}</b></div>
      <div><span class="label">لهم رصيد:</span> <b>${creditCount}</b> مستأجر — <span class="label">إجمالي</span> <b>${formatMoney(creditTotal, cur)}</b></div>
      <div><span class="label">الرصيد صفر:</span> <b>${zeroCount}</b> مستأجر</div>
    </div>
    <script>window.onload=function(){window.print()}<\/script>
    </body></html>`)
  w.document.close()
}

onMounted(() => {
  loadBuildings()
  fetchTenants(1)
})
</script>
