<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 class="text-2xl font-bold text-navy-900">العقارات</h1>
          <p class="text-sm text-navy-400 mt-1">إدارة العقارات والطوابق والوحدات في مكان واحد</p>
        </div>
        <div class="flex items-center gap-3">
          <button class="btn-premium btn-outline text-sm" @click="showInactive = !showInactive">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
            {{ showInactive ? 'إخفاء المعطلة' : 'إظهار المعطلة' }}
          </button>
          <button class="btn-premium btn-gold" @click="showBuildingModal = true">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            إضافة عقار
          </button>
        </div>
      </div>

      <!-- Loading skeleton -->
      <PageSkeleton v-if="loading" layout="cards" :count="6" />

      <!-- Empty state -->
      <EmptyState v-else-if="filteredBuildings.length === 0" title="لا توجد عقارات" description="لم يتم إضافة أي عقارات بعد.">
        <template #action>
          <button class="btn-premium btn-gold" @click="showBuildingModal = true">+ إضافة عقار</button>
        </template>
      </EmptyState>

      <!-- Cards grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-3 gap-5 animate-fade-in">
        <BuildingCard
          v-for="building in filteredBuildings"
          :key="building.name"
          :building="building"
          :currency="currency"
          @view="router.push({ name: 'BuildingDetail', params: { id: building.name } })"
          @toggle-active="(val) => toggleActive(building, val)"
          @delete="confirmDelete(building)"
        />
      </div>

      <BuildingFormModal v-if="showBuildingModal" @close="showBuildingModal = false" @saved="handleSaved" />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeRequest } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageSkeleton from '@/components/ui/PageSkeleton.vue'
import BuildingCard from '@/components/buildings/BuildingCard.vue'
import BuildingFormModal from '@/components/buildings/BuildingFormModal.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const buildings = ref([])
const loading = ref(true)
const showBuildingModal = ref(false)
const showInactive = ref(false)

const filteredBuildings = computed(() => {
  if (showInactive.value) return buildings.value
  return buildings.value.filter(b => b.is_active)
})

async function fetchBuildings() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.property.get_buildings', { include_inactive: 1, limit: 100 })
    buildings.value = res.buildings || []
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function toggleActive(building, value) {
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.toggle_building_active',
      method: 'POST',
      params: { name: building.name, is_active: value ? 1 : 0 },
    })
    toast.success(value ? 'تم تفعيل العقار' : 'تم تعطيل العقار')
    fetchBuildings()
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function confirmDelete(building) {
  const ok = await confirm({
    title: 'حذف العقار',
    message: 'سيتم حذف العقار نهائيًا مع جميع بياناته. لا يمكن التراجع عن هذا الإجراء.',
    variant: 'danger',
  })
  if (!ok) return
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.delete_building',
      method: 'POST',
      params: { name: building.name },
    })
    toast.success('تم حذف العقار')
    fetchBuildings()
  } catch (e) {
    toast.error(extractError(e))
  }
}

function handleSaved() {
  showBuildingModal.value = false
  fetchBuildings()
}

onMounted(fetchBuildings)
</script>
