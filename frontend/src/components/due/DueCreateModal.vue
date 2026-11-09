<template>
  <!-- Create due modal (source: dues/page.tsx:960-1184). Mount with v-if; emits close / created. -->
  <div class="fixed inset-x-0 bottom-0 top-16 z-50 flex items-center justify-center p-4 md:p-6 print:hidden" dir="rtl">
    <div class="absolute inset-0 bg-foreground/20 backdrop-blur-sm" @click="emit('close')"></div>
    <div class="relative z-10 w-full max-w-2xl max-h-[calc(100%-32px)] md:max-h-[calc(100%-48px)] overflow-hidden rounded-[14px] border border-ivory-300 bg-white shadow-soft-lg animate-scale-in flex flex-col">
      <!-- Header -->
      <div class="shrink-0 p-6 pb-4 flex items-center justify-between">
        <div>
          <h3 class="text-base font-bold text-navy-900">إنشاء التزام</h3>
          <p class="mt-0.5 text-sm text-navy-400">إضافة التزام يدوي على عقد</p>
        </div>
        <button type="button" @click="emit('close')" class="inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-navy-400 transition-colors hover:bg-ivory-200 hover:text-navy-700">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <form @submit.prevent="createDue(false)" class="flex flex-col min-h-0 flex-1">
        <div class="flex-1 min-h-0 overflow-y-auto p-6 pt-4">
          <div v-if="createError" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ createError }}</div>

          <div class="space-y-4">
            <!-- Kind toggle (source: page.tsx:987-1004) -->
            <div class="space-y-2.5">
              <label class="text-sm font-medium text-navy-800">نوع الالتزام</label>
              <div class="inline-flex h-9 rounded-[10px] border border-ivory-300 bg-ivory-100 p-0.5">
                <button type="button" @click="handleKindChange('contractual')" :class="['h-8 rounded-lg px-3 text-xs font-medium transition-colors', formMode === 'contractual' ? 'bg-blue-500 text-white shadow-sm' : 'text-navy-700 hover:text-navy-900 hover:bg-ivory-200/60']">التزام تعاقدي</button>
                <button type="button" @click="handleKindChange('additional')" :class="['h-8 rounded-lg px-3 text-xs font-medium transition-colors', formMode === 'additional' ? 'bg-blue-500 text-white shadow-sm' : 'text-navy-700 hover:text-navy-900 hover:bg-ivory-200/60']">التزام إضافي</button>
              </div>
            </div>

            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <!-- Tenant (source: page.tsx:1008-1020) -->
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">المستأجر <span class="text-red-500">*</span></label>
                <SearchableTenantSelect
                  :model-value="newDue.tenantId"
                  :value-label="selectedFormTenantName"
                  placeholder="اختر المستأجر *"
                  @select="handleFormTenantSelect"
                />
              </div>

              <!-- Contract (source: page.tsx:1022-1040) -->
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">العقد <span class="text-red-500">*</span></label>
                <select :value="newDue.contract" @change="handleContractChange($event.target.value)" class="input-premium" :disabled="!newDue.tenantId">
                  <option value="">{{ newDue.tenantId ? 'اختر العقد *' : 'اختر المستأجر أولاّ' }}</option>
                  <option v-for="c in formContracts" :key="c.name" :value="c.name">{{ formatContractOptionLabel(c) }}</option>
                </select>
                <span v-if="selectedFormContract" class="flex items-center gap-1 text-xs text-navy-400">
                  <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                  الوحدة {{ selectedFormContract.unit_number || selectedFormContract.unit?.unit_number || '—' }} — {{ selectedFormContract.building_name || selectedFormContract.building?.name || '—' }}
                </span>
              </div>

              <!-- Due type (source: page.tsx:1042-1065) -->
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">نوع الالتزام <span class="text-red-500">*</span></label>
                <select :value="newDue.due_type" @change="handleDueTypeChange($event.target.value)" class="input-premium" :disabled="!newDue.contract">
                  <option value="">{{ newDue.contract ? (formMode === 'contractual' ? 'اختر نوع الالتزام *' : 'اختر نوع إضافي *') : 'اختر العقد أولاّ' }}</option>
                  <option v-for="opt in dueTypeOptions" :key="opt.value" :value="opt.value" :disabled="opt.disabled">{{ opt.label }}</option>
                </select>
                <span v-if="formMode === 'contractual' && selectedCharge && selectedCharge.calculation_method !== 'metered'" class="mt-1 text-xs text-navy-400">
                  طريقة الاحتساب: <span class="text-navy-800">{{ getCalculationMethodLabel(selectedCharge.calculation_method) }}</span>
                </span>
                <span v-if="formMode === 'additional' && newDue.contract && additionalDueTypes.length === 0" class="mt-1 text-xs text-amber-600">
                  لا توجد أنواع مخصصة فعالة لهذا العقد. يمكنك إضافتها من الإعدادات.
                </span>
              </div>

              <!-- Date (source: page.tsx:1067-1078) -->
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">التاريخ <span class="text-red-500">*</span></label>
                <input v-model="newDue.due_date" type="date" dir="ltr" class="input-premium" />
              </div>

              <!-- Metered fields (source: page.tsx:1080-1138) -->
              <template v-if="formMode === 'contractual' && selectedCharge?.calculation_method === 'metered'">
                <div class="space-y-1.5 md:col-span-2 rounded-lg border border-ivory-300 bg-ivory-100/40 p-3">
                  <label class="text-sm font-medium text-navy-800">بيانات الاستهلاك</label>
                  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div class="space-y-1.5">
                      <label class="text-xs text-navy-400">القراءة السابقة</label>
                      <input :value="newDue.previous_meter_reading" type="text" readonly class="input-premium bg-ivory-100" />
                    </div>
                    <div class="space-y-1.5">
                      <label class="text-xs text-navy-400">القراءة الحالية <span class="text-red-500">*</span></label>
                      <input :value="newDue.current_meter_reading" @input="handleMeterInput($event.target.value, newDue.unit_price)" type="number" step="0.01" placeholder="أدخل القراءة الجديدة" class="input-premium" />
                    </div>
                    <div class="space-y-1.5">
                      <label class="text-xs text-navy-400">الاستهلاك</label>
                      <input :value="newDue.meter_consumption" type="text" readonly class="input-premium bg-ivory-100" />
                    </div>
                    <div class="space-y-1.5">
                      <label class="text-xs text-navy-400">سعر الوحدة <span class="text-red-500">*</span></label>
                      <input :value="newDue.unit_price" @input="handleMeterInput(newDue.current_meter_reading, $event.target.value)" type="number" step="0.01" placeholder="مثال: 0.15" class="input-premium" />
                    </div>
                    <div class="space-y-1.5 sm:col-span-2">
                      <label class="text-xs text-navy-400">المبلغ (تلقائي)</label>
                      <input :value="newDue.amount" type="text" readonly class="input-premium bg-ivory-100" />
                    </div>
                  </div>
                </div>
              </template>

              <!-- Amount (non-metered) (source: page.tsx:1140-1153) -->
              <template v-else>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium text-navy-800">المبلغ <span class="text-red-500">*</span></label>
                  <input v-model="newDue.amount" type="number" step="0.01" placeholder="أدخل المبلغ" class="input-premium" />
                </div>
              </template>

              <!-- Description (source: page.tsx:1156-1166) -->
              <div class="space-y-1.5 md:col-span-2">
                <label class="text-sm font-medium text-navy-800">{{ formMode === 'contractual' ? 'الوصف (اختياري)' : 'السبب *' }}</label>
                <input v-model="newDue.description" type="text" :placeholder="formMode === 'contractual' ? 'أدخل الوصف' : 'أدخل سبب الالتزام الإضافي'" class="input-premium" />
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="shrink-0 px-6 py-4 border-t border-ivory-300/60">
          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button type="button" class="btn-premium btn-outline" @click="emit('close')">إلغاء</button>
            <button type="submit" class="btn-premium btn-outline" :disabled="creating">
              <span v-if="creating && !approving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
            <button type="button" class="btn-premium btn-gold" :disabled="creating" @click="createDue(true)">
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
import { ref, computed, onMounted } from 'vue'
import SearchableTenantSelect from '@/components/ui/SearchableTenantSelect.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  // Optional preset: { name, full_name }
  tenant: { type: Object, default: null },
  // Optional preset contract id (must belong to the tenant)
  contract: { type: String, default: '' },
})
const emit = defineEmits(['close', 'created'])

