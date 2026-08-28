<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4 print:hidden" dir="rtl">
        <div class="absolute inset-0 bg-navy-950/40 backdrop-blur-sm" @click="$emit('update:modelValue', false)"></div>

        <div class="relative z-10 w-full max-w-md overflow-hidden rounded-[14px] border border-ivory-300 bg-white p-6 shadow-xl animate-scale-in">
          <div class="flex items-start gap-4">
            <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-100">
              <svg class="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z"/>
              </svg>
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="text-base font-bold text-navy-900">إلغاء العقد</h3>
              <p class="mt-1 text-sm leading-relaxed text-navy-500">
                أدخل تاريخ الإلغاء وسببه. سيتم إنشاء التسوية المالية بعد الإلغاء.
              </p>
            </div>
            <button
              class="rounded-full p-1 text-navy-400 transition hover:bg-ivory-100 hover:text-navy-900"
              aria-label="إغلاق"
              @click="$emit('update:modelValue', false)"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <form class="mt-5 space-y-4" @submit.prevent="handleSubmit">
            <div>
              <label for="cancellationDate" class="mb-1.5 block text-sm font-medium text-navy-900">تاريخ الإلغاء</label>
              <div class="relative">
                <svg class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <input
                  id="cancellationDate"
                  type="date"
                  v-model="cancellationDate"
                  class="w-full rounded-lg border border-ivory-300 bg-white px-3 py-2 pl-10 text-sm focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-200/40"
                />
              </div>
              <p class="mt-1.5 text-xs text-navy-500">
                فترة العقد: {{ formatDate(contractStart) }} — {{ formatDate(contractEnd) }}
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-navy-900">سبب الإلغاء</label>
              <input
                v-model="reason"
                placeholder="مثال: اتفاق الطرفين"
                class="w-full rounded-lg border border-ivory-300 bg-white px-3 py-2 text-sm focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-200/40"
              />
            </div>

            <p v-if="error" class="rounded-lg bg-red-50 p-2 text-sm text-red-600">{{ error }}</p>

            <div class="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
              <button type="button" class="btn-premium btn-outline text-sm" @click="$emit('update:modelValue', false)">
                إلغاء
              </button>
              <button
                type="submit"
                class="btn-premium bg-red-600 text-white hover:bg-red-700 text-sm"
                :disabled="loading || !reason.trim() || !isWithinContract"
              >
                {{ loading ? 'جارٍ...' : 'تأكيد الإلغاء' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  contractStart: { type: String, required: true },
  contractEnd: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const cancellationDate = ref(toISODate(new Date()))
const reason = ref('')
const loading = ref(false)
const error = ref('')

function toISODate(d) {
  const date = new Date(d)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function toCalendarDay(value) {
  if (!value) return null
  const d = new Date(value)
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function formatDate(value) {
  const d = toCalendarDay(value)
  if (!d) return ''
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  return `${day}/${month}/${d.getFullYear()}`
}

const isWithinContract = computed(() => {
  const start = toCalendarDay(props.contractStart)
  const end = toCalendarDay(props.contractEnd)
  const selected = toCalendarDay(cancellationDate.value)
  if (!start || !end || !selected) return false
  return selected >= start && selected <= end
})

watch(() => props.modelValue, (val) => {
  if (val) {
    cancellationDate.value = toISODate(new Date())
    reason.value = ''
    error.value = ''
    loading.value = false
  }
})

async function handleSubmit() {
  error.value = ''
  if (!cancellationDate.value) {
    error.value = 'تاريخ الإلغاء مطلوب'
    return
  }
  if (!isWithinContract.value) {
    error.value = `تاريخ الإلغاء يجب أن يكون بين ${formatDate(props.contractStart)} و ${formatDate(props.contractEnd)}`
    return
  }
  if (!reason.value.trim()) {
    error.value = 'سبب الإلغاء مطلوب'
    return
  }

  try {
    loading.value = true
    await emit('confirm', cancellationDate.value, reason.value)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
