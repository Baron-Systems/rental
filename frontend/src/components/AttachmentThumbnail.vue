<template>
  <div
    ref="containerRef"
    class="group relative overflow-hidden rounded-lg border border-ivory-300 bg-navy-50/40"
    :class="className"
  >
    <!-- Image loaded -->
    <img
      v-if="fileData && isImage"
      :src="fileData"
      :alt="attachment.file_name || attachment.fileName"
      class="h-32 w-full object-cover"
    />
    <!-- Placeholder / loading -->
    <div v-else class="flex h-32 w-full flex-col items-center justify-center gap-2 text-navy-400">
      <svg v-if="loading" class="h-6 w-6 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <svg v-else class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
      </svg>
      <span class="text-xs">{{ loading ? 'جاري التحميل...' : (attachment.file_type || attachment.fileType || 'ملف') }}</span>
    </div>

    <!-- Hover actions -->
    <div class="absolute inset-0 flex items-start justify-end gap-1 bg-black/0 p-2 opacity-0 transition-opacity group-hover:bg-black/20 group-hover:opacity-100">
      <button
        type="button"
        class="rounded-md bg-white/90 p-1.5 text-navy-700 shadow-sm hover:bg-navy-50"
        title="معاينة"
        @click="handlePreview"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
      </button>
      <button
        type="button"
        class="rounded-md bg-white/90 p-1.5 text-navy-700 shadow-sm hover:bg-navy-50"
        title="تنزيل"
        @click.stop="handleDownload"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
      </button>
      <button
        v-if="canDelete"
        type="button"
        class="rounded-md bg-white/90 p-1.5 text-red-600 shadow-sm hover:bg-red-50"
        title="حذف"
        @click.stop="$emit('delete', attachment)"
      >
        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
      </button>
    </div>

    <!-- File name bar -->
    <div class="absolute bottom-0 left-0 right-0 truncate bg-white/90 px-2 py-1 text-xs text-navy-500">
      {{ attachment.file_name || attachment.fileName || 'ملف' }}
    </div>
  </div>

  <!-- Preview modal -->
  <Teleport to="body">
    <div
      v-if="previewOpen && fileData && isImage"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click="closePreview"
    >
      <img
        :src="fileData"
        :alt="attachment.file_name || attachment.fileName"
        class="max-h-[80vh] w-auto rounded-lg shadow-xl"
        @click.stop
      />
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { callApi, extractError } from '@/composables/useApi'

const props = defineProps({
  attachment: { type: Object, required: true },
  contractId: { type: String, default: '' },
  className: { type: String, default: '' },
  canDelete: { type: Boolean, default: true },
})
const emit = defineEmits(['delete', 'preview'])

const containerRef = ref(null)
const fileData = ref(null)
const loading = ref(false)
const previewOpen = ref(false)
let observer = null

const isImage = computed(() => {
  const type = props.attachment.file_type || props.attachment.fileType || ''
  if (type.startsWith('image/')) return true
  const url = props.attachment.file_url || props.attachment.fileUrl || ''
  return /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(url)
})

async function loadFile() {
  if (fileData.value || loading.value) return
  loading.value = true
  try {
    // If file_url is already a data URL or direct URL, use it
    const url = props.attachment.file_url || props.attachment.fileUrl
    if (url && (url.startsWith('data:') || url.startsWith('http'))) {
      fileData.value = url
    } else if (props.contractId) {
      // Fetch from API
      const res = await callApi('rental.rental.api.contract.get_attachment', {
        name: props.contractId,
        attachment_id: props.attachment.name || props.attachment.id,
      })
      // Backend returns { attachment: { file_data, ... } }
      const att = res?.attachment || res
      fileData.value = att?.file_data || att?.fileData || null
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function handleDownload() {
  let data = fileData.value
  if (!data) {
    await loadFile()
    data = fileData.value
  }
  if (!data) return
  const link = document.createElement('a')
  link.href = data
  link.download = props.attachment.file_name || props.attachment.fileName || 'attachment'
  link.click()
}

function handlePreview() {
  if (!fileData.value) {
    loadFile().then(() => { previewOpen.value = true })
  } else {
    previewOpen.value = true
  }
  emit('preview', props.attachment)
}

function closePreview() {
  previewOpen.value = false
}

onMounted(() => {
  if (!containerRef.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) {
        loadFile()
        observer?.disconnect()
      }
    },
    { rootMargin: '100px' }
  )
  observer.observe(containerRef.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>
