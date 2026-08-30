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

      <div v-else class="animate-fade-in space-y-6" :class="{ 'print:hidden': printing }">
        <!-- Header card (source: dues/[id]/page.tsx:312-346) -->
        <div class="rounded-xl border border-ivory-300 bg-white p-6 shadow-soft">
          <div class="flex items-center gap-2 mb-4">
            <router-link to="/dues" class="btn-premium btn-ghost text-navy-400">
              <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
              الالتزامات
            </router-link>
          </div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 class="text-2xl font-bold tracking-tight text-navy-900">التزام {{ due.due_number || 'مسودة' }}</h1>
              <div class="mt-2 flex items-center gap-3">
                <DueDetailStatus :due="due" />
                <span class="text-sm text-navy-400">{{ due.due_type_name || '—' }}</span>
                <span v-if="due.source_type === 'auto_contract'" class="text-xs text-navy-400">(ناتج من عقد)</span>
                <span v-if="due.source_type === 'manual' || due.source_type === 'manual_contract'" class="text-xs text-navy-400">(يدوي تعاقدي)</span>
                <span v-if="due.source_type === 'additional'" class="inline-flex items-center rounded-full bg-gold-50 px-2 py-0.5 text-[11px] font-medium text-gold-600">(إضافي)</span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="btn-premium btn-outline" @click="handlePrint">
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                طباعة
              </button>
              <button v-if="due.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(due.source_type)" class="btn-premium btn-gold" @click="approveDue">
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                اعتماد
              </button>
              <button v-if="due.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(due.source_type) && !editMode" class="btn-premium btn-outline" @click="toggleEdit">
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                تعديل
              </button>
              <button v-if="due.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(due.source_type)" class="btn-premium btn-ghost text-red-600" @click="deleteDue">
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                حذف
              </button>
              <button v-if="due.status === 'approved' && ['manual', 'manual_contract', 'additional'].includes(due.source_type)" class="btn-premium btn-ghost text-red-600" @click="cancelDue">
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                إلغاء
              </button>
              <button
                v-if="due.status === 'approved' && due.source_type === 'auto_contract'
                  && (!due.settlement_item || due.settlement_item?.settlement?.status !== 'completed')
                  && activeWaiversTotal(due) < Number(due.amount)"
                class="btn-premium btn-outline" @click="showWaiverModal = true"
              >
                <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                إعفاء
              </button>
            </div>
          </div>
        </div>

        <!-- Edit form (source: dues/[id]/page.tsx:348-383) -->
        <div v-if="editMode" class="rounded-xl border border-ivory-300 bg-white p-5 shadow-soft animate-scale-in">
          <div v-if="editError" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ editError }}</div>
          <form @submit.prevent="saveEdit" class="space-y-3">
            <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
              <FormField label="تاريخ الاستحقاق" required>
                <input v-model="editForm.due_date" type="date" dir="ltr" required class="input-premium" />
              </FormField>
              <template v-if="isMeterDue(due)">
                <FormField label="القراءة السابقة">
                  <input :value="editForm.previous_meter_reading" type="text" readonly class="input-premium bg-ivory-100" />
                </FormField>
                <FormField label="القراءة الحالية" required>
                  <input :value="editForm.current_meter_reading" @input="handleEditMeterInput($event.target.value, editForm.unit_price)" type="number" step="0.01" required class="input-premium" />
                </FormField>
                <FormField label="الاستهلاك">
                  <input :value="editForm.meter_consumption" type="text" readonly class="input-premium bg-ivory-100" />
                </FormField>
                <FormField label="سعر الوحدة" required>
                  <input :value="editForm.unit_price" @input="handleEditMeterInput(editForm.current_meter_reading, $event.target.value)" type="number" step="0.01" required class="input-premium" />
                </FormField>
                <FormField label="المبلغ (تلقائي)">
                  <input :value="editForm.amount" type="text" readonly class="input-premium bg-ivory-100" />
                </FormField>
              </template>
              <FormField v-else label="المبلغ" required>
                <input v-model="editForm.amount" type="number" step="0.01" required class="input-premium" />
              </FormField>
              <FormField label="الوصف (اختياري)">
                <input v-model="editForm.description" type="text" class="input-premium" />
              </FormField>
            </div>
            <div class="mt-4 flex gap-2">
              <button type="submit" class="btn-premium btn-gold">حفظ التعديل</button>
              <button type="button" class="btn-premium btn-outline" @click="editMode = false">إلغاء</button>
            </div>
          </form>
        </div>

        <!-- Info cards grid (source: dues/[id]/page.tsx:385-413) -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="item in infoCards" :key="item.label" class="rounded-xl border border-ivory-300 bg-white p-4 shadow-soft">
            <div class="flex items-center gap-2 text-xs text-navy-400 mb-1">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="item.icon"/></svg>
              {{ item.label }}
            </div>
            <div class="text-sm font-bold text-navy-900">
              <router-link v-if="item.link" :to="item.link" class="text-navy-900 hover:opacity-80 transition-opacity">{{ item.value }}</router-link>
              <span v-else>{{ item.value }}</span>
            </div>
          </div>
        </div>

        <!-- Waiver form (source: dues/[id]/page.tsx:415-430) -->
        <div v-if="due.source_type === 'auto_contract' && due.status === 'approved' && showWaiverModal" class="rounded-xl border border-ivory-300 bg-white p-5 shadow-soft animate-scale-in">
          <div v-if="waiverError" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ waiverError }}</div>
          <h3 class="text-base font-semibold text-navy-900 mb-3">إضافة إعفاء</h3>
          <form @submit.prevent="createWaiver">
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <FormField label="مبلغ الإعفاء" required>
                <input v-model="waiverForm.amount" type="number" step="0.01" required class="input-premium" />
              </FormField>
              <FormField label="سبب الإعفاء" required>
                <input v-model="waiverForm.reason" type="text" required class="input-premium" />
              </FormField>
            </div>
            <div class="mt-4 flex gap-2">
              <button type="submit" class="btn-premium btn-gold">حفظ الإعفاء</button>
              <button type="button" class="btn-premium btn-outline" @click="showWaiverModal = false">إلغاء</button>
            </div>
          </form>
        </div>

        <!-- Waivers list (source: dues/[id]/page.tsx:432-449) -->
        <div v-if="due.source_type === 'auto_contract' && due.waivers && due.waivers.length > 0" class="rounded-xl border border-ivory-300 bg-white p-5 shadow-soft">
          <div class="flex items-center gap-2 text-xs text-navy-400 mb-4">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            سجل الإعفاءات
          </div>
          <div class="space-y-3">
            <div v-for="w in due.waivers" :key="w.name" class="flex items-center justify-between rounded-lg bg-ivory-100/50 p-3">
              <div class="space-y-1">
                <div class="text-sm font-medium text-navy-900">{{ formatMoney(w.amount, currency) }} — {{ w.reason }}</div>
                <div class="text-xs text-navy-400">{{ formatDate(w.creation) }} · <StatusBadge :status="w.status === 'active' ? 'active' : 'cancelled'" :label="w.status === 'active' ? 'فعال' : 'ملغي'" /></div>
              </div>
              <button
                v-if="w.status === 'active' && w.source_type !== 'contract_cancellation'
                  && (!due.settlement_item || due.settlement_item?.settlement?.status !== 'completed')"
                class="btn-premium btn-ghost text-red-600 text-xs px-3 py-1.5" @click="cancelWaiver(w)"
              >
                <svg class="h-3 w-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                إلغاء
              </button>
            </div>
          </div>
        </div>

        <!-- Description (source: dues/[id]/page.tsx:451-456) -->
        <div v-if="due.description" class="rounded-xl border border-ivory-300 bg-white p-5 shadow-soft">
          <div class="flex items-center gap-2 text-xs text-navy-400 mb-2">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            البيان
          </div>
          <p class="text-sm text-navy-900">{{ due.description }}</p>
        </div>
      </div>
    </div>

    <!-- Print Document (source: dues/[id]/page.tsx:460-468) -->
    <div v-if="printing && due" class="due-print-document">
      <DuePrintDocument :due="due" :lessor-data="lessorData" />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import FormField from '@/components/ui/FormField.vue'
