<template>
  <td
    class="px-[18px] py-3.5 text-sm text-navy-700 whitespace-nowrap"
    :class="align === 'center' ? 'text-center' : 'text-right'"
  >
    <slot />
  </td>
</template>

<script setup>
defineProps({
  align: { type: String, default: 'right' },
})
</script>
