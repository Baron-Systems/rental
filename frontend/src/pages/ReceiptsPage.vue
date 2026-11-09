<template>
  <AppLayout>
    <div class="space-y-5 animate-fade-in p-6 lg:p-8" :class="{ 'print:hidden': printing }" dir="rtl">
      <PageHeader
        title="سندات القبض"
        description="تسجيل وإدارة دفعات المستأجرين"
        action-label="إنشاء سند قبض"
        @action="showForm = true"
      >
        <template #actions>
          <button
            type="button"
            class="btn-premium btn-outline inline-flex items-center gap-1.5"
            :disabled="printLoading || loading"
            @click="handlePrint"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
            {{ printLoading ? 'جاري تجهيز الطباعة...' : 'طباعة' }}
          </button>
        </template>
      </PageHeader>

      <!-- Stat Cards -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="إجمالي السندات" :value="stats.total || 0" icon="banknote" color="navy" />
        <StatCard label="المعتمَدة" :value="stats.approved || 0" icon="banknote" color="green" />
        <StatCard label="المسودة" :value="stats.draft || 0" icon="banknote" color="amber" />
        <StatCard label="الملغاة" :value="stats.cancelled || 0" icon="banknote" color="red" />
      </div>

      <!-- Filter Error -->
      <Alert v-if="filterError" type="error" :message="filterError" dismissible @dismiss="filterError = ''" />

      <!-- Search + Status + Tenant + Advanced toggle -->
      <div class="flex flex-col gap-3 lg:flex-row lg:items-start">
        <div class="relative flex-1">
          <svg class="absolute top-1/2 h-4 w-4 -translate-y-1/2 text-navy-400 icon-start" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input
            type="text"
            placeholder="بحث برقم السند..."
            class="input-premium w-full has-icon-start"
            :value="filters.search"
            @input="onSearchInput"
          />
        </div>
        <div class="w-full lg:w-44">
          <select class="input-premium" :value="filters.statusFilter" @change="onStatusChange">
            <option v-for="o in statusOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="w-full lg:w-64">
          <SearchableTenantSelect
            :model-value="filters.tenantId"
            :value-label="selectedFilterTenantName"
            placeholder="اختر المستأجر"
            @select="handleFilterTenantSelect"
          />
        </div>
        <button
          type="button"
          class="btn-premium btn-outline w-full lg:w-auto inline-flex items-center gap-1.5"
          @click="showAdvanced = !showAdvanced"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
          فلاتر إضافية
          <span
            v-if="activeAdvancedCount > 0"
            class="mr-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-gold-500 px-1.5 text-[10px] font-medium text-white"
          >{{ activeAdvancedCount }}</span>
        </button>
      </div>

      <!-- Advanced Filters -->
      <div v-if="showAdvanced" class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div class="space-y-1.5">
          <label class="text-xs text-navy-400">العقد</label>
          <div class="flex items-center gap-2">
            <select
              class="input-premium flex-1"
              :value="filters.contractId || 'all'"
              :disabled="!filters.tenantId || filterContractsLoading || filterContracts.length === 0"
              @change="handleFilterContractChange"
            >
              <option value="all">كل العقود</option>
              <option v-for="c in filterContracts" :key="c.name" :value="c.name">{{ formatContractLabel(c) }}</option>
            </select>
            <button
              v-if="filters.contractId"
              type="button"
              class="rounded-md p-1.5 text-navy-400 hover:bg-ivory-200 hover:text-navy-800"
              aria-label="مسح فلتر العقد"
              @click="clearContractFilter"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
        <div class="space-y-1.5">
          <label class="text-xs text-navy-400">طريقة الدفع</label>
          <select class="input-premium" :value="filters.paymentMethod || 'all'" @change="handlePaymentMethodChange">
            <option v-for="o in paymentMethodFilterOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <label class="text-xs text-navy-400">من تاريخ</label>
          <input type="date" dir="ltr" class="input-premium" :value="filters.fromDate" @input="handleDateChange('fromDate', $event.target.value)" />
        </div>
        <div class="space-y-1.5">
          <label class="text-xs text-navy-400">إلى تاريخ</label>
          <input type="date" dir="ltr" class="input-premium" :value="filters.toDate" @input="handleDateChange('toDate', $event.target.value)" />
        </div>
        <div class="flex flex-wrap items-center gap-2 sm:col-span-2 lg:col-span-4">
          <button v-if="filters.fromDate || filters.toDate" type="button" class="btn-premium btn-ghost text-sm inline-flex items-center gap-1" @click="clearDatePeriod">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            مسح الفترة
          </button>
          <button v-if="hasActiveFilters" type="button" class="btn-premium btn-ghost text-sm inline-flex items-center gap-1" @click="clearAllFilters">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            مسح الفلاتر
          </button>
        </div>
      </div>

      <!-- Table -->
      <Card padding="none" class="overflow-hidden shadow-soft">
        <DataTable :columns="columns">
          <tr v-if="receipts.length === 0">
            <td colspan="8" class="py-8">
              <EmptyState
                title="لا توجد سندات قبض"
                description="لم يتم العثور على سندات قبض مطابقة."
              >
                <template #action>
                  <button class="btn-premium btn-gold" @click="showForm = true">إنشاء سند قبض</button>
                </template>
              </EmptyState>
            </td>
          </tr>
          <TableRow v-for="r in receipts" :key="r.name" :class="r.status === 'cancelled' ? 'opacity-50' : 'group'">
            <TableCell>
              <router-link
                :to="`/receipts/${r.name}`"
                class="font-medium text-navy-800 hover:text-gold-600 transition-colors"
              >{{ r.receipt_number || 'مسودة' }}</router-link>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-[14px] font-medium text-navy-800">
                <svg class="h-3 w-3 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                {{ r.tenant_name || '—' }}
              </div>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-[13.5px] text-navy-400">
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                {{ formatDate(r.receipt_date) }}
              </div>
            </TableCell>
            <TableCell class="font-medium">{{ formatMoney(r.amount, currency) }}</TableCell>
            <TableCell>
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
                :class="r.transaction_type === 'refund' ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'"
              >{{ r.transaction_type === 'refund' ? 'رد للمستأجر' : 'قبض' }}</span>
            </TableCell>
            <TableCell><StatusBadge :status="r.payment_method" /></TableCell>
            <TableCell><StatusBadge :status="r.status" /></TableCell>
            <TableCell @click.stop>
              <div class="flex items-center gap-1">
                <router-link
                  :to="`/receipts/${r.name}`"
                  class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors"
                  title="عرض"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
                <button
                  v-if="r.status === 'draft'"
                  class="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-600 hover:bg-emerald-50 transition-colors"
                  title="اعتماد"
                  @click="handleApprove(r)"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                </button>
                <button
                  v-if="r.status === 'draft'"
                  class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors"
                  title="حذف"
                  @click="handleDelete(r)"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
                <button
                  v-if="r.status === 'approved'"
                  class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors"
                  title="إلغاء"
                  @click="handleCancel(r)"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
            </TableCell>
          </TableRow>
        </DataTable>
        <div class="border-t border-ivory-300/60 px-4 py-3 text-xs text-navy-400 flex items-center justify-between">
          <span>إجمالي: {{ pagination?.total || 0 }} سند</span>
          <span v-if="filters.search">نتائج البحث: "{{ filters.search }}"</span>
        </div>
        <div v-if="pagination && pagination.totalPages > 1" class="border-t border-ivory-300/60 px-4 py-3 flex items-center justify-center gap-3">
          <button
            class="btn-premium btn-outline text-sm"
            :disabled="pagination.page <= 1"
            @click="changePage(pagination.page - 1)"
          >السابق</button>
          <span class="text-sm text-navy-400">
            صفحة {{ pagination.page }} من {{ pagination.totalPages }}
          </span>
          <button
            class="btn-premium btn-outline text-sm"
            :disabled="pagination.page >= pagination.totalPages"
            @click="changePage(pagination.page + 1)"
          >التالي</button>
        </div>
      </Card>
    </div>

    <!-- Create Form Modal -->
    <ReceiptCreateModal v-if="showForm" @close="showForm = false" @created="filters.page = 1; loadReceipts()" />

    <!-- Print Document -->
    <div v-if="printData" class="print-only">
      <ReceiptsListPrintDocument
        :receipts="printData.receipts"
        :applied-filters="printData.appliedFilters"
        :total="printData.total"
        :total-amount="printData.totalAmount"
        :lessor-data="lessorData"
      />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Alert from '@/components/ui/Alert.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SearchableTenantSelect from '@/components/ui/SearchableTenantSelect.vue'
