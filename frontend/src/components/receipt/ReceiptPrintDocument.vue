<template>
  <!--
    Source: Rental_Management_olde/src/components/receipt/ReceiptPrintDocument.tsx
    Colors matched to old project's CSS variables (globals.css):
      --foreground (#002350), --muted-foreground (#656970), --muted (#F3F2F0),
      --border (#E5E2DB), --success (#16875E), --destructive (#C63D3D), --card (#FFFFFF).
    Font: IBM Plex Sans Arabic (old body font) — applied to print document only.
  -->
  <div class="receipt-print-document print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <div class="print-keep-together border-b-2 rp-border pb-4 mb-6">
      <h1 class="text-2xl font-bold rp-fg text-center mb-4">{{ isRefund ? 'سند صرف' : 'سند قبض' }}</h1>
      <div v-if="isRefund" class="text-center text-sm rp-muted-fg mb-2">رد مبلغ للمستأجر</div>
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div class="space-y-1">
          <div><span class="font-bold rp-fg">رقم السند:</span> {{ receipt.receipt_number || '—' }}</div>
          <div><span class="font-bold rp-fg">التاريخ:</span> {{ formatDate(receipt.receipt_date) }}</div>
        </div>
        <div class="space-y-1 text-left">
          <div><span class="font-bold rp-fg">المستأجر:</span> {{ receipt.tenant_name || receipt.tenant || '-' }}</div>
          <div v-if="receipt.contract_number || receipt.contract">
            <span class="font-bold rp-fg">رقم العقد:</span> {{ receipt.contract_number || receipt.contract }}
          </div>
        </div>
      </div>
    </div>

    <table class="w-full text-sm border-collapse print-table">
      <thead>
        <tr class="rp-muted-bg border-b rp-border">
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold rp-muted-fg w-1/3">البيان</th>
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold rp-muted-fg">التفاصيل</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i" class="border-b rp-row-border">
          <td class="px-3 py-2.5 text-[14px] font-medium rp-fg">{{ row.label }}</td>
          <td class="px-3 py-2.5 text-[14px] rp-fg">{{ row.value }}</td>
        </tr>
      </tbody>
    </table>

    <div class="print-totals mt-6 border-t-2 rp-border pt-4 text-center text-sm">
      <div class="font-bold rp-fg mb-1">المبلغ</div>
      <div
        class="text-lg font-bold rp-fg"
        :class="receipt.status === 'cancelled' ? 'rp-muted-fg line-through' : ''"
      >
        {{ formatAmount(Number(receipt.amount)) }} {{ currencySymbol }} ({{ currencyLabel }})
      </div>
      <div v-if="receipt.status === 'cancelled' && receipt.cancellation_reason" class="text-xs rp-destructive mt-1">
        ملغي - {{ receipt.cancellation_reason }}
      </div>
    </div>

    <div
      v-if="receipt.attachment && isImageAttachment(receipt.attachment)"
      class="print-keep-together mt-8 border-t-2 rp-border pt-4"
    >
      <div class="font-bold rp-fg mb-3 text-sm text-right">
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
  // Source: old settings.ts getCurrencyLabel (lines 125-132) — exact match
  const labels = { ILS: 'شيكل', JOD: 'دينار أردني', USD: 'دولار' }
  return labels[currency.value] || currency.value
})
const currencySymbol = computed(() => {
  // Source: old settings.ts getCurrencySymbol (lines 134-141) — exact match, default ''
  const symbols = { ILS: '₪', JOD: 'JD', USD: '$' }
  return symbols[currency.value] || ''
})

const methodLabels = { cash: 'نقداُّ', cheque: 'شيك', bank_transfer: 'تحويل بنكي', card: 'بطاقة' }

const isRefund = computed(() => props.receipt?.transaction_type === 'refund')

const rows = computed(() => {
  const r = props.receipt
  const result = [
    { label: 'نوع الحركة', value: isRefund.value ? 'رد للمستأجر' : 'قبض من المستأجر' },
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
/*
  Color values sourced from old project globals.css CSS variables (exact hex):
    --foreground       = hsl(214 98% 16%)  = #002350
    --muted-foreground = hsl(220 5% 42%)   = #656970
    --muted            = hsl(43 10% 95%)   = #F3F2F0
    --border           = hsl(40 16% 88%)   = #E5E2DB
    --success          = hsl(158 72% 31%)  = #16875E
    --destructive      = hsl(0 55% 51%)    = #C63D3D
    --card             = hsl(0 0% 100%)    = #FFFFFF
  Font: old body font-family = 'IBM Plex Sans Arabic' (globals.css:89).
  Applied to receipt print document ONLY — does not affect the rest of the app.
*/
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap');

.receipt-print-document {
  font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.rp-fg { color: #002350; }
.rp-muted-fg { color: #656970; }
.rp-muted-bg { background-color: #F3F2F0; }
.rp-border { border-color: #002350; }
.rp-row-border { border-color: #E5E2DB; }
.rp-success { color: #16875E; }
.rp-destructive { color: #C63D3D; }

@media print {
  .print-table { border-collapse: collapse; }
  .print-keep-together { page-break-inside: avoid; }
}
</style>
