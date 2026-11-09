<template>
  <!-- Create receipt modal. Mount with v-if; emits close / created. -->
  <div class="fixed inset-x-0 bottom-0 top-16 z-50 flex items-center justify-center p-4 md:p-6 print:hidden" dir="rtl">
    <div class="absolute inset-0 bg-navy-950/20 backdrop-blur-sm" @click="emit('close')" />
    <div class="relative z-10 w-full max-w-2xl max-h-[calc(100%-32px)] md:max-h-[calc(100%-48px)] overflow-hidden rounded-[14px] border border-ivory-300 bg-white shadow-xl animate-scale-in flex flex-col">
      <div class="shrink-0 p-6 pb-4 flex items-center justify-between">
        <div>
          <h3 class="text-base font-bold text-navy-900">إنشاء سند</h3>
          <p class="mt-0.5 text-sm text-navy-400">سجل دفعة أو رد مبلغ لمستأجر</p>
        </div>
        <button
          type="button"
          class="inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-navy-400 transition-colors hover:bg-ivory-200 hover:text-navy-800"
          @click="emit('close')"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <form ref="formRef" class="flex flex-col min-h-0 flex-1" @submit.prevent="handleSubmit(false)">
        <div ref="formBodyRef" class="flex-1 min-h-0 overflow-y-auto p-6 pt-4">
          <Alert v-if="error" type="error" title="تعذّر إنشاء سند القبض" :message="error" class="mb-4" />

          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">
                المستأجر <span class="text-red-500">*</span>
              </label>
              <SearchableTenantSelect
                :model-value="formData.tenantId"
                :value-label="selectedFormTenantName"
                placeholder="اختر المستأجر"
                @select="handleFormTenantSelect"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">
                العقد <span class="text-red-500">*</span>
              </label>
              <select
                class="input-premium"
                :value="formData.contractId"
                :disabled="!formData.tenantId || formContractsLoading || formContracts.length === 0"
                @change="handleContractChange($event.target.value)"
              >
                <option value="">{{ formContractPlaceholder }}</option>
                <option v-for="c in formContracts" :key="c.name" :value="c.name">{{ formatContractLabel(c) }}</option>
              </select>
              <span v-if="selectedContract" class="flex items-center gap-1 text-xs text-navy-400">
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                الوحدة {{ selectedContract.unit_number || '—' }} — {{ selectedContract.building_name || '—' }}
              </span>
            </div>

            <!-- Contract Balance Card -->
            <div v-if="formData.contractId && contractBalance !== null" class="md:col-span-2 rounded-lg border border-ivory-300 bg-ivory-50 px-4 py-3">
              <div class="flex items-center justify-between gap-3">
                <div class="flex items-center gap-2">
                  <svg class="h-4 w-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/></svg>
                  <span class="text-sm font-medium text-navy-700">رصيد العقد</span>
                  <span
                    :class="contractBalance > 0 ? 'text-red-600' : contractBalance < 0 ? 'text-emerald-600' : 'text-navy-400'"
                    class="text-sm font-bold"
                  >{{ contractBalanceLabel }}</span>
                </div>
                <button
                  v-if="canShowSettlement"
                  type="button"
                  class="btn-premium btn-outline text-sm inline-flex items-center gap-1.5"
                  @click="handleSettleBalance"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  تسوية كامل الرصيد
                </button>
              </div>
            </div>

            <!-- Transaction Type -->
            <div v-if="showTransactionType" class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">نوع الحركة</label>
              <select class="input-premium" v-model="formData.transactionType" @change="formData.amount = ''">
                <option value="receipt">قبض من المستأجر</option>
                <option v-if="canRefund" value="refund">رد للمستأجر</option>
              </select>
            </div>

            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">
                التاريخ <span class="text-red-500">*</span>
              </label>
              <input type="date" dir="ltr" class="input-premium" v-model="formData.receiptDate" required />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">
                المبلغ <span class="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="0.00"
                class="input-premium"
                :class="{ 'border-red-400': amountError }"
                v-model="formData.amount"
                required
              />
              <span v-if="amountError" class="text-xs text-red-500">{{ amountError }}</span>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-800">طريقة الدفع</label>
              <select class="input-premium" v-model="formData.paymentMethod">
                <option v-for="o in paymentMethodOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>

            <template v-if="formData.paymentMethod === 'cheque'">
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">
                  رقم الشيك <span class="text-red-500">*</span>
                </label>
                <input type="text" placeholder="رقم الشيك" class="input-premium" v-model="formData.referenceNumber" required />
              </div>
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">تاريخ الشيك</label>
                <input type="date" dir="ltr" class="input-premium" v-model="formData.chequeDate" />
              </div>
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">اسم البنك</label>
                <input type="text" placeholder="اسم البنك" class="input-premium" v-model="formData.bankName" />
              </div>
            </template>

            <div class="space-y-1.5 md:col-span-2">
              <ReceiptAttachmentField v-model="formData.attachment" :payment-method="formData.paymentMethod" />
            </div>

            <div class="space-y-1.5 md:col-span-2">
              <label class="text-sm font-medium text-navy-800">ملاحظات</label>
              <input type="text" placeholder="ملاحظات إضافية..." class="input-premium" v-model="formData.notes" />
            </div>
          </div>
        </div>
        <div class="shrink-0 px-6 py-4" :class="{ 'border-t border-ivory-300': bodyHasOverflow }">
          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button type="button" class="btn-premium btn-outline" @click="emit('close')">إلغاء</button>
            <button type="submit" class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="creating">
              <span v-if="creating && !approving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ السند
            </button>
            <button type="button" class="btn-premium btn-gold inline-flex items-center gap-1.5" :disabled="creating" @click="submitAndApprove">
              <span v-if="creating && approving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ واعتماد
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Alert from '@/components/ui/Alert.vue'
import SearchableTenantSelect from '@/components/ui/SearchableTenantSelect.vue'
import ReceiptAttachmentField from '@/components/ReceiptAttachmentField.vue'
import { callApi, formatMoney, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  // Optional preset: { name, full_name }
  tenant: { type: Object, default: null },
  // Optional preset contract id (must belong to the tenant)
  contract: { type: String, default: '' },
})
const emit = defineEmits(['close', 'created'])

