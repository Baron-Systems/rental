<template>
  <div class="print-document" dir="rtl">
    <PrintHeader :logo="lessor?.logo" :name="lessor?.name" />

    <!-- Tenant info -->
    <div class="tenant-info">
      <div class="space-y-1.5">
        <div><span class="label">اسم المستأجر:</span> <b>{{ tenant?.full_name }}</b></div>
        <div><span class="label">رقم الهوية:</span> {{ tenant?.national_id || '-' }}</div>
        <div v-if="singleContract">
          <span class="label">رقم العقد:</span> {{ singleContract.contract_number }}
        </div>
      </div>
      <div class="space-y-1.5 text-left">
        <template v-if="singleContract">
          <div><span class="label">العقار:</span> {{ singleContract.building_name || '-' }}</div>
          <div><span class="label">الوحدة:</span> {{ singleContract.unit_number || '-' }}</div>
        </template>
        <div v-else>
          <span class="label">نطاق الكشف:</span> جميع العقود
        </div>
        <div><span class="label">تاريخ إصدار التقرير:</span> {{ reportDate || formatDate(new Date().toISOString()) }}</div>
      </div>
    </div>

    <!-- Statement table -->
    <table class="print-table">
      <thead>
        <tr>
          <th>المرجع</th>
          <th>التاريخ</th>
          <th>النوع</th>
          <th v-if="showUnitColumn">الوحدة</th>
          <th class="num">المستحق</th>
          <th class="num">المدفوع</th>
          <th class="num">الرصيد</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(line, i) in lines" :key="i">
          <td>{{ line.reference || '-' }}</td>
          <td>{{ formatDate(line.date) }}</td>
          <td>{{ line.typeName || line.type }}</td>
          <td v-if="showUnitColumn">{{ line.unit || '—' }}</td>
          <td class="num red" v-if="line.debit > 0">{{ formatMoney(line.debit, currency) }}</td>
          <td class="num" v-else>-</td>
          <td class="num green" v-if="line.credit > 0">{{ formatMoney(line.credit, currency) }}</td>
          <td class="num" v-else>-</td>
          <td class="num bold">{{ formatMoney(line.balance, currency) }}</td>
        </tr>
        <tr v-if="!lines.length"><td :colspan="showUnitColumn ? 7 : 6" class="empty"><div class="empty-title">لا توجد حركات</div><div class="empty-desc">لا توجد حركات في كشف الحساب.</div></td></tr>
      </tbody>
    </table>

    <!-- Totals -->
    <div class="totals">
      <div>إجمالي المستحقات: <b class="red">{{ formatMoney(totalDues, currency) }}</b></div>
      <div>إجمالي المدفوعات: <b class="green">{{ formatMoney(totalReceipts, currency) }}</b></div>
      <div>الرصيد الحالي: <b :class="closingClass">{{ formatMoney(closingBalance, currency) }}</b></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatMoney, formatDate } from '@/composables/useApi'

const props = defineProps({
  tenant: { type: Object, default: () => ({}) },
  statement: { type: Object, default: () => ({}) },
  lessor: { type: Object, default: () => ({}) },
  currency: { type: String, default: 'ILS' },
  // single-contract mode hides the unit column and shows contract/building/unit header
  singleContract: { type: Object, default: null },
  reportDate: { type: String, default: '' },
})

const lines = computed(() => props.statement?.lines || [])
const totalDues = computed(() => props.statement?.totalDues ?? 0)
const totalReceipts = computed(() => props.statement?.totalReceipts ?? 0)
const closingBalance = computed(() => props.statement?.closingBalance ?? 0)

const showUnitColumn = computed(() => !props.singleContract) // all-contracts mode shows unit column
const scopeHeader = computed(() => props.singleContract
  ? `العقد: ${props.singleContract.contract_number}`
  : 'جميع العقود')

const closingClass = computed(() => {
  const bal = closingBalance.value
  if (bal > 0) return 'red'
  if (bal < 0) return 'green'
  return ''
})
</script>

<script>
export default { name: 'TenantPrintDocument' }
</script>

<style scoped>
.print-document { padding: 24px; color: #1a2238; font-family: Arial, sans-serif; }
.tenant-info { display: flex; gap: 24px; flex-wrap: wrap; font-size: 13px; margin: 12px 0; }
.tenant-info .label { color: #64748b; }
.print-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.print-table th, .print-table td { border: 1px solid #e2e8f0; padding: 6px 8px; text-align: right; }
.print-table th { background: #f1f5f9; }
.num { text-align: left; }
.bold { font-weight: bold; }
.red { color: #dc2626; }
.green { color: #059669; }
.empty { text-align: center; color: #94a3b8; padding: 16px; }
.empty-title { font-weight: bold; margin-bottom: 4px; }
.empty-desc { font-size: 12px; }
.totals { margin-top: 16px; display: flex; gap: 24px; font-size: 13px; flex-wrap: wrap; }
.totals div { padding: 8px 12px; background: #f8fafc; border-radius: 6px; }
@media print { print-color-adjust: exact; }
</style>