const toast = useToast()

const newDue = ref({
  tenantId: '',
  contract: '',
  due_type: '',
  amount: '',
  due_date: new Date().toISOString().split('T')[0],
  description: '',
  due_kind: 'contractual',
  previous_meter_reading: '',
  current_meter_reading: '',
  meter_consumption: '',
  unit_price: '',
})
const formMode = ref('contractual')  // 'contractual' | 'additional'
const formContracts = ref([])        // contracts for selected tenant
const contractCharges = ref([])      // charges for selected contract
const dueTypes = ref([])
const selectedFormTenantName = ref('')
const createError = ref('')
const creating = ref(false)
const approving = ref(false)

const selectedFormContract = computed(() =>
  formContracts.value.find((c) => c.name === newDue.value.contract) || null
)

const isContractualMode = computed(() => formMode.value === 'contractual')

const additionalDueTypes = computed(() => {
  if (!selectedFormContract.value) return []
  const contractDueTypeIds = new Set((selectedFormContract.value.contract_charges || []).map((c) => c.due_type || c.due_type_id))
  return dueTypes.value.filter((dt) => !dt.is_system && dt.is_active && !contractDueTypeIds.has(dt.name))
})

const selectedCharge = computed(() =>
  isContractualMode.value ? contractCharges.value.find((c) => c.due_type_id === newDue.value.due_type) : null
)

