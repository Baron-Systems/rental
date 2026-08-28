<template>
  <div class="space-y-4">
    <!-- System charges (electricity, water) -->
    <ChargeCard
      v-for="(charge, idx) in systemCharges"
      :key="'sys-' + chargeKey(charge, idx)"
      :charge="charge"
      :index="idx"
      :list="systemCharges"
      :editable="editable"
      :errors="errors"
      :unit="unit"
      :contractStartDate="contractStartDate"
      :contractEndDate="contractEndDate"
      :currency="currency"
      :dueTypes="dueTypes"
      :allCharges="charges"
      :isSystem="true"
      @update="updateCharge"
    />

    <!-- Custom charges -->
    <ChargeCard
      v-for="(charge, idx) in customCharges"
      :key="'cust-' + chargeKey(charge, idx)"
      :charge="charge"
      :index="idx"
      :list="customCharges"
      :editable="editable"
      :errors="errors"
      :unit="unit"
      :contractStartDate="contractStartDate"
      :contractEndDate="contractEndDate"
      :currency="currency"
      :dueTypes="dueTypes"
      :allCharges="charges"
      :isSystem="false"
      @update="updateCharge"
      @remove="removeCustomService"
    />

    <!-- Add custom service -->
    <div v-if="editable && addableDueTypes.length > 0" class="flex items-center gap-2">
      <select
        v-model="selectedAddDueType"
        class="select-v2 flex-1 rounded px-2 py-1 text-sm"
        :class="!selectedAddDueType ? 'text-navy-400' : 'text-navy-900'"
      >
        <option value="" disabled hidden>+ إضافة خدمة</option>
        <option v-for="dt in addableDueTypes" :key="dt.name" :value="dt.name">
          {{ dt.due_type_name }}
        </option>
      </select>
      <button
        type="button"
        class="btn-premium btn-gold text-sm"
        :disabled="!selectedAddDueType"
        @click="addCustomService"
      >
        إضافة
      </button>
    </div>

    <p v-if="charges.length === 0" class="text-navy-400">لا توجد خدمات محددة.</p>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import ChargeCard from './ContractChargeCard.vue'
import { callApi } from '@/composables/useApi'
import { getAvailableFixedPeriodicFrequencies } from '@/utils/contractUtils'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  availableDueTypes: { type: Array, default: () => [] },
  unit: { type: Object, default: null },
  editable: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
  contractStartDate: { type: String, default: '' },
  contractEndDate: { type: String, default: '' },
  currency: { type: String, default: 'ILS' },
})
const emit = defineEmits(['update:modelValue'])

// ---- Constants (ported from contract-charge.service.ts) ----
const SYSTEM_CODES = ['electricity', 'water', 'rent']

const RESPONSIBILITY_LABELS = {
  landlord: 'على المؤجر',
  tenant: 'على المستأجر',
  included: 'مشمول بالإيجار',
}

const PAYMENT_BY = { landlord: 'landlord', tenant: 'tenant' }
const PAYMENT_BY_LABELS = {
  landlord: 'المؤجر',
  tenant: 'المستأجر (مباشر)',
}

const CALCULATION_METHODS = {
  metered: 'metered',
  fixed_periodic: 'fixed_periodic',
  actual_bill: 'actual_bill',
  on_demand: 'on_demand',
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
  weekly: 'أسبوعي',
  once: 'مرة واحدة',
  monthly: 'شهريًا',
  bi_monthly: 'كل شهرين',
  quarterly: 'ربع سنويًا',
  semi_annual: 'نصف سنويًا',
  annual: 'سنويًا',
}

// ---- Helper functions (ported from contract-charge.service.ts) ----
function isMeteredDueTypeCode(code) {
  return !!code && ['electricity', 'water'].includes(code)
}

function getMeterField(code) {
  if (code === 'electricity') return 'current_electricity_meter_reading'
  if (code === 'water') return 'current_water_meter_reading'
  return null
}

function getDefaultCalculationMethodForDueType(code, responsibility, paymentBy) {
  if (responsibility !== 'tenant') return null
  if (paymentBy === PAYMENT_BY.tenant) return null
  return isMeteredDueTypeCode(code) ? CALCULATION_METHODS.metered : CALCULATION_METHODS.fixed_periodic
}

function getAvailableCalculationMethodsForDueType(code, paymentBy) {
  if (paymentBy === PAYMENT_BY.tenant) return []
  const methods = isMeteredDueTypeCode(code)
    ? [CALCULATION_METHODS.metered, CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill]
    : [CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill, CALCULATION_METHODS.on_demand]
  return methods.map((m) => ({ value: m, label: CALCULATION_METHOD_LABELS[m] }))
}