import ReceiptCreateModal from '@/components/receipt/ReceiptCreateModal.vue'
import ReceiptsListPrintDocument from '@/components/receipt/ReceiptsListPrintDocument.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const session = useSession()
const toast = useToast()
const { confirm, prompt } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const lessorData = computed(() => session.state.account?.settings || null)

const paymentMethodOptions = [
  { value: 'cash', label: 'نقداً' },
  { value: 'cheque', label: 'شيك' },
]

const paymentMethodFilterOptions = [
  { value: 'all', label: 'كل طرق الدفع' },
  ...paymentMethodOptions,
]

const statusOptions = [
  { value: 'all', label: 'كل الحالات' },
  { value: 'draft', label: 'مسودة' },
  { value: 'approved', label: 'معتمد' },
  { value: 'cancelled', label: 'ملغي' },
]

const columns = [
  { key: 'number', label: 'رقم السند' },
  { key: 'tenant', label: 'المستأجر' },
  { key: 'date', label: 'التاريخ' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'type', label: 'النوع' },
  { key: 'method', label: 'طريقة الدفع' },
  { key: 'status', label: 'الحالة' },
  { key: 'actions', label: 'إجراءات', align: 'center' },
]

const receipts = ref([])
const loading = ref(true)
const showForm = ref(false)
const showAdvanced = ref(false)
const filterError = ref('')

