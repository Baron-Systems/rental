<template>
  <AppLayout>
    <!-- Source: contracts/page.tsx:515 — main content gets print:hidden when printing -->
    <div class="p-6 lg:p-8" :class="{ 'print:hidden': printing }" dir="rtl">
      <PageHeader title="العقود" description="إدارة العقود الإيجارية" action-label="عقد جديد" @action="router.push({ name: 'ContractNew' })">
        <template #actions>
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="loading || printing" @click="handlePrint">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
            <span>{{ printing ? 'جاري تجهيز الطباعة...' : 'طباعة' }}</span>
          </button>
        </template>
      </PageHeader>

      <!-- Stats -->
      <div v-if="stats" class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <StatCard label="إجمالي العقود" :value="stats.total || 0" icon="file" color="navy" />
        <StatCard label="العقود النشطة" :value="stats.active || 0" icon="file" color="green" />
        <StatCard label="العقود القادمة" :value="stats.upcoming || 0" icon="file" color="amber" />
      </div>

      <!-- Filter error -->
      <div v-if="filterError" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center justify-between">
        <span>{{ filterError }}</span>
        <button class="text-red-500 hover:text-red-700" @click="filterError = ''">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- Search & Basic Filters -->
      <Card padding="md" class="mb-4">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start">
          <!-- Search -->
          <div class="relative flex-1">
            <svg class="absolute top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400 pointer-events-none icon-start" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="filters.search" type="text" placeholder="بحث برقم العقد..." class="input-premium has-icon-start" @input="onFilterChange" />
          </div>
          <!-- Status -->
          <div class="w-full lg:w-44">
            <select v-model="filters.status" class="input-premium w-full" @change="onStatusFilterChange">
              <option value="all">كل الحالات</option>
              <option value="draft">مسودة</option>
              <option value="active">نشط</option>
              <option value="upcoming">قادمة</option>
              <option value="expired">منتهي</option>
              <option value="cancelled">ملغي</option>
              <option value="evicted">تم الإخلاء</option>
              <option value="archived">مؤرشفة</option>
            </select>
          </div>
          <!-- Tenant -->
          <div class="w-full lg:w-64">
            <SearchableTenantSelect
              v-model="filters.tenant"
              :placeholder="'اختر المستأجر'"
              :includeInactive="true"
              @select="onTenantFilterSelect"
            />
          </div>
          <!-- Advanced toggle -->
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" @click="showAdvanced = !showAdvanced">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
            فلاتر إضافية
            <span v-if="activeAdvancedCount > 0" class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-gold-500 px-1.5 text-[10px] font-medium text-white">{{ activeAdvancedCount }}</span>
          </button>
        </div>

        <!-- Advanced filters (collapsible) -->
        <div v-if="showAdvanced" class="mt-3 pt-3 border-t border-ivory-300/60 space-y-3">
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <!-- Building -->
            <div class="space-y-1.5">
              <label class="text-xs text-navy-400">العقار</label>
              <div class="flex items-center gap-2">
                <select v-model="filters.building" class="input-premium flex-1" @change="onBuildingFilterChange">
                  <option value="">كل العقارات</option>
                  <option v-for="b in buildings" :key="b.name" :value="b.name">{{ b.building_name }}</option>
                </select>
                <button v-if="filters.building" class="rounded-md p-1.5 text-navy-400 hover:bg-navy-50 hover:text-navy-700" @click="clearBuildingFilter">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
            <!-- Unit -->
            <div class="space-y-1.5">
              <label class="text-xs text-navy-400">الوحدة</label>
              <div class="flex items-center gap-2">
                <select v-model="filters.unit" class="input-premium flex-1" :disabled="!filters.building" @change="onFilterChange">
                  <option value="">كل الوحدات</option>
                  <option v-for="u in filterUnits" :key="u.name" :value="u.name">{{ u.unit_number }}</option>
                </select>
                <button v-if="filters.unit" class="rounded-md p-1.5 text-navy-400 hover:bg-navy-50 hover:text-navy-700" @click="clearUnitFilter">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
            <!-- From date -->
            <div class="space-y-1.5">
              <label class="text-xs text-navy-400">من تاريخ</label>
              <input v-model="filters.from_date" type="date" dir="ltr" class="input-premium w-full" @change="onFilterChange" />
            </div>
            <!-- To date -->
            <div class="space-y-1.5">
              <label class="text-xs text-navy-400">إلى تاريخ</label>
              <input v-model="filters.to_date" type="date" dir="ltr" class="input-premium w-full" @change="onFilterChange" />
            </div>
            <!-- Contract type -->
            <div class="space-y-1.5">
              <label class="text-xs text-navy-400">نوع العقد</label>
              <select v-model="filters.contract_type" class="input-premium w-full" @change="onFilterChange">
                <option value="all">كل العقود</option>
                <option value="original">عقد أصلي</option>
                <option value="renewal">تجديد</option>
              </select>
            </div>
          </div>

          <!-- Clear buttons -->
          <div class="flex flex-wrap items-center gap-2">
            <button v-if="filters.from_date || filters.to_date" class="text-sm text-navy-500 hover:text-navy-700 inline-flex items-center gap-1" @click="clearDatePeriod">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              مسح الفترة
            </button>
            <button v-if="hasAnyFilter" class="text-sm text-navy-500 hover:text-navy-700 inline-flex items-center gap-1" @click="clearAllFilters">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              مسح جميع الفلاتر
            </button>
          </div>
        </div>
      </Card>

      <!-- Table -->
      <Card padding="none">
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <EmptyState v-else-if="contracts.length === 0" title="لا توجد عقود" description="لم يتم العثور على عقود مطابقة لبحثك.">
          <template #action>
            <button class="btn-premium btn-gold" @click="router.push({ name: 'ContractNew' })">إنشاء عقد جديد</button>
          </template>
        </EmptyState>
        <DataTable v-else :columns="columns">
          <TableRow v-for="c in contracts" :key="c.name">
            <TableCell>
              <router-link :to="`/contracts/${c.name}`" class="font-semibold text-navy-800 hover:text-gold-600">{{ c.contract_number }}</router-link>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-sm font-medium text-navy-800">
                <svg class="w-3.5 h-3.5 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                {{ c.tenant_name || c.tenant || '—' }}
              </div>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-xs text-navy-400">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                {{ c.building_name || '—' }}
              </div>
              <div class="mt-0.5 flex items-center gap-1 text-sm font-medium text-navy-800">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                {{ c.unit_number || '—' }}
              </div>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-xs text-navy-400">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                {{ formatDate(c.start_date) }} - {{ formatDate(c.end_date) }}
              </div>
            </TableCell>
            <TableCell>
              <div class="text-sm font-medium text-navy-800">{{ formatMoney(c.rent_amount, currency) }}</div>
              <div class="text-xs text-navy-400">{{ frequencyLabel(c.payment_frequency) }}</div>
            </TableCell>
            <TableCell>
              <div class="flex flex-col items-start gap-1">
                <StatusBadge :status="displayStatus(c).status" :label="displayStatus(c).label" />
                <span v-if="c.is_archived" class="status-badge border bg-navy-50 text-navy-500 border-navy-200 text-xs px-2 py-0.5 rounded">مؤرشف</span>
                <span v-if="c.previous_contract_number" class="status-badge border bg-blue-50 text-blue-600 border-blue-200 text-xs px-2 py-0.5 rounded">تجديد: {{ c.previous_contract_number }}</span>
                <span v-if="c.closed_by_renewal_at" class="status-badge border bg-blue-50 text-blue-600 border-blue-200 text-xs px-2 py-0.5 rounded">مغلق بالتجديد</span>
              </div>
            </TableCell>
            <TableCell align="center">
              <div class="flex items-center justify-center gap-1">
                <!-- 1. Eye (details) (source: page.tsx:815-817) -->
                <router-link :to="`/contracts/${c.name}`" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="التفاصيل">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
                <!-- 2. CheckCircle (approve, draft only) (source: page.tsx:818-826) -->
                <button v-if="!c.is_archived && !isApprovedHistoricalLocal(c) && c.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-600 hover:bg-emerald-50 transition-colors" title="اعتماد" @click="approveContract(c)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                </button>
                <!-- 3. Trash2 (delete, draft only) (source: page.tsx:827-835) -->
                <button v-if="!c.is_archived && !isApprovedHistoricalLocal(c) && c.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors" title="حذف" @click="deleteContract(c)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
                <!-- 4. XCircle (cancel, active only) (source: page.tsx:836-844) -->
                <button v-if="!c.is_archived && !isApprovedHistoricalLocal(c) && c.status === 'active'" class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors" title="إلغاء العقد" @click="openCancelDialog(c)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
                <!-- 5. LogOut (evict, needsEviction) (source: page.tsx:845-849) -->
                <button v-if="canEvict(c)" class="w-8 h-8 rounded-lg flex items-center justify-center text-amber-600 hover:bg-amber-50 transition-colors" title="إخلاء" @click="router.push({ name: 'ContractEvict', params: { id: c.name } })">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                </button>
                <!-- 6. RefreshCw (renew, canRenew) (source: page.tsx:850-854) -->
                <button v-if="canRenew(c)" class="w-8 h-8 rounded-lg flex items-center justify-center text-gold-600 hover:bg-gold-50 transition-colors" title="تجديد العقد" @click="router.push({ name: 'ContractRenew', params: { id: c.name } })">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                </button>
                <!-- 7. Archive (source: page.tsx:855-883) -->
                <!-- Unarchive removed: archive is now final closure. -->
                <template v-if="!c.is_archived">
                  <button v-if="canArchive(c)" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-navy-50 transition-colors" title="أرشفة" @click="archiveContract(c)">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
                  </button>
                  <!-- 8. ImageIcon (attachments, not archived, not cancelled/expired/evicted) (source: page.tsx:874-882) -->
                  <button v-if="c.status !== 'cancelled' && c.status !== 'expired' && c.status !== 'evicted'" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-navy-50 transition-colors" title="صور العقد" @click="openAttachmentsModal(c)">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                  </button>
                </template>
              </div>
            </TableCell>
          </TableRow>
        </DataTable>
        <!-- Table footer -->
        <div v-if="!loading && contracts.length > 0" class="border-t border-ivory-300/60 px-4 py-3 text-xs text-navy-400 flex items-center justify-between">
          <span>إجمالي: {{ pagination?.total || 0 }} عقد</span>
          <span v-if="filters.search">نتائج البحث: "{{ filters.search }}"</span>
        </div>
        <Pagination v-if="pagination" :page="pagination.page" :page-size="pagination.pageSize" :total="pagination.total" @change="onPageChange" />
      </Card>

      <!-- Attachments Modal -->
      <ContractAttachmentsModal
        v-model="showAttachmentsModal"
        :contractId="attachmentsContractId"
        :attachments="attachmentsList"
        :loading="attachmentsLoading"
        :status="attachmentsContractStatus"
        :isArchived="attachmentsContractArchived"
        @upload="handleAttachmentUpload"
        @delete="handleAttachmentDelete"
      />

      <!-- Past Contract Dues Dialog -->
      <PastContractDuesDialog
        v-model="showDuesDialog"
        :isLoading="isProcessing"
        @confirm="handleApproveWithDuesChoice"
        @cancel="cancelDuesDialog"
      />

      <!-- Cancel Dialog -->
      <ContractCancelDialog
        v-model="showCancelDialog"
        :contractStart="cancelDialogContract?.start_date || ''"
        :contractEnd="cancelDialogContract?.end_date || ''"
        :onConfirm="handleCancelContract"
      />

    </div>

    <!-- Source: contracts/page.tsx:948-957 — print document is a sibling with print-only class -->
    <div v-if="printData" class="print-only">
      <ContractsListPrintDocument
        :contracts="printData.contracts"
        :appliedFilters="printData.appliedFilters"
        :total="printData.total"
        :lessorData="lessorData"
      />
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
import Pagination from '@/components/ui/Pagination.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ContractAttachmentsModal from '@/components/ContractAttachmentsModal.vue'
import PastContractDuesDialog from '@/components/PastContractDuesDialog.vue'
import ContractCancelDialog from '@/components/contract/ContractCancelDialog.vue'
import ContractsListPrintDocument from '@/components/contract/ContractsListPrintDocument.vue'
import SearchableTenantSelect from '@/components/ui/SearchableTenantSelect.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import {
  canRenewContract,
  canEvictContract,
  canArchiveContract,
  isApprovedHistorical,
  getContractDisplayStatus,
} from '@/utils/contractUtils.js'

