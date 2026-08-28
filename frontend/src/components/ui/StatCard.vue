<template>
  <div class="card-premium p-5 relative overflow-hidden">
    <!-- Decorative gradient corner -->
    <div class="absolute -top-8 -left-8 w-24 h-24 rounded-full opacity-[0.06]" :class="bgGradient"></div>

    <div class="relative flex items-start justify-between">
      <div class="flex-1">
        <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">{{ label }}</p>
        <p class="text-3xl font-bold text-navy-800 tracking-tight tabular-nums">
          {{ formattedValue }}
        </p>
        <p v-if="sub" class="text-xs text-navy-400 mt-1.5 font-medium">{{ sub }}</p>
      </div>
      <div class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0" :class="iconBg">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" :d="iconPath"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], required: true },
  sub: { type: String, default: '' },
  icon: { type: String, default: 'file' },
  color: { type: String, default: 'navy' }, // navy, gold, green, amber, red, blue
})

const colorMap = {
  navy: { bg: 'bg-navy-600', iconBg: 'bg-navy-50 text-navy-600', gradient: 'bg-navy-500' },
  gold: { bg: 'bg-gold-500', iconBg: 'bg-gold-50 text-gold-600', gradient: 'bg-gold-400' },
  green: { bg: 'bg-emerald-500', iconBg: 'bg-emerald-50 text-emerald-600', gradient: 'bg-emerald-400' },
  amber: { bg: 'bg-amber-500', iconBg: 'bg-amber-50 text-amber-600', gradient: 'bg-amber-400' },
  red: { bg: 'bg-red-500', iconBg: 'bg-red-50 text-red-600', gradient: 'bg-red-400' },
  blue: { bg: 'bg-blue-500', iconBg: 'bg-blue-50 text-blue-600', gradient: 'bg-blue-400' },
  muted: { bg: 'bg-slate-400', iconBg: 'bg-slate-100 text-slate-500', gradient: 'bg-slate-300' },
}

const c = computed(() => colorMap[props.color] || colorMap.navy)
const bgGradient = computed(() => c.value.gradient)
const iconBg = computed(() => c.value.iconBg)

const iconPaths = {
  file: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  receipt: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  banknote: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  alert: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  users: 'M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-1.13a4 4 0 10-8 0 4 4 0 008 0zm6 0a4 4 0 11-8 0 4 4 0 018 0z',
  building: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4',
  chart: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  calendar: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
  wallet: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z',
  card: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z',
  trend: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
}

const iconPath = computed(() => iconPaths[props.icon] || iconPaths.file)

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString('en-US')
  }
  return props.value
})
</script>
