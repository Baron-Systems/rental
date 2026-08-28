<template>
  <div
    class="card-premium p-5 group"
    :class="{ 'opacity-60 bg-ivory-50/50': !building.is_active }"
  >
    <!-- Header -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex items-center gap-3 cursor-pointer" @click="$emit('view')">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center bg-navy-50 text-navy-600 group-hover:bg-gold-50 group-hover:text-gold-600 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
        </div>
        <h3 class="text-base font-bold text-navy-800 group-hover:text-gold-600 transition-colors">{{ building.building_name }}</h3>
      </div>
      <StatusBadge v-if="!building.is_active" status="inactive" />
    </div>

    <!-- Address -->
    <p v-if="building.address" class="text-sm text-navy-400 mb-4 flex items-center gap-1.5">
      <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
      {{ building.address }}
    </p>

    <!-- Status counts -->
    <div class="grid grid-cols-4 gap-2 mb-4">
      <div class="text-center bg-ivory-50 rounded-lg py-2.5 px-1">
        <p class="text-xs text-navy-400 mb-0.5">الطوابق</p>
        <p class="text-lg font-bold text-navy-800 tabular-nums">{{ building.floors_count || 0 }}</p>
      </div>
      <div class="text-center bg-emerald-50/60 rounded-lg py-2.5 px-1">
        <p class="text-xs text-navy-400 mb-0.5">مؤجرة</p>
        <p class="text-lg font-bold text-emerald-600 tabular-nums">{{ building.rented_units || 0 }}</p>
      </div>
      <div class="text-center bg-gray-50 rounded-lg py-2.5 px-1">
        <p class="text-xs text-navy-400 mb-0.5">فارغة</p>
        <p class="text-lg font-bold text-gray-500 tabular-nums">{{ building.empty_units || 0 }}</p>
      </div>
      <div class="text-center bg-amber-50/60 rounded-lg py-2.5 px-1">
        <p class="text-xs text-navy-400 mb-0.5">محجوزة</p>
        <p class="text-lg font-bold text-amber-600 tabular-nums">{{ building.reserved_units || 0 }}</p>
      </div>
    </div>

    <!-- Financial row -->
    <div class="grid grid-cols-3 gap-2 mb-4">
      <div class="text-center">
        <p class="text-xs text-navy-400 mb-0.5">المستحقات</p>
        <p class="text-sm font-bold text-navy-700 tabular-nums">{{ formatMoney(building.total_dues, currency) }}</p>
      </div>
      <div class="text-center">
        <p class="text-xs text-navy-400 mb-0.5">التحصيلات</p>
        <p class="text-sm font-bold text-emerald-600 tabular-nums">{{ formatMoney(building.total_receipts, currency) }}</p>
      </div>
      <div class="text-center">
        <p class="text-xs text-navy-400 mb-0.5">الرصيد</p>
        <p class="text-sm font-bold tabular-nums" :class="(building.balance_due || 0) > 0 ? 'text-red-600' : 'text-emerald-600'">{{ formatMoney(building.balance_due, currency) }}</p>
      </div>
    </div>

    <!-- Occupancy bar -->
    <div class="mb-4">
      <div class="flex items-center justify-between mb-1.5">
        <span class="text-xs text-navy-400">نسبة الإشغال</span>
        <span class="text-xs font-bold text-navy-700 tabular-nums">{{ occupancyRate }}%</span>
      </div>
      <div class="h-2 bg-ivory-200 rounded-full overflow-hidden">
        <div class="h-full bg-gradient-to-r from-gold-400 to-gold-600 rounded-full transition-all duration-500" :style="{ width: occupancyRate + '%' }"></div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-1 pt-3 border-t border-ivory-300/40">
      <button class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="عرض" @click="$emit('view')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
      </button>
      <button v-if="building.is_active" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-amber-50 hover:text-amber-600 transition-colors" title="تعطيل" @click="$emit('toggle-active', false)">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M18.363 18.363A9 9 0 005.637 5.637m12.726 12.726A9 9 0 015.637 5.637m12.726 12.726L5.637 5.637"/></svg>
      </button>
      <button v-else class="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-500 hover:bg-emerald-50 hover:text-emerald-600 transition-colors" title="تفعيل" @click="$emit('toggle-active', true)">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
      </button>
      <button class="w-8 h-8 rounded-lg flex items-center justify-center text-red-500 hover:bg-red-50 transition-colors" title="حذف نهائي" @click="$emit('delete')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatMoney } from '@/composables/useApi'

const props = defineProps({
  building: { type: Object, required: true },
  currency: { type: String, default: 'ILS' },
})
defineEmits(['view', 'toggle-active', 'delete'])

const occupancyRate = computed(() => {
  const total = (props.building.rented_units || 0) + (props.building.empty_units || 0) + (props.building.reserved_units || 0)
  if (total === 0) return 0
  return Math.round(((props.building.rented_units || 0) / total) * 100)
})
</script>
