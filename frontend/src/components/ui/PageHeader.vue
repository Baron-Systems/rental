<template>
  <div class="mb-6 animate-slide-up">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1.5">
          <button
            v-if="backHref"
            @click="goBack"
            class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:text-navy-800 hover:bg-ivory-200 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </button>
          <h1 class="text-2xl font-bold text-navy-900 tracking-tight">{{ title }}</h1>
        </div>
        <p v-if="description" class="text-sm text-navy-400 font-medium">{{ description }}</p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <slot name="actions" />
        <button
          v-if="actionLabel"
          class="btn-premium btn-gold"
          @click="$emit('action')"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          {{ actionLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
  backHref: { type: String, default: '' },
})
defineEmits(['action'])

function goBack() {
  router.back()
}
</script>
