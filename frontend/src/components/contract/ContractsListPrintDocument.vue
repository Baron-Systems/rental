<template>
  <div id="print-area" class="contracts-list-print-document print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <!-- Title + filter summary -->
    <div class="print-keep-together border-b-2 border-navy-300 pb-4 mb-6">
      <h1 class="text-2xl font-bold text-navy-900 text-center mb-4">تقرير العقود</h1>
      <div class="text-center text-sm text-navy-500">
        {{ filterSummary || 'جميع العقود' }}
      </div>
    </div>

    <!-- Table with dynamic columns -->
    <table class="w-full text-sm border border-navy-200 print-table">
      <thead class="bg-navy-50/60">
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            class="border border-navy-200 px-3 py-2 text-right font-semibold"
            :class="[col.nowrap ? 'whitespace-nowrap' : '', col.className || '']"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(c, index) in contracts" :key="c.name || c.id" class="hover:bg-navy-50/30">
          <td
            v-for="col in columns"
            :key="col.key"
            class="border border-navy-200 px-3 py-2"
            :class="[col.nowrap ? 'whitespace-nowrap' : '', col.cellClass || '']"
          >
            <template v-if="col.key === 'index'">{{ index + 1 }}</template>
            <template v-else-if="col.key === 'contractNumber'">{{ c.contract_number || c.contractNumber || '—' }}</template>
            <template v-else-if="col.key === 'tenant'">{{ c.tenant_name || c.tenant?.full_name || c.tenant?.fullName || '—' }}</template>
            <template v-else-if="col.key === 'buildingUnit'">{{ getBuildingUnit(c) }}</template>
            <template v-else-if="col.key === 'startDate'">{{ formatDate(c.start_date || c.startDate) }}</template>
            <template v-else-if="col.key === 'endDate'">{{ formatDate(c.end_date || c.endDate) }}</template>
            <template v-else-if="col.key === 'rentAmount'">{{ formatMoney(c.rent_amount || c.rentAmount, currency) }}</template>
            <template v-else-if="col.key === 'status'">{{ statusLabel(c) }}</template>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Totals -->
    <div class="mt-8 border-t-2 border-navy-300 pt-6 text-sm">
      <div class="grid grid-cols-1 gap-4 text-right">
        <div>
          <span class="font-bold text-navy-900">عدد العقود:</span>
          <span class="text-navy-700">{{ total }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatMoney, formatDate } from '@/composables/useApi'

const props = defineProps({
  contracts: { type: Array, default: () => [] },
  appliedFilters: { type: Object, default: () => ({}) },
  total: { type: Number, default: 0 },
  lessorData: { type: Object, default: null },
})

const currency = computed(() => props.lessorData?.currency || 'ILS')

// ---- Filter summary ----
const filterSummary = computed(() => {
  const parts = []
  const f = props.appliedFilters || {}
  if (f.eviction) parts.push('عقود بانتظار الإخلاء')
  if (f.search) parts.push(`بحث: ${f.search}`)
  if (f.status || f.statusValue) parts.push(`الحالة: ${f.status || f.statusValue}`)
  if (f.tenant) parts.push(`المستأجر: ${f.tenant}`)
  if (f.building || f.buildingId) parts.push(`العقار: ${f.building || f.buildingId}`)
  if (f.unit || f.unitId) parts.push(`الوحدة: ${f.unit || f.unitId}`)
  if (f.contractType || f.contractTypeValue) parts.push(`نوع العقد: ${f.contractType || f.contractTypeValue}`)
  if (f.dateRange) parts.push(`الفترة: ${f.dateRange}`)
  return parts.join(' | ')
})

// ---- Dynamic columns ----
const columns = computed(() => {
  const all = [
    { key: 'index', label: '#', always: true, className: 'w-8' },
    { key: 'contractNumber', label: 'رقم العقد', always: true, cellClass: 'font-medium' },
    { key: 'tenant', label: 'المستأجر' },
    { key: 'buildingUnit', label: 'العقار / الوحدة' },
    { key: 'startDate', label: 'تاريخ البداية', always: true, nowrap: true },
    { key: 'endDate', label: 'تاريخ النهاية', always: true, nowrap: true },
    { key: 'rentAmount', label: 'قيمة الإيجار', always: true, nowrap: true, cellClass: 'font-medium' },
    { key: 'status', label: 'الحالة' },
  ]
  const f = props.appliedFilters || {}
  return all.filter((c) => {
    if (c.always) return true
    if (c.key === 'tenant') return !f.tenant
    if (c.key === 'buildingUnit') return !f.unitId && !f.unit
    if (c.key === 'status') return !f.status && !f.statusValue && !f.eviction
    return true
  })
})

// ---- Helpers ----
function getBuildingUnit(c) {
  const buildingName = c.building_name || c.building?.building_name || c.building?.name || ''
  const unitNumber = c.unit_number || c.unit?.unitNumber || c.unit?.unit_number
  const unitStr = unitNumber ? `وحدة ${unitNumber}` : ''
  const f = props.appliedFilters || {}
  if (!f.buildingId && !f.building) {
    return [buildingName, unitStr].filter(Boolean).join(' — ') || '—'
  }
  return unitStr || '—'
}

function statusLabel(c) {
  const status = c.status || c.displayStatus
  const labels = {
    draft: 'مسودة', active: 'نشط', expired: 'منتهي',
    cancelled: 'ملغي', evicted: 'مخلى', pending_eviction: 'بانتظار الإخلاء',
  }
  return labels[status] || status || '—'
}
</script>

<style scoped>
@media print {
  .print-keep-together {
    break-inside: avoid;
  }
  #print-area {
    padding: 0 !important;
  }
}
</style>
