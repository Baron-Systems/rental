<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <PageHeader title="الالتزامات" description="إدارة الالتزامات المالية للمستأجرين" action-label="إضافة التزام" @action="showCreateForm = !showCreateForm" />

      <!-- Stats -->
      <div v-if="stats" class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <StatCard label="إجمالي الالتزامات" :value="stats.total || 0" icon="receipt" color="navy" />
        <StatCard label="مسودات" :value="stats.draft || 0" icon="receipt" color="amber" />
        <StatCard label="مستحق حتى اليوم" :value="stats.due || 0" icon="receipt" color="green" />
        <StatCard label="مستقبلي" :value="stats.future || 0" icon="receipt" color="blue" />
        <StatCard label="ملغي" :value="stats.cancelled || 0" icon="receipt" color="red" />
      </div>

      <!-- Inline create form -->
      <Card v-if="showCreateForm" padding="lg" class="mb-4 animate-slide-up">
        <template #title>إضافة التزام جديد</template>
        <form @submit.prevent="createDue" class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="العقد" required>
              <select v-model="newDue.contract" required class="input-premium" @change="onContractChange">
                <option value="">اختر العقد...</option>
                <option v-for="c in activeContracts" :key="c.name" :value="c.name">{{ c.contract_number }} - {{ c.tenant_name || c.tenant }}</option>
              </select>
            </FormField>
            <FormField label="نوع الالتزام" required>
              <select v-model="newDue.due_type" required class="input-premium">
                <option value="">اختر النوع...</option>
                <option v-for="dt in dueTypes" :key="dt.name" :value="dt.name">{{ dt.due_type_name }}</option>
              </select>
            </FormField>
            <FormField label="المبلغ" required>
              <input v-model.number="newDue.amount" type="number" step="0.01" required class="input-premium" />
            </FormField>
            <FormField label="تاريخ الاستحقاق" required>
              <input v-model="newDue.due_date" type="date" dir="ltr" required class="input-premium" />
            </FormField>
            <FormField label="الوصف">
              <input v-model="newDue.description" type="text" class="input-premium" />
            </FormField>
            <FormField label="نوع الالتزام">
              <select v-model="newDue.due_kind" class="input-premium">
                <option value="contractual">عقدي</option>
                <option value="additional">إضافي</option>
              </select>
            </FormField>
          </div>
          <div class="flex gap-2 justify-end">
            <button type="button" class="btn-premium btn-outline" @click="showCreateForm = false">إلغاء</button>
            <button type="submit" class="btn-premium btn-gold" :disabled="creating">
              <span v-if="creating" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
          </div>
        </form>
      </Card>

      <!-- Inline edit modal -->
      <Card v-if="editingDue" padding="lg" class="mb-4 animate-slide-up">
        <template #title>تعديل التزام</template>
        <form @submit.prevent="saveEdit" class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="المبلغ" required>
              <input v-model.number="editForm.amount" type="number" step="0.01" required class="input-premium" />
            </FormField>
            <FormField label="تاريخ الاستحقاق" required>
              <input v-model="editForm.due_date" type="date" dir="ltr" required class="input-premium" />
            </FormField>
            <FormField label="الوصف">
              <input v-model="editForm.description" type="text" class="input-premium" />
            </FormField>
            <template v-if="editingDue.calculation_method === 'metered'">
              <FormField label="القراءة الحالية">
                <input v-model.number="editForm.current_meter_reading" type="number" step="0.01" class="input-premium" />
              </FormField>
              <FormField label="سعر الوحدة">
                <input v-model.number="editForm.unit_price" type="number" step="0.01" class="input-premium" />
              </FormField>
            </template>
          </div>
          <div class="flex gap-2 justify-end">
            <button type="button" class="btn-premium btn-outline" @click="editingDue = null">إلغاء</button>
            <button type="submit" class="btn-premium btn-gold" :disabled="savingEdit">
              <span v-if="savingEdit" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
          </div>
        </form>
      </Card>

      <!-- Filters -->
      <Card padding="md" class="mb-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="filters.search" type="text" placeholder="بحث برقم الالتزام..." class="input-premium pr-10" @input="debouncedFetch" />
          </div>
          <select v-model="filters.status" class="input-premium" @change="fetchDues">
            <option value="">كل الحالات</option>
            <option value="draft">مسودة</option>
            <option value="due">مستحق</option>
            <option value="future">مستقبلي</option>
            <option value="cancelled">ملغي</option>
          </select>
          <select v-model="filters.sourceType" class="input-premium" @change="fetchDues">
            <option value="">كل المصادر</option>
            <option value="auto_contract">تلقائي</option>
            <option value="manual_contract">يدوي عقدي</option>
            <option value="additional">إضافي</option>
          </select>
          <input v-model="filters.fromDate" type="date" dir="ltr" class="input-premium" @change="fetchDues" />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-3 pt-3 border-t border-ivory-300/60">
          <input v-model="filters.toDate" type="date" dir="ltr" class="input-premium" @change="fetchDues" />
          <input v-model="filters.tenant" type="text" placeholder="فلترة بمستأجر..." class="input-premium" @input="debouncedFetch" />
          <input v-model="filters.contract" type="text" placeholder="فلترة بعقد..." class="input-premium" @input="debouncedFetch" />
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="loading || printing" @click="handlePrint">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
            <span>{{ printing ? 'جاري...' : 'طباعة' }}</span>
          </button>
        </div>
      </Card>

      <!-- Table -->
      <Card padding="none">
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <EmptyState v-else-if="dues.length === 0" title="لا توجد التزامات" />
        <DataTable v-else :columns="columns">
          <TableRow v-for="d in dues" :key="d.name">
            <TableCell>
              <router-link :to="`/dues/${d.name}`" class="font-semibold text-navy-800 hover:text-gold-600">{{ d.due_number }}</router-link>
            </TableCell>
            <TableCell>{{ d.tenant_name || d.tenant }}</TableCell>
            <TableCell>{{ d.due_type_name || d.due_type }}</TableCell>
            <TableCell><span class="font-bold tabular-nums">{{ formatMoney(d.amount, currency) }}</span></TableCell>
            <TableCell>{{ formatDate(d.due_date) }}</TableCell>
            <TableCell><StatusBadge :status="d.status" /></TableCell>
            <TableCell align="center">
              <div class="flex items-center justify-center gap-1">
                <router-link :to="`/dues/${d.name}`" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="عرض">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
                <button v-if="d.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-600 hover:bg-emerald-50 transition-colors" title="اعتماد" @click="approveDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                </button>
                <button v-if="d.status === 'approved'" class="w-8 h-8 rounded-lg flex items-center justify-center text-amber-600 hover:bg-amber-50 transition-colors" title="إلغاء" @click="cancelDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
                <button v-if="d.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(d.source_type)" class="w-8 h-8 rounded-lg flex items-center justify-center text-gold-600 hover:bg-gold-50 transition-colors" title="تعديل" @click="startEdit(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <button v-if="d.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors" title="حذف" @click="deleteDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            </TableCell>
          </TableRow>
        </DataTable>
        <Pagination v-if="pagination" :page="pagination.page" :page-size="pagination.pageSize" :total="pagination.total" @change="onPageChange" />
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Pagination from '@/components/ui/Pagination.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import FormField from '@/components/ui/FormField.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const session = useSession()
const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const columns = [
  { key: 'number', label: 'الرقم' },
  { key: 'tenant', label: 'المستأجر' },
  { key: 'type', label: 'النوع' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'date', label: 'تاريخ الاستحقاق' },
  { key: 'status', label: 'الحالة' },
  { key: 'actions', label: '', align: 'center' },
]

