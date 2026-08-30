<template>
  <!--
    Source: Rental_Management_olde/src/components/due/DuesListPrintDocument.tsx
    Colors matched to old project's CSS variables (globals.css):
      --foreground (#002350), --muted-foreground (#656970), --muted (#F3F2F0),
      --border (#E5E2DB), --destructive (#C63D3D), --card (#FFFFFF).
    Font: IBM Plex Sans Arabic (old body font) — applied to print document only.
    CSS module: DuesListPrintDocument.module.css — replicated as scoped styles.
  -->
  <div class="dues-list-print-document print-document bg-white p-8" dir="rtl">
    <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />

    <div class="print-keep-together border-b-2 dlp-border pb-4 mb-6">
      <h1 class="text-2xl font-bold dlp-fg text-center mb-4">تقرير الالتزامات</h1>
      <div class="text-center text-sm dlp-muted-fg">
        {{ filterSummary || 'جميع الالتزامات' }}
      </div>
    </div>

    <table class="dlp-print-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :class="[col.nowrap && 'whitespace-nowrap', col.className]">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <template v-for="(d, index) in dues" :key="d.id || d.name">
        <tbody>
          <tr
            class="dlp-due-row"
            :class="d.status === 'cancelled' ? 'dlp-muted-fg' : ''"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="[
                col.nowrap && 'whitespace-nowrap',
                col.cellClass,
                col.key === 'amount' && d.status === 'cancelled' && 'line-through'
              ]"
            >
              {{ renderCell(col.key, d, index) }}
            </td>
          </tr>
          <tr v-if="hasNotes(d)" class="dlp-note-row">
            <td :colSpan="columns.length">
              ملاحظة: {{ noteText(d) }}
            </td>
          </tr>
        </tbody>
      </template>
    </table>

    <div class="print-totals mt-8 border-t-2 dlp-border pt-6 text-sm">
      <div
        class="grid gap-4 text-right"
        :class="showAmountTotal ? 'grid-cols-2' : 'grid-cols-1'"
      >
        <div>
          <span class="font-bold dlp-fg">عدد الالتزامات:</span>
          <span class="dlp-fg"> {{ total }}</span>
        </div>
        <div v-if="showAmountTotal">
          <span class="font-bold dlp-fg">إجمالي المبالغ (صافي):</span>
          <span class="dlp-fg"> {{ formatCurrency(totalAmount, currency) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatDate, formatMoney } from '@/composables/useApi'

const props = defineProps({
  dues: { type: Array, default: () => [] },
  appliedFilters: { type: Object, default: null },
  total: { type: Number, default: 0 },
  totalAmount: { type: Number, default: 0 },
  lessorData: { type: Object, default: null },
})

const currency = computed(() => props.lessorData?.currency || 'ILS')
const showAmountTotal = computed(() => props.appliedFilters?.statusValue !== 'cancelled')

// statusLabels (source: DuesListPrintDocument.tsx:54-58)
const statusLabels = {
  draft: 'مسودة',
  approved: 'معتمد',
  cancelled: 'ملغي',
}

// sourceTypeLabels (source: DuesListPrintDocument.tsx:60-65) — NOT used in columns, kept for reference

// activeWaiversTotal (source: DuesListPrintDocument.tsx:67-71)
function activeWaiversTotal(d) {
  return (d.waivers || [])
    .filter((w) => w.status === 'active')
    .reduce((sum, w) => sum + Number(w.amount), 0)
}

// effectiveAmount (source: DuesListPrintDocument.tsx:73-75)
function effectiveAmount(d) {
  return Math.max(Number(d.amount) - activeWaiversTotal(d), 0)
}

// getTemporalStatus (source: DuesListPrintDocument.tsx:77-86)
function getTemporalStatus(d) {
  if (d.status === 'draft') return { label: 'مسودة', status: 'draft' }
  if (d.status === 'cancelled') return { label: 'ملغي', status: 'cancelled' }
  const due = new Date(d.due_date || d.dueDate)
  due.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (due > today) return { label: 'مستقبلي', status: 'upcoming' }
  return { label: 'مستحق', status: 'pending' }
}

// formatCurrency — same as old utils.ts formatCurrency: formatted + ' ' + symbol
function formatCurrency(amount, curr) {
  return formatMoney(amount, curr)
}

// filterSummary (source: DuesListPrintDocument.tsx:103-114)
const filterSummary = computed(() => {
  const parts = []
  const f = props.appliedFilters || {}
  if (f.search) parts.push(`بحث: ${f.search}`)
  if (f.status) parts.push(`الحالة: ${f.status}`)
  if (f.tenant) parts.push(`المستأجر: ${f.tenant}`)
  if (f.contract) parts.push(`العقد: ${f.contract}`)
  if (f.dueType) parts.push(`نوع الالتزام: ${f.dueType}`)
  if (f.sourceType) parts.push(`المصدر: ${f.sourceType}`)
  if (f.dateRange) parts.push(`الفترة: ${f.dateRange}`)
  return parts.join(' | ')
})

// columns (source: DuesListPrintDocument.tsx:116-136)
const columns = computed(() => {
  const all = [
    { key: 'index', label: '#', always: true, className: 'w-8' },
    { key: 'dueNumber', label: 'رقم الالتزام', always: true, cellClass: 'font-medium' },
    { key: 'dueDate', label: 'تاريخ الاستحقاق', always: true, nowrap: true },
    { key: 'tenant', label: 'المستأجر' },
    { key: 'buildingUnit', label: 'العقار / الوحدة' },
    { key: 'contract', label: 'العقد' },
    { key: 'dueType', label: 'نوع الالتزام' },
    { key: 'amount', label: 'المبلغ', always: true, nowrap: true, cellClass: 'font-medium' },
    { key: 'status', label: 'الحالة' },
  ]
  return all.filter((c) => {
    if (c.always) return true
    if (c.key === 'tenant') return !props.appliedFilters?.tenant
    if (c.key === 'buildingUnit' || c.key === 'contract') return !props.appliedFilters?.contract
    if (c.key === 'dueType') return !props.appliedFilters?.dueType
    if (c.key === 'status') return !props.appliedFilters?.status
    return true
  })
})

// noteText (source: DuesListPrintDocument.tsx:161)
function noteText(d) {
  return [d.description, d.notes].filter(Boolean).join(' — ').trim()
}

function hasNotes(d) {
  return noteText(d).length > 0
}

// renderCell (source: DuesListPrintDocument.tsx:176-206)
function renderCell(key, d, index) {
  const temporal = getTemporalStatus(d)
  switch (key) {
    case 'index':
      return index + 1
    case 'dueNumber':
      return d.due_number || d.dueNumber || 'مسودة'
    case 'dueDate':
      return formatDate(d.due_date || d.dueDate)
    case 'tenant':
      return d.tenant_name || d.tenant?.fullName || '—'
    case 'buildingUnit': {
      const buildingName = d.building_name || d.building?.name || ''
      const unitNumber = (d.unit_number || d.unit?.unitNumber) ? `وحدة ${d.unit_number || d.unit?.unitNumber}` : ''
      const location = [buildingName, unitNumber].filter(Boolean).join(' — ')
      return location || '—'
    }
    case 'contract':
      return d.contract_number || d.contract?.contractNumber || '—'
    case 'dueType':
      return d.due_type_name || d.dueType?.name || '—'
    case 'amount':
      return formatCurrency(effectiveAmount(d), currency.value)
    case 'status':
      return statusLabels[temporal.status] || temporal.label
    default:
      return ''
  }
}
</script>

<style scoped>
/*
  Color values sourced from old project globals.css CSS variables (exact hex):
    --foreground       = hsl(214 98% 16%)  = #002350
    --muted-foreground = hsl(220 5% 42%)   = #656970
    --muted            = hsl(43 10% 95%)   = #F3F2F0
    --border           = hsl(40 16% 88%)   = #E5E2DB
    --destructive      = hsl(0 55% 51%)    = #C63D3D
    --card             = hsl(0 0% 100%)    = #FFFFFF
  Font: old body font-family = 'IBM Plex Sans Arabic' (globals.css:89).
  CSS module styles replicated from DuesListPrintDocument.module.css.
  Applied to dues list print document ONLY — does not affect the rest of the app.
*/
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap');

.dues-list-print-document {
  font-family: 'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.dlp-fg { color: #002350; }
.dlp-muted-fg { color: #656970; }
.dlp-border { border-color: #002350; }

@media print {
  .dlp-print-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    break-inside: auto;
    page-break-inside: auto;
  }

  .dlp-print-table thead {
    display: table-row-group;
  }

  .dlp-print-table tbody {
    break-inside: auto;
    page-break-inside: auto;
  }

  .dlp-print-table tr {
    break-inside: auto;
    page-break-inside: auto;
  }

  .dlp-print-table th,
  .dlp-print-table td {
    padding: 8px 6px;
    text-align: right;
    vertical-align: top;
    border-bottom: 1px solid #e5e7eb;
  }

  .dlp-print-table th {
    font-weight: 600;
    background-color: #f3f4f6;
  }

  /* Keep each due record in one piece, but do not force the next record onto the same page. */
  .dlp-due-row {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .dlp-note-row {
    font-size: 12px;
    color: #6b7280;
    background-color: #f9fafb;
    break-inside: auto;
    page-break-inside: auto;
    break-before: avoid;
    page-break-before: avoid;
  }

  .dlp-note-row td {
    padding-top: 4px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;
  }

  .print-keep-together { page-break-inside: avoid; }
}
</style>