const dueTypeOptions = computed(() => {
  if (isContractualMode.value) {
    return contractCharges.value.map((c) => ({
      value: c.due_type_id,
      label: `${c.due_type_name || ''}${c.disabled_reason ? ` — ${c.disabled_reason}` : ''}`,
      disabled: !!c.disabled_reason,
    }))
  }
  return additionalDueTypes.value.map((dt) => ({ value: dt.name, label: dt.due_type_name || '' }))
})

// ---- Helpers (source: page.tsx:172-194, 510-534) ----
function formatContractOptionLabel(c) {
  const building = c.building_name || c.building?.name || '—'
  const unit = c.unit_number || c.unit?.unit_number || '—'
  return `${c.contract_number} — ${building} — الوحدة ${unit}`
}

function getCalculationMethodLabel(method) {
  switch (method) {
    case 'metered': return 'حسب قراءة العداد'
    case 'actual_bill': return 'حسب قيمة الفاتورة'
    case 'on_demand': return 'حسب الحاجة'
    case 'fixed_periodic': return 'دوري ثابت (تلقائي)'
    default: return '—'
  }
}

function roundMoney(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100
}

function calculateMeterFields(prev, curr, price) {
  const p = parseFloat(prev || '0')
  const c = parseFloat(curr || '0')
  const pr = parseFloat(price || '0')
  const consumption = (!isNaN(c) && !isNaN(p)) ? String(c - p) : ''
  const amount = (consumption && !isNaN(pr)) ? roundMoney(parseFloat(consumption) * pr).toFixed(2) : ''
  return { consumption, amount }
}

const EMPTY_DETAILS = { due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }

// ---- Data loading (source: page.tsx:542-757) ----
async function loadDueTypes() {
  try {
    const dtRes = await callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 1 })
    dueTypes.value = (dtRes.dueTypes || []).filter(dt => !dt.is_system || dt.due_type_code !== 'rent')
  } catch { /* ignore */ }
}

async function loadContractsForTenant(tenantId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      tenant: tenantId, status: 'active,expired', include_charges: 1, limit: 100,
    })
    formContracts.value = res.contracts || []
  } catch { formContracts.value = [] }
}

async function loadContractCharges(contractId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_contract_due_types', { name: contractId })
    contractCharges.value = res.charges || []
  } catch { contractCharges.value = [] }
}

async function loadPreviousReading(contractId, dueTypeId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_previous_reading', { name: contractId, due_type: dueTypeId })
    return res.previous_meter_reading || '0'
  } catch { return '0' }
}

// ---- Form handlers ----
async function handleFormTenantSelect(item) {
  selectedFormTenantName.value = item ? (item.full_name || item.name) : ''
  newDue.value = { ...newDue.value, ...EMPTY_DETAILS, tenantId: item?.name || '', contract: '' }
  contractCharges.value = []
  formContracts.value = []
  if (item?.name) await loadContractsForTenant(item.name)
}

async function handleContractChange(contractId) {
  if (!contractId) {
    newDue.value = { ...newDue.value, ...EMPTY_DETAILS, contract: '' }
    contractCharges.value = []
    return
  }
  if (!formContracts.value.some((c) => c.name === contractId)) return
  newDue.value = { ...newDue.value, ...EMPTY_DETAILS, contract: contractId }
  await loadContractCharges(contractId)
}

async function handleDueTypeChange(dueTypeId) {
  const charge = isContractualMode.value ? contractCharges.value.find((c) => c.due_type_id === dueTypeId) : null
  const updates = { due_type: dueTypeId, previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '' }
  if (isContractualMode.value && charge?.calculation_method === 'metered' && newDue.value.contract) {
    updates.previous_meter_reading = await loadPreviousReading(newDue.value.contract, dueTypeId)
  }
  newDue.value = { ...newDue.value, ...updates }
}

