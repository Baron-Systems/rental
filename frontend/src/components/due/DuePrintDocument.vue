<template>
  <!--
    Source: Rental_Management_olde/src/components/due/DuePrintDocument.tsx
    Colors matched to old project's CSS variables (globals.css):
      --foreground (#002350), --muted-foreground (#656970), --muted (#F3F2F0),
      --border (#E5E2DB), --success (#16875E), --destructive (#C63D3D),
      --warning (#C87617), --card (#FFFFFF).
    Font: IBM Plex Sans Arabic (old body font) — applied to print document only.
  -->
  <div class="due-print-document print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <div class="print-keep-together border-b-2 dp-border pb-4 mb-6">
      <h1 class="text-2xl font-bold dp-fg text-center mb-4">سند التزام</h1>
      <div class="grid grid-cols-2 gap-4 text-sm">
        <div class="space-y-1">
          <div class="break-words"><span class="font-bold dp-fg">رقم السند:</span> {{ d.due_number || '—' }}</div>
          <div class="break-words"><span class="font-bold dp-fg">التاريخ:</span> {{ formatDate(d.transaction_date) }}</div>
        </div>
        <div class="space-y-1 text-left">
          <div class="break-words"><span class="font-bold dp-fg">المستأجر:</span> {{ d.tenant_name || d.tenant?.fullName || '-' }}</div>
          <div v-if="d.contract || d.contract_number" class="break-words">
            <span class="font-bold dp-fg">رقم العقد:</span> {{ d.contract_number || d.contract?.contractNumber }}
          </div>
        </div>
      </div>
    </div>

    <table class="w-full text-sm border-collapse print-table">
      <thead>
        <tr class="dp-muted-bg border-b dp-border">
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold dp-muted-fg w-1/3">البيان</th>
          <th class="px-3 py-2.5 text-right text-[13px] font-semibold dp-muted-fg">التفاصيل</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i" class="border-b dp-row-border">
          <td class="px-3 py-2.5 text-[14px] font-medium dp-fg">{{ row.label }}</td>
          <td class="px-3 py-2.5 text-[14px] dp-fg break-words">{{ row.value }}</td>
        </tr>
        <!-- Meter data sub-table (source: DuePrintDocument.tsx:195-219) -->
        <tr v-if="meterRows.length > 0" class="border-b dp-row-border">
          <td colspan="2" class="px-3 py-3">
            <div class="font-bold dp-fg mb-2">بيانات العداد</div>
            <table class="w-full text-sm border-collapse print-table">
              <thead>
                <tr class="dp-muted-bg border-b dp-row-border">
                  <th class="px-2 py-1.5 text-right text-[13px] font-semibold dp-muted-fg">القراءة السابقة</th>
                  <th class="px-2 py-1.5 text-right text-[13px] font-semibold dp-muted-fg">القراءة الحالية</th>
                  <th class="px-2 py-1.5 text-right text-[13px] font-semibold dp-muted-fg">الاستهلاك</th>
                  <th class="px-2 py-1.5 text-right text-[13px] font-semibold dp-muted-fg">سعر الوحدة</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td class="px-2 py-1.5 text-[14px] dp-fg break-words">{{ d.previous_meter_reading != null ? d.previous_meter_reading : '-' }}</td>
                  <td class="px-2 py-1.5 text-[14px] dp-fg break-words">{{ d.current_meter_reading != null ? d.current_meter_reading : '-' }}</td>
                  <td class="px-2 py-1.5 text-[14px] dp-fg break-words">{{ d.meter_consumption != null ? d.meter_consumption : '-' }}</td>
                  <td class="px-2 py-1.5 text-[14px] dp-fg break-words">{{ d.unit_price != null ? `${formatAmount(Number(d.unit_price))} ${currencySymbol} (${currencyLabel})` : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- WaiverAmountFooter (source: DuePrintDocument.tsx:56-106, 223-225) -->
    <div class="print-totals mt-6 border-t-2 dp-border pt-4 text-center text-sm">
      <!-- No waiver case -->
      <template v-if="waived === 0">
        <div class="font-bold dp-fg mb-1">المبلغ</div>
        <div class="text-lg font-bold" :class="d.status === 'cancelled' ? 'dp-muted-fg line-through' : 'dp-destructive'">
          {{ formatAmount(original) }} {{ currencySymbol }} ({{ currencyLabel }})
        </div>
        <div v-if="d.status === 'cancelled'" class="text-xs dp-destructive mt-1">ملغي</div>
      </template>
      <!-- Fully waived case -->
      <template v-else-if="isFullyWaived">
        <div class="font-bold dp-fg mb-1">المبلغ الفعلي بعد الإعفاء</div>
        <div class="text-lg font-bold dp-muted-fg line-through">
          {{ formatAmount(original) }} {{ currencySymbol }} ({{ currencyLabel }})
        </div>
        <div class="text-sm font-bold dp-success mt-1">معفى بالكامل</div>
        <div class="text-lg font-bold dp-destructive mt-1">{{ formatAmount(0) }} {{ currencySymbol }} ({{ currencyLabel }})</div>
        <div v-if="d.status === 'cancelled'" class="text-xs dp-destructive mt-1">ملغي</div>
      </template>
      <!-- Partially waived case -->
      <template v-else>
        <div class="font-bold dp-fg mb-1">المبلغ الأصلي</div>
        <div class="text-lg font-bold dp-muted-fg line-through">
          {{ formatAmount(original) }} {{ currencySymbol }} ({{ currencyLabel }})
        </div>
        <div class="text-sm dp-muted-fg mt-1">المعفى: {{ formatAmount(waived) }} {{ currencySymbol }} ({{ currencyLabel }})</div>
        <div class="text-sm font-bold dp-warning mt-1">معفى جزئياً</div>
        <div class="text-lg font-bold dp-destructive mt-1">{{ formatAmount(effective) }} {{ currencySymbol }} ({{ currencyLabel }})</div>
        <div v-if="d.status === 'cancelled'" class="text-xs dp-destructive mt-1">ملغي</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatDate } from '@/composables/useApi'

const props = defineProps({
  due: { type: Object, required: true },
  lessorData: { type: Object, default: null },
})

const d = computed(() => props.due)

// Currency (source: old settings.ts getCurrencyLabel/getCurrencySymbol — exact match)
const currency = computed(() => props.lessorData?.currency || 'ILS')
const currencyLabel = computed(() => {
  const labels = { ILS: 'شيكل', JOD: 'دينار أردني', USD: 'دولار' }
  return labels[currency.value] || currency.value
})
const currencySymbol = computed(() => {
  const symbols = { ILS: '₪', JOD: 'JD', USD: '$' }
  return symbols[currency.value] || ''
})

// Helpers (source: DuePrintDocument.tsx:38-54, 108-138)
function formatAmount(amount) {
  return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function isMeterDue(due) {
  return due && due.calculation_method === 'metered'
}

function activeWaiversTotal(due) {
  return (due.waivers || [])
    .filter((w) => w.status === 'active')
    .reduce((sum, w) => sum + Number(w.amount), 0)
}

function hasMeterData(due) {
  // Source: DuePrintDocument.tsx:108-110 — uses || which works for String? in old.
  // In Frappe, meter readings are Float (numbers), so 0 is falsy with ||.
  // Fix: use != null to preserve 0 values (same behavior as old String "0" being truthy).
  return isMeterDue(due) && (due.previous_meter_reading != null || due.current_meter_reading != null || due.meter_consumption != null || due.unit_price != null)
}

// getDueDetails (source: DuePrintDocument.tsx:112-138)
const details = computed(() => {
  const due = d.value
  const rows = []

  if (due.source_type === 'auto_contract' && due.period_label) {
    rows.push({ label: 'الفترة', value: due.period_label })
  }

  if (due.source_type === 'additional') {
    rows.push({ label: 'سبب الالتزام', value: due.description || '-' })
  } else if (due.source_type !== 'auto_contract' && due.description) {
    rows.push({ label: 'البيان', value: due.description })
  }

  if (due.source_type !== 'auto_contract' && due.reference_number) {
    rows.push({ label: 'رقم المرجع', value: due.reference_number })
  }

  if (due.notes) {
    rows.push({ label: 'ملاحظات', value: due.notes })
  }

  if (due.status === 'cancelled' && due.cancellation_reason) {
    rows.push({ label: 'سبب الإلغاء', value: due.cancellation_reason })
  }

  return rows
})

// Main rows (source: DuePrintDocument.tsx:144-150)
const rows = computed(() => {
  const due = d.value
  return [
    { label: 'نوع الالتزام', value: due.due_type_name || due.due_type?.name || '-' },
    { label: 'تاريخ الاستحقاق', value: formatDate(due.due_date) },
    { label: 'العقار', value: due.building_name || due.building?.name || '-' },
    { label: 'الوحدة', value: due.unit_number || due.unit?.unitNumber || '-' },
    ...details.value,
  ]
})

// Meter rows (source: DuePrintDocument.tsx:154-159) — used to conditionally show sub-table
const meterRows = computed(() => {
  const due = d.value
  return hasMeterData(due) ? [
    { label: 'القراءة السابقة', value: due.previous_meter_reading != null ? due.previous_meter_reading : '-' },
    { label: 'القراءة الحالية', value: due.current_meter_reading != null ? due.current_meter_reading : '-' },
    { label: 'الاستهلاك', value: due.meter_consumption != null ? due.meter_consumption : '-' },
    { label: 'سعر الوحدة', value: due.unit_price != null ? `${formatAmount(Number(due.unit_price))} ${currencySymbol.value} (${currencyLabel.value})` : '-' },
  ] : []
})

// Waiver calculations (source: DuePrintDocument.tsx:56-106)
const original = computed(() => Number(d.value.amount))
const waived = computed(() => activeWaiversTotal(d.value))
const effective = computed(() => Math.max(original.value - waived.value, 0))
const isFullyWaived = computed(() => waived.value >= original.value)
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
    --warning          = hsl(32 79% 44%)   = #C87617
    --card             = hsl(0 0% 100%)    = #FFFFFF
  Font: old body font-family = 'IBM Plex Sans Arabic' (globals.css:89).
  Applied to due print document ONLY — does not affect the rest of the app.
*/
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap');

.due-print-document {
  font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.dp-fg { color: #002350; }
.dp-muted-fg { color: #656970; }
.dp-muted-bg { background-color: #F3F2F0; }
.dp-border { border-color: #002350; }
.dp-row-border { border-color: #E5E2DB; }
.dp-success { color: #16875E; }
.dp-destructive { color: #C63D3D; }
.dp-warning { color: #C87617; }

@media print {
  .print-table { border-collapse: collapse; }
  .print-keep-together { page-break-inside: avoid; }
}
</style>
