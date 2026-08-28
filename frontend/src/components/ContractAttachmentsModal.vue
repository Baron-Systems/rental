<template>
  <Modal :title="title" size="lg" v-model="show">
    <div class="space-y-4">
      <!-- Upload area (only when not readonly) -->
      <div v-if="!isReadonly" class="border-2 border-dashed border-ivory-300 rounded-xl p-6 text-center hover:border-gold-400 transition-colors">
        <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="handleFileUpload" />
        <button class="btn-premium btn-outline" @click="$refs.fileInput.click()" :disabled="uploading">
          <svg v-if="uploading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          <svg v-else class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
          {{ uploading ? 'جاري الرفع...' : 'إضافة صور' }}
        </button>
      </div>

      <!-- Readonly notice (toast-only in original; no static notice) -->


      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل الصور...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="!attachments.length" class="text-center py-12">
        <svg class="w-12 h-12 text-navy-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
        <p class="text-sm font-medium text-navy-500">لا توجد صور مرفقة</p>
        <p class="text-xs text-navy-400 mt-1">لم يتم إرفاق أي صور بهذا العقد بعد.</p>
      </div>

      <!-- Attachments grid -->
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <AttachmentThumbnail
          v-for="att in attachments"
          :key="att.name || att.id"
          :attachment="att"
          :contractId="contractId"
          :canDelete="!isReadonly"
          @delete="handleDelete"
          @preview="$emit('preview', att)"
        />
      </div>
    </div>

    <template #footer>
      <button class="btn-premium btn-outline" @click="show = false">إغلاق</button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import Modal from '@/components/ui/Modal.vue'
import AttachmentThumbnail from '@/components/AttachmentThumbnail.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { callApi, extractError } from '@/composables/useApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  contractId: { type: String, default: '' },
  attachments: { type: Array, default: () => [] },
  title: { type: String, default: 'صور العقد' },
  uploading: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  status: { type: String, default: '' },
  isArchived: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'upload', 'delete', 'preview'])

const toast = useToast()
const { confirm } = useConfirm()

const READONLY_STATUSES = ['cancelled', 'expired', 'evicted']
const isReadonly = computed(() =>
  props.isArchived || (props.status ? READONLY_STATUSES.includes(props.status) : false)
)

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const fileInput = ref(null)

function handleFileUpload(e) {
  if (isReadonly.value) {
    toast.error('لا يمكن إضافة صور لعقد في هذه الحالة')
    return
  }
  const files = e.target.files
  if (!files?.length) return
  // Filter only images
  const imageFiles = Array.from(files).filter((f) => f.type.startsWith('image/'))
  if (imageFiles.length === 0) {
    toast.error('يمكن رفع الصور فقط')
    e.target.value = ''
    return
  }
  emit('upload', imageFiles)
  e.target.value = ''
}

async function handleDelete(attachment) {
  const ok = await confirm({
    title: 'حذف الصورة',
    message: 'هل أنت متأكد من حذف هذه الصورة المرفقة؟',
    variant: 'danger',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  emit('delete', attachment)
}
</script>
