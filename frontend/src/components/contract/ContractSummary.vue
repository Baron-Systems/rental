<template>
  <div class="space-y-4">
    <!-- Preview / Edit / Print -->
    <div class="grid gap-2" :class="viewMode === 'edit' ? 'grid-cols-1' : 'grid-cols-2'">
      <button v-if="viewMode === 'edit'" class="btn-premium btn-outline justify-center" @click="$emit('preview')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
        معاينة
      </button>
      <template v-else>
        <button class="btn-premium btn-outline justify-center" @click="$emit('preview')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          تحرير
        </button>
        <button class="btn-premium btn-outline justify-center" @click="$emit('print')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
          طباعة
        </button>
      </template>
    </div>

    <!-- Key Info -->
    <div class="card-premium p-3">
      <h3 class="mb-2 font-bold text-navy-900">
        {{ isRenewal ? 'ملخص تجديد العقد' : 'ملخص العقد' }}
      </h3>
      <div v-if="isRenewal && previousContractNumber" class="mb-2 rounded-lg border border-blue-200 bg-blue-50/60 p-2 text-sm text-blue-700">
        تجديد للعقد: <strong>{{ previousContractNumber }}</strong>
      </div>
      <div class="space-y-2 text-sm">
        <div class="flex items-start gap-2">
          <svg class="mt-0.5 h-4 w-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
          <div>
            <p class="text-xs text-navy-500">المستأجر</p>
            <p class="font-medium text-navy-900">{{ selectedTenant?.full_name || selectedTenant?.fullName || '—' }}</p>
          </div>
        </div>
        <div class="flex items-start gap-2">
          <svg class="mt-0.5 h-4 w-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
          <div>
            <p class="text-xs text-navy-500">الوحدة</p>
            <p class="font-medium text-navy-900">
              {{ selectedUnit ? `${selectedUnit.unit_number || selectedUnit.unitNumber} — ${selectedBuilding?.building_name || selectedBuilding?.name || ''}` : '—' }}
            </p>
            <p v-if="selectedUnit" class="text-xs text-navy-500">
              {{ selectedUnit.floor?.name || selectedUnit.floor_name }}
              <template v-if="selectedUnit.unit_type || selectedUnit.unitType">
                ({{ unitTypeLabel(selectedUnit.unit_type || selectedUnit.unitType) }})
              </template>
            </p>
          </div>
        </div>
        <div class="flex items-start gap-2">
          <svg class="mt-0.5 h-4 w-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <div>
            <p class="text-xs text-navy-500">المدة</p>
            <p class="font-medium text-navy-900">
              {{ (formData.start_date || formData.startDate) && (formData.end_date || formData.endDate)
                ? `${formatDateDisplay(formData.start_date || formData.startDate)} — ${formatDateDisplay(formData.end_date || formData.endDate)}`
                : '—' }}
            </p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-x-4 gap-y-2">
          <div class="text-xs text-navy-500 text-start">دورية الإيجار</div>
          <div class="text-sm font-medium text-navy-900 text-end">{{ paymentFrequencyLabel(formData.payment_frequency || formData.paymentFrequency) }}</div>
          <template v-if="dueAmount > 0">
            <div class="text-xs text-navy-500 text-start">قيمة الإيجار</div>
            <div class="text-sm font-medium text-navy-900 text-end">{{ formatAmount(dueAmount, currency) }}</div>
          </template>
          <template v-if="rentSchedule.length > 0">
            <div class="text-xs text-navy-500 text-start">عدد التزامات الإيجار</div>
            <div class="text-sm font-medium text-navy-900 text-end">{{ rentSchedule.length }}</div>
          </template>
          <template v-if="rentTotal > 0">
            <div class="text-xs text-navy-500 text-start">إجمالي الإيجار</div>
            <div class="text-sm font-bold text-navy-900 text-end">{{ formatAmount(rentTotal, currency) }}</div>
          </template>
        </div>

        <div v-if="fixedPeriodicItems.length > 0" class="mt-2 border-t border-ivory-300 pt-2">
          <p class="mb-1 text-xs font-semibold text-navy-900">التزامات دورية إضافية</p>
          <div class="space-y-1">
            <div
              v-for="item in fixedPeriodicItems"
              :key="item.due_type_id || item.dueTypeId"
              class="space-y-1 border-b border-ivory-200 pb-1.5 last:border-0 last:pb-0"
            >
              <p class="font-medium text-sm text-navy-900">{{ item.due_type_name || item.dueTypeName }}</p>
              <div class="flex items-center justify-between text-sm text-navy-900">
                <span>{{ formatAmount(item.amount, currency) }} × {{ cycleCountLabel(item.count) }}</span>
                <span>{{ formatAmount(item.full_total || item.fullTotal, currency) }}</span>
              </div>
              <div v-if="item.partial_period_exists && item.last_period_handling === 'none'" class="flex items-center justify-between text-xs text-navy-500">
                <span>الفترة الأخيرة: غير محتسبة</span>
                <span>—</span>
              </div>
              <div v-if="item.partial_amount > 0" class="flex items-center justify-between text-xs text-navy-500">
                <span>تسوية الفترة الأخيرة</span>
                <span>{{ formatAmount(item.partial_amount, currency) }}</span>
              </div>
              <div class="flex items-center justify-between text-sm font-medium text-navy-900">
                <span>إجمالي {{ item.due_type_name || item.dueTypeName }}</span>
                <span>{{ formatAmount(item.total, currency) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="fixedPeriodicItems.length > 0" class="mt-2 border-t border-ivory-300 pt-2">
          <div class="space-y-1">
            <div class="flex items-center justify-between text-sm text-navy-900">
              <span>إجمالي الإيجار</span>
              <span>{{ formatAmount(rentTotal, currency) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm text-navy-900">
              <span>إجمالي الالتزامات الدورية</span>
              <span>{{ formatAmount(fixedPeriodicTotal, currency) }}</span>
            </div>
            <div class="my-1 border-t border-ivory-300"></div>
            <div class="flex items-center justify-between text-sm font-bold text-navy-900">
              <span>الإجمالي الثابت المتوقع</span>
              <span>{{ formatAmount(expectedFixedTotal, currency) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Validation -->
    <div v-if="errorCount > 0 || warningCount > 0" class="card-premium p-4">
      <h3 class="mb-2 font-bold text-navy-900">التحقق والتنبيهات</h3>
      <div v-if="errorCount > 0" class="mb-2 space-y-1">
        <div v-for="(msg, field) in errors" :key="field" class="flex items-center gap-1.5 text-sm text-red-600">
          <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          {{ msg }}
        </div>
      </div>
      <div v-if="warningCount > 0" class="space-y-1">
        <div v-for="(w, i) in warnings" :key="i" class="flex items-center gap-1.5 text-sm text-amber-600">
          <svg class="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z"/></svg>
          {{ w }}
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="space-y-2">
      <button
        class="btn-premium bg-navy-800 text-white hover:bg-navy-900 w-full justify-center"
        :disabled="isSaving"
        @click="$emit('save', false)"
      >
        {{ isSaving ? 'جاري الحفظ...' : (mode === 'create' ? 'حفظ العقد' : 'حفظ التعديلات') }}
      </button>
      <button
        v-if="mode === 'create'"
        class="btn-premium btn-outline w-full justify-center"
        :disabled="isSaving"
        @click="$emit('save', true)"
      >
        حفظ كمسودة
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { calculateContractDueSchedule, getFrequencyCount, analyzeFixedPeriodicCharge } from '@/utils/contractUtils.js'

const props = defineProps({
  formData: { type: Object, required: true },
  tenants: { type: Array, default: () => [] },
  units: { type: Array, default: () => [] },
  buildings: { type: Array, default: () => [] },
  errors: { type: Object, default: () => ({}) },
  warnings: { type: Array, default: () => [] },
  isSaving: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // create | edit
  status: { type: String, default: '' },
  viewMode: { type: String, default: 'edit' }, // edit | preview | print
  dues: { type: Array, default: () => [] },
  isRenewal: { type: Boolean, default: false },
  previousContractNumber: { type: String, default: '' },
  currency: { type: String, default: 'ILS' },
})

defineEmits(['save', 'preview', 'print'])

const PAYMENT_FREQUENCIES = [
  { value: 'weekly', label: 'أسبوعي' },
  { value: 'monthly', label: 'شهري' },
  { value: 'bi_monthly', label: 'كل شهرين' },
  { value: 'quarterly', label: 'ربع سنوي' },
  { value: 'semi_annual', label: 'نصف سنوي' },
  { value: 'annual', label: 'سنوي' },
]

const UNIT_TYPE_LABELS = {
  apartment: 'شقة',
  office: 'مكتب',
  shop: 'محل',
  warehouse: 'مستودع',
  villa: 'فيلا',
  studio: 'استوديو',
  room: 'غرفة',
  building: 'مبنى',
}

const FIXED_PERIODIC_FREQUENCY_LABELS = {
  weekly: 'أسبوعي',
  monthly: 'شهريًا',
  bi_monthly: 'كل شهرين',
  quarterly: 'كل 3 شهور',
  semi_annual: 'نصف سنوي',
  annual: 'سنوي',
}

const CURRENCY_LABELS = { ILS: 'شيكل', JOD: 'دينار أردني', USD: 'دولار' }

function unitTypeLabel(type) {
  return UNIT_TYPE_LABELS[type] || type || ''
}

function paymentFrequencyLabel(freq) {
  const f = PAYMENT_FREQUENCIES.find((x) => x.value === freq)
  return f ? f.label : freq || ''
}

function getCurrencyLabel(currency) {
  return CURRENCY_LABELS[currency] || currency || ''
}

function formatAmount(amount, currency) {
  const num = Number(amount || 0)
  return `${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${getCurrencyLabel(currency)}`
}

function formatDateDisplay(value) {
  if (!value) return ''
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  return d.toLocaleDateString('en-GB')
}

function cycleCountLabel(count) {
  if (count === 1) return 'دورة'
  if (count === 2) return 'دورتين'
  return `${count} دورات`
}

const selectedTenant = computed(() => {
  const id = props.formData.tenant_id || props.formData.tenantId
  return props.tenants.find((t) => (t.id || t.name) === id) || null
})

const selectedUnit = computed(() => {
  const id = props.formData.unit_id || props.formData.unitId
  return props.units.find((u) => (u.id || u.name) === id) || null
})

const selectedBuilding = computed(() => {
  const id = props.formData.building_id || props.formData.buildingId
  return props.buildings.find((b) => (b.id || b.name) === id) || null
})

const rentSchedule = computed(() => {
  const baseDate = props.formData.first_due_date || props.formData.firstDueDate || props.formData.start_date || props.formData.startDate
  const endDate = props.formData.end_date || props.formData.endDate
  const rent = parseFloat(props.formData.rent_amount || props.formData.rentAmount) || 0
  const freq = props.formData.payment_frequency || props.formData.paymentFrequency
  const commitmentTiming = props.formData.commitment_timing || props.formData.commitmentTiming || 'start'
  if (!baseDate || !endDate || !rent || !freq) return []
  // If dues were passed in, use them
  if (props.dues && props.dues.length > 0) return props.dues
  // Source: ContractSummary.tsx:99-121 — compute schedule client-side
  const firstDue = new Date(baseDate)
  const end = new Date(endDate)
  const count = getFrequencyCount(firstDue, end, freq, commitmentTiming)
  return calculateContractDueSchedule(firstDue, end, rent, freq, count, commitmentTiming)
})

const rentTotal = computed(() => rentSchedule.value.reduce((sum, s) => sum + (s.amount || 0), 0))
const dueAmount = computed(() => (rentSchedule.value.length > 0 ? rentSchedule.value[0].amount : 0))

const fixedPeriodicItems = computed(() => {
  const charges = props.formData.contract_charges || props.formData.contractCharges || []
  const endDate = props.formData.end_date || props.formData.endDate
  if (!endDate) return []
  return charges
    .filter((c) => c.responsibility === 'tenant' && c.calculation_method === 'fixed_periodic' && c.amount && c.frequency && (c.first_due_date || c.firstDueDate))
    .map((charge) => {
      const amount = parseFloat(charge.amount) || 0
      // Source: ContractSummary.tsx:74-97 — use analyzeFixedPeriodicCharge
      const analysis = analyzeFixedPeriodicCharge(charge, new Date(endDate))
      return {
        due_type_id: charge.due_type || charge.dueTypeId,
        due_type_name: charge.due_type_name || charge.dueTypeName || charge.due_type || charge.dueTypeId,
        amount,
        frequency: charge.frequency,
        count: analysis.dues.length,
        full_total: analysis.dues.filter((d) => !d.partial).reduce((sum, d) => sum + d.amount, 0),
        partial_amount: analysis.partialPeriod.exists ? analysis.partialPeriod.amount : 0,
        last_period_handling: charge.last_period_handling || 'none',
        partial_period_exists: analysis.partialPeriod.exists,
        total: analysis.dues.reduce((sum, d) => sum + d.amount, 0),
      }
    })
})

const fixedPeriodicTotal = computed(() => fixedPeriodicItems.value.reduce((sum, item) => sum + item.total, 0))
const expectedFixedTotal = computed(() => rentTotal.value + fixedPeriodicTotal.value)

const errorCount = computed(() => Object.keys(props.errors || {}).length)
const warningCount = computed(() => (props.warnings || []).length)
</script>
