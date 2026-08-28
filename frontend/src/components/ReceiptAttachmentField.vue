<template>
  <div class="space-y-1.5">
    <label class="text-sm font-medium text-navy-800">{{ effectiveLabel }}</label>
    <div v-if="modelValue" class="rounded-[10px] border border-ivory-300 bg-ivory-50/40 p-3">
      <div class="flex items-center gap-3">
        <button
          v-if="isImage"
          type="button"
          class="h-14 w-14 overflow-hidden rounded-lg border border-ivory-300 bg-white"
          @click="previewOpen = true"
        >
          <img :src="modelValue" alt="معاينة المرفق" class="h-full w-full object-cover" />
        </button>
        <div v-else class="flex h-14 w-14 items-center justify-center rounded-lg border border-ivory-300 bg-white text-navy-400">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-navy-800 truncate">{{ isImage ? 'صورة مرفقة' : 'ملف مرفق' }}</p>
          <p class="text-xs text-navy-400">{{ isImage ? 'صورة' : 'ملف' }}</p>
        </div>
        <div class="flex items-center gap-1">
          <a
            :href="modelValue"
            download="receipt-attachment"
            target="_blank"
            rel="noreferrer"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-navy-400 hover:bg-ivory-200 hover:text-navy-800 transition-colors"
            title="تحميل"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          </a>
          <button
            v-if="!readOnly"
            type="button"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-navy-400 hover:bg-red-50 hover:text-red-600 transition-colors"
            title="إزالة"
            @click="handleRemove"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
      </div>

      <div
        v-if="previewOpen && isImage"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-4"
        @click="previewOpen = false"
      >
        <div class="max-h-[80vh] overflow-hidden rounded-xl bg-white p-2 shadow-xl" @click.stop>
          <img :src="modelValue" alt="معاينة" class="max-h-[75vh] w-auto rounded-lg" />
        </div>
      </div>
    </div>
    <div v-else>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        :disabled="readOnly"
        @change="handleFileChange"
      />
      <button
        type="button"
        class="btn-premium btn-outline text-sm inline-flex items-center gap-1.5"
        :disabled="readOnly"
        @click="fileInput?.click()"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
        {{ buttonText }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, null], default: null },
  readOnly: { type: Boolean, default: false },
  label: { type: String, default: '' },
  paymentMethod: { type: String, default: 'cash' },
})
const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const previewOpen = ref(false)

const isImage = computed(() => {
  const v = props.modelValue
  return typeof v === 'string' && v.startsWith('data:image/')
})

const effectiveLabel = computed(() => {
  if (props.label) return props.label
  return props.paymentMethod === 'cheque' ? 'صورة الشيك' : 'المرفق'
})

const buttonText = computed(() => {
  return props.paymentMethod === 'cheque' ? 'إرفاق صورة الشيك' : 'إرفاق صورة'
})

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const base64 = await new Promise((resolve) => {
    const reader = new FileReader()
    reader.onloadend = () => resolve(reader.result)
    reader.readAsDataURL(file)
  })
  emit('update:modelValue', base64)
  e.target.value = ''
}

function handleRemove() {
  emit('update:modelValue', null)
}
</script>