const router = useRouter()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const lessorData = computed(() => session.state.account?.settings || null)

const columns = [
  { key: 'number', label: 'رقم العقد' },
  { key: 'tenant', label: 'المستأجر' },
  { key: 'unit', label: 'العقار / الوحدة' },
  { key: 'period', label: 'الفترة' },
  { key: 'rent', label: 'القيمة / الدورة' },
  { key: 'status', label: 'الحالة' },
  { key: 'actions', label: 'إجراءات', align: 'center' },
]

const contracts = ref([])
const loading = ref(true)
const pagination = ref(null)
const stats = ref(null)
const buildings = ref([])
const filterUnits = ref([])
const showAdvanced = ref(false)
const filterError = ref('')
const printing = ref(false)
const printData = ref(null)

const filters = ref({
  search: '', status: 'all', building: '', unit: '',
  contract_type: 'all', from_date: '', to_date: '', eviction: 0,
  tenant: '', page: 1,
})
const selectedTenantName = ref('')

// ---- Computed filter helpers ----
const activeAdvancedCount = computed(() => {
  return [
    filters.value.building,
    filters.value.unit,
    filters.value.from_date,
    filters.value.to_date,
    filters.value.contract_type !== 'all' ? 'x' : '',
  ].filter(Boolean).length
})