import DuePrintDocument from '@/components/due/DuePrintDocument.vue'
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
const printing = ref(false)
const lessorData = computed(() => session.state.account?.settings || null)
const showWaiverModal = ref(false)
const savingWaiver = ref(false)
const editMode = ref(false)
const savingEdit = ref(false)
const editError = ref('')
const waiverError = ref('')

const editForm = ref({ amount: '', due_date: '', description: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '' })

const waiverForm = ref({ amount: '', reason: '' })

// ---- Helpers (source: dues/[id]/page.tsx:62-69, 150-161, 262-273) ----

// Temporal status (source: page.tsx:62-69)
function getTemporalStatus(d) {
  if (d.status === 'draft') return { label: 'مسودة', status: 'draft' }
  if (d.status === 'cancelled') return { label: 'ملغي', status: 'cancelled' }
  const dueDate = new Date(d.due_date); dueDate.setHours(0, 0, 0, 0)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  if (dueDate > today) return { label: 'مستقبلي', status: 'upcoming' }
  return { label: 'مستحق', status: 'pending' }
}

// Active waivers total (source: page.tsx:150-154)
function activeWaiversTotal(d) {
  return (d.waivers || [])
    .filter((w) => w.status === 'active')
    .reduce((sum, w) => sum + Number(w.amount), 0)
}