// ---- Due types (fetch if not provided) ----
const fetchedDueTypes = ref([])
const dueTypes = computed(() => props.availableDueTypes.length > 0 ? props.availableDueTypes : fetchedDueTypes.value)

onMounted(() => {
  if (props.availableDueTypes.length > 0) return
  callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 0 })
    .then((res) => { fetchedDueTypes.value = (res && res.dueTypes) ? res.dueTypes : (res || []) })
    .catch(() => {})
})

// ---- Charges (v-model bridge) ----
const charges = computed(() => props.modelValue || [])

function emitCharges(updated) {
  emit('update:modelValue', updated)
}

// ---- System vs Custom split ----
function getChargeCode(charge) {
  if (charge.due_type_code) return charge.due_type_code
  const dt = dueTypes.value.find((d) => d.name === (charge.due_type || charge.due_type_id))
  return dt?.due_type_code || null
}

const systemCharges = computed(() =>
  charges.value.filter((c) => SYSTEM_CODES.includes(getChargeCode(c)))
)
const customCharges = computed(() =>
  charges.value.filter((c) => !SYSTEM_CODES.includes(getChargeCode(c)))
)

// ---- Addable due types (exclude system codes, rent, and already-used) ----
const addableDueTypes = computed(() =>
  dueTypes.value.filter((dt) => {
    const code = dt.due_type_code
    if (SYSTEM_CODES.includes(code) || code === 'rent') return false
    if (charges.value.some((c) => (c.due_type || c.due_type_id) === dt.name)) return false
    return true
  })
)

const selectedAddDueType = ref('')

// ---- Clean charge item (ported from getCleanChargeItem) ----
function getCleanChargeItem(dueType, responsibility, unit) {
  const code = dueType.due_type_code || dueType.code || null
  const name = dueType.due_type_name || dueType.name || ''
  const id = dueType.name || dueType.id || ''
  const isTenant = responsibility === 'tenant'
  const paymentBy = isTenant ? PAYMENT_BY.landlord : ''
  const defaultMethod = isTenant
    ? getDefaultCalculationMethodForDueType(code, responsibility, paymentBy) || ''
    : ''

  let openingMeterReading = undefined
  if (isTenant && paymentBy === PAYMENT_BY.landlord && defaultMethod === CALCULATION_METHODS.metered && isMeteredDueTypeCode(code)) {
    const field = getMeterField(code)
    if (field && unit) {
      openingMeterReading = unit[field] || undefined
    }
  }

  return {
    due_type: id,
    due_type_name: name,
    due_type_code: code,
    responsibility,
    payment_by: paymentBy,
    calculation_method: defaultMethod,
    amount: undefined,
    frequency: undefined,
    first_due_date: undefined,
    commitment_timing: isTenant && defaultMethod === CALCULATION_METHODS.fixed_periodic ? COMMITMENT_TIMING.start : undefined,
    last_period_handling: isTenant && defaultMethod === CALCULATION_METHODS.fixed_periodic ? LAST_PERIOD_HANDLING.none : undefined,
    last_period_adjustment_amount: undefined,
    opening_meter_reading: openingMeterReading,
  }
}

// ---- Update charge ----
function updateCharge({ charge, updates }) {
  const realIndex = charges.value.findIndex((c) =>
    (c.due_type || c.due_type_id) === (charge.due_type || charge.due_type_id)
  )
  if (realIndex === -1) return
  const updated = [...charges.value]

  if ('responsibility' in updates) {
    const responsibility = updates.responsibility
    const dt = dueTypes.value.find((d) => d.name === (charge.due_type || charge.due_type_id))
    if (dt) {
      updated[realIndex] = getCleanChargeItem(dt, responsibility, props.unit)
    }
  } else {
    let ch = { ...updated[realIndex], ...updates }

    if ('payment_by' in updates) {
      const paymentBy = updates.payment_by
      if (paymentBy === PAYMENT_BY.landlord && ch.responsibility === 'tenant') {
        const defaultMethod = getDefaultCalculationMethodForDueType(getChargeCode(ch), ch.responsibility, paymentBy)
        ch.calculation_method = defaultMethod || ''
        ch = applyCalcMethodDefaults(ch, ch.calculation_method)
      } else {
        ch.calculation_method = ''
        ch.amount = undefined
        ch.frequency = undefined
        ch.first_due_date = undefined
        ch.commitment_timing = undefined
        ch.last_period_handling = undefined
        ch.last_period_adjustment_amount = undefined
        ch.opening_meter_reading = undefined
      }
    } else if ('calculation_method' in updates) {
      ch = applyCalcMethodDefaults(ch, updates.calculation_method)
    }

    updated[realIndex] = ch
  }

  emitCharges(updated)
}