const hasAnyFilter = computed(() =>
  filters.value.status !== 'all' ||
  filters.value.tenant !== '' ||
  filters.value.building !== '' ||
  filters.value.unit !== '' ||
  filters.value.from_date !== '' ||
  filters.value.to_date !== '' ||
  filters.value.contract_type !== 'all' ||
  filters.value.eviction
)

const activeFilters = computed(() => {
  const result = {}
  if (filters.value.search.trim()) result.search = filters.value.search.trim()
  if (filters.value.eviction) result.eviction = true
  if (filters.value.status !== 'all' && !filters.value.eviction) {
    const labels = { draft: 'مسودة', active: 'نشط', upcoming: 'قادمة', expired: 'منتهي', cancelled: 'ملغي', evicted: 'تم الإخلاء', archived: 'مؤرشفة' }
    result.status = labels[filters.value.status] || filters.value.status
    result.statusValue = filters.value.status
  }
  if (filters.value.tenant) {
    result.tenant = selectedTenantName.value || filters.value.tenant
  }
  if (filters.value.building) {
    const b = buildings.value.find((x) => x.name === filters.value.building)
    result.building = b?.building_name || filters.value.building
    result.buildingId = filters.value.building
  }
  if (filters.value.unit) {
    const u = filterUnits.value.find((x) => x.name === filters.value.unit)
    result.unit = u?.unit_number || filters.value.unit
    result.unitId = filters.value.unit
  }
  if (filters.value.from_date || filters.value.to_date) {
    const from = filters.value.from_date ? formatDate(filters.value.from_date) : '—'
    const to = filters.value.to_date ? formatDate(filters.value.to_date) : '—'
    result.dateRange = `${from} - ${to}`
  }
  if (filters.value.contract_type !== 'all') {
    const labels = { original: 'عقد أصلي', renewal: 'تجديد' }
    result.contractType = labels[filters.value.contract_type] || filters.value.contract_type
    result.contractTypeValue = filters.value.contract_type
  }
  return result
})

