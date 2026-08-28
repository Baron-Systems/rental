<template>
  <div v-if="total > 0" class="flex items-center justify-between px-5 py-4 border-t border-ivory-300/60 bg-ivory-50/50">
    <p class="text-xs text-navy-400 font-medium">
      عرض {{ (page - 1) * pageSize + 1 }}-{{ Math.min(page * pageSize, total) }} من {{ total }}
    </p>
    <div class="flex items-center gap-1">
      <button
        :disabled="page <= 1"
        class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-ivory-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        @click="$emit('change', page - 1)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
      </button>
      <div class="flex items-center gap-1 px-2">
        <span class="text-sm font-bold text-navy-800">{{ page }}</span>
        <span class="text-xs text-navy-400">/</span>
        <span class="text-sm text-navy-400">{{ totalPages }}</span>
      </div>
      <button
        :disabled="page >= totalPages"
        class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-ivory-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        @click="$emit('change', page + 1)"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
})
defineEmits(['change'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
</script>
