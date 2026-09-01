<template>
  <div class="space-y-1.5">
    <label class="block text-sm font-semibold text-navy-700 no-underline flex items-center gap-1">
      {{ label }}<span v-if="required" class="text-gold-500">*</span>
    </label>
    <p v-if="hint" class="text-xs text-navy-400 -mt-1 mb-1">{{ hint }}</p>
    <slot />
    <p v-if="error" class="text-xs text-red-600 font-medium">{{ error }}</p>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  required: { type: Boolean, default: false },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
})
</script>