// Waiver status label (source: page.tsx:156-161)
function waiverStatusLabel(d) {
  const total = activeWaiversTotal(d)
  if (total === 0) return null
  if (total >= Number(d.amount)) return 'معفى بالكامل'
  return 'معفى جزئياً'
}

// Is meter due (source: page.tsx:262-264)
function isMeterDue(d) {
  return d && d.calculation_method === 'metered'
}

// Calculate meter fields (source: page.tsx:266-273)
function calculateMeterFields(prev, curr, price) {
  const p = parseFloat(prev || '0')
  const c = parseFloat(curr || '0')
  const pr = parseFloat(price || '0')
  const consumption = (!isNaN(c) && !isNaN(p)) ? String(c - p) : ''
  const amount = (consumption && !isNaN(pr)) ? String(parseFloat(consumption) * pr) : ''
  return { consumption, amount }
}

// ---- DueDetailStatus component (source: page.tsx:163-192) ----
import { h } from 'vue'
const DueDetailStatus = {
  props: ['due'],
  setup(props) {
    return () => {
      const temporal = getTemporalStatus(props.due)
      const total = activeWaiversTotal(props.due)
      if (total === 0) {
        return h(StatusBadge, { status: temporal.status, label: temporal.label })
      }
      const isFullyWaived = total >= Number(props.due.amount)
      if (isFullyWaived) {
        return h('div', { class: 'flex items-center gap-2' }, [
          h(StatusBadge, { status: 'active', label: 'معفى بالكامل' }),
          ...(temporal.status === 'upcoming' ? [h('span', { class: 'text-xs text-navy-400' }, temporal.label)] : []),
        ])
      }
      return h('div', { class: 'flex items-center gap-2' }, [
        h(StatusBadge, { status: temporal.status, label: temporal.label }),
        h('span', { class: 'inline-flex items-center rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-600' }, 'معفى جزئياً'),
      ])
    }
  },
}

// ---- Info cards (source: page.tsx:385-413) ----
const infoCards = computed(() => {
  if (!due.value) return []
  const d = due.value
  const temporal = getTemporalStatus(d)
  const waived = activeWaiversTotal(d)
  const iconTag = 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z'
  const iconUser = 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z'
  const iconBuilding = 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4'
  const iconHome = 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
  const iconFile = 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z'
  const iconCalendar = 'M8 7V3m8 4V3m3 18H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v12a2 2 0 01-2 2z'
  const iconBanknote = 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  const iconAlert = 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'

  const cards = [
    { label: 'النوع', value: d.due_type_name || '—', icon: iconTag },
    { label: 'المستأجر', value: d.tenant_name || '—', icon: iconUser },
    { label: 'العقار', value: d.building_name || '—', icon: iconBuilding },
    { label: 'الوحدة', value: d.unit_number || '—', icon: iconHome },
  ]
  if (d.contract) {
    cards.push({ label: 'العقد', value: d.contract_number || d.contract, icon: iconFile, link: `/contracts/${d.contract}` })
  }
  cards.push({ label: 'تاريخ الالتزام', value: d.due_date ? new Date(d.due_date).toLocaleDateString('en-GB') : '—', icon: iconCalendar })
  cards.push({ label: 'المبلغ الأصلي', value: formatMoney(d.amount, currency.value), icon: iconBanknote })
  if (d.source_type === 'auto_contract' && waived > 0) {
    cards.push({ label: 'المعفى', value: formatMoney(waived, currency.value), icon: iconBanknote })
    cards.push({ label: 'المبلغ الفعلي', value: formatMoney(Math.max(Number(d.amount) - waived, 0), currency.value), icon: iconBanknote })
    cards.push({ label: 'حالة الإعفاء', value: waiverStatusLabel(d) || '—', icon: iconAlert })
  }
  cards.push({ label: 'الحالة الزمنية', value: temporal.label, icon: iconAlert })
  if (d.previous_meter_reading) cards.push({ label: 'القراءة السابقة', value: d.previous_meter_reading, icon: iconTag })
  if (d.current_meter_reading) cards.push({ label: 'القراءة الحالية', value: d.current_meter_reading, icon: iconTag })
  if (d.meter_consumption) cards.push({ label: 'الاستهلاك', value: d.meter_consumption, icon: iconTag })
  if (d.unit_price) cards.push({ label: 'سعر الوحدة', value: formatMoney(d.unit_price, currency.value), icon: iconTag })
  if (d.cancellation_reason) cards.push({ label: 'سبب الإلغاء', value: d.cancellation_reason, icon: iconAlert })
  return cards
})

