<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل بيانات التسوية...</p>
      </div>

      <div v-else-if="!settlementData" class="text-center py-20">
        <p class="text-sm font-medium text-navy-500">لا توجد تسوية</p>
        <p class="text-xs text-navy-400 mt-1">لم يتم إنشاء تسوية إلغاء لهذا العقد.</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'ContractDetail', params: { id: route.params.id } })">العودة للعقد</button>
      </div>

      <div v-else class="animate-fade-in space-y-6">
        <!-- Header card -->
        <Card padding="lg">
          <div class="mb-3 flex items-center gap-2">
            <router-link :to="`/contracts/${route.params.id}`" class="text-sm text-navy-400 hover:text-navy-700 flex items-center gap-1">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
              العقد
            </router-link>
          </div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
              <h1 class="text-2xl font-bold tracking-tight text-navy-900">تسوية إلغاء العقد</h1>
              <div v-if="contract" class="mt-3 flex flex-wrap items-center gap-3 text-sm text-navy-400">
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                  {{ contract.tenant_name || contract.tenant?.full_name || '—' }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                  {{ contract.building_name || contract.building?.building_name || contract.building?.name || '—' }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                  {{ contract.unit_number || contract.unit?.unit_number || contract.unit?.unitNumber || '—' }}
                </span>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-2 text-sm text-navy-400">
                <span class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                  تاريخ الإلغاء: {{ formatDate(settlement.cancellation_date || settlement.cancellationDate) }}
                </span>
                <span v-if="settlement.reason" class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  السبب: {{ settlement.reason }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium"
                :class="isCompleted ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="isCompleted ? 'bg-emerald-500' : 'bg-amber-500'"></span>
                {{ isCompleted ? 'مكتمل' : 'قيد الانتظار' }}
              </span>
            </div>
          </div>
        </Card>

        <!-- Totals cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card padding="md">
            <p class="text-xs text-navy-400 mb-1">المبلغ الأصلي</p>
            <p class="text-2xl font-bold text-navy-900 tabular-nums">{{ formatMoney(totals.originalTotal || totals.original_total, currency) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs text-navy-400 mb-1">إعفاءات سابقة</p>
            <p class="text-2xl font-bold text-navy-900 tabular-nums">{{ formatMoney(totals.waiverSnapshotTotal || totals.waiver_snapshot_total, currency) }}</p>
          </Card>
          <Card padding="md" class="bg-emerald-50/40">
            <p class="text-xs text-emerald-600 mb-1">إعفاء التسوية</p>
            <p class="text-2xl font-bold text-emerald-700 tabular-nums">{{ showComputedTotals ? formatMoney(totals.adjustmentTotal || totals.adjustment_total, currency) : '—' }}</p>
          </Card>
          <Card padding="md" class="bg-amber-50/40">
            <p class="text-xs text-amber-600 mb-1">المبلغ المستحق</p>
            <p class="text-2xl font-bold text-amber-700 tabular-nums">{{ showComputedTotals ? formatMoney(totals.settledTotal || totals.settled_total, currency) : '—' }}</p>
          </Card>
        </div>

        <!-- Unresolved dues warning -->
        <div v-if="unresolvedDues.length > 0" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <div>
              <p class="text-sm font-bold text-amber-800">بيانات تاريخية غير محسومة</p>
              <p class="text-sm text-amber-700 mt-1">يوجد {{ unresolvedDues.length }} التزام لم يتم تحديد فترته. لا يمكن إكمال التسوية قبل تحديد الفترة لكل منها.</p>
            </div>
          </div>
        </div>

        <!-- Settlement items -->
        <div class="space-y-4">
          <h2 class="text-lg font-semibold text-navy-900">بنود التسوية</h2>
          <div v-if="settlement.items.length === 0" class="text-center py-12">
            <p class="text-sm font-medium text-navy-500">لا توجد بنود</p>
            <p class="text-xs text-navy-400 mt-1">لا توجد التزامات جارية تتطلب تسوية.</p>
          </div>
          <Card v-for="item in settlement.items" :key="item.id || item.name" padding="md" :class="isCompleted ? 'opacity-70' : ''">
            <!-- Item header -->
            <div class="mb-4">
              <p class="font-semibold text-navy-900">
                {{ item.due?.due_type_name || item.due?.dueType?.name || item.due_type_name || '—' }}
                — {{ item.due?.due_number || item.due?.dueNumber || item.due_id || item.name }}
              </p>
              <p class="text-xs text-navy-400 mt-0.5">
                <template v-if="item.due?.period_start && item.due?.period_end">
                  من {{ formatDate(item.due.period_start) }} إلى {{ formatDate(item.due.period_end) }}
                </template>
                <template v-else-if="item.due?.periodStart && item.due?.periodEnd">
                  من {{ formatDate(item.due.periodStart) }} إلى {{ formatDate(item.due.periodEnd) }}
                </template>
                <template v-else>الفترة غير محددة</template>
              </p>
            </div>

            <!-- Amounts grid -->
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
              <div class="rounded-lg bg-navy-50 p-3">
                <div class="text-xs text-navy-400">المبلغ الأصلي</div>
                <div class="text-base font-semibold text-navy-900">{{ formatMoney(Number(item.original_amount || item.originalAmount), currency) }}</div>
              </div>
              <div class="rounded-lg bg-navy-50 p-3">
                <div class="text-xs text-navy-400">الإعفاءات السابقة</div>
                <div class="text-base font-semibold text-navy-900">{{ formatMoney(getManualWaiverTotal(item.due), currency) }}</div>
              </div>
              <div class="rounded-lg bg-navy-50 p-3">
                <div class="text-xs text-navy-400">المبلغ الحالي</div>
                <div class="text-base font-semibold text-navy-900">{{ formatMoney(getCurrentAmount(item), currency) }}</div>
              </div>
              <template v-if="item.gross_settled_amount != null || item.grossSettledAmount != null">
                <div v-if="item.adjustment_amount != null || item.adjustmentAmount != null" class="rounded-lg bg-emerald-50 p-3">
                  <div class="text-xs text-emerald-600">إعفاء التسوية</div>
                  <div class="text-base font-semibold text-emerald-700">{{ formatMoney(Number(item.adjustment_amount || item.adjustmentAmount), currency) }}</div>
                </div>
                <div class="rounded-lg bg-blue-50 p-3">
                  <div class="text-xs text-blue-600">المبلغ المستحق</div>
                  <div class="text-base font-semibold text-blue-700">{{ formatMoney(Number(item.gross_settled_amount || item.grossSettledAmount), currency) }}</div>
                </div>
              </template>
            </div>

            <!-- Prorated info -->
            <div v-if="item.decision === 'prorated' && (item.prorated_occupied_days || item.proratedOccupiedDays) && (item.prorated_total_days || item.proratedTotalDays)" class="mb-4 flex items-center gap-2 text-sm text-blue-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 12h6m-6 4h6m-6-8h6M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
              الأيام المستخدمة: {{ item.prorated_occupied_days || item.proratedOccupiedDays }} من {{ item.prorated_total_days || item.proratedTotalDays }} يوم
            </div>

            <!-- Decision buttons -->
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                type="button"
                class="btn-premium"
                :class="item.decision === 'keep_full' ? 'btn-gold' : 'btn-outline'"
                :disabled="isCompleted || itemSaving[item.id || item.name]"
                @click="applyDecision(item, 'keep_full')"
              >
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                استحقاق كامل
              </button>
              <button
                type="button"
                class="btn-premium"
                :class="item.decision === 'prorated' ? 'btn-gold' : 'btn-outline'"
                :disabled="isCompleted || itemSaving[item.id || item.name]"
                @click="applyDecision(item, 'prorated')"
              >
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 12h6m-6 4h6m-6-8h6M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                احتساب نسبي حسب الأيام
              </button>
              <button
                type="button"
                class="btn-premium"
                :class="item.decision === 'manual_settlement' ? 'btn-gold' : 'btn-outline'"
                :disabled="isCompleted || itemSaving[item.id || item.name]"
                @click="selectDecision(item, 'manual_settlement')"
              >
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                تحديد المبلغ المستحق
              </button>
              <button
                type="button"
                class="btn-premium"
                :class="item.decision === 'full_waiver' ? 'btn-danger' : 'btn-outline text-red-600 border-red-300 hover:bg-red-50'"
                :disabled="isCompleted || itemSaving[item.id || item.name]"
                @click="applyDecision(item, 'full_waiver')"
              >
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                إعفاء كامل
              </button>
            </div>

            <!-- Manual settlement input -->
            <div v-if="item.decision === 'manual_settlement'" class="mt-4 rounded-lg border border-navy-200 p-4">
              <label class="block text-sm font-medium text-navy-800 mb-0.5">المبلغ المستحق</label>
              <p class="mb-2 text-xs text-navy-400">أدخل المبلغ الذي سيبقى مستحقًا على المستأجر بعد التسوية. (0 - {{ getCurrentAmount(item).toFixed(2) }})</p>
              <div class="flex gap-2">
                <input
                  v-model="manualGross[item.id || item.name]"
                  type="number"
                  min="0"
                  step="0.01"
                  :max="getCurrentAmount(item)"
                  placeholder="0.00"
                  class="input-premium flex-1"
                  :disabled="isCompleted"
                />
                <button class="btn-premium btn-gold" :disabled="isCompleted || itemSaving[item.id || item.name]" @click="applyManualDecision(item)">تطبيق</button>
              </div>
            </div>

            <!-- Full waiver warning -->
            <div v-if="item.decision === 'full_waiver'" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p class="text-sm font-bold text-amber-800 mb-1">تحذير: إعفاء كامل</p>
              <p class="text-sm text-amber-700">عند إكمال التسوية سيتم إنشاء إعفاء بقيمة {{ formatMoney(getCurrentAmount(item), currency) }} ليصبح المبلغ المستحق صفرًا، مع الإبقاء على أصل الالتزام تاريخيًا.</p>
            </div>
          </Card>
        </div>

        <!-- Unresolved dues table -->
        <Card v-if="unresolvedDues.length > 0" padding="none">
          <template #title>بيانات تاريخية غير محسومة</template>
          <p class="text-xs text-navy-400 px-5 pt-3">حدد فترة كل التزام لتمكين إكمال التسوية.</p>
          <DataTable :columns="unresolvedColumns" class="mt-3">
            <TableRow v-for="due in unresolvedDues" :key="due.due_id || due.dueId">
              <TableCell>{{ due.due_number || due.dueNumber || '-' }}</TableCell>
              <TableCell>{{ due.due_type || due.dueType || '—' }}</TableCell>
              <TableCell>{{ formatDate(due.due_date || due.dueDate) }}</TableCell>
              <TableCell class="text-xs">{{ due.blocking_reason || due.blockingReason || '—' }}</TableCell>
              <TableCell>
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <input
                    v-model="duePeriod[due.due_id || due.dueId].start"
                    type="date"
                    dir="ltr"
                    class="input-premium w-full sm:w-40"
                    :disabled="isCompleted"
                  />
                  <input
                    v-model="duePeriod[due.due_id || due.dueId].end"
                    type="date"
                    dir="ltr"
                    class="input-premium w-full sm:w-40"
                    :disabled="isCompleted"
                  />
                  <button
                    class="btn-premium btn-outline text-sm"
                    :disabled="isCompleted || !duePeriod[due.due_id || due.dueId].start || !duePeriod[due.due_id || due.dueId].end"
                    @click="resolveDue(due)"
                  >
                    حفظ
                  </button>
                </div>
              </TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Actions -->
        <div class="flex justify-end gap-3 rounded-xl border border-ivory-300 bg-white p-4">
          <button class="btn-premium btn-outline" @click="router.push({ name: 'ContractDetail', params: { id: route.params.id } })">العودة للعقد</button>
          <button
            class="btn-premium"
            :class="isCompleted ? 'btn-outline' : 'btn-gold'"
            :disabled="isCompleted || completing"
            @click="completeSettlement"
          >
            <span v-if="completing" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <svg v-if="isCompleted" class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <svg v-else class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 12h6m-6 4h6m-6-8h6M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
            {{ isCompleted ? 'تمت التسوية' : 'إكمال التسوية' }}
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const contract = ref(null)
const settlementData = ref(null)
const loading = ref(true)
const completing = ref(false)
const itemSaving = reactive({})
const manualGross = reactive({})
const duePeriod = reactive({})

const settlement = computed(() => settlementData.value?.settlement || null)
const unresolvedDues = computed(() => settlementData.value?.unresolvedDues || settlementData.value?.unresolved_dues || [])
const totals = computed(() => settlementData.value?.totals || {})
const isCompleted = computed(() => settlement.value?.status === 'completed')
const hasPendingItems = computed(() =>
  (settlement.value?.items || []).some((i) => i.decision === 'pending' || i.status === 'pending')
)
const hasUnresolvedDues = computed(() => unresolvedDues.value.length > 0)
const showComputedTotals = computed(() => !hasPendingItems.value && !hasUnresolvedDues.value)

const unresolvedColumns = [
  { key: 'number', label: 'الرقم' },
  { key: 'type', label: 'النوع' },
  { key: 'date', label: 'تاريخ الاستحقاق' },
  { key: 'reason', label: 'سبب المنع' },
  { key: 'period', label: 'الفترة' },
]

function roundMoneySafe(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

function getManualWaiverTotal(due) {
  const waivers = due?.waivers || []
  // Source: contract-cancellation-settlement.service.ts:31-36 —
  // strict status === 'active' and sourceType !== 'contract_cancellation'
  return waivers
    .filter((w) => w.status === 'active' && (w.source_type || w.sourceType) !== 'contract_cancellation')
    .reduce((sum, w) => sum + Number(w.amount), 0)
}

function getCurrentAmount(item) {
  const original = Number(item.original_amount || item.originalAmount || 0)
  const manualWaiver = getManualWaiverTotal(item.due)
  return Math.max(0, roundMoneySafe(original - manualWaiver))
}

async function loadData() {
  loading.value = true
  try {
    const [contractRes, settlementRes] = await Promise.all([
      callApi('rental.rental.api.contract.get_contract', { name: route.params.id }).catch(() => null),
      callApi('rental.rental.api.cancellation_settlement.get_settlement', { contract: route.params.id }).catch(() => null),
    ])
    contract.value = contractRes?.contract || contractRes
    if (settlementRes && (settlementRes.settlement || settlementRes.name)) {
      settlementData.value = settlementRes
      // Initialize manualGross and duePeriod
      for (const item of (settlementRes.settlement?.items || [])) {
        const id = item.id || item.name
        if (item.gross_settled_amount != null || item.grossSettledAmount != null) {
          manualGross[id] = String(Number(item.gross_settled_amount || item.grossSettledAmount))
        }
      }
      for (const due of (settlementRes.unresolvedDues || settlementRes.unresolved_dues || [])) {
        const id = due.due_id || due.dueId
        if (!duePeriod[id]) duePeriod[id] = { start: '', end: '' }
      }
    } else {
      settlementData.value = null
    }
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

function selectDecision(item, decision) {
  // For manual_settlement, just select without applying
  item.decision = decision
}

async function applyDecision(item, decision) {
  const itemId = item.id || item.name
  let finalAmount
  if (decision === 'manual_settlement') {
    const value = parseFloat(manualGross[itemId])
    const currentAmount = getCurrentAmount(item)
    if (Number.isNaN(value) || value < 0 || value > currentAmount) {
      toast.error(currentAmount > 0 ? `أدخل المبلغ المستحق بين 0 و ${currentAmount.toFixed(2)}` : 'لا يمكن إدخال مبلغ مستحق لالتزام غير مستحق')
      return
    }
    finalAmount = roundMoneySafe(value)
  }
  item.decision = decision
  itemSaving[itemId] = true
  try {
    const payload = { item: itemId, decision }
    if (finalAmount !== undefined) payload.gross_settled_amount = finalAmount
    await callApi('rental.rental.api.cancellation_settlement.update_item_decision', payload)
    toast.success('تم تحديث القرار')
    await loadData()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    itemSaving[itemId] = false
  }
}

async function applyManualDecision(item) {
  await applyDecision(item, 'manual_settlement')
}

async function resolveDue(due) {
  const dueId = due.due_id || due.dueId
  const period = duePeriod[dueId]
  if (!period?.start || !period?.end) return
  try {
    await callApi('rental.rental.api.cancellation_settlement.resolve_due_period', {
      settlement: settlement.value.name,
      due_id: dueId,
      period_start: period.start,
      period_end: period.end,
    })
    toast.success('تم تحديد فترة الالتزام')
    await loadData()
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function completeSettlement() {
  if (!settlementData.value) return
  const missing = []
  if (unresolvedDues.value.length > 0) {
    missing.push(`${unresolvedDues.value.length} التزام لم يتم تحديد فترته`)
  }
  const pendingItems = (settlement.value.items || []).filter((i) => i.status === 'pending' || i.decision === 'pending')
  if (pendingItems.length > 0) {
    missing.push(`${pendingItems.length} عنصر لم يتم اتخاذ قرار بشأنه`)
  }
  if (missing.length > 0) {
    await confirm({
      title: 'لا يمكن إكمال التسوية',
      message: missing.join(' • '),
      variant: 'warning',
      confirmLabel: 'حسناً',
    })
    return
  }
  const ok = await confirm({
    title: 'إكمال التسوية',
    message: 'سيتم تطبيق التسويات المالية وإقفال الإعفاءات. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'warning',
    confirmLabel: 'إكمال',
  })
  if (!ok) return
  completing.value = true
  try {
    await callApi('rental.rental.api.cancellation_settlement.complete_settlement', { name: settlement.value.name })
    toast.success('تمت تسوية إلغاء العقد بنجاح')
    await loadData()
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    completing.value = false
  }
}

onMounted(loadData)
</script>
