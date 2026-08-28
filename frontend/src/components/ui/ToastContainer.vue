<template>
  <Teleport to="body">
    <div class="fixed top-5 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 items-center" dir="rtl">
      <transition-group name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="card-premium px-4 py-3 min-w-[280px] max-w-md flex items-center gap-3 animate-slide-up shadow-soft-lg"
          :class="borderClass(t.type)"
        >
          <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" :class="iconBgClass(t.type)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="t.type === 'success'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              <path v-else-if="t.type === 'error'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <p class="text-sm font-medium text-navy-800 flex-1">{{ t.message }}</p>
          <button class="text-navy-400 hover:text-navy-700" @click="remove(t.id)">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/composables/useToast'

const { state, dismiss: remove } = useToast()
const toasts = state.toasts

function borderClass(type) {
  return { success: 'border-r-4 !border-r-emerald-500', error: 'border-r-4 !border-r-red-500', info: 'border-r-4 !border-r-navy-500' }[type] || ''
}
function iconBgClass(type) {
  return { success: 'bg-emerald-50 text-emerald-600', error: 'bg-red-50 text-red-600', info: 'bg-navy-50 text-navy-600' }[type] || 'bg-navy-50 text-navy-600'
}
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-12px); }
.toast-leave-to { opacity: 0; transform: translateY(-12px); }
</style>
