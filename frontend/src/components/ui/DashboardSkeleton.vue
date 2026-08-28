<template>
  <div class="space-y-6 animate-fade-in">
    <!-- Header skeleton -->
    <div class="flex items-center justify-between">
      <div class="space-y-2">
        <div class="h-8 w-48 bg-ivory-200 rounded-lg animate-pulse"></div>
        <div class="h-4 w-64 bg-ivory-100 rounded animate-pulse"></div>
      </div>
      <div class="flex gap-2">
        <div class="h-[42px] w-36 bg-ivory-200 rounded-[10px] animate-pulse"></div>
        <div class="h-[42px] w-28 bg-ivory-100 rounded-[10px] animate-pulse"></div>
        <div class="h-[42px] w-24 bg-ivory-100 rounded-[10px] animate-pulse"></div>
        <div class="h-[42px] w-24 bg-ivory-100 rounded-[10px] animate-pulse"></div>
      </div>
    </div>

    <!-- KPI strip skeleton (4 cards) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px rounded-[14px] border border-ivory-300 bg-ivory-200 overflow-hidden">
      <div v-for="i in 4" :key="'kpi' + i" class="bg-white p-5 sm:p-6 animate-pulse">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 space-y-3">
            <div class="h-4 w-24 bg-ivory-200 rounded"></div>
            <div class="h-8 w-20 bg-ivory-100 rounded"></div>
            <div class="h-3 w-16 bg-ivory-100 rounded"></div>
          </div>
          <div class="h-5 w-5 bg-ivory-200 rounded"></div>
        </div>
      </div>
    </div>

    <!-- Secondary stats strip skeleton -->
    <div class="rounded-[14px] border border-ivory-300 bg-white px-4 py-5 sm:px-6 animate-pulse">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-7">
        <div v-for="i in 7" :key="'ss' + i" class="flex items-center gap-2.5">
          <div class="h-[18px] w-[18px] bg-ivory-200 rounded"></div>
          <div class="space-y-1.5">
            <div class="h-3 w-14 bg-ivory-100 rounded"></div>
            <div class="h-5 w-8 bg-ivory-200 rounded"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts skeleton -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div class="card-premium p-5 lg:col-span-2 animate-pulse">
        <div class="h-5 w-32 bg-ivory-200 rounded mb-2"></div>
        <div class="h-4 w-56 bg-ivory-100 rounded mb-6"></div>
        <div class="space-y-3">
          <div class="h-3 w-full bg-ivory-100 rounded"></div>
          <div class="h-3 w-3/4 bg-ivory-100 rounded"></div>
          <div class="h-3 w-5/6 bg-ivory-100 rounded"></div>
          <div class="h-3 w-2/3 bg-ivory-100 rounded"></div>
        </div>
      </div>
      <div class="card-premium p-5 animate-pulse">
        <div class="h-5 w-28 bg-ivory-200 rounded mb-2"></div>
        <div class="h-4 w-44 bg-ivory-100 rounded mb-6"></div>
        <div class="mx-auto h-32 w-32 bg-ivory-100 rounded-full"></div>
      </div>
    </div>

    <!-- Collection performance skeleton -->
    <div class="rounded-[14px] border border-ivory-300 bg-white p-4 sm:p-5 animate-pulse">
      <div class="flex items-center justify-between mb-3">
        <div class="space-y-2">
          <div class="h-5 w-28 bg-ivory-200 rounded"></div>
          <div class="h-4 w-44 bg-ivory-100 rounded"></div>
        </div>
        <div class="h-8 w-16 bg-ivory-200 rounded"></div>
      </div>
      <div class="h-2.5 w-full bg-ivory-200 rounded-full"></div>
      <div class="mt-4 grid grid-cols-3 gap-4 sm:gap-6">
        <div class="space-y-2">
          <div class="h-3 w-20 bg-ivory-100 rounded"></div>
          <div class="h-5 w-16 bg-ivory-200 rounded"></div>
        </div>
        <div class="space-y-2 text-center">
          <div class="h-3 w-12 mx-auto bg-ivory-100 rounded"></div>
          <div class="h-5 w-16 mx-auto bg-ivory-200 rounded"></div>
        </div>
        <div class="space-y-2 text-left">
          <div class="h-3 w-16 ml-auto bg-ivory-100 rounded"></div>
          <div class="h-5 w-16 ml-auto bg-ivory-200 rounded"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
