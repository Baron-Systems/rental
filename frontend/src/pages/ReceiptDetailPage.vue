<template>
  <AppLayout>
    <div v-if="loading" class="flex items-center justify-center py-20" dir="rtl">
      <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-sm text-navy-400 mr-3">جاري تحميل بيانات السند...</p>
    </div>

    <div v-else-if="!receipt" class="text-center py-20" dir="rtl">
      <p class="text-navy-400 text-lg">السند غير موجود</p>
      <p class="text-navy-300 text-sm mt-1">تعذر العثور على بيانات سند القبض المطلوب.</p>
      <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Receipts' })">العودة للقائمة</button>
    </div>

    <template v-else>
      <div class="space-y-6 animate-fade-in p-6 lg:p-8" :class="{ 'print:hidden': printing }" dir="rtl">
        <!-- Hero -->
        <div class="card-premium p-6 shadow-soft">
          <div class="flex items-center gap-2 mb-4">
            <router-link to="/receipts" class="btn-ghost text-navy-400 inline-flex items-center gap-1">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
              الدفعات
            </router-link>
          </div>
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 class="text-2xl font-bold tracking-tight text-navy-900">سند قبض {{ receipt.receipt_number || 'مسودة' }}</h1>
              <div class="mt-2 flex flex-wrap items-center gap-3">
                <StatusBadge :status="receipt.status" />
                <span class="text-sm text-navy-400">{{ formatMoney(receipt.amount, currency) }}</span>
                <span v-if="receipt.status === 'cancelled' && receipt.cancellation_reason" class="text-sm text-red-600">
                  سبب الإلغاء: {{ receipt.cancellation_reason }}
                </span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button v-if="receipt.status !== 'draft'" class="btn-premium btn-outline inline-flex items-center gap-1.5" @click="handlePrint">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
                طباعة
              </button>
              <template v-if="receipt.status === 'draft'">
                <button class="btn-premium btn-gold inline-flex items-center gap-1.5" @click="startEdit">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                  تعديل
                </button>
                <button class="btn-premium btn-gold inline-flex items-center gap-1.5" @click="handleApprove">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  اعتماد
                </button>
                <button class="btn-premium btn-danger inline-flex items-center gap-1.5" @click="handleDelete">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                  حذف
                </button>
              </template>
              <button v-if="receipt.status === 'approved'" class="btn-premium btn-danger inline-flex items-center gap-1.5" @click="handleCancel">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                إلغاء
              </button>
            </div>
          </div>
        </div>

        <!-- Edit Mode -->
        <div v-if="editMode && receipt.status === 'draft'" class="card-premium p-5 shadow-soft animate-scale-in">
          <Alert v-if="editError" type="error" title="تعذر حفظ التعديل" :message="editError" class="mb-4" />
          <form @submit.prevent="handleEditSubmit">
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">تاريخ القبض <span class="text-red-500">*</span></label>
                <input type="date" dir="ltr" class="input-premium" v-model="editForm.receiptDate" required />
              </div>
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">المبلغ <span class="text-red-500">*</span></label>
                <input type="number" step="0.01" placeholder="المبلغ" class="input-premium" v-model="editForm.amount" required />
              </div>
              <div class="space-y-1.5">
                <label class="text-sm font-medium text-navy-800">طريقة الدفع</label>
                <select class="input-premium" v-model="editForm.paymentMethod">
                  <option v-for="o in paymentMethodOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
              </div>

              <template v-if="editForm.paymentMethod === 'cheque'">
                <div class="space-y-1.5">
                  <label class="text-sm font-medium text-navy-800">رقم الشيك <span class="text-red-500">*</span></label>
                  <input type="text" placeholder="رقم الشيك" class="input-premium" v-model="editForm.referenceNumber" required />
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium text-navy-800">تاريخ الشيك</label>
                  <input type="date" dir="ltr" class="input-premium" v-model="editForm.chequeDate" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-sm font-medium text-navy-800">اسم البنك</label>
                  <input type="text" placeholder="اسم البنك" class="input-premium" v-model="editForm.bankName" />
                </div>
              </template>

              <div class="space-y-1.5 md:col-span-2">
                <ReceiptAttachmentField
                  v-model="editForm.attachment"
                  :payment-method="editForm.paymentMethod"
                  :read-only="receipt.status !== 'draft'"
                />
              </div>

              <div class="space-y-1.5 md:col-span-2">
                <input type="text" placeholder="ملاحظات" class="input-premium" v-model="editForm.notes" />
              </div>
            </div>
            <div class="mt-4 flex gap-2">
              <button type="submit" class="btn-premium btn-gold">حفظ التعديل</button>
              <button type="button" class="btn-premium btn-outline" @click="editMode = false">إلغاء</button>
            </div>
          </form>
        </div>

        <!-- Info Grid -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="item in infoItems" :key="item.label" class="card-premium p-4 shadow-soft">
            <div class="flex items-center gap-2 text-xs text-navy-400 mb-1">
              <svg v-if="item.icon" class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="item.icon" />
              </svg>
              {{ item.label }}
            </div>
            <div class="text-sm font-bold text-navy-900">
              <button
                v-if="item.attachment"
                type="button"
                class="inline-flex items-center gap-2 text-navy-900 hover:opacity-80 transition-opacity"
                @click="attachmentPreviewOpen = true"
              >
                <img
                  :src="item.attachment"
                  :alt="item.label"
                  class="h-16 w-16 rounded-lg border border-ivory-300 object-cover"
                />
              </button>
              <router-link
                v-else-if="item.link"
                :to="item.link"
                class="text-navy-900 hover:opacity-80 transition-opacity"
              >{{ item.value }}</router-link>
              <span v-else>{{ item.value }}</span>
            </div>
          </div>
        </div>

        <!-- Cancelled info -->
        <div v-if="receipt.status === 'cancelled' && receipt.cancelled_by" class="card-premium bg-red-50 p-4 text-sm text-red-600">
          أُلغي السند بواسطة {{ receipt.cancelled_by }} بتاريخ {{ receipt.cancelled_at ? formatDate(receipt.cancelled_at) : '—' }}.
        </div>

        <!-- Attachment Preview Modal -->
        <div
          v-if="attachmentPreviewOpen && receipt.attachment"
          class="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-4"
          @click="attachmentPreviewOpen = false"
        >
          <div class="max-h-[80vh] overflow-hidden rounded-xl bg-white p-2 shadow-xl" @click.stop>
            <img
              :src="receipt.attachment"
              :alt="receipt.payment_method === 'cheque' ? 'صورة الشيك' : 'الصورة المرفقة'"
              class="max-h-[75vh] w-auto rounded-lg"
            />
          </div>
        </div>
      </div>

      <!-- Print Document -->
      <div v-if="printing" class="receipt-print-document">
        <ReceiptPrintDocument :receipt="receipt" :lessor-data="lessorData" />
      </div>
    </template>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Alert from '@/components/ui/Alert.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ReceiptAttachmentField from '@/components/ReceiptAttachmentField.vue'
