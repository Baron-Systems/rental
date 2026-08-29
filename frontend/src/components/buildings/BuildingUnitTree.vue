<template>
  <div class="space-y-3">
    <!-- Floors -->
    <Card v-for="floor in floors" :key="floor.name" padding="none">
      <div class="flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-gold-50/30 transition-colors" @click="toggleFloor(floor.name)">
        <div class="flex items-center gap-3">
          <svg class="w-4 h-4 text-navy-400 transition-transform" :class="{ 'rotate-90': expanded.has(floor.name) }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          <span class="font-bold text-navy-800">{{ floor.floor_name }}</span>
          <span class="text-xs text-navy-400 bg-ivory-100 px-2 py-0.5 rounded-full">{{ unitsByFloor[floor.name]?.length || 0 }} وحدة</span>
        </div>
        <div class="flex items-center gap-1" @click.stop>
          <button class="w-7 h-7 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="إضافة وحدة" @click="$emit('add-unit-to-floor', floor)">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          </button>
          <button class="w-7 h-7 rounded-lg flex items-center justify-center text-red-500 hover:bg-red-50 transition-colors" title="حذف" @click="$emit('delete-floor', floor)">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
      </div>
      <div v-if="expanded.has(floor.name)" class="border-t border-ivory-300/40">
        <div v-if="!unitsByFloor[floor.name]?.length" class="text-center py-6 text-navy-400 text-xs">لا توجد وحدات في هذا الطابق</div>
        <div v-else class="divide-y divide-ivory-200/40">
          <div
            v-for="unit in unitsByFloor[floor.name]" :key="unit.name"
            class="flex items-center justify-between px-5 py-3 hover:bg-gold-50/20 cursor-pointer transition-colors"
            :class="{ 'opacity-60 bg-ivory-50/50': !unit.is_active }"
            @click="$emit('unit-click', unit)"
          >
            <div class="flex items-center gap-3">
              <span class="w-2 h-2 rounded-full" :class="statusDot(unit)"></span>
              <span class="text-sm font-medium text-navy-800">{{ unit.unit_number }}</span>
              <span class="text-xs text-navy-400">{{ unitTypeLabel(unit.unit_type) }}</span>
              <StatusBadge v-if="!unit.is_active" status="inactive" />
            </div>
            <StatusBadge :status="unit.status || 'empty'" />
          </div>
        </div>
      </div>
    </Card>

    <!-- Units without floor -->
    <Card v-if="unitsWithoutFloor.length > 0" padding="none">
      <div class="flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-gold-50/30 transition-colors" @click="toggleFloor('__none')">
        <div class="flex items-center gap-3">
          <svg class="w-4 h-4 text-navy-400 transition-transform" :class="{ 'rotate-90': expanded.has('__none') }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          <span class="font-bold text-navy-800">وحدات بدون طابق</span>
          <span class="text-xs text-navy-400 bg-ivory-100 px-2 py-0.5 rounded-full">{{ unitsWithoutFloor.length }} وحدة</span>
        </div>
      </div>
      <div v-if="expanded.has('__none')" class="border-t border-ivory-300/40">
        <div class="divide-y divide-ivory-200/40">
          <div
            v-for="unit in unitsWithoutFloor" :key="unit.name"
            class="flex items-center justify-between px-5 py-3 hover:bg-gold-50/20 cursor-pointer transition-colors"
            :class="{ 'opacity-60 bg-ivory-50/50': !unit.is_active }"
            @click="$emit('unit-click', unit)"
          >
            <div class="flex items-center gap-3">
              <span class="w-2 h-2 rounded-full" :class="statusDot(unit)"></span>
              <span class="text-sm font-medium text-navy-800">{{ unit.unit_number }}</span>
              <span class="text-xs text-navy-400">{{ unitTypeLabel(unit.unit_type) }}</span>
              <StatusBadge v-if="!unit.is_active" status="inactive" />
            </div>
            <StatusBadge :status="unit.status || 'empty'" />
          </div>
        </div>
      </div>
    </Card>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import Card from '@/components/ui/Card.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  floors: { type: Array, default: () => [] },
  units: { type: Array, default: () => [] },
})
defineEmits(['unit-click', 'add-unit-to-floor', 'delete-floor'])

const expanded = reactive(new Set())

const unitTypeLabels = {
  apartment: 'شقة', shop: 'محل', office: 'مكتب', warehouse: 'مستودع',
  room: 'غرفة', garage: 'كراج', independent: 'عقار مستقل', other: 'أخرى',
}
function unitTypeLabel(type) { return unitTypeLabels[type] || type || '' }

const unitsByFloor = computed(() => {
  const map = {}
  for (const u of props.units) {
    // Source: page.tsx:327 — floor is an object {id, name}, use .id as key
    const key = u.floor?.id || u.floor || '__none'
    if (!map[key]) map[key] = []
    map[key].push(u)
  }
  for (const key in map) {
    map[key].sort((a, b) => (a.unit_number || '').localeCompare(b.unit_number || ''))
  }
  return map
})

const unitsWithoutFloor = computed(() => unitsByFloor.value['__none'] || [])

function statusDot(unit) {
  if (!unit.is_active) return 'bg-gray-400'
  const map = { empty: 'bg-gray-400', rented: 'bg-emerald-500', reserved: 'bg-amber-500', unavailable: 'bg-red-500' }
  return map[unit.status] || 'bg-gray-400'
}

function toggleFloor(name) {
  if (expanded.has(name)) expanded.delete(name)
  else expanded.add(name)
}

// Expand all floors by default (source: page.tsx:272 — new Set(building.floors.map(f => f.id)))
watch(() => props.floors, (floors) => {
  if (floors.length > 0 && expanded.size === 0) {
    for (const f of floors) {
      expanded.add(f.name)
    }
  }
}, { immediate: true })
</script>