const session = useSession()
const toast = useToast()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const paymentMethodOptions = [
  { value: 'cash', label: 'نقداً' },
  { value: 'cheque', label: 'شيك' },
]

const formRef = ref(null)
const formBodyRef = ref(null)
const bodyHasOverflow = ref(false)
const error = ref('')
const creating = ref(false)
const approving = ref(false)

const formData = reactive({
  tenantId: '',
  contractId: '',
  transactionType: 'receipt',
  receiptDate: new Date().toISOString().split('T')[0],
  amount: '',
  paymentMethod: 'cash',
  referenceNumber: '',
  chequeDate: '',
  bankName: '',
  attachment: null,
  notes: '',
})

const contractBalance = ref(null)
const canRefund = ref(false)
const canSettle = ref(false)
const isContractArchived = ref(false)

const selectedFormTenantName = ref('')
const formContracts = ref([])
const formContractsLoading = ref(false)

const selectedContract = computed(() => formContracts.value.find((c) => c.name === formData.contractId))

const formContractPlaceholder = computed(() => {
  if (!formData.tenantId) return 'اختر المستأجر أولاً'
  if (formContractsLoading.value) return 'جاري تحميل العقود...'
  return 'اختر العقد'
})

function formatContractLabel(c) {
  const building = c.building_name || c.building || '—'
  const unit = c.unit_number || c.unit || '—'
  return `${c.contract_number} — ${building} — الوحدة ${unit}`
}

function resetContractInfo() {
  formData.transactionType = 'receipt'
  formData.amount = ''
  contractBalance.value = null
  canRefund.value = false
  canSettle.value = false
  isContractArchived.value = false
}

async function loadFormContractsForTenant(tenantId) {
  formContractsLoading.value = true
  formContracts.value = []
  try {
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      tenant: tenantId,
      status: 'active,expired,cancelled,evicted',
      limit: 100,
    })
    formContracts.value = res.contracts || []
  } catch {
    formContracts.value = []
  } finally {
    formContractsLoading.value = false
  }
  return formContracts.value
}

async function loadContractSettlementInfo(contractId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_contract_settlement_info', { name: contractId })
    contractBalance.value = res.balance
    canRefund.value = res.can_refund
    canSettle.value = res.can_settle
    isContractArchived.value = res.is_archived
  } catch {
    resetContractInfo()
  }
}