// ---- API calls ----
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
  const d = due.value
  editForm.value = {
    amount: String(d.amount),
    due_date: d.due_date || '',
    description: d.description || '',
    previous_meter_reading: d.previous_meter_reading || '',
    current_meter_reading: d.current_meter_reading || '',
    meter_consumption: d.meter_consumption || '',
    unit_price: d.unit_price ? String(d.unit_price) : '',
  }
  editMode.value = true
}

function handleEditMeterInput(curr, price) {
  const { consumption, amount } = calculateMeterFields(editForm.value.previous_meter_reading, curr, price)
  editForm.value = {
    ...editForm.value,
    current_meter_reading: curr,
    unit_price: price,
    meter_consumption: consumption,
    amount,
  }
}

async function saveEdit() {
  savingEdit.value = true
  editError.value = ''
  try {
    const payload = {}
    if (editForm.value.due_date) payload.due_date = editForm.value.due_date
    if (editForm.value.description !== undefined) payload.description = editForm.value.description
    if (isMeterDue(due.value)) {
      if (editForm.value.current_meter_reading) payload.current_meter_reading = editForm.value.current_meter_reading
      if (editForm.value.unit_price) payload.unit_price = editForm.value.unit_price
      if (editForm.value.current_meter_reading && editForm.value.previous_meter_reading) {
        const prev = parseFloat(editForm.value.previous_meter_reading || '0')
        const curr = parseFloat(editForm.value.current_meter_reading)
        if (isNaN(curr) || curr < prev) {
          editError.value = 'القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة'
          savingEdit.value = false
          return
        }
      }
    } else {
      if (editForm.value.amount) payload.amount = editForm.value.amount
    }
    await callApi('rental.rental.api.due.update_due', { name: due.value.name, ...payload })
    toast.success('تم تحديث الالتزام')
    editMode.value = false
    fetchDue()
  } catch (e) { editError.value = extractError(e) } finally { savingEdit.value = false }
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
  const ok = await confirm({ title: 'حذف التزام', message: 'سيتم حذف مسودة الالتزام نهائيًا. لا يمكن التراجع عن هذا الإجراء.', variant: 'danger', confirmLabel: 'حذف' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.delete_due', { name: due.value.name })
    toast.success('تم الحذف')
    router.push({ name: 'Dues' })
  } catch (e) { toast.error(extractError(e)) }
}

async function createWaiver() {
  waiverError.value = ''
  savingWaiver.value = true
  try {
    await callApi('rental.rental.api.due.create_waiver', {
      name: due.value.name, amount: waiverForm.value.amount, reason: waiverForm.value.reason,
    })
    toast.success('تم إنشاء الإعفاء')
    showWaiverModal.value = false
    waiverForm.value = { amount: '', reason: '' }
    fetchDue()
  } catch (e) { waiverError.value = extractError(e) } finally { savingWaiver.value = false }
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

// Print behavior (source: dues/[id]/page.tsx:86, 460-468 + usePrint.ts)
// Same pattern as ReceiptDetailPage: set printing=true, wait for images, window.print()
async function handlePrint() {
  printing.value = true
  await nextTick()
  await waitForImages()
  window.print()
  printing.value = false
}

function waitForImages() {
  return new Promise((resolve) => {
    const images = Array.from(document.images).filter((img) => !img.complete)
    if (images.length === 0) return resolve()
    let finished = 0
    const onFinish = () => { finished++; if (finished >= images.length) resolve() }
    images.forEach((img) => {
      img.addEventListener('load', onFinish)
      img.addEventListener('error', onFinish)
    })
  })
}

onMounted(fetchDue)
</script>

<style scoped>
/* Source: old dues/[id]/page.tsx — when printing, only the due document is visible.
   The sidebar (print:hidden in AppLayout), header (print:hidden), and page content
   (print:hidden when `printing` is true) are all hidden via Tailwind print variants.
   Global print CSS in index.css handles layout unblocking and .print-document sizing. */
@media print {
  .due-print-document {
    width: 100% !important;
    max-width: none !important;
  }
}
</style>
