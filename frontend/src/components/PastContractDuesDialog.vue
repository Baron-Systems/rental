<template>
  <Modal v-model="show" size="md" title="عقد بتاريخ سابق">
    <div class="mb-4 flex items-center gap-3">
      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
        <svg class="h-5 w-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
      </div>
      <div>
        <h3 class="text-lg font-bold text-navy-900">عقد بتاريخ سابق</h3>
        <p class="text-sm text-navy-400">تم إدخال عقد انتهت مدته قبل تاريخ اليوم.</p>
      </div>
    </div>

    <p class="mb-4 text-sm font-medium text-navy-900">اختر طريقة التعامل مع المستحقات:</p>

    <div class="space-y-3">
      <!-- Generate all dues -->
      <button
        type="button"
        class="flex w-full items-start gap-3 rounded-xl border border-navy-200 bg-navy-50/40 p-4 text-right transition hover:bg-navy-50 hover:border-navy-300 disabled:opacity-60"
        :disabled="isLoading"
        @click="handleConfirm(true)"
      >
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100">
          <svg class="h-4 w-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <div>
          <p class="font-medium text-navy-900">إنشاء جميع المستحقات</p>
          <p class="text-xs text-navy-400">إنشاء جميع المستحقات المستحقة خلال فترة العقد، وتكون حالتها مستحقة.</p>
        </div>
      </button>

      <!-- Skip dues -->
      <button
        type="button"
        class="flex w-full items-start gap-3 rounded-xl border border-navy-200 bg-navy-50/40 p-4 text-right transition hover:bg-navy-50 hover:border-navy-300 disabled:opacity-60"
        :disabled="isLoading"
        @click="handleConfirm(false)"
      >
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-100">
          <svg class="h-4 w-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </div>
        <div>
          <p class="font-medium text-navy-900">عدم إنشاء المستحقات</p>
          <p class="text-xs text-navy-400">عدم إنشاء أي التزامات أو مطالبات مالية، ويعتبر العقد للأرشفة فقط.</p>
        </div>
      </button>
    </div>

    <template #footer>
      <button class="btn-premium btn-outline w-full" :disabled="isLoading" @click="handleCancel">
        {{ isLoading ? 'جاري المعالجة...' : 'إلغاء' }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { computed } from 'vue'
import Modal from '@/components/ui/Modal.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  isLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

function handleConfirm(generateDues) {
  if (props.isLoading) return
  emit('confirm', generateDues)
}

function handleCancel() {
  if (props.isLoading) return
  show.value = false
  emit('cancel')
}
</script>
