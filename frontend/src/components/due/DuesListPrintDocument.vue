<template>
  <div id="print-area" class="bg-white p-8" dir="rtl">
    <PrintHeader :logo="settings?.logo" :name="settings?.name" />
    <h1 class="text-xl font-bold text-center my-6">قائمة الالتزامات</h1>
    <table class="w-full text-sm border border-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th class="border border-gray-200 px-3 py-2 text-right">رقم</th>
          <th class="border border-gray-200 px-3 py-2 text-right">المستأجر</th>
          <th class="border border-gray-200 px-3 py-2 text-right">النوع</th>
          <th class="border border-gray-200 px-3 py-2 text-right">التاريخ</th>
          <th class="border border-gray-200 px-3 py-2 text-right">المبلغ</th>
          <th class="border border-gray-200 px-3 py-2 text-right">الحالة</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in dues" :key="d.name">
          <td class="border border-gray-200 px-3 py-2">{{ d.due_number }}</td>
          <td class="border border-gray-200 px-3 py-2">{{ d.tenant_name || '—' }}</td>
          <td class="border border-gray-200 px-3 py-2">{{ d.due_type_name || '—' }}</td>
          <td class="border border-gray-200 px-3 py-2">{{ formatDate(d.transaction_date) }}</td>
          <td class="border border-gray-200 px-3 py-2 tabular-nums">{{ formatMoney(d.amount, currency) }}</td>
          <td class="border border-gray-200 px-3 py-2">{{ statusLabel(d.docstatus) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="printTotal" class="mt-6 text-right">
      <p class="text-sm font-bold">الإجمالي: {{ formatMoney(printTotal, currency) }}</p>
    </div>
    <div v-if="settings?.print_footer" class="mt-8 pt-4 border-t border-gray-200 text-xs text-gray-500 text-center">{{ settings.print_footer }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatMoney, formatDate } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'

const props = defineProps({
  dues: { type: Array, default: () => [] },
  printTotal: { type: Number, default: null },
})
const session = useSession()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const settings = computed(() => session.state.account?.settings || null)

function statusLabel(d) { return d === 1 ? 'معتمد' : (d === 2 ? 'ملغي' : 'مسودة') }
</script>