// ---- Debounce ----
let debounceTimer = null
function onFilterChange() {
  filters.value.page = 1
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchContracts(), 400)
}

function onStatusFilterChange() {
  filters.value.eviction = 0
  filters.value.page = 1
  fetchContracts()
}

function activateEvictionFilter() {
  filters.value.status = 'all'
  filters.value.eviction = 1
  filters.value.page = 1
  fetchContracts()
}

// ---- Clear filter helpers ----
function clearBuildingFilter() {
  filters.value.building = ''
  filters.value.unit = ''
  filterUnits.value = []
  filters.value.page = 1
  fetchContracts()
}

function clearUnitFilter() {
  filters.value.unit = ''
  filters.value.page = 1
  fetchContracts()
}

function clearDatePeriod() {
  filters.value.from_date = ''
  filters.value.to_date = ''
  filters.value.page = 1
  fetchContracts()
}

function clearAllFilters() {
  // Source: contracts/page.tsx:290-303 — reset search too
  filters.value = {
    search: '',
    status: 'all', building: '', unit: '', tenant: '',
    contract_type: 'all', from_date: '', to_date: '', eviction: 0,
    page: 1,
  }
  selectedTenantName.value = ''
  filterUnits.value = []
  fetchContracts()
}

function onTenantFilterSelect(item) {
  selectedTenantName.value = item.full_name || item.name
  filters.value.page = 1
  fetchContracts()
}

