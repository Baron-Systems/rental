
<template>
  <div class="print-document" dir="rtl">
    <PrintHeader :title="'تقرير المستأجرين'" :subtitle="filterSummary" :lessor="lessor" />

    <table class="print-table">
      <thead>
        <tr>
          <th>#</th>
          <th>اسم المستأجر</th>
          <th>رقم الهوية</th>
          <th>الهاتف</th>
          <th v-if="showContractColumn">العقد الحالي / القادم</th>
          <th v-if="showBuildingUnitColumn">العقار / الوحدة</th>
          <th class="num">الرصيد</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(t, i) in tenants" :key="t.name">
          <td>{{ i + 1 }}</td>
          <td class="bold">{{ t.full_name }}</td>
          <td>{{ t.national_id || '—' }}</td>
          <td dir="ltr">{{ t.phone || '—' }}</td>
          <td v-if="showContractColumn">{{ t.currentContract?.contract_number || '—' }}</td>
          <td v-if="showBuildingUnitColumn">{{ locationFor(t.currentContract) }}</td>
          <td class="num bold" :class="balanceClass(t.balance)">{{ formatMoney(t.balance, currency) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Group totals -->
    <div class="totals">
      <div><span class="label">عدد المستأجرين:</span> <b>{{ total }}</b></div>
      <div><span class="label">عليهم رصيد:</span> <b>{{ debtorsCount }}</b> مستأجر — <span class="label">إجمالي</span> <b>{{ formatMoney(debtTotal, currency) }}</b></div>
      <div><span class="label">لهم رصيد:</span> <b>{{ creditorsCount }}</b> مستأجر — <span class="label">إجمالي</span> <b>{{ formatMoney(creditTotal, currency) }}</b></div>
      <div><span class="label">الرصيد صفر:</span> <b>{{ zeroCount }}</b> مستأجر</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatMoney } from '@/composables/useApi'

const props = defineProps({
  tenants: { type: Array, default: () => [] },
  stats: { type: Object, default: () => ({}) },
  total: { type: Number, default: 0 },
  currency: { type: String, default: 'ILS' },
  showContractColumn: { type: Boolean, default: true },
  showBuildingUnitColumn: { type: Boolean, default: true },
  hideBuildingInLocation: { type: Boolean, default: false },
  filterSummary: { type: String, default: '' },
  lessor: { type: Object, default: () => ({}) },
})

const debtorsCount = computed(() => props.stats?.debt ?? props.tenants.filter(t => (t.balance ?? 0) > 0).length)
const creditorsCount = computed(() => props.stats?.credit ?? props.tenants.filter(t => (t.balance ?? 0) < 0).length)
const zeroCount = computed(() => props.stats?.zero ?? props.tenants.filter(t => (t.balance ?? 0) === 0).length)
const debtTotal = computed(() => props.tenants.reduce((s, t) => s + (t.balance > 0 ? t.balance : 0), 0))
const creditTotal = computed(() => props.tenants.reduce((s, t) => s + (t.balance < 0 ? Math.abs(t.balance) : 0), 0))

function balanceClass(bal) {
  if (bal > 0) return 'text-red'
  if (bal < 0) return 'text-green'
  return ''
}

function locationFor(contract) {
  if (!contract) return '—'
  const buildingName = props.hideBuildingInLocation ? '' : (contract.building_name || '')
  const unitNumber = contract.unit_number ? `وحدة ${contract.unit_number}` : ''
  return [buildingName, unitNumber].filter(Boolean).join(' — ') || '—'
}
</script>

<style scoped>
.print-document { padding: 24px; color: #1a2238; font-family: Arial, sans-serif; }
.print-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 16px; }
.print-table th, .print-table td { border: 1px solid #e2e8f0; padding: 6px 8px; text-align: right; }
.print-table th { background: #f1f5f9; }
.num { text-align: left; }
.bold { font-weight: bold; }
.text-red { color: #dc2626; }
.text-green { color: #059669; }
.totals { margin-top: 16px; display: flex; gap: 24px; font-size: 13px; flex-wrap: wrap; }
.totals div { padding: 8px 12px; background: #f8fafc; border-radius: 6px; }
.totals .label { color: #64748b; font-weight: bold; }
@media print { .no-print { display: none; } }
</style>
