<template>
  <div class="card-v2 p-3">
    <!-- Header -->
    <div class="mb-2 flex items-center justify-between">
      <h4 class="font-semibold text-navy-900">{{ charge.due_type_name || chargeName }}</h4>
      <button
        v-if="!isSystem && editable"
        type="button"
        class="text-xs text-red-600 hover:text-red-800"
        @click="emit('remove', { charge, index })"
      >
        إزالة
      </button>
    </div>

    <!-- Editable mode -->
    <div v-if="editable" class="space-y-2">
      <!-- Responsibility -->
      <div>
        <label class="mb-1 block text-sm text-navy-700">المسؤولية</label>
        <select
          :value="charge.responsibility"
          class="select-v2 w-full rounded px-2 py-1 text-sm"
          :class="!charge.responsibility ? 'text-navy-400' : 'text-navy-900'"
          @change="(e) => emit('update', { charge, updates: { responsibility: e.target.value } })"
        >
          <option value="" disabled hidden>اختر المسؤولية</option>
          <option value="landlord">{{ RESPONSIBILITY_LABELS.landlord }}</option>
          <option value="tenant">{{ RESPONSIBILITY_LABELS.tenant }}</option>
          <option value="included">{{ RESPONSIBILITY_LABELS.included }}</option>
        </select>
      </div>

      <!-- Payment By (only when tenant) -->
      <div v-if="charge.responsibility === 'tenant'">
        <label class="mb-1 block text-sm text-navy-700">من يدفع</label>
        <select
          :value="charge.payment_by || ''"
          class="select-v2 w-full rounded px-2 py-1 text-sm"
          :class="!charge.payment_by ? 'text-navy-400' : 'text-navy-900'"
          @change="(e) => emit('update', { charge, updates: { payment_by: e.target.value } })"
        >
          <option value="" disabled hidden>اختر من يدفع قيمة الخدمة</option>
          <option :value="PAYMENT_BY.landlord">{{ PAYMENT_BY_LABELS.landlord }}</option>
          <option :value="PAYMENT_BY.tenant">{{ PAYMENT_BY_LABELS.tenant }}</option>
        </select>
      </div>

      <!-- Calculation Method (only when tenant && paymentBy=landlord) -->
      <div
        v-if="charge.responsibility === 'tenant' && charge.payment_by === PAYMENT_BY.landlord && calculationMethods.length > 0"
      >
        <label class="mb-1 block text-sm text-navy-700">طريقة الاحتساب</label>
        <select
          :value="charge.calculation_method || ''"
          class="select-v2 w-full rounded px-2 py-1 text-sm"
          :class="!charge.calculation_method ? 'text-navy-400' : 'text-navy-900'"
          @change="(e) => emit('update', { charge, updates: { calculation_method: e.target.value } })"
        >
          <option value="" disabled hidden>اختر طريقة الاحتساب</option>
          <option v-for="m in calculationMethods" :key="m.value" :value="m.value">{{ m.label }}</option>
        </select>
      </div>

      <!-- Fixed Periodic fields -->
      <div
        v-if="charge.responsibility === 'tenant' && charge.payment_by === PAYMENT_BY.landlord && charge.calculation_method === 'fixed_periodic'"
        class="space-y-3"
      >
        <!-- Amount -->
        <div>
          <label class="mb-1 block text-sm text-navy-700">المبلغ</label>
          <input
            type="text"
            :value="charge.amount || ''"
            placeholder="المبلغ"
            class="input-v2 w-full text-sm"
            @input="(e) => emit('update', { charge, updates: { amount: e.target.value } })"
          />
        </div>

        <!-- Frequency -->
        <div>
          <label class="mb-1 block text-sm text-navy-700">الدورية</label>
          <select
            :value="charge.frequency || ''"
            class="select-v2 w-full rounded px-2 py-1 text-sm"
            :class="!charge.frequency ? 'text-navy-400' : 'text-navy-900'"
            @change="(e) => emit('update', { charge, updates: { frequency: e.target.value } })"
          >
            <option value="" disabled hidden>اختر الدورية</option>
            <option v-for="freq in availableFrequencies" :key="freq" :value="freq">
              {{ FREQUENCY_LABELS[freq] || freq }}
            </option>
          </select>
          <p
            v-if="availableFrequencies.length === 0 && charge.first_due_date && contractStartDate && contractEndDate"
            class="mt-1 text-xs text-red-600"
          >
            لا توجد دورية متاحة لتاريخ الاستحقاق والمدة المحددة
          </p>
        </div>

        <!-- Commitment Timing -->
        <div>
          <label class="mb-1 block text-sm text-navy-700">توقيت الاستحقاق</label>
          <select
            :value="charge.commitment_timing || ''"
            class="select-v2 w-full rounded px-2 py-1 text-sm"
            :class="!charge.commitment_timing ? 'text-navy-400' : 'text-navy-900'"
            @change="(e) => emit('update', { charge, updates: { commitment_timing: e.target.value } })"
          >
            <option value="" disabled hidden>اختر التوقيت</option>
            <option :value="COMMITMENT_TIMING.start">{{ COMMITMENT_TIMING_LABELS.start }}</option>
            <option :value="COMMITMENT_TIMING.end">{{ COMMITMENT_TIMING_LABELS.end }}</option>
          </select>
        </div>

        <!-- First due date display + partial period warning -->
        <div v-if="firstDisplayedDueDate">
          <p class="mt-1 text-xs text-navy-400">
            أول استحقاق: {{ formatDate(firstDisplayedDueDate) }}
          </p>
        </div>

        <!-- Partial period warning -->
        <div
          v-if="partialPeriod && partialPeriod.exists"
          class="rounded-lg border border-amber-200 bg-amber-50 p-3"
        >
          <div class="mb-2 flex items-center gap-1.5 text-sm font-medium text-amber-700">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>الفترة الأخيرة غير مكتملة</span>
          </div>
          <p class="mb-3 text-xs text-amber-700">
            تبقى فترة من {{ partialPeriod.startDate ? formatDate(partialPeriod.startDate) : '—' }} إلى
            {{ partialPeriod.endDate ? formatDate(partialPeriod.endDate) : '—' }}
          </p>

          <!-- Last period handling -->
          <div>
            <label class="mb-1 block text-sm text-navy-700">طريقة المعالجة</label>
            <select
              :value="charge.last_period_handling || ''"
              class="select-v2 w-full rounded px-2 py-1 text-sm"
              :class="!charge.last_period_handling ? 'text-navy-400' : 'text-navy-900'"
              @change="(e) => emit('update', { charge, updates: { last_period_handling: e.target.value, last_period_adjustment_amount: undefined } })"
            >
              <option value="" disabled hidden>اختر طريقة المعالجة</option>
              <option :value="LAST_PERIOD_HANDLING.none">{{ LAST_PERIOD_HANDLING_LABELS.none }}</option>
              <option :value="LAST_PERIOD_HANDLING.prorated">{{ LAST_PERIOD_HANDLING_LABELS.prorated }}</option>
              <option :value="LAST_PERIOD_HANDLING.manual">{{ LAST_PERIOD_HANDLING_LABELS.manual }}</option>
            </select>
          </div>

          <!-- Manual settlement amount -->
          <div v-if="charge.last_period_handling === 'manual'" class="mt-2">
            <label class="mb-1 block text-sm text-navy-700">مبلغ التسوية</label>
            <input
              type="text"
              :value="charge.last_period_adjustment_amount || ''"
              placeholder="مبلغ التسوية"
              class="input-v2 w-full text-sm"
              @input="(e) => emit('update', { charge, updates: { last_period_adjustment_amount: e.target.value } })"
            />
          </div>

          <!-- Prorated amount display -->
          <p
            v-if="charge.last_period_handling === 'prorated' && partialPeriod.amount > 0"
            class="mt-2 text-xs text-navy-700"
          >
            مبلغ التسوية المحسوب: {{ formatMoney(partialPeriod.amount, currency) }}
          </p>
        </div>
      </div>

      <!-- Metered: opening reading -->
      <input
        v-if="charge.responsibility === 'tenant' && charge.payment_by === PAYMENT_BY.landlord && charge.calculation_method === 'metered'"
        type="text"
        :value="charge.opening_meter_reading || ''"
        placeholder="قراءة بداية العداد"
        class="input-v2 w-full text-sm"
        @input="(e) => emit('update', { charge, updates: { opening_meter_reading: e.target.value } })"
      />

      <!-- Per-charge errors -->
      <p v-if="errorFor('responsibility')" class="text-xs text-red-600">{{ errorFor('responsibility') }}</p>
      <p v-if="errorFor('amount')" class="text-xs text-red-600">{{ errorFor('amount') }}</p>
      <p v-if="errorFor('first_due_date')" class="text-xs text-red-600">{{ errorFor('first_due_date') }}</p>
      <p v-if="errorFor('frequency')" class="text-xs text-red-600">{{ errorFor('frequency') }}</p>
      <p v-if="errorFor('commitment_timing')" class="text-xs text-red-600">{{ errorFor('commitment_timing') }}</p>
      <p v-if="errorFor('last_period_handling')" class="text-xs text-red-600">{{ errorFor('last_period_handling') }}</p>
      <p v-if="errorFor('last_period_adjustment_amount')" class="text-xs text-red-600">{{ errorFor('last_period_adjustment_amount') }}</p>
    </div>

    <!-- Preview mode: clause text -->
    <p v-else class="text-justify leading-loose text-navy-900">{{ clauseText }}</p>

    <!-- Fixed Periodic Preview table -->
    <FixedPeriodicPreview
      v-if="showFixedPreview"
      :charge="charge"
      :endDate="contractEndDate"
      :currency="currency"
    />
  </div>
