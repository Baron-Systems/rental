<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center p-4" dir="rtl">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-navy-950/50 backdrop-blur-sm" @click="$emit('update:modelValue', false)"></div>

        <!-- Modal -->
        <div class="relative card-premium w-full overflow-hidden animate-scale-in" :class="sizeClass">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-ivory-300/60 bg-ivory-50/50">
            <h3 class="text-base font-bold text-navy-900">{{ title }}</h3>
            <button
              class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-400 hover:text-navy-800 hover:bg-ivory-200 transition-colors"
              @click="$emit('update:modelValue', false)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <!-- Body -->
          <div class="px-6 py-5 max-h-[70vh] overflow-y-auto">
            <slot />
          </div>

          <!-- Footer -->
          <div v-if="$slots.footer" class="flex items-center justify-end gap-2 px-6 py-4 border-t border-ivory-300/60 bg-ivory-50/50">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, required: true },
  size: { type: String, default: 'md' }, // sm, md, lg, xl
})
defineEmits(['update:modelValue'])

const sizeClass = computed(() => ({
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}[props.size] || 'max-w-lg'))
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
