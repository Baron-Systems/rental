<template>
  <AppLayout>
    <div class="p-6 lg:p-8 animate-fade-in" dir="rtl">
      <div class="mx-auto max-w-2xl space-y-5">
        <!-- Back link (source: evict/page.tsx:113-117) -->
        <div class="flex items-center gap-2">
          <router-link :to="`/contracts/${route.params.id}`" class="btn-premium btn-ghost text-navy-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            العقد
          </router-link>
        </div>

        <!-- Title (source: evict/page.tsx:119) -->
        <h1 class="text-2xl font-bold tracking-tight text-navy-900">إخلاء وحدة</h1>

        <div v-if="loading" class="flex items-center justify-center py-20">
          <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        </div>

        <div v-else-if="!contract" class="text-center py-20">
          <p class="text-navy-400">العقد غير موجود</p>
          <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Contracts' })">العودة للقائمة</button>
        </div>

        <template v-else>
          <!-- Contract info card (source: evict/page.tsx:121-146) -->
          <div class="card-premium overflow-hidden">
            <div class="border-b border-ivory-300/50 px-5 py-4 bg-blue-50/50">
              <div class="flex items-center gap-2 text-sm font-semibold text-blue-600">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                بيانات العقد
              </div>
            </div>
            <div class="px-5 py-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
              <div class="flex items-center gap-2">
                <span class="text-navy-400">العقد:</span>
                <span class="font-semibold text-navy-900">{{ contract.contract_number }}</span>
              </div>
              <div class="flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                <span class="text-navy-400">المستأجر:</span>
                <span class="font-semibold text-navy-900">{{ contract.tenant_name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                <span class="text-navy-400">الوحدة:</span>
                <span class="font-semibold text-navy-900">{{ contract.unit_number }} - {{ contract.building_name }}</span>
              </div>
            </div>
          </div>

          <!-- Eviction form (source: evict/page.tsx:148-229) -->
          <form @submit.prevent="submitEviction" class="card-premium overflow-hidden">
            <div class="border-b border-ivory-300/50 px-5 py-4">
              <div class="flex items-center gap-2 text-sm font-semibold text-navy-900">
                <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                بيانات الإخلاء
              </div>
            </div>

            <div class="px-5 py-5 space-y-4">
              <!-- Error (source: evict/page.tsx:157) -->
              <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <p class="font-bold mb-1">تعذر حفظ الإخلاء</p>
                <p>{{ error }}</p>
              </div>

              <!-- Manual due warning (source: evict/page.tsx:159-163) -->
              <div v-if="manualDueCharges.length > 0" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div class="flex items-start gap-3">
                  <svg class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                  <div>
                    <p class="text-sm font-bold text-amber-800">تنبيه قبل الإخلاء</p>
                    <p class="text-sm text-amber-700 mt-1">بعد إتمام الإخلاء لن تتمكن من إضافة التزامات جديدة على هذا العقد. تأكد من تسجيل أي استهلاك نهائي أو فواتير فعلية أو مبالغ مستحقة حسب الحاجة قبل المتابعة.</p>
                  </div>
                </div>
              </div>

              <!-- Last meter reading review (source: evict/page.tsx:165-196) -->
              <div v-if="meteredCharges.length > 0" class="space-y-3">
                <h3 class="text-sm font-semibold text-navy-900">مراجعة العدادات</h3>
                <div v-for="ch in meteredCharges" :key="ch.name || ch.due_type" class="rounded-xl border border-ivory-300 bg-ivory-100/40 p-4">
                  <div class="flex items-center gap-2 text-sm font-semibold text-navy-900">
                    <svg v-if="ch.due_type_code === 'electricity'" class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                    <svg v-else class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    {{ serviceLabel(ch) }}
                  </div>
                  <div class="mt-2 grid grid-cols-1 gap-1 text-sm">
                    <div class="flex items-center gap-2">
                      <span class="text-navy-400">آخر قراءة مسجلة:</span>
                      <span class="font-medium text-navy-900">{{ getLastMeterReading(ch).reading ?? '—' }}</span>
                    </div>
                    <div v-if="getLastMeterReading(ch).date" class="flex items-center gap-2">
                      <span class="text-navy-400">تاريخ آخر تسجيل:</span>
                      <span class="font-medium text-navy-900">{{ formatDate(getLastMeterReading(ch).date) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Notes (source: evict/page.tsx:198-210) -->
              <div class="space-y-1.5">
                <label class="flex items-center gap-1.5 text-sm font-medium text-navy-900">
                  <svg class="w-4 h-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                  ملاحظات
                </label>
                <textarea
                  v-model="form.notes"
                  placeholder="أي ملاحظات إضافية حول حالة الوحدة..."
                  class="input-premium h-auto w-full py-2"
                  rows="3"
                ></textarea>
              </div>
            </div>

            <!-- Actions (source: evict/page.tsx:213-228) -->
            <div class="border-t border-ivory-300/50 px-5 py-4 flex flex-col sm:flex-row-reverse gap-3">
              <button
                type="submit"
                :disabled="submitting"
                class="btn-premium btn-danger disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {{ submitting ? 'جاري التنفيذ...' : 'تنفيذ الإخلاء' }}
              </button>
              <button
                type="button"
                @click="router.back()"
                class="btn-premium btn-outline"
              >
                إلغاء
              </button>
            </div>
          </form>
        </template>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import { callApi, extractError, formatDate } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const contract = ref(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')

const form = ref({
  notes: '',
})

const MANUAL_DUE_METHODS = ['metered', 'actual_bill', 'on_demand']

const meteredCharges = computed(() =>
  (contract.value?.contract_charges || []).filter(isTenantMeteredCharge)
)

const manualDueCharges = computed(() =>
  (contract.value?.contract_charges || []).filter(isTenantManualDueCharge)
)

function isTenantMeteredCharge(charge) {
  const code = charge.due_type_code || charge.dueType?.code
  return (
    (code === 'electricity' || code === 'water') &&
    charge.responsibility === 'tenant' &&
    charge.payment_by !== 'tenant' &&
    charge.paymentBy !== 'tenant' &&
    charge.calculation_method === 'metered'
  )
}

function isTenantManualDueCharge(charge) {
  return (
    charge.responsibility === 'tenant' &&
    charge.payment_by !== 'tenant' &&
    charge.paymentBy !== 'tenant' &&
    MANUAL_DUE_METHODS.includes(charge.calculation_method)
  )
}

const SERVICE_LABELS = { electricity: 'الكهرباء', water: 'المياه' }

function serviceLabel(ch) {
  const code = ch.due_type_code || ch.dueType?.code
  return SERVICE_LABELS[code] || ch.due_type_name || ch.due_type || ''
}

function getLastMeterReading(charge) {
  const dueTypeId = charge.due_type || charge.dueTypeId
  const dues = [...(contract.value?.dues || [])]
    .filter((d) => (d.due_type || d.dueTypeId) === dueTypeId && (d.status === 'approved' || d.docstatus === 1) && d.current_meter_reading != null)
    .sort((a, b) => {
      const aTime = new Date(a.transaction_date || a.transactionDate || a.creation || a.createdAt).getTime()
      const bTime = new Date(b.transaction_date || b.transactionDate || b.creation || b.createdAt).getTime()
      if (bTime !== aTime) return bTime - aTime
      return new Date(b.creation || b.createdAt).getTime() - new Date(a.creation || a.createdAt).getTime()
    })
  const lastDue = dues[0]
  if (lastDue) {
    return {
      reading: lastDue.current_meter_reading || lastDue.currentMeterReading,
      date: lastDue.transaction_date || lastDue.transactionDate || lastDue.creation,
    }
  }
  return {
    reading: charge.opening_meter_reading || charge.openingMeterReading || null,
    date: null,
  }
}

async function fetchContract() {
  loading.value = true
  try {
    contract.value = await callApi('rental.rental.api.contract.get_contract', { name: route.params.id })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function submitEviction() {
  error.value = ''
  submitting.value = true
  try {
    await callApi('rental.rental.api.eviction.create_eviction', {
      contract: route.params.id,
      notes: form.value.notes || undefined,
    })
    router.push({ name: 'ContractDetail', params: { id: route.params.id } })
  } catch (e) {
    error.value = extractError(e)
  } finally {
    submitting.value = false
  }
}

onMounted(fetchContract)
</script>
