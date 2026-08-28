<template>
  <div class="print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <div class="print-keep-together border-b-2 border-navy-900 pb-4 mb-6">
      <h1 class="text-2xl font-bold text-navy-900 text-center mb-4">سند قبض</h1>
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div class="space-y-1">
          <div><span class="font-bold text-navy-900">رقم السند:</span> {{ receipt.receipt_number || '—' }}</div>
          <div><span class="font-bold text-navy-900">التاريخ:</span> {{ formatDate(receipt.receipt_date) }}</div>
        </div>
        <div class="space-y-1 text-left">
          <div><span class="font-bold text-navy-900">المستأجر:</span> {{ receipt.tenant_name || receipt.tenant || '-' }}</div>
          <div v-if="receipt.contract_number || receipt.contract">
            <span class="font-bold text-navy-900">رقم العقد:</span> {{ receipt.contract_number || receipt.contract }}
          </div>
        </div>
      </div>
    </div>

    <table class="w-full text-sm border-collapse print-table">
      <thead>
        <tr class="bg-ivory-100 border-b border-navy-900">
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold text-navy-500 w-1/3">البيان</th>
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold text-navy-500">التفاصيل</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i" class="border-b border-ivory-300">
          <td class="px-3 py-2.5 text-[14px] font-medium text-navy-900">{{ row.label }}</td>
          <td class="px-3 py-2.5 text-[14px] text-navy-900">{{ row.value }}</td>
        </tr>
      </tbody>
    </table>

    <div class="print-totals mt-6 border-t-2 border-navy-900 pt-4 text-center text-sm">
      <div class="font-bold text-navy-900 mb-1">المبلغ</div>
      <div
        class="text-lg font-bold"
        :class="receipt.status === 'cancelled' ? 'text-navy-400 line-through' : 'text-emerald-600'"
      >
        {{ formatAmount(Number(receipt.amount)) }} {{ currencySymbol }} ({{ currencyLabel }})
      </div>
      <div v-if="receipt.status === 'cancelled' && receipt.cancellation_reason" class="text-xs text-red-600 mt-1">
        ملغي - {{ receipt.cancellation_reason }}
      </div>
    </div>

    <div
      v-if="receipt.attachment && isImageAttachment(receipt.attachment)"
      class="print-keep-together mt-8 border-t-2 border-navy-900 pt-4"
    >
      <div class="font-bold text-navy-900 mb-3 text-sm text-right">
        {{ receipt.payment_method === 'cheque' ? 'صورة الشيك' : 'الصورة المرفقة' }}
      </div>
      <img
        :src="receipt.attachment"
        :alt="receipt.payment_method === 'cheque' ? 'صورة الشيك' : 'الصورة المرفقة'"
        class="block"
        style="max-width: 130mm; max-height: 100mm; width: auto; height: auto; object-fit: contain;"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatDate, formatMoney } from '@/composables/useApi'

const props = defineProps({
  receipt: { type: Object, required: true },
  lessorData: { type: Object, default: null },
})

const currency = computed(() => props.lessorData?.currency || 'ILS')
const currencyLabel = computed(() => {
  const labels = { ILS: 'شيكل', USD: 'دولار', EUR: 'يورو', JOD: 'دينار', SAR: 'ريال', AED: 'درهم' }
  return labels[currency.value] || currency.value
})
const currencySymbol = computed(() => {
  const symbols = { ILS: '₪', USD: '$', EUR: '€', JOD: 'د.أ', SAR: 'ر.س', AED: 'د.إ' }
  return symbols[currency.value] || currency.value
})

const methodLabels = { cash: 'نقداً', cheque: 'شيك' }

const rows = computed(() => {
  const r = props.receipt
  const result = [
    { label: 'العقار', value: r.building_name || r.building || '-' },
    { label: 'الوحدة', value: r.unit_number || r.unit || '-' },
    { label: 'طريقة الدفع', value: methodLabels[r.payment_method] || r.payment_method },
  ]
  if (r.payment_method === 'cheque') {
    result.push({ label: 'رقم الشيك', value: r.reference_number || '-' })
    if (r.cheque_date) result.push({ label: 'تاريخ الشيك', value: formatDate(r.cheque_date) })
    if (r.bank_name) result.push({ label: 'اسم البنك', value: r.bank_name })
  }
  if (r.notes) result.push({ label: 'ملاحظات', value: r.notes })
  return result
})

function formatAmount(amount) {
  return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function isImageAttachment(data) {
  return typeof data === 'string' && data.startsWith('data:image/')
}
</script>

<style scoped>
@media print {
  .print-table { border-collapse: collapse; }
  .print-keep-together { page-break-inside: avoid; }
}
</style>
