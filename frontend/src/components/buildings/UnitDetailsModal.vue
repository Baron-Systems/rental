<template>
  <Modal :model-value="true" title="تفاصيل الوحدة" size="md" @update:model-value="$emit('close')">
    <div v-if="loading" class="flex items-center justify-center py-8">
      <div class="w-6 h-6 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <div v-else class="space-y-4">
      <!-- Hero -->
      <div class="text-center space-y-1.5">
        <div class="inline-flex items-center justify-center h-12 w-12 rounded-xl mb-1" :class="statusIconBg">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
        </div>
        <div class="text-xl font-bold text-navy-900 tracking-tight">{{ unit.unit_number }}</div>
        <div class="flex items-center justify-center gap-2 flex-wrap">
          <StatusBadge :status="unit.status || 'empty'" />
          <StatusBadge v-if="!unit.is_active" status="inactive" />
        </div>
      </div>

      <!-- Core Info Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <div class="bg-ivory-50 rounded-lg p-2.5">
          <p class="text-xs text-navy-400 mb-1">النوع</p>
          <p class="text-sm font-semibold text-navy-800">{{ unitTypeLabel }}</p>
        </div>
        <div class="bg-ivory-50 rounded-lg p-2.5">
          <p class="text-xs text-navy-400 mb-1">المساحة</p>
          <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ unit.area ? `${unit.area} م²` : '—' }}</p>
        </div>
      </div>

      <!-- Dynamic Attributes -->
      <div v-if="displayAttributes.length" class="space-y-2">
        <p class="text-xs font-semibold text-navy-400">الخصائص</p>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <div v-for="attr in displayAttributes" :key="attr.attribute" class="bg-ivory-50 rounded-lg p-2.5">
            <p class="text-xs text-navy-400 mb-1">{{ attr.attribute_name }}</p>
            <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ formatAttributeValue(attr) }}</p>
          </div>
        </div>
      </div>

      <!-- Meter Fields (conditional) -->
      <div v-if="hasElectricityMeter || hasWaterMeter" class="space-y-2">
        <p class="text-xs font-semibold text-navy-400">العدادات</p>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <div v-if="hasElectricityMeter" class="bg-ivory-50 rounded-lg p-2.5">
            <p class="text-xs text-navy-400 mb-1">رقم عداد الكهرباء</p>
            <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ unitData.electricity_meter_number || '—' }}</p>
          </div>
          <div v-if="hasElectricityMeter" class="bg-ivory-50 rounded-lg p-2.5">
            <p class="text-xs text-navy-400 mb-1">آخر قراءة كهرباء</p>
            <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ unitData.current_electricity_meter_reading || '—' }}</p>
          </div>
          <div v-if="hasWaterMeter" class="bg-ivory-50 rounded-lg p-2.5">
            <p class="text-xs text-navy-400 mb-1">رقم عداد المياه</p>
            <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ unitData.water_meter_number || '—' }}</p>
          </div>
          <div v-if="hasWaterMeter" class="bg-ivory-50 rounded-lg p-2.5">
            <p class="text-xs text-navy-400 mb-1">آخر قراءة مياه</p>
            <p class="text-sm font-semibold text-navy-800 tabular-nums">{{ unitData.current_water_meter_reading || '—' }}</p>
          </div>
        </div>
      </div>

      <!-- Current Contract -->
      <div v-if="currentContract" class="bg-emerald-50/60 border border-emerald-200/60 rounded-xl p-3.5 space-y-1.5">
        <div class="flex items-center gap-2">
          <span class="w-6 h-6 rounded-md bg-emerald-100 flex items-center justify-center">
            <svg class="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
          </span>
          <span class="text-xs font-bold text-emerald-700">المستأجر الحالي</span>
        </div>
        <p class="text-sm font-semibold text-navy-800 mr-8">{{ currentContractTenantName }}</p>
        <p class="text-xs text-navy-400 mr-8 flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          نهاية العقد: {{ formatDate(currentContract.end_date) }}
        </p>
      </div>

      <!-- Upcoming Contract -->
      <div v-if="upcomingContract" class="bg-gold-50/60 border border-gold-200/60 rounded-xl p-3.5 space-y-1.5">
        <div class="flex items-center gap-2">
          <span class="w-6 h-6 rounded-md bg-gold-100 flex items-center justify-center">
            <svg class="w-3.5 h-3.5 text-gold-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          </span>
          <span class="text-xs font-bold text-gold-700">المستأجر القادم</span>
        </div>
        <p class="text-sm font-semibold text-navy-800 mr-8">{{ upcomingContractTenantName }}</p>
        <p class="text-xs text-navy-400 mr-8 flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          بداية العقد: {{ formatDate(upcomingContract.start_date) }}
        </p>
      </div>

      <!-- Notes -->
      <div v-if="unit.notes" class="bg-ivory-50 rounded-lg p-3">
        <p class="text-xs text-navy-400 mb-1">ملاحظات</p>
        <p class="text-sm text-navy-700 leading-relaxed">{{ unit.notes }}</p>
      </div>
    </div>

    <template #footer>
      <div v-if="!loading" class="flex flex-wrap gap-2.5 w-full">
        <button v-if="permissions.can_edit" class="btn-premium btn-gold text-sm flex-1" @click="$emit('edit', unit)">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
          تعديل
        </button>
        <button v-if="unit.is_active && permissions.can_disable" class="btn-premium btn-outline text-sm flex-1" @click="$emit('toggle-active', unit)">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M18.363 18.363A9 9 0 005.637 5.637m12.726 12.726A9 9 0 015.637 5.637m12.726 12.726L5.637 5.637"/></svg>
          تعطيل
        </button>
        <button v-if="!unit.is_active && permissions.can_reactivate" class="btn-premium btn-outline text-sm flex-1" @click="$emit('toggle-active', unit)">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          تفعيل
        </button>
        <button v-if="permissions.can_delete" class="btn-premium btn-outline text-sm text-red-600 hover:bg-red-50 flex-1" @click="$emit('delete', unit)">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          حذف نهائي
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { callApi } from '@/composables/useApi'
import Modal from '@/components/ui/Modal.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  unit: { type: Object, required: true },
  buildingName: { type: String, default: '' },
  floors: { type: Array, default: () => [] },
})
defineEmits(['close', 'edit', 'toggle-active', 'delete'])