function applyCalcMethodDefaults(charge, method) {
  let ch = { ...charge }
  if (method === CALCULATION_METHODS.fixed_periodic) {
    ch.first_due_date = props.contractStartDate
    if (!ch.commitment_timing) ch.commitment_timing = COMMITMENT_TIMING.start
    if (!ch.last_period_handling) ch.last_period_handling = LAST_PERIOD_HANDLING.none
  } else {
    ch.amount = undefined
    ch.frequency = undefined
    ch.first_due_date = undefined
    ch.commitment_timing = undefined
    ch.last_period_handling = undefined
    ch.last_period_adjustment_amount = undefined
  }

  if (method === CALCULATION_METHODS.metered && isMeteredDueTypeCode(getChargeCode(ch))) {
    const field = getMeterField(getChargeCode(ch))
    if (field && props.unit && !ch.opening_meter_reading) {
      ch.opening_meter_reading = props.unit[field] || undefined
    }
  } else if (method !== CALCULATION_METHODS.metered) {
    ch.opening_meter_reading = undefined
  }
  return ch
}

// ---- Add / Remove custom service ----
function addCustomService() {
  if (!selectedAddDueType.value) return
  const dt = addableDueTypes.value.find((d) => d.name === selectedAddDueType.value)
  if (!dt) return
  const newCharge = getCleanChargeItem(dt, 'landlord', props.unit)
  emitCharges([...charges.value, newCharge])
  selectedAddDueType.value = ''
}

function removeCustomService({ charge }) {
  emitCharges(charges.value.filter((c) =>
    (c.due_type || c.due_type_id) !== (charge.due_type || charge.due_type_id)
  ))
}

// ---- Available frequencies helper (source: ContractChargesSection.tsx:177-192) ----
// Delegates to utils.ts:396-414 getAvailableFixedPeriodicFrequencies (imported)
function getAvailableFrequencies(startDate, endDate, firstDueDate, commitmentTiming, lastPeriodHandling) {
  if (!startDate || !endDate || !firstDueDate) return []
  const start = new Date(startDate)
  const end = new Date(endDate)
  const firstDue = new Date(firstDueDate)
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || isNaN(firstDue.getTime())) return []
  if (firstDue < start || firstDue > end) return []

  return getAvailableFixedPeriodicFrequencies(firstDueDate, endDate, commitmentTiming, lastPeriodHandling)
}

// ---- Auto-sync firstDueDate and validate frequency on date changes ----
// Source: ContractChargesSection.tsx:291-322
watch(
  () => [charges.value, props.contractStartDate, props.contractEndDate],
  () => {
    let hasChanges = false
    const updated = charges.value.map((charge) => {
      if (charge.calculation_method !== CALCULATION_METHODS.fixed_periodic) {
        return charge
      }
      const derivedFirstDue = props.contractStartDate
      if (derivedFirstDue && charge.first_due_date !== derivedFirstDue) {
        hasChanges = true
        charge = { ...charge, first_due_date: derivedFirstDue }
      }
      if (!charge.frequency) return charge
      const available = getAvailableFrequencies(
        props.contractStartDate,
        props.contractEndDate,
        charge.first_due_date,
        charge.commitment_timing,
        charge.last_period_handling
      )
      if (available.length === 0 || !available.includes(charge.frequency)) {
        hasChanges = true
        return { ...charge, frequency: undefined }
      }
      return charge
    })
    if (hasChanges) emitCharges(updated)
  },
  { deep: true }
)

// ---- Key helper ----
function chargeKey(charge, idx) {
  return charge.due_type || charge.due_type_id || idx
}

// Expose helpers for child component
defineExpose({
  RESPONSIBILITY_LABELS,
  PAYMENT_BY,
  PAYMENT_BY_LABELS,
  CALCULATION_METHODS,
  CALCULATION_METHOD_LABELS,
  COMMITMENT_TIMING,
  COMMITMENT_TIMING_LABELS,
  LAST_PERIOD_HANDLING,
  LAST_PERIOD_HANDLING_LABELS,
  FREQUENCY_LABELS,
  isMeteredDueTypeCode,
  getMeterField,
  getAvailableCalculationMethodsForDueType,
})
</script>

<style scoped>
.select-v2 {
  border: 1px solid #d4d0c8;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  background: #fff;
}
</style>
