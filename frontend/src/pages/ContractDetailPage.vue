<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 gap-3">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400">جاري تحميل بيانات العقد...</p>
      </div>

      <div v-else-if="!contract" class="text-center py-20">
        <p class="text-navy-400">العقد غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Contracts' })">العودة للقائمة</button>
      </div>

      <div v-else class="animate-fade-in">
        <PageHeader :title="contract.contract_number" :back-href="'/contracts'">
          <template #actions>
            <!-- Preview (source: page.tsx:348-350) -->
            <button class="btn-premium btn-outline" @click="router.push({ name: 'ContractPreview', params: { id: contract.name } })">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
              معاينة العقد
            </button>
            <!-- Edit (draft only, not archived/historical) (source: page.tsx:351-353) -->
            <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-outline" @click="router.push({ name: 'ContractEdit', params: { id: contract.name } })">تعديل</button>
            <!-- Approve (draft only, with CheckCircle icon) (source: page.tsx:354-358) -->
            <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-gold" @click="approveContract">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              اعتماد
            </button>
            <!-- Delete (draft only, with Trash2 icon) (source: page.tsx:359-367) -->
            <button v-if="!contract.is_archived && !isApprovedHistoricalLocal && contract.status === 'draft'" class="btn-premium btn-ghost text-red-600" @click="deleteContract">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              حذف
            </button>
            <!-- Renew (with RefreshCw icon) (source: page.tsx:368-375) -->
            <button v-if="canRenew" class="btn-premium btn-outline" @click="router.push({ name: 'ContractRenew', params: { id: contract.name } })">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
              تجديد العقد
            </button>
            <!-- Cancel (active only, with XCircle icon, destructive styling) (source: page.tsx:376-384) -->
            <button v-if="canCancel" class="btn-premium btn-outline text-red-600 border-red-200 hover:bg-red-50" @click="showCancelModal = true">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              إلغاء العقد
            </button>
            <!-- Evict (source: page.tsx:385-393) -->
            <button v-if="canEvict" class="btn-premium btn-outline text-red-600 border-red-200 hover:bg-red-50" @click="handleEvict">إخلاء</button>
            <!-- Archive/Unarchive (source: page.tsx:394-412) -->
            <button v-if="contract.is_archived" class="btn-premium btn-outline text-amber-600 border-amber-200 hover:bg-amber-50" @click="unarchiveContract">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
              إلغاء الأرشفة
            </button>
            <button v-else-if="canArchive" class="btn-premium btn-ghost" @click="archiveContract">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>
              أرشفة
            </button>
          </template>
        </PageHeader>

        <!-- Historical contract warning (approved historical only, source: page.tsx:435-448) -->
        <div v-if="isApprovedHistoricalLocal" class="mb-4 bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <div>
              <p class="text-sm font-medium text-amber-800">عقد تاريخي</p>
              <p class="text-xs text-amber-700/80 mt-1">
                <span v-if="contractDues.length === 0">لم يُنشأ لهذا العقد أي التزامات مالية. يُعتبر هذا العقد للأرشفة والاطلاع فقط.</span>
                <span v-else>عقد تاريخي تم إنشاؤه لسجل المستأجر. المستحقات أُضيفت إلى ذمة المستأجر لكن العقد لا يُؤثر على الحالة الحالية للوحدة.</span>
              </p>
            </div>
          </div>
        </div>

        <!-- Cancellation settlement alerts -->
        <div v-if="contract.status === 'cancelled' && pendingSettlement" class="mb-4 bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            <div>
              <p class="text-sm font-bold text-amber-800">إلغاء العقد لم تكتمل تسويته المالية</p>
              <p class="text-sm text-amber-700 mt-1">تم إلغاء العقد ولكن لم يتم إكمال التسوية المالية بعد. <button class="font-semibold underline text-amber-700 hover:text-amber-800" @click="router.push({ name: 'ContractSettlement', params: { id: contract.name } })">فتح التسوية</button></p>
            </div>
          </div>
        </div>
        <div v-if="contract.status === 'cancelled' && completedSettlement" class="mb-4 bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <div>
              <p class="text-sm font-bold text-emerald-800">تمت تسوية إلغاء العقد</p>
              <p class="text-sm text-emerald-700 mt-1">تمت تسوية إلغاء العقد بنجاح.</p>
            </div>
          </div>
        </div>

        <!-- Renewal indicator (badge-style, source: page.tsx:332-339) -->
        <div v-if="contract.renewed_from_contract && contract.previous_contract_number" class="mb-4">
          <router-link
            :to="`/contracts/${contract.renewed_from_contract}`"
            class="inline-flex items-center gap-1.5 status-badge border bg-navy-50 text-navy-600 border-navy-200 hover:bg-gold-50 hover:text-gold-600 hover:border-gold-200 transition-colors"
          >
            تجديد للعقد: {{ contract.previous_contract_number }}
          </router-link>
        </div>

        <!-- Balance cards -->
        <div v-if="balance" class="grid grid-cols-3 gap-4 mb-6">
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">المستحقات</p>
            <p class="text-2xl font-bold text-navy-800 tabular-nums">{{ formatMoney(balance.total_dues, currency) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">التحصيلات</p>
            <p class="text-2xl font-bold text-emerald-600 tabular-nums">{{ formatMoney(balance.total_receipts, currency) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الرصيد</p>
            <p class="text-2xl font-bold tabular-nums" :class="balance.balance > 0 ? 'text-red-600' : 'text-emerald-600'">{{ formatMoney(balance.balance, currency) }}</p>
          </Card>
        </div>

        <!-- Info cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">المستأجر</p>
            <router-link :to="`/tenants/${contract.tenant}`" class="font-bold text-navy-800 hover:text-gold-600">{{ contract.tenant_name || contract.tenant }}</router-link>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الوحدة</p>
            <p class="font-bold text-navy-800">{{ contract.building_name || '—' }} / {{ contract.unit_number || '—' }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">قيمة الإيجار</p>
            <p class="text-2xl font-bold text-navy-800 tabular-nums">{{ formatMoney(contract.rent_amount, currency) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الحالة</p>
            <div class="flex flex-wrap items-center gap-1">
              <StatusBadge :status="displayStatus.status" :label="displayStatus.label" />
              <StatusBadge v-if="isApprovedHistoricalLocal" status="archived" label="عقد تاريخي" />
              <span v-if="contract.status === 'active' && displayStatus.status === 'upcoming'" class="status-badge border bg-blue-50 text-blue-600 border-blue-200">عقد قادم</span>
              <span v-if="contract.status === 'active' && displayStatus.status === 'expired'" class="status-badge border bg-amber-50 text-amber-600 border-amber-200">عقد منتهي (ينتظر التحديث)</span>
              <StatusBadge v-if="contract.is_archived" status="archived" />
              <span v-if="contract.closed_by_renewal_at" class="status-badge border bg-blue-50 text-blue-600 border-blue-200">مغلق بتجديد</span>
            </div>
          </Card>
        </div>

        <!-- Contract details + Terms -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card padding="md">
            <template #title>تفاصيل العقد</template>
            <dl class="space-y-3 text-sm">
              <div class="flex justify-between"><dt class="text-navy-400">تاريخ البداية</dt><dd class="font-medium text-navy-800">{{ formatDate(contract.start_date) }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">تاريخ النهاية</dt><dd class="font-medium text-navy-800">{{ formatDate(contract.end_date) }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">تاريخ العقد</dt><dd class="font-medium text-navy-800">{{ formatDate(contract.contract_date) }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">تكرار الدفع</dt><dd class="font-medium text-navy-800">{{ frequencyLabel(contract.payment_frequency) }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">طريقة الدفع</dt><dd class="font-medium text-navy-800">{{ contract.payment_method || '—' }}</dd></div>
              <div class="flex justify-between" v-if="contract.first_due_date"><dt class="text-navy-400">أول استحقاق</dt><dd class="font-medium text-navy-800">{{ formatDate(contract.first_due_date) }}</dd></div>
              <div class="flex justify-between" v-if="contract.cancelled_at"><dt class="text-navy-400">تاريخ الإلغاء</dt><dd class="font-medium text-red-600">{{ formatDate(contract.cancelled_at) }}</dd></div>
              <div class="flex justify-between" v-if="contract.cancellation_reason"><dt class="text-navy-400">سبب الإلغاء</dt><dd class="font-medium text-red-600">{{ contract.cancellation_reason }}</dd></div>
            </dl>
          </Card>

          <Card padding="md">
            <template #title>الشروط والشهود</template>
            <div class="space-y-3 text-sm">
              <div>
                <p class="text-navy-400 mb-1">الشروط</p>
                <p class="text-navy-800 whitespace-pre-wrap">{{ contract.terms || '—' }}</p>
              </div>
              <div>
                <p class="text-navy-400 mb-1">الشهود</p>
                <p class="text-navy-800 whitespace-pre-wrap">{{ contract.witnesses || '—' }}</p>
              </div>
            </div>
          </Card>
        </div>

        <!-- Contract charges -->
        <Card v-if="contract.contract_charges?.length" padding="none" class="mb-6">
          <template #title>رسوم الخدمات</template>
          <DataTable :columns="chargeColumns">
            <TableRow v-for="ch in contract.contract_charges" :key="ch.name">
              <TableCell>{{ ch.due_type_name || ch.due_type }}</TableCell>
              <TableCell>{{ responsibilityLabel(ch.responsibility) }}</TableCell>
              <TableCell>{{ paymentByLabel(ch.payment_by) }}</TableCell>
              <TableCell>{{ methodLabel(ch.calculation_method) }}</TableCell>
              <TableCell><span class="font-bold tabular-nums">{{ ch.amount || '—' }}</span></TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Eviction data section -->
        <Card v-if="contract.eviction_data" padding="md" class="mb-6">
          <template #title>بيانات الإخلاء</template>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between"><dt class="text-navy-400">تاريخ الإخلاء</dt><dd class="font-medium text-red-600">{{ formatDate(contract.eviction_data.eviction_date) }}</dd></div>
            <div class="flex justify-between" v-if="contract.eviction_data.reason"><dt class="text-navy-400">السبب</dt><dd class="font-medium text-navy-800">{{ contract.eviction_data.reason }}</dd></div>
            <div class="flex justify-between" v-if="contract.eviction_data.notes"><dt class="text-navy-400">ملاحظات</dt><dd class="font-medium text-navy-800">{{ contract.eviction_data.notes }}</dd></div>
          </dl>
        </Card>

        <!-- Dues table -->
        <Card padding="none" class="mb-6">
          <template #title>التزامات العقد ({{ contractDues.length }})</template>
          <DataTable :columns="dueColumns">
            <TableRow
              v-for="d in contractDues"
              :key="d.name"
              class="cursor-pointer hover:bg-gold-50/30"
              :class="d.status === 'cancelled' || d.docstatus === 2 ? 'opacity-50' : ''"
              @click="router.push(`/dues/${d.name}`)"
            >
              <TableCell><span class="font-semibold text-navy-800">{{ d.due_number }}</span></TableCell>
              <TableCell>
                <div class="flex flex-col gap-0.5">
                  <span>{{ d.due_type_name || d.due_type }}</span>
                  <span v-if="d.source_type === 'additional' || d.sourceType === 'additional'" class="self-start rounded bg-navy-100 px-1.5 py-0.5 text-[10px] text-navy-500">إضافي</span>
                </div>
              </TableCell>
              <TableCell>{{ formatDate(d.transaction_date || d.transactionDate) }}</TableCell>
              <TableCell>
                <!-- Waiver-aware amount cell -->
                <div v-if="activeWaiverTotal(d) > 0" class="flex flex-col gap-0.5">
                  <span :class="isFullyWaived(d) ? 'text-navy-400' : 'text-navy-800'">
                    {{ formatMoney(effectiveDueAmount(d), currency) }}
                  </span>
                  <span class="text-xs text-navy-400 line-through">{{ formatMoney(Number(d.amount) || 0, currency) }}</span>
                  <span v-if="isFullyWaived(d)" class="inline-flex w-fit items-center rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">معفى بالكامل</span>
                  <span v-else class="inline-flex w-fit items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">معفى جزئياً</span>
                </div>
                <span v-else class="tabular-nums">{{ formatMoney(Number(d.amount) || 0, currency) }}</span>
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

        <!-- Receipts table -->
        <Card v-if="contractReceipts.length" padding="none" class="mb-6">
          <template #title>سندات القبض ({{ contractReceipts.length }})</template>
          <DataTable :columns="receiptColumns">
            <TableRow v-for="r in contractReceipts" :key="r.name" class="cursor-pointer hover:bg-gold-50/30" @click="router.push(`/receipts/${r.name}`)">
              <TableCell><span class="font-semibold text-navy-800">{{ r.receipt_number }}</span></TableCell>
              <TableCell>{{ formatDate(r.receipt_date) }}</TableCell>
              <TableCell><span class="tabular-nums">{{ formatMoney(r.amount, currency) }}</span></TableCell>
              <TableCell>{{ r.payment_method }}</TableCell>
              <TableCell><StatusBadge :status="r.docstatus === 1 ? 'active' : (r.docstatus === 2 ? 'cancelled' : 'draft')" /></TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Attachments (inline thumbnails, source: page.tsx:585-606) -->
        <Card padding="none" class="mb-6">
          <template #title>صور العقد ({{ contract.attachments?.length || 0 }})</template>
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

        <!-- Renewals section -->
        <Card v-if="contract.renewals?.length" padding="none" class="mb-6">
          <template #title>العقود المجددة ({{ contract.renewals.length }})</template>
          <DataTable :columns="renewalColumns">
            <TableRow v-for="rn in contract.renewals" :key="rn.name" class="cursor-pointer hover:bg-gold-50/30" @click="router.push(`/contracts/${rn.name}`)">
              <TableCell><span class="font-semibold text-navy-800">{{ rn.contract_number }}</span></TableCell>
              <TableCell><StatusBadge :status="rn.status" /></TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Cancel dialog -->
        <ContractCancelDialog
          v-model="showCancelModal"
          :contractStart="contract?.start_date || ''"
          :contractEnd="contract?.end_date || ''"
          @confirm="handleCancelContract"
        />

        <!-- Attachments modal -->
        <ContractAttachmentsModal
          v-model="showAttachmentsModal"
          :contractId="contract?.name || ''"
          :attachments="contract?.attachments || []"
          :status="contract?.status"
          :isArchived="contract?.is_archived"
          @upload="handleAttachmentUpload"
          @delete="handleAttachmentDelete"
        />

        <!-- Past contract dues dialog -->
        <PastContractDuesDialog
          v-model="showPastDuesDialog"
          :isLoading="isProcessing"
          @confirm="confirmApprove"
          @cancel="cancelPastDuesDialog"
        />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ContractCancelDialog from '@/components/contract/ContractCancelDialog.vue'
import ContractAttachmentsModal from '@/components/ContractAttachmentsModal.vue'
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
  isApprovedHistorical,
  hasApprovedRenewal,
  getContractDisplayStatus,
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
const contractReceipts = ref([])
const settlementInfo = ref(null)
const loading = ref(true)
const showCancelModal = ref(false)
const showAttachmentsModal = ref(false)
const showPastDuesDialog = ref(false)
const cancelling = ref(false)

const cancelForm = ref({ cancellation_date: '', reason: '' })
const isProcessing = ref(false)

const chargeColumns = [
  { key: 'type', label: 'النوع' },
  { key: 'resp', label: 'المسؤولية' },
  { key: 'payby', label: 'يدفعها' },
  { key: 'method', label: 'طريقة الحساب' },
  { key: 'amount', label: 'المبلغ' },
]
const dueColumns = [
  { key: 'number', label: 'رقم' },
  { key: 'type', label: 'النوع' },
  { key: 'date', label: 'التاريخ' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'status', label: 'الحالة' },
]
const receiptColumns = [
  { key: 'number', label: 'رقم' },
  { key: 'date', label: 'التاريخ' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'method', label: 'الطريقة' },
  { key: 'status', label: 'الحالة' },
]
const renewalColumns = [
  { key: 'number', label: 'رقم العقد' },
  { key: 'status', label: 'الحالة' },
]

const canCancel = computed(() => {
  const c = contract.value
  if (!c) return false
  return !c.is_archived && !isApprovedHistorical(c) && c.status === 'active' && !hasApprovedRenewal(c)
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
const canEvict = computed(() => {
  const c = contract.value
  if (!c) return false
  if (c.status === 'cancelled' && settlementInfo.value?.status === 'pending') return false
  return canEvictContract(c) || (c.status === 'cancelled' && settlementInfo.value?.status === 'completed')
})
const showSettlementButton = computed(() => contract.value?.status === 'cancelled' && settlementInfo.value?.status === 'pending')
const pendingSettlement = computed(() => contract.value?.status === 'cancelled' && settlementInfo.value?.status === 'pending')
const completedSettlement = computed(() => contract.value?.status === 'cancelled' && settlementInfo.value?.status === 'completed')

function frequencyLabel(f) {
  return { monthly: 'شهري', bi_monthly: 'كل شهرين', quarterly: 'ربع سنوي', semi_annual: 'نصف سنوي', annual: 'سنوي', once: 'مرة واحدة' }[f] || f
}
function responsibilityLabel(r) { return { tenant: 'المستأجر', landlord: 'المؤجر' }[r] || r }
function paymentByLabel(p) { return { tenant: 'المستأجر', landlord: 'المؤجر' }[p] || p }
function methodLabel(m) { return { fixed_periodic: 'دوري ثابت', metered: 'عداد', actual_bill: 'فاتورة فعلية', on_demand: 'عند الطلب' }[m] || m }

function isPastContract() {
  if (!contract.value?.start_date) return false
  return new Date(contract.value.start_date) < new Date()
}

const displayStatus = computed(() => {
  if (!contract.value) return { status: '', label: '' }
  return getContractDisplayStatus(contract.value)
})

const isApprovedHistoricalLocal = computed(() => {
  if (!contract.value) return false
  return isApprovedHistorical(contract.value)
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
  if (d.docstatus === 1) return 'active'
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
    // Fetch balance, dues, receipts, settlement in parallel
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
    promises.push(
      callApi('rental.rental.api.receipt.get_receipts', { contract: route.params.id, limit: 100 })
        .then(res => { contractReceipts.value = res.receipts || [] })
        .catch(() => { contractReceipts.value = [] })
    )
    if (contract.value?.status === 'cancelled') {
      promises.push(
        callApi('rental.rental.api.contract.get_cancellation_settlement', { contract: route.params.id })
          .then(res => { settlementInfo.value = res })
          .catch(() => { settlementInfo.value = null })
      )
    }
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
    showCancelModal.value = false
    // Source: page.tsx:237-238 — navigate to settlement page after cancel
    router.push({ name: 'ContractSettlement', params: { id: contract.value.name } })
  } catch (e) { toast.error(extractError(e)) } finally { cancelling.value = false }
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

async function handleAttachmentUpload(files) {
  if (!contract.value) return
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
      contract: contract.value.name,
      attachments: items,
    })
    fetchContract()
  } catch (e) { toast.error('حدث خطأ أثناء رفع الصور') }
}

async function handleAttachmentDelete(attachment) {
  if (!contract.value) return
  try {
    await callApi('rental.rental.api.contract.delete_attachment', {
      contract: contract.value.name,
      attachment: attachment.name || attachment.id,
    })
    fetchContract()
  } catch (e) { toast.error('حدث خطأ أثناء حذف الصور') }
}

onMounted(fetchContract)
</script>