import ReceiptPrintDocument from '@/components/receipt/ReceiptPrintDocument.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm, prompt } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const lessorData = computed(() => session.state.account?.settings || null)

const paymentMethodOptions = [
  { value: 'cash', label: 'نقداً' },
  { value: 'cheque', label: 'شيك' },
]

const receipt = ref(null)
const loading = ref(true)
const printing = ref(false)
const editMode = ref(false)
const editError = ref('')
const attachmentPreviewOpen = ref(false)

const editForm = reactive({
  receiptDate: '',
  amount: '',
  paymentMethod: 'cash',
  referenceNumber: '',
  chequeDate: '',
  bankName: '',
  attachment: null,
  notes: '',
})

const infoItems = computed(() => {
  if (!receipt.value) return []
  const r = receipt.value
  const icons = {
    user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    building: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
    home: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    file: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    calendar: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    banknote: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    paperclip: 'M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13',
  }

  const items = [
    { label: 'المستأجر', value: r.tenant_name || r.tenant || '—', icon: icons.user, link: r.tenant ? `/tenants/${r.tenant}` : undefined },
    { label: 'العقار', value: r.building_name || r.building || '—', icon: icons.building },
    { label: 'الوحدة', value: r.unit_number || r.unit || '—', icon: icons.home },
    { label: 'العقد', value: r.contract_number || r.contract || '—', icon: icons.file, link: r.contract ? `/contracts/${r.contract}` : undefined },
    { label: 'تاريخ القبض', value: formatDate(r.receipt_date), icon: icons.calendar },
    { label: 'المبلغ', value: formatMoney(r.amount, currency.value), icon: icons.banknote },
    { label: 'طريقة الدفع', value: paymentMethodOptions.find((o) => o.value === r.payment_method)?.label || r.payment_method, icon: icons.banknote },
  ]

  if (r.payment_method === 'cheque') {
    items.push({ label: 'رقم الشيك', value: r.reference_number || '—', icon: icons.banknote })
    if (r.cheque_date) items.push({ label: 'تاريخ الشيك', value: formatDate(r.cheque_date), icon: icons.calendar })
    if (r.bank_name) items.push({ label: 'اسم البنك', value: r.bank_name || '—', icon: icons.building })
  }

  if (r.notes) {
    items.push({ label: 'ملاحظات', value: r.notes, icon: null })
  }

  if (r.attachment) {
    items.push({
      label: r.payment_method === 'cheque' ? 'صورة الشيك' : 'الصورة المرفقة',
      value: '',
      icon: icons.paperclip,
      attachment: r.attachment,
    })
  }

  return items
})