// ---- Data fetching ----
async function fetchContracts() {
  loading.value = true
  filterError.value = ''
  try {
    if (filters.value.from_date && filters.value.to_date && filters.value.from_date > filters.value.to_date) {
      filterError.value = 'تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية'
      loading.value = false
      return
    }
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      search: filters.value.search || undefined,
      status: filters.value.status !== 'all' ? filters.value.status : undefined,
      archived: filters.value.status === 'archived' ? 'true' : 'false',
      tenant: filters.value.tenant || undefined,
      building: filters.value.building || undefined,
      unit: filters.value.unit || undefined,
      contract_type: filters.value.contract_type !== 'all' ? filters.value.contract_type : undefined,
      from_date: filters.value.from_date || undefined,
      to_date: filters.value.to_date || undefined,
      eviction: filters.value.eviction || undefined,
      page: filters.value.page, limit: 15,
    })
    contracts.value = res.contracts || []
    pagination.value = res.pagination
    stats.value = res.stats
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function loadBuildings() {
  try {
    const res = await callApi('rental.rental.api.property.get_buildings', { simple: 1, include_inactive: 1, limit: 100 })
    buildings.value = res || []
  } catch { buildings.value = [] }
}

async function onBuildingFilterChange() {
  filters.value.unit = ''
  filterUnits.value = []
  filters.value.page = 1
  if (!filters.value.building) { fetchContracts(); return }
  try {
    const res = await callApi('rental.rental.api.property.get_units', { building: filters.value.building, limit: 100 })
    filterUnits.value = res.units || res || []
  } catch { filterUnits.value = [] }
  fetchContracts()
}

function onPageChange(page) {
  filters.value.page = page
  fetchContracts()
}

// ---- Contract status helpers (delegated to shared utils) ----
function canEvict(c) {
  return canEvictContract(c)
}

function canRenew(c) {
  return canRenewContract(c)
}

function canArchive(c) {
  return canArchiveContract(c)
}

function isApprovedHistoricalLocal(c) {
  return isApprovedHistorical(c)
}

function displayStatus(c) {
  return getContractDisplayStatus(c)
}

function frequencyLabel(f) {
  return { monthly: 'شهري', bi_monthly: 'كل شهرين', quarterly: 'ربع سنوي', semi_annual: 'نصف سنوي', annual: 'سنوي' }[f] || f || ''
}