</template>

<script setup>
import { computed, h, defineComponent } from 'vue'
import { formatMoney, formatDate } from '@/composables/useApi'
import {
  analyzeFixedPeriodicCharge,
  getAvailableFixedPeriodicFrequencies,
} from '@/utils/contractUtils'

const props = defineProps({
  charge: { type: Object, required: true },
  index: { type: Number, required: true },
  list: { type: Array, required: true },
  allCharges: { type: Array, default: () => [] },
  isSystem: { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
  unit: { type: Object, default: null },
  contractStartDate: { type: String, default: '' },
  contractEndDate: { type: String, default: '' },
  currency: { type: String, default: 'ILS' },
  dueTypes: { type: Array, default: () => [] },
})
const emit = defineEmits(['update', 'remove'])

// ---- Constants ----
const RESPONSIBILITY_LABELS = {
  landlord: 'على المؤجر',
  tenant: 'على المستأجر',
  included: 'مشمول بالإيجار',
}
const PAYMENT_BY = { landlord: 'landlord', tenant: 'tenant' }
const PAYMENT_BY_LABELS = { landlord: 'المؤجر', tenant: 'المستأجر (مباشر)' }
const CALCULATION_METHODS = {
  metered: 'metered', fixed_periodic: 'fixed_periodic',
  actual_bill: 'actual_bill', on_demand: 'on_demand',
}
const CALCULATION_METHOD_LABELS = {
  metered: 'حسب الاستهلاك بالعداد',
  fixed_periodic: 'مبلغ ثابت دوري',
  actual_bill: 'حسب الفاتورة الفعلية',
  on_demand: 'حسب الحاجة',
}
const COMMITMENT_TIMING = { start: 'start', end: 'end' }
const COMMITMENT_TIMING_LABELS = { start: 'بداية كل دورة', end: 'نهاية كل دورة' }
const LAST_PERIOD_HANDLING = { none: 'none', prorated: 'prorated', manual: 'manual' }
const LAST_PERIOD_HANDLING_LABELS = {
  none: 'لا يتم احتسابها',
  prorated: 'احتساب نسبي',
  manual: 'تسوية يدوية',
}
const FREQUENCY_LABELS = {
  weekly: 'أسبوعي', once: 'مرة واحدة', monthly: 'شهريًا',
  bi_monthly: 'كل شهرين', quarterly: 'ربع سنويًا',
  semi_annual: 'نصف سنويًا', annual: 'سنويًا',
}

// ---- Helpers ----
function isMeteredDueTypeCode(code) {
  return !!code && ['electricity', 'water'].includes(code)
}

function getMeterField(code) {
  if (code === 'electricity') return 'current_electricity_meter_reading'
  if (code === 'water') return 'current_water_meter_reading'
  return null
}

function getAvailableCalculationMethodsForDueType(code, paymentBy) {
  if (paymentBy === PAYMENT_BY.tenant) return []
  const methods = isMeteredDueTypeCode(code)
    ? [CALCULATION_METHODS.metered, CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill]
    : [CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill, CALCULATION_METHODS.on_demand]
  return methods.map((m) => ({ value: m, label: CALCULATION_METHOD_LABELS[m] }))
}

// ---- Computed ----
const chargeCode = computed(() => props.charge.due_type_code || null)
const chargeName = computed(() => {
  if (props.charge.due_type_name) return props.charge.due_type_name
  const dt = props.dueTypes.find((d) => d.name === (props.charge.due_type || props.charge.due_type_id))
  return dt?.due_type_name || ''
})

const calculationMethods = computed(() => {
  if (props.charge.responsibility !== 'tenant') return []
  if (props.charge.payment_by !== PAYMENT_BY.landlord) return []
  return getAvailableCalculationMethodsForDueType(chargeCode.value, props.charge.payment_by)
})

// ---- Available frequencies ----
// Source: ContractChargesSection.tsx:177-192 getAvailableFrequencies
// Delegates to utils.ts:396-414 getAvailableFixedPeriodicFrequencies
function getAvailableFrequencies(startDate, endDate, firstDueDate, commitmentTiming, lastPeriodHandling) {
  if (!startDate || !endDate || !firstDueDate) return []
  const start = new Date(startDate)
  const end = new Date(endDate)
  const firstDue = new Date(firstDueDate)
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || isNaN(firstDue.getTime())) return []
  if (firstDue < start || firstDue > end) return []

  return getAvailableFixedPeriodicFrequencies(firstDueDate, endDate, commitmentTiming, lastPeriodHandling)
}