const selectedFilterTenantName = ref('')
const filterContracts = ref([])
const filterContractsLoading = ref(false)

const filters = reactive({
  search: '',
  statusFilter: 'all',
  tenantId: '',
  contractId: '',
  paymentMethod: '',
  fromDate: '',
  toDate: '',
  page: 1,
})

const pagination = ref({ page: 1, pageSize: 15, total: 0, totalPages: 0 })
const stats = ref({ total: 0, draft: 0, approved: 0, cancelled: 0 })

const printing = ref(false)
const printLoading = ref(false)
const printData = ref(null)

const activeAdvancedCount = computed(() => {
  return [filters.contractId, filters.paymentMethod, filters.fromDate, filters.toDate].filter(Boolean).length
})

const hasActiveFilters = computed(() => {
  return filters.statusFilter !== 'all' ||
    filters.tenantId !== '' ||
    filters.contractId !== '' ||
    filters.paymentMethod !== '' ||
    filters.fromDate !== '' ||
    filters.toDate !== ''
})

const activeFilters = computed(() => {
  const result = {}
  if (filters.search.trim()) result.search = filters.search.trim()
  if (filters.statusFilter !== 'all') {
    const label = statusOptions.find((o) => o.value === filters.statusFilter)?.label
    if (label) {
      result.status = label
      result.statusValue = filters.statusFilter
    }
  }
  if (filters.tenantId) {
    result.tenant = selectedFilterTenantName.value || filters.tenantId
  }
  if (filters.contractId) {
    const contract = filterContracts.value.find((c) => c.name === filters.contractId)
    result.contract = contract ? formatContractLabel(contract) : filters.contractId
  }
  if (filters.paymentMethod) {
    const label = paymentMethodFilterOptions.find((o) => o.value === filters.paymentMethod)?.label
    if (label) result.paymentMethod = label
  }
  if (filters.fromDate || filters.toDate) {
    const from = filters.fromDate ? formatDate(filters.fromDate) : '—'
    const to = filters.toDate ? formatDate(filters.toDate) : '—'
    result.dateRange = `${from} - ${to}`
  }
  return result
})

let debounceTimer = null
function onSearchInput(e) {
  filters.search = e.target.value
  filters.page = 1
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => loadReceipts(), 300)
}

function onStatusChange(e) {
  filters.statusFilter = e.target.value
  filters.page = 1
  loadReceipts()
}

async function loadReceipts() {
  if (filters.fromDate && filters.toDate && filters.fromDate > filters.toDate) {
    filterError.value = 'تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية'
    return
  }
  filterError.value = ''
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.receipt.get_receipts', {
      search: filters.search.trim() || undefined,
      status: filters.statusFilter !== 'all' ? filters.statusFilter : undefined,
      tenant: filters.tenantId || undefined,
      contract: filters.contractId || undefined,
      payment_method: filters.paymentMethod || undefined,
      from_date: filters.fromDate || undefined,
      to_date: filters.toDate || undefined,
      page: filters.page,
      limit: 15,
    })
    if (res.pagination && filters.page > res.pagination.totalPages) {
      const correctedPage = Math.max(1, res.pagination.totalPages)
      if (correctedPage !== filters.page) {
        filters.page = correctedPage
        return
      }
    }
    receipts.value = res.receipts || []
    pagination.value = res.pagination || { page: 1, pageSize: 15, total: 0, totalPages: 0 }
    stats.value = res.stats || { total: 0, draft: 0, approved: 0, cancelled: 0 }
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء تحميل سندات القبض')
  } finally {
    loading.value = false
  }
}

async function fetchContractsForTenant(tenantId) {
  const res = await callApi('rental.rental.api.contract.get_contracts', {
    tenant: tenantId,
    status: 'active,expired,cancelled,evicted',
    limit: 100,
  })
  return res.contracts || []
}

