<template>
  <div class="card-premium overflow-hidden">
    <div class="overflow-x-auto">
      <table class="w-full">
        <thead class="table-header-premium">
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="col.align === 'center' ? 'text-center' : 'text-right'"
            >{{ col.label }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-ivory-300/50">
          <slot />
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
defineProps({
  columns: { type: Array, required: true },
})
</script>
