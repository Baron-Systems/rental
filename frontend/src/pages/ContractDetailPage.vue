<template>
  <AppLayout>
    <div class="p-6 lg:p-8 space-y-6" dir="rtl">
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400">جاري تحميل بيانات العقد...</p>
      </div>

      <div v-else-if="!contract" class="text-center py-20">
        <p class="text-navy-400">العقد غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Contracts' })">العودة للقائمة</button>
      </div>

      <template v-else>
        <!-- Header Card (source: page.tsx:295-415) -->
        <Card padding="lg">
          <div class="mb-3 flex items-center gap-2">
            <router-link to="/contracts" class="text-navy-400 hover:text-navy-800 inline-flex items-center gap-1 text-sm">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7m0 0l-7 7m7-7H3"/></svg>
              العقود
            </router-link>
          </div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <h1 class="text-2xl font-bold tracking-tight text-navy-900">عقد {{ contract.contract_number }}</h1>
              <div class="mt-3 flex flex-wrap items-center gap-2">
                <StatusBadge :status="displayStatus.status" :label="displayStatus.label" />
                <span v-if="isApprovedHistoricalLocal" class="status-badge border bg-navy-50 text-navy-500 border-navy-200">عقد تاريخي</span>
                <span v-if="contract.status === 'active' && periodStatus === 'upcoming'" class="status-badge border bg-blue-50 text-blue-600 border-blue-200">عقد قادم</span>
                <span v-if="contract.status === 'active' && periodStatus === 'past'" class="status-badge border bg-amber-50 text-amber-600 border-amber-200">عقد منتهي (ينتظر التحديث)</span>
                <span v-if="contract.is_archived" class="status-badge border bg-navy-50 text-navy-500 border-navy-200 inline-flex items-center gap-1">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
                  مؤرشف
                </span>
                <span v-if="contract.closed_by_renewal_at" class="status-badge border bg-blue-50 text-blue-600 border-blue-200">مغلق بتجديد</span>
                <router-link
                  v-if="contract.renewed_from_contract && (contract.previous_contract_number || contract.previous_contract?.contract_number)"
                  :to="`/contracts/${contract.renewed_from_contract}`"
                  class="status-badge border bg-navy-50 text-navy-500 border-navy-200 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors"
                >
                  تجديد للعقد: {{ contract.previous_contract_number || contract.previous_contract?.contract_number }}
                </router-link>
              </div>
              <div class="mt-3 flex flex-wrap items-center gap-3 text-sm text-navy-400">
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                  {{ contract.tenant_name || contract.tenant?.full_name || contract.tenant }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                  {{ contract.building_name || contract.building?.name || '—' }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                  {{ contract.unit_number || contract.unit?.unit_number || '—' }}
                </span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn-premium btn-outline inline-flex items-center gap-1.5" @click="router.push({ name: 'ContractPreview', params: { id: contract.name } })">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                معاينة العقد
              </button>
              <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-outline" @click="router.push({ name: 'ContractEdit', params: { id: contract.name } })">تعديل</button>
              <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-gold inline-flex items-center gap-1.5" @click="approveContract">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                اعتماد
              </button>
              <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-ghost text-red-600 inline-flex items-center gap-1.5" @click="deleteContract">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                حذف
              </button>
              <button v-if="canRenew" class="btn-premium btn-outline inline-flex items-center gap-1.5 text-blue-600 border-blue-200 hover:bg-blue-50" @click="router.push({ name: 'ContractRenew', params: { id: contract.name } })">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                تجديد العقد
              </button>
              <button v-if="canCancel" class="btn-premium btn-outline text-red-600 border-red-200 hover:bg-red-50 inline-flex items-center gap-1.5" @click="showCancelModal = true">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                إلغاء العقد
              </button>
              <button v-if="canEvict" class="btn-premium btn-outline text-red-600 border-red-200 hover:bg-red-50" @click="handleEvict">إخلاء</button>
              <button v-if="contract.is_archived" class="btn-premium btn-outline text-amber-600 border-amber-200 hover:bg-amber-50 inline-flex items-center gap-1.5" @click="unarchiveContract">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
                إلغاء الأرشفة
              </button>
              <button v-else-if="canArchive" class="btn-premium btn-ghost inline-flex items-center gap-1.5" @click="archiveContract">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
                أرشفة
              </button>
            </div>
          </div>
        </Card>

        <!-- Cancellation settlement alerts (source: page.tsx:417-433) -->
        <div v-if="contract.status === 'cancelled' && pendingSettlement" class="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <div>
              <p class="text-sm font-bold text-amber-800">إلغاء العقد لم تكتمل تسويته المالية</p>
              <p class="text-sm text-amber-700 mt-1">تم إلغاء العقد ولكن لم يتم إكمال التسوية المالية بعد. <button class="font-semibold underline text-amber-700 hover:text-amber-800" @click="router.push({ name: 'ContractSettlement', params: { id: contract.name } })">فتح التسوية</button></p>
            </div>
          </div>
        </div>
        <div v-if="contract.status === 'cancelled' && completedSettlement" class="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <div>
              <p class="text-sm font-bold text-emerald-800">تمت تسوية إلغاء العقد</p>
              <p class="text-sm text-emerald-700 mt-1">تمت تسوية إلغاء العقد بنجاح.</p>
            </div>
          </div>
        </div>

        <!-- Historical contract warning (source: page.tsx:435-448) -->
        <div v-if="isApprovedHistoricalLocal" class="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p class="text-sm font-medium text-amber-800 flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            عقد تاريخي
          </p>
          <p class="text-xs text-amber-700/80 mt-1">
            <span v-if="contractDues.length === 0">لم يُنشأ لهذا العقد أي التزامات مالية. يُعتبر هذا العقد للأرشفة والاطلاع فقط.</span>
            <span v-else>عقد تاريخي تم إنشاؤه لسجل المستأجر. المستحقات أُضيفت إلى ذمة المستأجر لكن العقد لا يُؤثر على الحالة الحالية للوحدة.</span>
          </p>
        </div>

        <!-- Info Grid: 4 StatCards (source: page.tsx:450-474) -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="قيمة الإيجار" :value="formatMoney(contract.rent_amount, currency)" icon="banknote" color="navy" />
          <StatCard label="تاريخ البدء" :value="formatDate(contract.start_date)" icon="calendar" color="navy" />
          <StatCard label="تاريخ الانتهاء" :value="formatDate(contract.end_date)" icon="calendar" color="navy" />
          <StatCard label="تكرار الدفع" :value="frequencyLabel(contract.payment_frequency)" icon="receipt" color="navy" />
        </div>

        <!-- Contract Balance: 3 StatCards (source: page.tsx:476-510) -->
        <div v-if="balance" class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard label="المستحقات" :value="formatMoney(balance.totalDues, currency)" icon="receipt" color="navy" />
          <StatCard label="التحصيلات" :value="formatMoney(balance.totalReceipts, currency)" icon="banknote" color="navy" />
          <StatCard label="الرصيد" :value="formatMoney(balance.balance, currency)" icon="wallet" :color="balance.balance > 0 ? 'red' : (balance.balance < 0 ? 'green' : 'navy')" />
        </div>

        <!-- Eviction data (source: page.tsx:512-537) -->
        <Card v-if="contract.status === 'evicted' && contract.evictions?.length" padding="none" class="border-amber-200">
          <div class="border-b border-amber-200 px-5 py-4">
            <h3 class="font-semibold text-amber-600">بيانات الإخلاء</h3>
          </div>
          <div class="p-5 space-y-3 text-sm">
            <div v-for="e in contract.evictions" :key="e.name" class="space-y-2">
              <div class="flex flex-wrap gap-x-6 gap-y-1">
                <div>
                  <span class="text-navy-400">تاريخ الإخلاء:</span>
                  <span class="font-medium text-navy-800">{{ formatDate(e.eviction_date) }}</span>
                </div>
              </div>
              <div v-if="e.notes">
                <span class="text-navy-400">ملاحظات:</span>
                <span class="font-medium text-navy-800">{{ e.notes }}</span>
              </div>
            </div>
          </div>
        </Card>

        <!-- Dues Table (source: page.tsx:539-583) -->
        <Card padding="none">
          <div class="flex items-center justify-between border-b border-ivory-300/60 px-5 py-4">
            <h3 class="font-semibold text-navy-800">التزامات العقد</h3>
            <span class="text-xs text-navy-400">{{ contractDues.length }} التزام</span>
          </div>
          <DataTable :columns="dueColumns">
            <TableRow
              v-for="d in contractDues"
              :key="d.name"
              class="cursor-pointer hover:bg-gold-50/30"
              :class="d.status === 'cancelled' || d.docstatus === 2 ? 'opacity-50' : ''"
              @click="router.push(`/dues/${d.name}`)"
            >
              <TableCell><span class="font-medium text-navy-800">{{ d.due_number }}</span></TableCell>
              <TableCell>
                <div class="flex flex-col gap-0.5">
                  <span class="text-sm text-navy-400">{{ d.due_type_name || d.due_type }}</span>
                  <span v-if="d.source_type === 'additional'" class="self-start rounded bg-navy-100 px-1.5 py-0.5 text-[10px] text-navy-500">إضافي</span>
                </div>
              </TableCell>
              <TableCell><span class="text-sm text-navy-400">{{ formatDate(d.transaction_date) }}</span></TableCell>
              <TableCell>
                <div v-if="activeWaiverTotal(d) > 0" class="flex flex-col gap-0.5">
                  <span :class="isFullyWaived(d) ? 'text-navy-400' : 'text-navy-800'">
                    {{ formatMoney(effectiveDueAmount(d), currency) }}
                  </span>
                  <span class="text-xs text-navy-400 line-through">{{ formatMoney(Number(d.amount) || 0, currency) }}</span>
                  <span v-if="isFullyWaived(d)" class="inline-flex w-fit items-center rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">معفى بالكامل</span>
                  <span v-else class="inline-flex w-fit items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">معفى جزئياً</span>
                </div>
                <span v-else class="font-medium text-navy-800 tabular-nums">{{ formatMoney(Number(d.amount) || 0, currency) }}</span>
              </TableCell>
              <TableCell><StatusBadge :status="dueDisplayStatus(d)" /></TableCell>
            </TableRow>
            <TableRow v-if="contractDues.length === 0">
              <TableCell colspan="5">
                <div class="text-center py-8">
                  <p class="text-sm font-medium text-navy-500">لا توجد التزامات</p>
                  <p class="text-xs text-navy-400 mt-1">لم يتم إنشاء التزامات لهذا العقد.</p>
                </div>
              </TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Attachments (source: page.tsx:585-606) -->
        <Card padding="none">
          <div class="flex items-center justify-between border-b border-ivory-300/60 px-5 py-4">
            <h3 class="font-semibold text-navy-800">صور العقد</h3>
            <span class="text-xs text-navy-400">{{ contract.attachments?.length || 0 }} صورة</span>
          </div>
          <div class="p-5">
            <div v-if="contract.attachments?.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
              <AttachmentThumbnail
                v-for="a in contract.attachments"
                :key="a.id || a.name"
                :contractId="contract.name"
                :attachment="a"
                :canDelete="!contract.is_archived && contract.status !== 'cancelled' && contract.status !== 'expired' && contract.status !== 'evicted'"
                @delete="handleAttachmentDelete"
              />
            </div>
            <div v-else class="text-center py-8">
              <p class="text-sm font-medium text-navy-500">لا توجد صور مرفقة</p>
              <p class="text-xs text-navy-400 mt-1">لم يتم إرفاق أي صور بهذا العقد.</p>
            </div>
          </div>
        </Card>

        <!-- Cancel dialog -->
        <ContractCancelDialog
          v-model="showCancelModal"
          :contractStart="contract?.start_date || ''"
          :contractEnd="contract?.end_date || ''"
          :onConfirm="handleCancelContract"
        />

        <!-- Past contract dues dialog -->
        <PastContractDuesDialog
          v-model="showPastDuesDialog"
          :isLoading="isProcessing"
          @confirm="confirmApprove"
          @cancel="cancelPastDuesDialog"
        />
      </template>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ContractCancelDialog from '@/components/contract/ContractCancelDialog.vue'
import PastContractDuesDialog from '@/components/PastContractDuesDialog.vue'
import AttachmentThumbnail from '@/components/AttachmentThumbnail.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import {
  canRenewContract,
  canEvictContract,
  canArchiveContract,
  getContractDisplayStatus,
  getContractPeriodStatus,
} from '@/utils/contractUtils.js'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const contract = ref(null)
const balance = ref(null)
const contractDues = ref([])
const loading = ref(true)
const showCancelModal = ref(false)
const showPastDuesDialog = ref(false)
const cancelling = ref(false)

const isProcessing = ref(false)

const dueColumns = [
  { key: 'number', label: 'رقم' },
  { key: 'type', label: 'النوع' },
  { key: 'date', label: 'التاريخ' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'status', label: 'الحالة' },
]

// Source: [id]/page.tsx:162 — isApprovedHistorical uses isHistorical field, NOT period status
const isApprovedHistoricalLocal = computed(() => {
  const c = contract.value
  if (!c) return false
  return (c.is_historical ?? c.isHistorical) && c.status !== 'draft'
})

// Source: [id]/page.tsx:164 — hasApprovedRenewal
const hasApprovedRenewalLocal = computed(() => {
  const c = contract.value
  if (!c) return false
  return (c.renewals || []).some((r) => r.status !== 'draft' && r.status !== 'cancelled' && r.status !== 'evicted')
})

const canCancel = computed(() => {
  const c = contract.value
  if (!c) return false
  return !c.is_archived && !isApprovedHistoricalLocal.value && c.status === 'active' && !hasApprovedRenewalLocal.value
})
const canArchive = computed(() => {
  const c = contract.value
  if (!c) return false
  return canArchiveContract(c)
})
const canRenew = computed(() => {
  const c = contract.value
  if (!c) return false
  return canRenewContract(c)
})
// Source: [id]/page.tsx:170 — needsEviction = canEvictContract(c), no settlement check
const canEvict = computed(() => {
  const c = contract.value
  if (!c) return false
  return canEvictContract(c)
})
// Source: [id]/page.tsx:417,429 — settlement from contract data (c.cancellationSettlement)
const pendingSettlement = computed(() => contract.value?.status === 'cancelled' && contract.value?.cancellation_settlement?.status === 'pending')
const completedSettlement = computed(() => contract.value?.status === 'cancelled' && contract.value?.cancellation_settlement?.status === 'completed')

// Source: page.tsx:161 — periodStatus for upcoming/past badges
const periodStatus = computed(() => {
  if (!contract.value) return ''
  return getContractPeriodStatus(contract.value.start_date, contract.value.end_date)
})

function frequencyLabel(f) {
  return { monthly: 'شهري', bi_monthly: 'كل شهرين', quarterly: 'ربع سنوي', semi_annual: 'نصف سنوي', annual: 'سنوي', once: 'مرة واحدة' }[f] || f
}

function isPastContract() {
  if (!contract.value?.start_date || !contract.value?.end_date) return false
  return getContractPeriodStatus(contract.value.start_date, contract.value.end_date) === 'past'
}

const displayStatus = computed(() => {
  if (!contract.value) return { status: '', label: '' }
  return getContractDisplayStatus(contract.value)
})

// ---- Waiver helpers ----
function activeWaiverTotal(due) {
  const waivers = due.waivers || []
  // Source: [id]/page.tsx:94-97 — strict status === 'active'
  return waivers
    .filter((w) => w.status === 'active')
    .reduce((sum, w) => sum + Number(w.amount), 0)
}

function effectiveDueAmount(due) {
  const original = Number(due.amount) || 0
  const waived = activeWaiverTotal(due)
  return Math.max(original - waived, 0)
}

function isFullyWaived(due) {
  const original = Number(due.amount) || 0
  return activeWaiverTotal(due) >= original
}

function dueDisplayStatus(d) {
  if (d.status) return d.status
  if (d.docstatus === 1) return 'approved'
  if (d.docstatus === 2) return 'cancelled'
  return 'draft'
}

async function fetchContract() {
  loading.value = true
  try {
    // Source: [id]/page.tsx:141-145 — expire contracts before fetching
    try {
      await callApi('rental.rental.api.contract.expire_contracts_api', {})
    } catch (e) {
      // Expire is best-effort; don't block page load
    }
    contract.value = await callApi('rental.rental.api.contract.get_contract', { name: route.params.id })
    // Source: [id]/page.tsx:142-148 — fetch balance and dues in parallel
    // cancellation_settlement is part of contract data (returned by get_contract)
    const promises = []
    promises.push(
      callApi('rental.rental.api.contract.get_contract_balance', { name: route.params.id })
        .then(res => { balance.value = res })
        .catch(() => { balance.value = null })
    )
    promises.push(
      callApi('rental.rental.api.due.get_dues', { contract: route.params.id, limit: 100 })
        .then(res => { contractDues.value = res.dues || [] })
        .catch(() => { contractDues.value = [] })
    )
    await Promise.all(promises)
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function approveContract() {
  if (isPastContract()) {
    showPastDuesDialog.value = true
    return
  }
  const ok = await confirm({ title: 'اعتماد العقد', message: 'هل أنت متأكد من اعتماد هذا العقد؟ سيتم تفعيل المستحقات المرتبطة به.', variant: 'warning', confirmLabel: 'اعتماد' })
  if (!ok) return
  await doApprove(true)
}

async function confirmApprove(generateDues) {
  showPastDuesDialog.value = false
  isProcessing.value = true
  try {
    await doApprove(generateDues)
  } finally {
    isProcessing.value = false
  }
}

function cancelPastDuesDialog() {
  showPastDuesDialog.value = false
  isProcessing.value = false
}

async function doApprove(generateDues) {
  try {
    await callApi('rental.rental.api.contract.approve_contract', { name: contract.value.name, generate_dues: generateDues ? 1 : 0 })
    fetchContract()
  } catch (e) { toast.error(extractError(e)) }
}

async function handleCancelContract(cancellationDate, reason) {
  if (!cancellationDate) { toast.error('يرجى تحديد تاريخ الإلغاء'); return }
  cancelling.value = true
  try {
    await callApi('rental.rental.api.contract.cancel_contract', {
      name: contract.value.name,
      cancellation_date: cancellationDate,
      reason: reason || undefined,
    })
    // Source: page.tsx:237-238 — navigate to settlement page after cancel
    router.push({ name: 'ContractSettlement', params: { id: contract.value.name } })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    // Source: old project page.tsx:237-243 — close dialog on BOTH success and error
    showCancelModal.value = false
    cancelling.value = false
  }
}

async function handleEvict() {
  if (contract.value.status === 'cancelled' && pendingSettlement.value) {
    const ok = await confirm({
      title: 'التسوية المالية غير مكتملة',
      message: 'لا يمكن إخلاء الوحدة قبل إكمال تسوية الالتزامات الناتجة عن إلغاء العقد.',
      variant: 'warning',
      confirmLabel: 'فتح التسوية',
    })
    if (ok) router.push({ name: 'ContractSettlement', params: { id: route.params.id } })
    return
  }
  router.push({ name: 'ContractEvict', params: { id: route.params.id } })
}

async function archiveContract() {
  const ok = await confirm({ title: 'أرشفة العقد', message: 'سيتم إخفاء العقد من القائمة الافتراضية دون تغيير حالته أو بياناته. متابعة؟', variant: 'warning', confirmLabel: 'أرشفة' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.archive_contract_api', { name: contract.value.name })
    fetchContract()
  } catch (e) { toast.error(extractError(e)) }
}

async function unarchiveContract() {
  const ok = await confirm({ title: 'إلغاء الأرشفة', message: 'هل أنت متأكد من إلغاء أرشفة هذا العقد؟', variant: 'warning', confirmLabel: 'إلغاء الأرشفة' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.unarchive_contract_api', { name: contract.value.name })
    fetchContract()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteContract() {
  const ok = await confirm({ title: 'حذف العقد', message: 'سيتم حذف العقد نهائيًا مع جميع بياناته. لا يمكن التراجع عن هذا الإجراء.', variant: 'danger', confirmLabel: 'حذف' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.contract.delete_contract', { name: contract.value.name })
    router.push({ name: 'Contracts' })
  } catch (e) { toast.error(extractError(e)) }
}

async function handleAttachmentDelete(attachment) {
  if (!contract.value) return
  try {
    await callApi('rental.rental.api.contract.delete_attachment', {
      contract: contract.value.name,
      attachment: attachment.name || attachment.id,
    })
    fetchContract()
  } catch (e) { toast.error(extractError(e)) }
}

onMounted(fetchContract)
</script>