const availableFrequencies = computed(() =>
  getAvailableFrequencies(
    props.contractStartDate,
    props.contractEndDate,
    props.charge.first_due_date,
    props.charge.commitment_timing,
    props.charge.last_period_handling
  )
)

// ---- Partial period analysis ----
// Source: utils.ts analyzeFixedPeriodicCharge (lines 423-563) — imported from contractUtils

const analysis = computed(() => {
  if (!props.charge.frequency || !props.charge.first_due_date) return null
  return analyzeFixedPeriodicCharge(props.charge, props.contractEndDate)
})

const firstDisplayedDueDate = computed(() => {
  if (analysis.value?.dues?.[0]?.dueDate) return analysis.value.dues[0].dueDate
  return props.charge.first_due_date || ''
})

const partialPeriod = computed(() => analysis.value?.partialPeriod || null)

// ---- Service clause text (preview mode) ----
// Source: contract-charge.service.ts:818-855 buildServiceClauseText
// Uses local formatCurrency (number only, NO currency symbol) matching original
function formatCurrencyLocal(amount) {
  return (Number(amount) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function buildServiceClauseText(charge) {
  const { due_type_name, responsibility, payment_by, calculation_method, amount, frequency, opening_meter_reading } = charge
  const name = due_type_name || chargeName.value
  const code = chargeCode.value

  if (responsibility === 'tenant' && calculation_method && !isAllowedCalcMethod(code, calculation_method)) {
    return null
  }

  switch (responsibility) {
    case 'landlord':
      return `يتحمل المؤجر التكاليف المتعلقة بـ ${name}، ولا يترتب على المستأجر أي التزام مالي مستقل بشأنها.`
    case 'included':
      return `تُعد خدمة ${name} مشمولة في مبلغ الإيجار المتفق عليه، ولا يترتب على المستأجر أي مبلغ إضافي مستقل بشأنها.`
    case 'tenant':
      if (payment_by === PAYMENT_BY.tenant) {
        return `يلتزم المستأجر بتسديد فواتير ${name} مباشرة للجهة المختصة، ولا يترتب على المؤجر أي التزام مالي مستقل بشأنها.`
      }
      switch (calculation_method) {
        case 'fixed_periodic': {
          if (!amount || !frequency) return null
          const freqLabel = FREQUENCY_LABELS[frequency] || frequency
          return `يلتزم المستأجر بسداد مبلغ قدره ${formatCurrencyLocal(parseFloat(String(amount).replace(/,/g, '')) || 0)} ${freqLabel} بدل ${name} للمؤجر.`
        }
        case 'metered':
          return `يتحمل المستأجر تكاليف استهلاك ${name} حسب قراءة العداد، وتبلغ قراءة العداد عند بداية العقد ${opening_meter_reading || '—'}، ويُحتسب الاستهلاك وفق سعر الوحدة المعتمد وقت تسجيل الاستهلاك، ويسدد المبلغ للمؤجر.`
        case 'actual_bill':
          return `يتحمل المستأجر تكلفة ${name} وفق قيمة الفاتورة الفعلية المسجلة خلال مدة العقد، ويسددها للمؤجر.`
        case 'on_demand':
          return `يتحمل المستأجر تكاليف ${name} عند الحاجة وفق المبالغ المستحقة والمسجلة خلال مدة العقد، ويسددها للمؤجر.`
        default:
          return null
      }
    default:
      return null
  }
}

function isAllowedCalcMethod(code, method) {
  if (!Object.values(CALCULATION_METHODS).includes(method)) return false
  if (isMeteredDueTypeCode(code)) return method !== CALCULATION_METHODS.on_demand
  return method !== CALCULATION_METHODS.metered
}

const clauseText = computed(() => buildServiceClauseText(props.charge) || '')

// ---- Fixed periodic preview ----
const showFixedPreview = computed(() =>
  props.charge.responsibility === 'tenant' &&
  props.charge.payment_by === PAYMENT_BY.landlord &&
  props.charge.calculation_method === CALCULATION_METHODS.fixed_periodic
)

// ---- Errors ----
const realIndex = computed(() =>
  props.allCharges.findIndex((c) =>
    (c.due_type || c.due_type_id) === (props.charge.due_type || props.charge.due_type_id)
  )
)

function errorFor(field) {
  const idx = realIndex.value
  if (idx === -1) return ''
  // Try both camelCase and snake_case error keys
  const camelKey = `contractCharges.${idx}.${field}`
  const snakeKey = `contract_charges.${idx}.${field}`
  return props.errors[camelKey] || props.errors[snakeKey] || ''
}

// ---- Inline FixedPeriodicPreview component ----
const FixedPeriodicPreview = defineComponent({
  props: {
    charge: { type: Object, required: true },
    endDate: { type: String, default: '' },
    currency: { type: String, default: 'ILS' },
  },
  setup(p) {
    const analysis = computed(() => analyzeFixedPeriodicCharge(p.charge, p.endDate))
    const schedule = computed(() => analysis.value.dues)
    const totalAmount = computed(() => schedule.value.reduce((sum, r) => sum + r.amount, 0))
    const allEqual = computed(() => {
      if (schedule.value.length === 0) return true
      const first = schedule.value[0].amount
      return schedule.value.every((r) => r.amount === first)
    })
    return () => {
      if (schedule.value.length === 0) return null
      const first = schedule.value[0]
      const last = schedule.value[schedule.value.length - 1]
      return h('div', { class: 'contract-table print-keep-together mt-4' }, [
        h('h4', { class: 'mb-2 font-bold text-navy-900' }, 'جدول الالتزامات الدورية'),
        h('div', { class: 'overflow-hidden rounded-lg border border-navy-200' }, [
          h('table', { class: 'w-full text-sm print-table' }, [
            h('thead', { class: 'bg-navy-50/40 text-navy-900' }, [
              h('tr', [
                h('th', { class: 'px-3 py-2 text-right font-semibold' }, 'الرقم'),
                h('th', { class: 'px-3 py-2 text-right font-semibold' }, 'تاريخ الالتزام'),
                h('th', { class: 'px-3 py-2 text-right font-semibold' }, 'القيمة'),
              ]),
            ]),
            h('tbody', { class: 'divide-y divide-navy-100' },
              schedule.value.map((row, i) =>
                h('tr', { key: i, class: 'text-navy-900' }, [
                  h('td', { class: 'px-3 py-2' }, String(i + 1)),
                  h('td', { class: 'px-3 py-2' }, formatDate(row.dueDate)),
                  h('td', { class: 'px-3 py-2 font-medium' }, formatMoney(row.amount, p.currency)),
                ])
              )
            ),
          ]),
          h('div', { class: 'border-t border-navy-100 bg-navy-50/40 px-3 py-2 text-sm text-navy-500' }, [
            h('div', { class: 'flex flex-wrap gap-x-4 gap-y-1' }, [
              h('span', [`عدد الالتزامات: `, h('strong', String(schedule.value.length))]),
              allEqual.value
                ? h('span', [`قيمة كل التزام: `, h('strong', formatMoney(first.amount, p.currency))])
                : h('span', [`القيمة الدورية الأساسية: `, h('strong', formatMoney(parseFloat(String(p.charge.amount).replace(/,/g, '')) || 0, p.currency))]),
              h('span', [`إجمالي الالتزامات: `, h('strong', formatMoney(totalAmount.value, p.currency))]),
              h('span', [`أول تاريخ: `, h('strong', formatDate(first.dueDate))]),
              h('span', [`آخر تاريخ: `, h('strong', formatDate(last.dueDate))]),
            ]),
            (!allEqual.value && analysis.value.partialPeriod.exists)
              ? h('p', { class: 'mt-1 text-xs text-amber-600' },
                `تتضمن فترة جزئية أخيرة بقيمة ${formatMoney(analysis.value.partialPeriod.amount, p.currency)}`)
              : null,
          ]),
        ]),
      ])
    }
  },
})
</script>

<style scoped>
.card-v2 {
  background: #faf9f6;
  border: 1px solid #e7e5e0;
  border-radius: 0.5rem;
}
.select-v2 {
  border: 1px solid #d4d0c8;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  background: #fff;
}
.input-v2 {
  border: 1px solid #d4d0c8;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  background: #fff;
}
</style>
