<template>
  <div class="space-y-4">
    <!-- Header skeleton -->
    <div class="flex items-center justify-between animate-pulse">
      <div class="space-y-2">
        <div class="h-7 w-48 bg-ivory-200 rounded-lg"></div>
        <div class="h-3 w-64 bg-ivory-100 rounded"></div>
      </div>
      <div class="h-10 w-32 bg-ivory-200 rounded-xl"></div>
    </div>

    <!-- Cards skeleton -->
    <div v-if="layout === 'cards'" class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3 gap-5">
      <div v-for="i in count" :key="i" class="card-premium p-5 animate-pulse">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-xl bg-ivory-200"></div>
          <div class="h-4 bg-ivory-200 rounded w-32"></div>
        </div>
        <div class="h-3 bg-ivory-200 rounded w-48 mb-4"></div>
        <div class="grid grid-cols-4 gap-2 mb-4">
          <div v-for="j in 4" :key="j" class="h-16 bg-ivory-100 rounded-lg"></div>
        </div>
        <div class="h-2 bg-ivory-200 rounded-full mb-2"></div>
        <div class="h-2 bg-ivory-100 rounded-full w-2/3"></div>
      </div>
    </div>

    <!-- Table skeleton -->
    <div v-else-if="layout === 'table'" class="card-premium p-5 animate-pulse">
      <div class="h-4 bg-ivory-200 rounded w-1/4 mb-6"></div>
      <div class="space-y-3">
        <div v-for="i in count" :key="i" class="flex items-center gap-4">
          <div class="h-4 w-12 bg-ivory-200 rounded"></div>
          <div class="h-4 w-32 bg-ivory-100 rounded"></div>
          <div class="h-4 w-24 bg-ivory-100 rounded"></div>
          <div class="h-4 w-20 bg-ivory-100 rounded"></div>
          <div class="h-4 w-16 bg-ivory-100 rounded ml-auto"></div>
        </div>
      </div>
    </div>

    <!-- Detail skeleton -->
    <div v-else-if="layout === 'detail'" class="space-y-4 animate-pulse">
      <div class="h-8 w-64 bg-ivory-200 rounded-lg"></div>
      <div class="card-premium p-6">
        <div class="grid grid-cols-3 gap-4 mb-6">
          <div v-for="i in 3" :key="i" class="h-20 bg-ivory-100 rounded-xl"></div>
        </div>
        <div class="space-y-3">
          <div v-for="i in count" :key="i" class="h-4 bg-ivory-100 rounded w-full"></div>
        </div>
      </div>
    </div>

    <!-- Generic lines -->
    <div v-else class="space-y-3 animate-pulse">
      <div v-for="i in count" :key="i" class="h-4 bg-ivory-100 rounded" :style="{ width: (60 + (i * 7) % 30) + '%' }"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  layout: { type: String, default: 'lines' }, // lines | cards | table | detail
  count: { type: Number, default: 6 },
})
</script>