async function fetchReceipt() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.receipt.get_receipt', { name: route.params.id })
    receipt.value = res
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء تحميل بيانات سند القبض')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  const confirmed = await confirm({
    title: 'حذف سند القبض',
    message: 'سيتم حذف مسودة سند القبض نهائيًا. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'danger',
    confirmLabel: 'حذف',
  })
  if (!confirmed) return
  try {
    await callApi('rental.rental.api.receipt.delete_receipt', { name: receipt.value.name })
    router.push({ name: 'Receipts' })
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء حذف سند القبض')
  }
}

async function handleApprove() {
  try {
    const res = await callApi('rental.rental.api.receipt.approve_receipt', { name: receipt.value.name })
    receipt.value = res
    editMode.value = false
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء اعتماد سند القبض')
  }
}

async function handleCancel() {
  const reason = await prompt({
    title: 'إلغاء سند القبض',
    message: 'أدخل سبب إلغاء سند القبض',
    inputLabel: 'سبب الإلغاء',
    variant: 'warning',
  })
  if (!reason) return
  try {
    const res = await callApi('rental.rental.api.receipt.cancel_receipt', { name: receipt.value.name, reason })
    receipt.value = res
  } catch (err) {
    toast.error(extractError(err) || 'حدث خطأ أثناء إلغاء سند القبض')
  }
}

function startEdit() {
  if (!receipt.value) return
  const r = receipt.value
  editForm.receiptDate = (r.receipt_date || '').slice(0, 10)
  editForm.amount = String(r.amount || '')
  editForm.paymentMethod = r.payment_method || 'cash'
  editForm.referenceNumber = r.reference_number || ''
  editForm.chequeDate = r.cheque_date ? r.cheque_date.slice(0, 10) : ''
  editForm.bankName = r.bank_name || ''
  editForm.attachment = r.attachment || null
  editForm.notes = r.notes || ''
  editMode.value = true
  editError.value = ''
}

async function handleEditSubmit() {
  editError.value = ''
  try {
    const payload = {
      receipt_date: editForm.receiptDate,
      amount: editForm.amount,
      payment_method: editForm.paymentMethod,
      notes: editForm.notes || undefined,
      attachment: editForm.attachment || undefined,
    }
    if (editForm.paymentMethod === 'cheque') {
      payload.reference_number = editForm.referenceNumber
      payload.cheque_date = editForm.chequeDate || undefined
      payload.bank_name = editForm.bankName || undefined
    }
    const res = await callApi('rental.rental.api.receipt.update_receipt', { name: receipt.value.name, ...payload })
    receipt.value = res
    editMode.value = false
  } catch (err) {
    editError.value = extractError(err) || 'حدث خطأ'
  }
}

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

onMounted(fetchReceipt)
</script>

<style scoped>
@media print {
  :deep(.app-layout > *:not(.receipt-print-document)),
  :deep(.app-layout nav),
  :deep(.app-layout header) {
    display: none !important;
  }
  .receipt-print-document {
    width: 100% !important;
    max-width: none !important;
  }
}
</style>
