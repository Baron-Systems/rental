<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 class="text-2xl font-bold text-navy-900">الطوابق</h1>
          <p class="text-sm text-navy-400 mt-1">إدارة طوابق العقارات</p>
        </div>
        <button class="btn-premium btn-gold" @click="router.push({ name: 'FloorNew' })">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          طابق جديد
        </button>
      </div>

      <!-- Search -->
      <Card padding="md" class="mb-4">
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input v-model="search" type="text" placeholder="بحث بالاسم أو العقار..." class="input-premium pr-10" @input="debouncedFetch" />
        </div>
      </Card>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 5" :key="i" class="h-14 bg-ivory-100 rounded-xl animate-pulse"></div>
      </div>

      <!-- Empty state -->
      <EmptyState v-else-if="filteredFloors.length === 0" title="لا توجد طوابق" description="لم يتم العثور على طوابق مطابقة.">
        <template #action>
          <button class="btn-premium btn-gold" @click="router.push({ name: 'FloorNew' })">+ طابق جديد</button>
        </template>
      </EmptyState>

      <!-- Table -->
      <Card v-else padding="none">
        <DataTable :columns="columns">
          <TableRow v-for="f in filteredFloors" :key="f.name">
            <TableCell><span class="font-semibold text-navy-800">{{ f.floor_name }}</span></TableCell>
            <TableCell>
              <router-link v-if="f.building" :to="{ name: 'BuildingDetail', params: { id: f.building } }" class="text-navy-600 hover:text-gold-600">{{ f.building_name || f.building }}</router-link>
              <span v-else>—</span>
            </TableCell>
            <TableCell><span class="tabular-nums text-navy-600">{{ f.sort_order || 0 }}</span></TableCell>
          </TableRow>
        </DataTable>
        <div class="border-t border-ivory-300/40 px-4 py-3 text-xs text-navy-400">إجمالي: {{ filteredFloors.length }} طابق</div>
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const toast = useToast()

const columns = [
  { key: 'name', label: 'الاسم' },
  { key: 'building', label: 'العقار' },
  { key: 'sort', label: 'الترتيب' },
]

const floors = ref([])
const loading = ref(true)
const search = ref('')

const filteredFloors = computed(() => {
  if (!search.value) return floors.value
  const q = search.value.toLowerCase()
  return floors.value.filter(f =>
    (f.floor_name || '').toLowerCase().includes(q) ||
    (f.building_name || f.building || '').toLowerCase().includes(q)
  )
})

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchFloors, 400)
}

async function fetchFloors() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.property.get_floors', { limit: 100 })
    floors.value = res.floors || res || []
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

onMounted(fetchFloors)
</script>