const dues = ref([])
const loading = ref(true)
const pagination = ref(null)
const stats = ref(null)
const showCreateForm = ref(false)
const creating = ref(false)
const activeContracts = ref([])
const dueTypes = ref([])

const filters = ref({ search: '', status: '', sourceType: '', fromDate: '', toDate: '', tenant: '', contract: '' })
const printing = ref(false)

const newDue = ref({ contract: '', due_type: '', amount: null, due_date: '', description: '', due_kind: 'contractual' })

const editingDue = ref(null)
const editForm = ref({ amount: null, due_date: '', description: '', current_meter_reading: null, unit_price: null })
const savingEdit = ref(false)

function startEdit(d) {
  editingDue.value = d
  editForm.value = {
    amount: d.amount,
    due_date: d.due_date || '',
    description: d.description || '',
    current_meter_reading: d.current_meter_reading ?? null,
    unit_price: d.unit_price ?? null,
  }
}

async function saveEdit() {
  savingEdit.value = true
  try {
    const payload = {}
    if (editForm.value.amount !== null) payload.amount = editForm.value.amount
    if (editForm.value.due_date) payload.due_date = editForm.value.due_date
    if (editForm.value.description !== undefined) payload.description = editForm.value.description
    if (editingDue.value.calculation_method === 'metered') {
      if (editForm.value.current_meter_reading !== null) payload.current_meter_reading = editForm.value.current_meter_reading
      if (editForm.value.unit_price !== null) payload.unit_price = editForm.value.unit_price
    }
    await callApi('rental.rental.api.due.update_due', { name: editingDue.value.name, ...payload })
    toast.success('تم تحديث الالتزام')
    editingDue.value = null
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) } finally { savingEdit.value = false }
}

