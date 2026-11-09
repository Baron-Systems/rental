<template>
  <div v-if="state.html" class="fixed inset-0 z-[100] flex flex-col bg-navy-950/40 backdrop-blur-sm print:hidden" dir="rtl">
    <div class="shrink-0 flex items-center justify-between gap-3 px-4 py-3 bg-white border-b border-ivory-300 shadow-sm">
      <h3 class="text-base font-bold text-navy-900 truncate">{{ state.title }}</h3>
      <div class="flex items-center gap-2">
        <button type="button" class="btn-premium btn-gold inline-flex items-center gap-1.5" @click="printFrame">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
          <span>طباعة</span>
        </button>
        <button type="button" class="inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-navy-500 transition-colors hover:bg-ivory-200 hover:text-navy-800" title="إغلاق" @click="close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>
    </div>
    <div class="flex-1 min-h-0 p-2 sm:p-4">
      <iframe ref="frameRef" :srcdoc="state.html" class="w-full h-full rounded-lg bg-white shadow-soft-lg border border-ivory-300" title="معاينة الطباعة"></iframe>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { usePrintPreview } from '@/composables/usePrintPreview'

const { state, close } = usePrintPreview()
const frameRef = ref(null)
const route = useRoute()

function printFrame() {
  const w = frameRef.value?.contentWindow
  if (!w) return
  w.focus()
  w.print()
}

function onKey(e) {
  if (e.key === 'Escape') close()
}

watch(() => state.html, (html) => {
  document.body.style.overflow = html ? 'hidden' : ''
  if (html) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
})

// Close the preview when navigating away
watch(() => route.fullPath, () => close())

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>
