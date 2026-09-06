<template>
  <div class="print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <div class="print-keep-together border-b-2 border-navy-900 pb-4 mb-6">
      <h1 class="text-2xl font-bold text-navy-900 text-center mb-4">تقرير سندات القبض</h1>
      <div class="text-center text-sm text-navy-500">
        {{ filterSummary || 'جميع سندات القبض' }}
      </div>
    </div>

    <table class="w-full text-sm border-collapse print-table">
      <thead>
        <tr class="bg-ivory-100 border-b border-navy-900">
          <th
            v-for="col in columns"
            :key="col.key"
            class="px-3 py-2.5 text-right text-[13px] font-semibold text-navy-500"
            :class="{ 'whitespace-nowrap': col.nowrap, [col.className]: !!col.className }"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <template v-for="(r, index) in receipts" :key="r.name || index">
        <tbody>
          <tr
            class="border-b border-ivory-300"
            :class="{ 'text-navy-400': r.status === 'cancelled' || r.docstatus === 2 }"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-3 py-2.5 text-[14px]"
              :class="{
                'whitespace-nowrap': col.nowrap,
                'font-medium': col.cellClass === 'font-medium',
                'line-through': col.key === 'amount' && (r.status === 'cancelled' || r.docstatus === 2),
              }"
            >
              {{ getCellContent(col.key, r, index) }}
            </td>
          </tr>
          <tr v-if="hasNotes(r)" class="border-b border-ivory-200 bg-ivory-50/30">
            <td :colspan="columns.length" class="px-3 py-1.5 text-xs text-navy-500">
              ملاحظة: {{ (r.notes || '').trim() }}
            </td>
          </tr>
        </tbody>
      </template>
    </table>

    <div class="print-totals mt-8 border-t-2 border-navy-900 pt-6 text-sm">
      <div
        class="grid gap-4 text-right"
        :class="showTotalAmount ? 'grid-cols-4' : 'grid-cols-1'"
      >
        <div>
          <span class="font-bold text-navy-900">عدد السندات:</span>
          <span class="text-navy-900">{{ total }}</span>
        </div>
        <div v-if="showTotalAmount">
          <span class="font-bold text-navy-900">إجمالي المقبوضات:</span>
          <span class="text-emerald-700">{{ formatMoney(totalReceipts, currency) }}</span>
        </div>
        <div v-if="showTotalAmount">
          <span class="font-bold text-navy-900">إجمالي المبالغ المردودة:</span>
          <span class="text-blue-700">{{ formatMoney(totalRefunds, currency) }}</span>
        </div>
        <div v-if="showTotalAmount">
          <span class="font-bold text-navy-900">صافي التحصيل:</span>
          <span class="text-navy-900">{{ formatMoney(totalReceipts - totalRefunds, currency) }}</span>
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
  receipts: { type: Array, default: () => [] },
  appliedFilters: { type: Object, default: () => ({}) },
  total: { type: Number, default: 0 },
  totalAmount: { type: Number, default: 0 },
  lessorData: { type: Object, default: null },
})

const currency = computed(() => props.lessorData?.currency || 'ILS')

const methodLabels = { cash: 'نقداً', cheque: 'شيك', bank_transfer: 'تحويل بنكي', card: 'بطاقة' }
const statusLabels = { draft: 'مسودة', approved: 'معتمد', cancelled: 'ملغي' }

const showTotalAmount = computed(() => {
  return props.appliedFilters?.statusValue !== 'draft' && props.appliedFilters?.statusValue !== 'cancelled'
})

const totalReceipts = computed(() => {
  return props.receipts
    .filter((r) => r.transaction_type !== 'refund' && (r.status === 'approved' || r.docstatus === 1))
    .reduce((sum, r) => sum + Number(r.amount || 0), 0)
})

const totalRefunds = computed(() => {
  return props.receipts
    .filter((r) => r.transaction_type === 'refund' && (r.status === 'approved' || r.docstatus === 1))
    .reduce((sum, r) => sum + Number(r.amount || 0), 0)
})

const filterSummary = computed(() => {
  const parts = []
  const f = props.appliedFilters || {}
  if (f.search) parts.push(`بحث: ${f.search}`)
  if (f.status) parts.push(`الحالة: ${f.status}`)
  if (f.tenant) parts.push(`المستأجر: ${f.tenant}`)
  if (f.contract) parts.push(`العقد: ${f.contract}`)
  if (f.paymentMethod) parts.push(`طريقة الدفع: ${f.paymentMethod}`)
  if (f.dateRange) parts.push(`الفترة: ${f.dateRange}`)
  return parts.join(' | ')
})

const columns = computed(() => {
  const all = [
    { key: 'index', label: '#', always: true, className: 'w-8' },
    { key: 'receiptNumber', label: 'رقم السند', always: true, cellClass: 'font-medium' },
    { key: 'date', label: 'التاريخ', always: true, nowrap: true },
    { key: 'tenant', label: 'المستأجر' },
    { key: 'buildingUnit', label: 'العقار / الوحدة' },
    { key: 'contract', label: 'العقد' },
    { key: 'amount', label: 'المبلغ', always: true, nowrap: true, cellClass: 'font-medium' },
    { key: 'transactionType', label: 'النوع', always: true },
    { key: 'paymentMethod', label: 'طريقة الدفع' },
    { key: 'status', label: 'الحالة' },
  ]
  return all.filter((c) => {
    if (c.always) return true
    if (c.key === 'tenant') return !props.appliedFilters?.tenant
    if (c.key === 'buildingUnit' || c.key === 'contract') return !props.appliedFilters?.contract
    if (c.key === 'paymentMethod') return !props.appliedFilters?.paymentMethod
    if (c.key === 'status') return !props.appliedFilters?.status
    return true
  })
})

function hasNotes(r) {
  return typeof r.notes === 'string' && r.notes.trim().length > 0
}

function getCellContent(key, r, index) {
  switch (key) {
    case 'index':
      return index + 1
    case 'receiptNumber':
      return r.receipt_number || r.receiptNumber || '—'
    case 'date':
      return formatDate(r.receipt_date || r.receiptDate)
    case 'tenant':
      return r.tenant_name || r.tenant?.full_name || r.tenant?.fullName || '—'
    case 'buildingUnit': {
      const buildingName = r.building_name || r.building?.building_name || r.building?.name || ''
      const unitNumber = r.unit_number || (r.unit?.unit_number ? `وحدة ${r.unit.unit_number}` : '') || (r.unit?.unitNumber ? `وحدة ${r.unit.unitNumber}` : '')
      const location = [buildingName, unitNumber].filter(Boolean).join(' — ')
      return location || '—'
    }
    case 'contract':
      return r.contract_number || r.contract?.contract_number || r.contract?.contractNumber || '—'
    case 'amount':
      return formatMoney(r.amount, currency.value)
    case 'transactionType':
      return r.transaction_type === 'refund' ? 'رد للمستأجر' : 'قبض'
    case 'paymentMethod':
      return methodLabels[r.payment_method || r.paymentMethod] || r.payment_method || r.paymentMethod
    case 'status': {
      const status = r.status || (r.docstatus === 1 ? 'approved' : r.docstatus === 2 ? 'cancelled' : 'draft')
      return statusLabels[status] || status
    }
    default:
      return ''
  }
}
</script>

<style scoped>
@media print {
  .print-table { border-collapse: collapse; }
  .print-keep-together { page-break-inside: avoid; }
}
</style>