function handleKindChange(mode) {
  formMode.value = mode
  newDue.value = { ...newDue.value, ...EMPTY_DETAILS }
  if (newDue.value.contract) loadContractCharges(newDue.value.contract)
}

function handleMeterInput(currentMeterReading, unitPrice) {
  const { consumption, amount } = calculateMeterFields(newDue.value.previous_meter_reading, currentMeterReading, unitPrice)
  newDue.value = { ...newDue.value, current_meter_reading: currentMeterReading, unit_price: unitPrice, meter_consumption: consumption, amount }
}

// ---- Submit (source: page.tsx:690-757) ----
async function createDue(approve) {
  if (creating.value) return
  createError.value = ''
  if (!newDue.value.tenantId) { createError.value = 'المستأجر مطلوب'; return }
  if (!newDue.value.contract) { createError.value = 'العقد مطلوب'; return }
  if (!newDue.value.due_type) { createError.value = 'نوع الالتزام مطلوب'; return }

  const payload = {
    contract: newDue.value.contract,
    due_type: newDue.value.due_type,
    due_date: newDue.value.due_date,
    description: newDue.value.description,
    due_kind: formMode.value,
  }

  if (isContractualMode.value) {
    if (!selectedCharge.value) { createError.value = 'نوع الالتزام غير موجود في العقد'; return }
    if (selectedCharge.value.disabled_reason) { createError.value = 'لا يمكن إنشاء هذا النوع يدويًا'; return }

    if (selectedCharge.value.calculation_method === 'metered') {
      if (!newDue.value.current_meter_reading || String(newDue.value.current_meter_reading).trim() === '') { createError.value = 'القراءة الحالية مطلوبة'; return }
      if (!newDue.value.unit_price || String(newDue.value.unit_price).trim() === '') { createError.value = 'سعر الوحدة مطلوب'; return }
      const prev = parseFloat(newDue.value.previous_meter_reading || '0')
      const curr = parseFloat(newDue.value.current_meter_reading)
      if (isNaN(curr) || curr < prev) { createError.value = 'القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة'; return }
      payload.current_meter_reading = newDue.value.current_meter_reading
      payload.previous_meter_reading = newDue.value.previous_meter_reading
      payload.unit_price = newDue.value.unit_price
    } else if (selectedCharge.value.calculation_method === 'actual_bill' || selectedCharge.value.calculation_method === 'on_demand') {
      if (!newDue.value.amount || String(newDue.value.amount).trim() === '') { createError.value = 'المبلغ مطلوب'; return }
      const amount = parseFloat(newDue.value.amount)
      if (isNaN(amount) || amount <= 0) { createError.value = 'المبلغ يجب أن يكون أكبر من صفر'; return }
      payload.amount = newDue.value.amount
    } else {
      createError.value = 'طريقة الاحتساب غير صالحة للإنشاء اليدوي'; return
    }
  } else {
    if (!newDue.value.description || String(newDue.value.description).trim() === '') { createError.value = 'يرجى إدخال سبب الالتزام الإضافي'; return }
    if (!newDue.value.amount || String(newDue.value.amount).trim() === '') { createError.value = 'المبلغ مطلوب'; return }
    const amount = parseFloat(newDue.value.amount)
    if (isNaN(amount) || amount <= 0) { createError.value = 'المبلغ يجب أن يكون أكبر من صفر'; return }
    payload.amount = newDue.value.amount
  }

  creating.value = true
  approving.value = approve
  let dueName = null
  try {
    dueName = await callApi('rental.rental.api.due.create_due', payload)
  } catch (e) {
    createError.value = extractError(e)
    creating.value = false
    return
  }

  if (approve) {
    try {
      await callApi('rental.rental.api.due.approve_due', { name: dueName })
      toast.success('تم إنشاء الالتزام واعتماده')
    } catch (e) {
      toast.error(`تم حفظ الالتزام كمسودة لكن تعذّر اعتماده: ${extractError(e)}`)
    }
  } else {
    toast.success('تم إنشاء الالتزام')
  }
  creating.value = false
  emit('created', dueName)
  emit('close')
}

onMounted(async () => {
  loadDueTypes()
  if (!props.tenant?.name) return
  await handleFormTenantSelect({ name: props.tenant.name, full_name: props.tenant.full_name || props.tenant.name })
  const target = props.contract && formContracts.value.some((c) => c.name === props.contract)
    ? props.contract
    : (formContracts.value.length === 1 ? formContracts.value[0].name : '')
  if (target) await handleContractChange(target)
})
</script>