let debounceTimer = null
function debouncedFetch() { clearTimeout(debounceTimer); debounceTimer = setTimeout(fetchDues, 400) }

async function fetchDues(page = 1) {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.due.get_dues', {
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      source_type: filters.value.sourceType || undefined,
      from_date: filters.value.fromDate || undefined,
      to_date: filters.value.toDate || undefined,
      tenant: filters.value.tenant || undefined,
      contract: filters.value.contract || undefined,
      page, limit: 15,
    })
    dues.value = res.dues || []
    pagination.value = res.pagination
    stats.value = res.stats
  } catch (e) { toast.error(extractError(e)) } finally { loading.value = false }
}

async function loadFormData() {
  try {
    const contractsRes = await callApi('rental.rental.api.contract.get_contracts', { status: 'active', limit: 100 })
    activeContracts.value = contractsRes.contracts || []
    const dtRes = await callApi('rental.rental.api.settings.get_due_types')
    dueTypes.value = (dtRes.dueTypes || []).filter(dt => !dt.is_system || dt.due_type_code !== 'rent')
  } catch { /* ignore */ }
}

function onContractChange() { newDue.value.due_type = '' }

async function createDue() {
  creating.value = true
  try {
    await callApi('rental.rental.api.due.create_due', newDue.value)
    toast.success('تم إنشاء الالتزام')
    showCreateForm.value = false
    newDue.value = { contract: '', due_type: '', amount: null, due_date: '', description: '', due_kind: 'contractual' }
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) } finally { creating.value = false }
}

async function approveDue(d) {
  const ok = await confirm({ title: 'اعتماد التزام', message: `اعتماد الالتزام "${d.due_number}"؟`, variant: 'warning', confirmLabel: 'اعتماد' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.approve_due', { name: d.name })
    toast.success('تم الاعتماد')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

async function cancelDue(d) {
  const reason = prompt('سبب الإلغاء:')
  if (!reason) return
  try {
    await callApi('rental.rental.api.due.cancel_due_api', { name: d.name, reason })
    toast.success('تم الإلغاء')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteDue(d) {
  const ok = await confirm({ title: 'حذف التزام', message: `حذف الالتزام "${d.due_number}"؟`, variant: 'danger', confirmLabel: 'حذف' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.delete_due', { name: d.name })
    toast.success('تم الحذف')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

function onPageChange(page) { fetchDues(page) }

async function handlePrint() {
  printing.value = true
  try {
    const res = await callApi('rental.rental.api.due.get_dues', {
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      source_type: filters.value.sourceType || undefined,
      from_date: filters.value.fromDate || undefined,
      to_date: filters.value.toDate || undefined,
      tenant: filters.value.tenant || undefined,
      contract: filters.value.contract || undefined,
      print: 1, limit: 1000,
    })
    const dues = res.dues || []
    const printTotal = res.print?.totalAmount || null
    const printWin = window.open('', '_blank')
    printWin.document.write(`<html dir="rtl"><head><title>قائمة الالتزامات</title></head><body>`)
    printWin.document.write(`<h1>قائمة الالتزامات</h1>`)
    printWin.document.write(`<table border="1" style="width:100%;border-collapse:collapse;font-size:12px">`)
    printWin.document.write(`<tr><th>رقم</th><th>المستأجر</th><th>النوع</th><th>التاريخ</th><th>المبلغ</th><th>الحالة</th></tr>`)
    for (const d of dues) {
      printWin.document.write(`<tr><td>${d.due_number}</td><td>${d.tenant_name||'—'}</td><td>${d.due_type_name||'—'}</td><td>${d.transaction_date||'—'}</td><td>${d.amount||0}</td><td>${d.status}</td></tr>`)
    }
    printWin.document.write(`</table>`)
    if (printTotal) printWin.document.write(`<p style="text-align:right;font-weight:bold;margin-top:12px">الإجمالي: ${printTotal}</p>`)
    printWin.document.write(`</body></html>`)
    printWin.document.close()
    printWin.print()
  } catch (e) { toast.error(extractError(e)) } finally { printing.value = false }
}

onMounted(() => { fetchDues(); loadFormData() })
</script>
