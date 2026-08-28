<template>
  <div id="print-area" class="bg-white p-8" dir="rtl">
    <PrintHeader :logo="settings?.logo" :name="settings?.name" />
    <h1 class="text-xl font-bold text-center my-6">تفاصيل التزام</h1>
    <div class="space-y-3 text-sm">
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">رقم:</span><span class="font-bold">{{ due.due_number }}</span></div>
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">المستأجر:</span><span>{{ due.tenant_name || '—' }}</span></div>
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">النوع:</span><span>{{ due.due_type_name || '—' }}</span></div>
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">التاريخ:</span><span>{{ formatDate(due.transaction_date) }}</span></div>
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">تاريخ الاستحقاق:</span><span>{{ formatDate(due.due_date) }}</span></div>
      <div class="flex justify-between border-b pb-2"><span class="text-gray-500">المبلغ:</span><span class="font-bold tabular-nums">{{ formatMoney(due.amount, currency) }}</span></div>
      <div v-if="due.description" class="flex justify-between border-b pb-2"><span class="text-gray-500">الوصف:</span><span>{{ due.description }}</span></div>
      <div v-if="due.calculation_method === 'metered'" class="flex justify-between border-b pb-2"><span class="text-gray-500">القراءة السابقة:</span><span class="tabular-nums">{{ due.previous_meter_reading }}</span></div>
      <div v-if="due.calculation_method === 'metered'" class="flex justify-between border-b pb-2"><span class="text-gray-500">القراءة الحالية:</span><span class="tabular-nums">{{ due.current_meter_reading }}</span></div>
      <div v-if="due.calculation_method === 'metered'" class="flex justify-between border-b pb-2"><span class="text-gray-500">الاستهلاك:</span><span class="tabular-nums">{{ due.meter_consumption }}</span></div>
      <div v-if="due.calculation_method === 'metered'" class="flex justify-between border-b pb-2"><span class="text-gray-500">سعر الوحدة:</span><span class="tabular-nums">{{ due.unit_price }}</span></div>
      <div class="flex justify-between"><span class="text-gray-500">الحالة:</span><span>{{ statusLabel(due.docstatus) }}</span></div>
    </div>
    <div v-if="settings?.print_footer" class="mt-8 pt-4 border-t border-gray-200 text-xs text-gray-500 text-center">{{ settings.print_footer }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import { formatMoney, formatDate } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'

const props = defineProps({ due: { type: Object, required: true } })
const session = useSession()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const settings = computed(() => session.state.account?.settings || null)

function statusLabel(d) { return d === 1 ? 'معتمد' : (d === 2 ? 'ملغي' : 'مسودة') }
</script>
