<template>
  <div
    class="card-premium"
    :class="paddingClass"
  >
    <div v-if="title || $slots.title" class="flex items-center justify-between mb-4 pb-3 border-b border-ivory-300/60">
      <h3 class="text-sm font-bold text-navy-800 tracking-tight flex items-center gap-2">
        <span v-if="icon" class="w-[3px] h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
        <slot name="title">{{ title }}</slot>
      </h3>
      <slot name="action" />
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  title: { type: String, default: '' },
  icon: { type: Boolean, default: true },
  padding: { type: String, default: 'md' }, // none, sm, md, lg
})

const paddingClass = computed(() => ({
  none: '',
  sm: 'p-3',
  md: 'p-5',
  lg: 'p-6',
}[props.padding] || 'p-5'))
</script>
