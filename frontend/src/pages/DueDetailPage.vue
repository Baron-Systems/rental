<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div v-else-if="!due" class="text-center py-20">
        <p class="text-navy-400">الالتزام غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Dues' })">العودة للقائمة</button>
      </div>

      <div v-else class="animate-fade-in">
        <PageHeader :title="due.due_number" :back-href="'/dues'">
          <template #actions>
            <button class="btn-premium btn-outline" @click="handlePrint">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              طباعة
            </button>
            <button v-if="due.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(due.source_type)" class="btn-premium btn-outline" @click="toggleEdit">{{ editMode ? 'إلغاء التعديل' : 'تعديل' }}</button>
            <button v-if="due.status === 'draft'" class="btn-premium btn-gold" @click="approveDue">اعتماد</button>
            <button v-if="due.status !== 'cancelled'" class="btn-premium btn-ghost text-amber-700" @click="cancelDue">إلغاء</button>
            <button v-if="due.status === 'draft'" class="btn-premium btn-ghost text-red-600" @click="deleteDue">حذف</button>
          </template>
        </PageHeader>

        <!-- Info cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">المستأجر</p>
            <router-link :to="`/tenants/${due.tenant}`" class="font-bold text-navy-800 hover:text-gold-600">{{ due.tenant_name || due.tenant }}</router-link>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">المبلغ</p>
            <p class="text-2xl font-bold text-navy-800 tabular-nums">{{ formatMoney(due.amount, currency) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">تاريخ الاستحقاق</p>
            <p class="font-bold text-navy-800">{{ formatDate(due.due_date) }}</p>
          </Card>
          <Card padding="md">
            <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الحالة</p>
            <StatusBadge :status="due.status" />
          </Card>
        </div>

        <!-- Details (view mode) -->
        <div v-if="!editMode" class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card padding="md">
            <template #title>تفاصيل الالتزام</template>
            <dl class="space-y-3 text-sm">
              <div class="flex justify-between"><dt class="text-navy-400">العقد</dt><dd><router-link :to="`/contracts/${due.contract}`" class="text-gold-600 hover:underline font-medium">{{ due.contract_number || due.contract }}</router-link></dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">نوع الالتزام</dt><dd class="font-medium text-navy-800">{{ due.due_type_name || due.due_type }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">المصدر</dt><dd class="font-medium text-navy-800">{{ sourceLabel(due.source_type) }}</dd></div>
              <div class="flex justify-between"><dt class="text-navy-400">طريقة الحساب</dt><dd class="font-medium text-navy-800">{{ methodLabel(due.calculation_method) }}</dd></div>
              <div class="flex justify-between" v-if="due.description"><dt class="text-navy-400">الوصف</dt><dd class="font-medium text-navy-800">{{ due.description }}</dd></div>
              <div class="flex justify-between" v-if="due.previous_meter_reading !== null"><dt class="text-navy-400">قراءة سابقة</dt><dd class="font-medium text-navy-800">{{ due.previous_meter_reading }}</dd></div>
              <div class="flex justify-between" v-if="due.current_meter_reading !== null"><dt class="text-navy-400">قراءة حالية</dt><dd class="font-medium text-navy-800">{{ due.current_meter_reading }}</dd></div>
              <div class="flex justify-between" v-if="due.meter_consumption !== null"><dt class="text-navy-400">الاستهلاك</dt><dd class="font-medium text-navy-800">{{ due.meter_consumption }}</dd></div>
              <div class="flex justify-between" v-if="due.unit_price"><dt class="text-navy-400">سعر الوحدة</dt><dd class="font-medium text-navy-800 tabular-nums">{{ formatMoney(due.unit_price, currency) }}</dd></div>
            </dl>
          </Card>
        </div>

        <!-- Details (edit mode) -->
        <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card padding="md">
            <template #title>تعديل الالتزام</template>
            <form @submit.prevent="saveEdit" class="space-y-4">
              <FormField label="المبلغ" required>
                <input v-model.number="editForm.amount" type="number" step="0.01" required class="input-premium" />
              </FormField>
              <FormField label="تاريخ الاستحقاق" required>
                <input v-model="editForm.due_date" type="date" dir="ltr" required class="input-premium" />
              </FormField>
              <FormField label="الوصف">
                <input v-model="editForm.description" type="text" class="input-premium" />
              </FormField>
              <template v-if="due.calculation_method === 'metered'">
                <FormField label="القراءة الحالية">
                  <input v-model.number="editForm.current_meter_reading" type="number" step="0.01" class="input-premium" />
                </FormField>
                <FormField label="سعر الوحدة">
                  <input v-model.number="editForm.unit_price" type="number" step="0.01" class="input-premium" />
                </FormField>
              </template>
              <div class="flex gap-2 justify-end pt-4 border-t border-ivory-300/60">
                <button type="button" class="btn-premium btn-outline" @click="editMode = false">إلغاء</button>
                <button type="submit" class="btn-premium btn-gold" :disabled="savingEdit">
                  <span v-if="savingEdit" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
                  حفظ
                </button>
              </div>
            </form>
          </Card>
        </div>

        <!-- Waivers -->
        <Card padding="none" class="mb-6">
          <template #title>الإعفاءات</template>
          <div class="p-4 border-b border-ivory-300/60">
            <button class="btn-premium btn-outline" @click="showWaiverModal = true">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
              إضافة إعفاء
            </button>
          </div>
          <div v-if="!due.waivers?.length" class="text-center py-12 text-navy-400 text-sm">لا توجد إعفاءات</div>
          <DataTable v-else :columns="waiverColumns">
            <TableRow v-for="w in due.waivers" :key="w.name">
              <TableCell><span class="font-bold tabular-nums">{{ formatMoney(w.amount, currency) }}</span></TableCell>
              <TableCell>{{ w.reason || '—' }}</TableCell>
              <TableCell>{{ sourceLabel(w.source_type) }}</TableCell>
              <TableCell><StatusBadge :status="w.status === 'active' ? 'active' : 'cancelled'" /></TableCell>
              <TableCell>{{ formatDate(w.creation) }}</TableCell>
              <TableCell align="center">
                <button v-if="w.status === 'active' && w.source_type !== 'contract_cancellation'" class="text-red-600 hover:underline text-xs font-medium" @click="cancelWaiver(w)">إلغاء</button>
              </TableCell>
            </TableRow>
          </DataTable>
        </Card>

        <!-- Waiver modal -->
        <Modal v-if="showWaiverModal" title="إضافة إعفاء" size="sm" v-model="showWaiverModal">
          <div class="space-y-4">
            <FormField label="المبلغ" required>
              <input v-model.number="waiverForm.amount" type="number" step="0.01" required class="input-premium" />
            </FormField>
            <FormField label="السبب" required>
              <textarea v-model="waiverForm.reason" rows="3" required class="input-premium"></textarea>
            </FormField>
          </div>
          <template #footer>
            <button class="btn-premium btn-outline" @click="showWaiverModal = false">إلغاء</button>
            <button class="btn-premium btn-gold" :disabled="savingWaiver" @click="createWaiver">
              <span v-if="savingWaiver" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
          </template>
        </Modal>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const due = ref(null)
const loading = ref(true)
const showWaiverModal = ref(false)
const savingWaiver = ref(false)
const editMode = ref(false)
const savingEdit = ref(false)

const editForm = ref({ amount: null, due_date: '', description: '', current_meter_reading: null, unit_price: null })

const waiverForm = ref({ amount: null, reason: '' })

const waiverColumns = [
  { key: 'amount', label: 'المبلغ' },
  { key: 'reason', label: 'السبب' },
  { key: 'source', label: 'المصدر' },
  { key: 'status', label: 'الحالة' },
  { key: 'date', label: 'التاريخ' },
  { key: 'actions', label: '', align: 'center' },
]

function sourceLabel(s) {
  return { auto_contract: 'تلقائي', manual_contract: 'يدوي عقدي', additional: 'إضافي', manual: 'يدوي', contract_cancellation: 'إلغاء عقد' }[s] || s
}
function methodLabel(m) {
  return { fixed_periodic: 'دوري ثابت', metered: 'عداد', actual_bill: 'فاتورة فعلية', on_demand: 'عند الطلب' }[m] || m
}

async function fetchDue() {
  loading.value = true
  try {
    due.value = await callApi('rental.rental.api.due.get_due', { name: route.params.id })
  } catch (e) { toast.error(extractError(e)) } finally { loading.value = false }
}

function toggleEdit() {
  if (editMode.value) {
    editMode.value = false
    return
  }
  editForm.value = {
    amount: due.value.amount,
    due_date: due.value.due_date || '',
    description: due.value.description || '',
    current_meter_reading: due.value.current_meter_reading ?? null,
    unit_price: due.value.unit_price ?? null,
  }
  editMode.value = true
}

async function saveEdit() {
  savingEdit.value = true
  try {
    const payload = {}
    if (editForm.value.amount !== null) payload.amount = editForm.value.amount
    if (editForm.value.due_date) payload.due_date = editForm.value.due_date
    if (editForm.value.description !== undefined) payload.description = editForm.value.description
    if (due.value.calculation_method === 'metered') {
      if (editForm.value.current_meter_reading !== null) payload.current_meter_reading = editForm.value.current_meter_reading
      if (editForm.value.unit_price !== null) payload.unit_price = editForm.value.unit_price
    }
    await callApi('rental.rental.api.due.update_due', { name: due.value.name, ...payload })
    toast.success('تم تحديث الالتزام')
    editMode.value = false
    fetchDue()
  } catch (e) { toast.error(extractError(e)) } finally { savingEdit.value = false }
}

async function approveDue() {
  const ok = await confirm({ title: 'اعتماد التزام', message: 'هل أنت متأكد؟', variant: 'warning', confirmLabel: 'اعتماد' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.approve_due', { name: due.value.name })
    toast.success('تم الاعتماد')
    fetchDue()
  } catch (e) { toast.error(extractError(e)) }
}

async function cancelDue() {
  const reason = prompt('سبب الإلغاء:')
  if (!reason) return
  try {
    await callApi('rental.rental.api.due.cancel_due_api', { name: due.value.name, reason })
    toast.success('تم الإلغاء')
    fetchDue()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteDue() {
  const ok = await confirm({ title: 'حذف التزام', message: 'هل أنت متأكد؟', variant: 'danger', confirmLabel: 'حذف' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.delete_due', { name: due.value.name })
    toast.success('تم الحذف')
    router.push({ name: 'Dues' })
  } catch (e) { toast.error(extractError(e)) }
}

async function createWaiver() {
  if (!waiverForm.value.amount || !waiverForm.value.reason) { toast.error('يرجى تعبئة المبلغ والسبب'); return }
  savingWaiver.value = true
  try {
    await callApi('rental.rental.api.due.create_waiver', {
      name: due.value.name, amount: waiverForm.value.amount, reason: waiverForm.value.reason,
    })
    toast.success('تم إنشاء الإعفاء')
    showWaiverModal.value = false
    waiverForm.value = { amount: null, reason: '' }
    fetchDue()
  } catch (e) { toast.error(extractError(e)) } finally { savingWaiver.value = false }
}

async function cancelWaiver(w) {
  const reason = prompt('سبب إلغاء الإعفاء:')
  if (!reason) return
  try {
    await callApi('rental.rental.api.due.cancel_waiver', { due_name: due.value.name, waiver_name: w.name, reason })
    toast.success('تم إلغاء الإعفاء')
    fetchDue()
  } catch (e) { toast.error(extractError(e)) }
}

function handlePrint() {
  const d = due.value
  const printWin = window.open('', '_blank')
  printWin.document.write(`<html dir="rtl"><head><title>التزام ${d.due_number}</title></head><body>`)
  printWin.document.write(`<h1>تفاصيل التزام</h1>`)
  printWin.document.write(`<p><strong>رقم:</strong> ${d.due_number}</p>`)
  printWin.document.write(`<p><strong>المستأجر:</strong> ${d.tenant_name || d.tenant}</p>`)
  printWin.document.write(`<p><strong>النوع:</strong> ${d.due_type_name || d.due_type}</p>`)
  printWin.document.write(`<p><strong>التاريخ:</strong> ${d.transaction_date || '—'}</p>`)
  printWin.document.write(`<p><strong>تاريخ الاستحقاق:</strong> ${d.due_date || '—'}</p>`)
  printWin.document.write(`<p><strong>المبلغ:</strong> ${d.amount || 0}</p>`)
  if (d.description) printWin.document.write(`<p><strong>الوصف:</strong> ${d.description}</p>`)
  if (d.calculation_method === 'metered') {
    printWin.document.write(`<p><strong>قراءة سابقة:</strong> ${d.previous_meter_reading || 0}</p>`)
    printWin.document.write(`<p><strong>قراءة حالية:</strong> ${d.current_meter_reading || 0}</p>`)
    printWin.document.write(`<p><strong>الاستهلاك:</strong> ${d.meter_consumption || 0}</p>`)
    printWin.document.write(`<p><strong>سعر الوحدة:</strong> ${d.unit_price || 0}</p>`)
  }
  printWin.document.write(`<p><strong>الحالة:</strong> ${d.status}</p>`)
  printWin.document.write(`</body></html>`)
  printWin.document.close()
  printWin.print()
}

onMounted(fetchDue)
</script>
