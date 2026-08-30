<template>
  <!-- Source: PrintHeader.tsx:13 — return null if no logo and no name.
       Color: text-foreground in old = #002350 (globals.css --deep-navy). -->
  <div v-if="logo || name" class="print-header flex items-center justify-between gap-4 pt-2 pb-0">
    <div class="flex justify-start">
      <img
        v-if="logo"
        :src="logo"
        alt="شعار المؤجر"
        class="h-[65px] w-auto object-contain"
      />
    </div>
    <div class="flex justify-end">
      <span v-if="name" class="text-[17px] font-bold rp-print-fg">{{ name }}</span>
    </div>
  </div>
</template>

<script setup>
// Source: PrintHeader.tsx:6-10 — only logo, name, className props
const props = defineProps({
  logo: { type: String, default: null },
  name: { type: String, default: null },
})
</script>

<style scoped>
/* Source: old globals.css --foreground = hsl(214 98% 16%) = #002350.
   Scoped so it only affects PrintHeader, not the rest of the app. */
.rp-print-fg { color: #002350; }
</style>