async function loadFilterContractsForTenant(tenantId) {
  filterContractsLoading.value = true
  filterContracts.value = []
  const list = await fetchContractsForTenant(tenantId)
  filterContracts.value = list
  filterContractsLoading.value = false
  return list
}

function formatContractLabel(c) {
  const building = c.building_name || c.building || '—'
  const unit = c.unit_number || c.unit || '—'
  return `${c.contract_number} — ${building} — الوحدة ${unit}`
}

async function handleFilterTenantSelect(item) {
  const tenantId = item?.name || ''
  const fullName = item?.full_name || ''
  selectedFilterTenantName.value = fullName
  filters.tenantId = tenantId
  filters.contractId = ''
  filters.page = 1
  filterContracts.value = []
  if (tenantId) {
    await loadFilterContractsForTenant(tenantId)
  }
  loadReceipts()
}

function handleFilterContractChange(e) {
  const value = e.target.value
  filters.contractId = value === 'all' ? '' : value
  filters.page = 1
  loadReceipts()
}

function handlePaymentMethodChange(e) {
  const value = e.target.value
  filters.paymentMethod = value === 'all' ? '' : value
  filters.page = 1
  loadReceipts()
}

function handleDateChange(type, value) {
  filters[type] = value
  filters.page = 1
  loadReceipts()
}

function clearContractFilter() {
  filters.contractId = ''
  filters.page = 1
  loadReceipts()
}

function clearDatePeriod() {
  filters.fromDate = ''
  filters.toDate = ''
  filters.page = 1
  loadReceipts()
}

function clearAllFilters() {
  filters.statusFilter = 'all'
  filters.tenantId = ''
  filters.contractId = ''
  filters.paymentMethod = ''
  filters.fromDate = ''
  filters.toDate = ''
  filters.page = 1
  selectedFilterTenantName.value = ''
  filterContracts.value = []
  loadReceipts()
}

function changePage(page) {
  filters.page = page
  loadReceipts()
}

async function handleDelete(r) {
  const confirmed = await confirm({
    title: 'حذف سند القبض',
    message: 'سيتم حذف مسودة سند القبض نهائيًا. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'danger',
    confirmLabel: 'حذف',
  })
  if (!confirmed) return
  try {
    await callApi('rental.rental.api.receipt.delete_receipt', { name: r.name })
    loadReceipts()
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء حذف سند القبض')
  }
}

async function handleApprove(r) {
  try {
    await callApi('rental.rental.api.receipt.approve_receipt', { name: r.name })
    loadReceipts()
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء اعتماد سند القبض')
  }
}

async function handleCancel(r) {
  const reason = await prompt({
    title: 'إلغاء سند القبض',
    message: 'أدخل سبب إلغاء سند القبض',
    inputLabel: 'سبب الإلغاء',
    variant: 'warning',
  })
  if (!reason) return
  try {
    await callApi('rental.rental.api.receipt.cancel_receipt', { name: r.name, reason })
    loadReceipts()
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء إلغاء سند القبض')
  }
}

async function handlePrint() {
  if (filters.fromDate && filters.toDate && filters.fromDate > filters.toDate) {
    toast.error('تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية')
    return
  }
  try {
    printLoading.value = true
    const res = await callApi('rental.rental.api.receipt.get_receipts', {
      search: filters.search.trim() || undefined,
      status: filters.statusFilter !== 'all' ? filters.statusFilter : undefined,
      tenant: filters.tenantId || undefined,
      contract: filters.contractId || undefined,
      payment_method: filters.paymentMethod || undefined,
      from_date: filters.fromDate || undefined,
      to_date: filters.toDate || undefined,
      print: 1,
    })
    const allReceipts = res.receipts || []
    if (allReceipts.length === 0) {
      toast.info('لا توجد سندات قبض مطابقة للطباعة')
      return
    }
    printData.value = {
      receipts: allReceipts,
      total: res.print?.total ?? allReceipts.length,
      totalAmount: res.print?.totalAmount ?? 0,
      appliedFilters: activeFilters.value,
    }
    printing.value = true
    await nextTick()
    await waitForImages()
    window.print()
    printing.value = false
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء تجهيز التقرير')
  } finally {
    printLoading.value = false
  }
}

function waitForImages() {
  return new Promise((resolve) => {
    const images = Array.from(document.images).filter((img) => !img.complete)
    if (images.length === 0) return resolve()
    let finished = 0
    const onFinish = () => { finished++; if (finished >= images.length) resolve() }
    images.forEach((img) => {
      img.addEventListener('load', onFinish)
      img.addEventListener('error', onFinish)
    })
  })
}

onMounted(loadReceipts)
</script>
