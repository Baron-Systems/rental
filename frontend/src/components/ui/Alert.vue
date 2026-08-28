<template>
  <div
    v-if="show"
    class="rounded-xl border p-4 flex items-start gap-3 animate-fade-in"
    :class="classMap[type] || classMap.info"
  >
    <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path v-if="type === 'error'" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      <path v-else-if="type === 'warning'" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      <path v-else-if="type === 'success'" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
    <div class="flex-1">
      <p v-if="title" class="font-bold text-sm mb-0.5">{{ title }}</p>
      <p class="text-sm">{{ message }}</p>
    </div>
    <button v-if="dismissible" class="text-current opacity-60 hover:opacity-100 transition-opacity" @click="$emit('dismiss')">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
    </button>
  </div>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: true },
  type: { type: String, default: 'info' }, // info | success | warning | error
  title: { type: String, default: '' },
  message: { type: String, required: true },
  dismissible: { type: Boolean, default: false },
})
defineEmits(['dismiss'])

const classMap = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  error: 'bg-red-50 border-red-200 text-red-800',
}
</script>