const loading = ref(true)
const permissions = ref({})
const unitData = ref({})
const typeAttributes = ref([])
const attributeValues = ref({})

const unitTypeLabel = computed(() => unitData.value.unit_type_name || '')

const statusIconBg = computed(() => {
  const map = {
    empty: 'bg-ivory-100 text-navy-400',
    rented: 'bg-emerald-50 text-emerald-600',
    reserved: 'bg-amber-50 text-amber-600',
    unavailable: 'bg-red-50 text-red-600',
  }
  return map[props.unit.status] || 'bg-ivory-100 text-navy-400'
})

// Meter capability checks
const hasElectricityMeter = computed(() => {
  // Check if electricity_meter attribute exists in type attributes AND its value is true
  const elecAttr = typeAttributes.value.find(a => a.capability_code === 'electricity_meter')
  if (!elecAttr) return false
  const val = attributeValues.value[elecAttr.attribute]
  return val === true || val === 1
})

const hasWaterMeter = computed(() => {
  const waterAttr = typeAttributes.value.find(a => a.capability_code === 'water_meter')
  if (!waterAttr) return false
  const val = attributeValues.value[waterAttr.attribute]
  return val === true || val === 1
})

// Display attributes (exclude meter capabilities — they're shown via meter section)
const displayAttributes = computed(() => {
  return typeAttributes.value.filter(a => !a.capability_code)
})

// Format attribute value for display
function formatAttributeValue(attr) {
  const val = attributeValues.value[attr.attribute]
  if (val === null || val === undefined || val === '') return '—'
  if (attr.data_type === 'Check') {
    return val ? 'نعم' : 'لا'
  }
  return String(val)
}

// Current/upcoming contracts
const today = new Date()
today.setHours(0, 0, 0, 0)

const currentContract = computed(() => {
  const contracts = props.unit.contracts || []
  return contracts.find(c => {
    const s = new Date(c.start_date); s.setHours(0, 0, 0, 0)
    const e = new Date(c.end_date); e.setHours(0, 0, 0, 0)
    return c.status === 'active' && s <= today && e >= today
  })
})

const upcomingContract = computed(() => {
  const contracts = props.unit.contracts || []
  return contracts.find(c => {
    const s = new Date(c.start_date); s.setHours(0, 0, 0, 0)
    return c.status === 'active' && s > today
  })
})

const currentContractTenantName = computed(() => {
  const c = currentContract.value
  if (!c) return ''
  return (c.tenant && c.tenant.full_name) || c.tenant_name || ''
})

const upcomingContractTenantName = computed(() => {
  const c = upcomingContract.value
  if (!c) return ''
  return (c.tenant && c.tenant.full_name) || c.tenant_name || ''
})

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${day}/${m}/${y}`
}

onMounted(async () => {
  try {
    // Fetch permissions
    const permRes = await frappeRequest({
      url: '/api/method/rental.rental.api.property.get_unit_permissions',
      params: { name: props.unit.name },
    })
    permissions.value = permRes?.message || permRes || {}

    // Fetch full unit data with attribute values
    const res = await callApi('rental.rental.api.property.get_unit', { name: props.unit.name })
    unitData.value = res
    typeAttributes.value = res.type_attributes || []

    // Extract attribute values (preserving 0, false correctly)
    const vals = {}
    if (res.attribute_values) {
      for (const [k, v] of Object.entries(res.attribute_values)) {
        vals[k] = v.value
      }
    }
    attributeValues.value = vals
  } catch {
    permissions.value = { can_edit: true, can_delete: false, can_disable: false, can_reactivate: false }
  } finally {
    loading.value = false
  }
})
</script>