async function handleFormTenantSelect(item) {
  selectedFormTenantName.value = item?.full_name || ''
  formData.tenantId = item?.name || ''
  formData.contractId = ''
  formContracts.value = []
  resetContractInfo()
  if (formData.tenantId) {
    const list = await loadFormContractsForTenant(formData.tenantId)
    if (list.length === 1) await handleContractChange(list[0].name)
  }
}

async function handleContractChange(contractId) {
  formData.contractId = contractId
  resetContractInfo()
  if (contractId) await loadContractSettlementInfo(contractId)
}

const contractBalanceLabel = computed(() => {
  if (contractBalance.value === null) return ''
  const formatted = formatMoney(Math.abs(contractBalance.value), currency.value)
  if (contractBalance.value > 0) return `على المستأجر: ${formatted}`
  if (contractBalance.value < 0) return `لصالح المستأجر: ${formatted}`
  return `رصيد العقد: ${formatted}`
})

const showTransactionType = computed(() => {
  if (!formData.contractId || isContractArchived.value) return false
  return canRefund.value
})

const canShowSettlement = computed(() => {
  if (!canSettle.value) return false
  if (contractBalance.value === null || contractBalance.value === 0) return false
  if (contractBalance.value > 0) return true
  return contractBalance.value < 0 && canRefund.value
})

const amountError = computed(() => {
  const amt = parseFloat(formData.amount)
  if (!formData.amount || isNaN(amt)) return ''
  if (amt <= 0) return 'المبلغ يجب أن يكون موجبًا'
  if (formData.transactionType === 'refund' && contractBalance.value !== null) {
    if (amt > Math.abs(contractBalance.value) + 0.005) return 'مبلغ الرد لا يمكن أن يتجاوز الرصيد الدائن للعقد.'
  }
  return ''
})

function handleSettleBalance() {
  if (contractBalance.value === null || contractBalance.value === 0) return
  if (contractBalance.value > 0) {
    formData.transactionType = 'receipt'
    formData.amount = contractBalance.value.toFixed(2)
  } else if (contractBalance.value < 0 && canRefund.value) {
    formData.transactionType = 'refund'
    formData.amount = Math.abs(contractBalance.value).toFixed(2)
  }
}

// "Save & approve" is a type=button, so run the browser's native required-field checks first.
function submitAndApprove() {
  if (formRef.value && !formRef.value.reportValidity()) return
  handleSubmit(true)
}

async function handleSubmit(approve) {
  if (creating.value) return
  error.value = ''
  creating.value = true
  approving.value = approve
  const payload = {
    tenant: formData.tenantId,
    contract: formData.contractId,
    transaction_type: formData.transactionType,
    receipt_date: formData.receiptDate,
    amount: formData.amount,
    payment_method: formData.paymentMethod,
    notes: formData.notes || null,
    attachment: formData.attachment,
    reference_number: formData.paymentMethod === 'cheque' ? formData.referenceNumber : null,
    cheque_date: formData.paymentMethod === 'cheque' ? (formData.chequeDate || null) : null,
    bank_name: formData.paymentMethod === 'cheque' ? (formData.bankName || null) : null,
  }

  let receipt = null
  try {
    receipt = await callApi('rental.rental.api.receipt.create_receipt', payload)
  } catch (err) {
    error.value = extractError(err) || 'حدث خطأ'
    creating.value = false
    return
  }

  if (approve && receipt?.name) {
    try {
      await callApi('rental.rental.api.receipt.approve_receipt', { name: receipt.name })
      toast.success('تم حفظ السند واعتماده')
    } catch (err) {
      toast.error(`تم حفظ السند كمسودة لكن تعذّر اعتماده: ${extractError(err)}`)
    }
  } else {
    toast.success('تم حفظ السند')
  }
  creating.value = false
  emit('created', receipt)
  emit('close')
}

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  await nextTick()
  const el = formBodyRef.value
  bodyHasOverflow.value = !!el && el.scrollHeight > el.clientHeight

  if (!props.tenant?.name) return
  await handleFormTenantSelect({ name: props.tenant.name, full_name: props.tenant.full_name || props.tenant.name })
  if (props.contract && props.contract !== formData.contractId && formContracts.value.some((c) => c.name === props.contract)) {
    await handleContractChange(props.contract)
  }
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>