// ---- Actions ----
async function approveContract(c) {
  // Check if historical contract
  if (isApprovedHistoricalLocal(c)) {
    pendingContractId.value = c.name
    showDuesDialog.value = true
    return
  }
  const ok = await confirm({
    title: 'اعتماد العقد',
    message: 'هل أنت متأكد من اعتماد هذا العقد؟ سيتم تفعيل المستحقات المرتبطة به.',
    variant: 'warning',
    confirmLabel: 'اعتماد',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.approve_contract', { name: c.name, generate_dues: 1 })
    fetchContracts()
  } catch (e) {
    toast.error(extractError(e))
  }
}

// Past contract dues dialog
const showDuesDialog = ref(false)
const pendingContractId = ref(null)
const isProcessing = ref(false)

async function handleApproveWithDuesChoice(generateDues) {
  if (!pendingContractId.value) return
  isProcessing.value = true
  try {
    await callApi('rental.rental.api.contract.approve_contract', {
      name: pendingContractId.value,
      generate_dues: generateDues ? 1 : 0,
    })
    showDuesDialog.value = false
    pendingContractId.value = null
    fetchContracts()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    isProcessing.value = false
  }
}

function cancelDuesDialog() {
  showDuesDialog.value = false
  pendingContractId.value = null
  isProcessing.value = false
}

async function deleteContract(c) {
  const ok = await confirm({
    title: 'حذف العقد',
    message: 'سيتم حذف العقد نهائيًا مع جميع بياناته. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'danger',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.delete_contract', { name: c.name })
    fetchContracts()
  } catch (e) {
    toast.error(extractError(e))
  }
}

// Cancel dialog
const showCancelDialog = ref(false)
const cancelDialogContract = ref(null)

function openCancelDialog(c) {
  cancelDialogContract.value = c
  showCancelDialog.value = true
}

async function handleCancelContract(cancellationDate, reason) {
  if (!cancelDialogContract.value) return
  try {
    await callApi('rental.rental.api.contract.cancel_contract', {
      name: cancelDialogContract.value.name,
      cancellation_date: cancellationDate,
      reason: reason || undefined,
    })
    fetchContracts()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    // Source: old project page.tsx:428-434 — close dialog on BOTH success and error
    showCancelDialog.value = false
    cancelDialogContract.value = null
  }
}

async function archiveContract(c) {
  // Backend is the source of truth — fetch readiness first.
  let readiness = null
  try {
    readiness = await callApi('rental.rental.api.contract.get_archive_readiness_api', { name: c.name })
  } catch (e) { toast.error(extractError(e)); return }

  if (!readiness.eligible) {
    const reasons = (readiness.reasons && readiness.reasons.length)
      ? readiness.reasons.join('\n')
      : 'لا يمكن أرشفة العقد حاليًا'
    await confirm({
      title: 'لا يمكن أرشفة العقد',
      message: reasons,
      variant: 'danger',
      confirmLabel: 'إغلاق',
    })
    return
  }

  const ok = await confirm({
    title: 'أرشفة العقد',
    message: 'سيتم أرشفة العقد نهائيًا بعد التأكد من الإغلاق التشغيلي والمالي (الرصيد = صفر). يصبح العقد للقراءة فقط ولا يمكن التراجع عن هذا الإجراء.',
    variant: 'warning',
    confirmLabel: 'أرشفة نهائية',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.archive_contract_api', { name: c.name })
    fetchContracts()
  } catch (e) {
    toast.error(extractError(e))
  }
}

// ---- Attachments ----
const showAttachmentsModal = ref(false)
const attachmentsContractId = ref('')
const attachmentsList = ref([])
const attachmentsLoading = ref(false)
const attachmentsContractStatus = ref('')
const attachmentsContractArchived = ref(false)

async function openAttachmentsModal(c) {
  attachmentsContractId.value = c.name
  attachmentsContractStatus.value = c.status
  attachmentsContractArchived.value = c.is_archived
  showAttachmentsModal.value = true
  attachmentsLoading.value = true
  try {
    const res = await callApi('rental.rental.api.contract.get_attachments', { contract: c.name })
    attachmentsList.value = res?.attachments || []
  } catch {
    attachmentsList.value = []
  } finally {
    attachmentsLoading.value = false
  }
}

async function handleAttachmentUpload(files) {
  if (!attachmentsContractId.value) return
  try {
    const items = []
    for (const file of files) {
      const base64 = await new Promise((resolve) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result)
        reader.readAsDataURL(file)
      })
      items.push({ file_name: file.name, file_type: file.type, file_data: base64 })
    }
    await callApi('rental.rental.api.contract.upload_attachments', {
      contract: attachmentsContractId.value,
      attachments: items,
    })
    // Reload
    openAttachmentsModal({ name: attachmentsContractId.value, status: attachmentsContractStatus.value, is_archived: attachmentsContractArchived.value })
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function handleAttachmentDelete(attachment) {
  if (!attachmentsContractId.value) return
  try {
    await callApi('rental.rental.api.contract.delete_attachment', {
      contract: attachmentsContractId.value,
      attachment: attachment.name || attachment.id,
    })
    attachmentsList.value = attachmentsList.value.filter((a) => (a.name || a.id) !== (attachment.name || attachment.id))
  } catch (e) {
    toast.error(extractError(e))
  }
}

// ---- Print ----
async function handlePrint() {
  if (filters.value.from_date && filters.value.to_date && filters.value.from_date > filters.value.to_date) {
    toast.error('تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية')
    return
  }
  printing.value = true
  try {
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      search: filters.value.search || undefined,
      status: filters.value.status !== 'all' ? filters.value.status : undefined,
      archived: filters.value.status === 'archived' ? 'true' : 'false',
      tenant: filters.value.tenant || undefined,
      building: filters.value.building || undefined,
      unit: filters.value.unit || undefined,
      contract_type: filters.value.contract_type !== 'all' ? filters.value.contract_type : undefined,
      from_date: filters.value.from_date || undefined,
      to_date: filters.value.to_date || undefined,
      eviction: filters.value.eviction || undefined,
      print: 1, limit: 1000,
    })
    const allContracts = res.contracts || []
    if (allContracts.length === 0) {
      toast.info('لا توجد عقود مطابقة للطباعة')
      return
    }
    printData.value = {
      contracts: allContracts,
      total: res.print?.total ?? allContracts.length,
      appliedFilters: activeFilters.value,
    }
    // Wait for render then print
    await new Promise((r) => setTimeout(r, 200))
    window.print()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    printing.value = false
  }
}

onMounted(async () => {
  // Source: contracts/page.tsx:211-214 — expire contracts before loading list
  try {
    await callApi('rental.rental.api.contract.expire_contracts_api', {})
  } catch (e) {
    // Expire is best-effort; don't block page load
  }
  loadBuildings()
  fetchContracts()
})
</script>
