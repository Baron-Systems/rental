<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <!-- Loading skeleton -->
      <PageSkeleton v-if="loading" layout="detail" :count="5" />

      <!-- Error state -->
      <div v-else-if="!building" class="text-center py-20">
        <div class="inline-flex w-16 h-16 rounded-2xl items-center justify-center mb-4 bg-red-50">
          <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </div>
        <p class="text-navy-400 mb-4">العقار غير موجود</p>
        <button class="btn-premium btn-outline" @click="router.push({ name: 'Buildings' })">العودة للقائمة</button>
      </div>

      <div v-else class="animate-fade-in">
        <!-- Hero header -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div class="flex items-center gap-3 mb-1">
              <div class="w-10 h-10 rounded-xl flex items-center justify-center bg-navy-50 text-navy-600">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
              </div>
              <h1 class="text-2xl font-bold text-navy-900">{{ building.building_name }}</h1>
              <StatusBadge v-if="!building.is_active" status="inactive" />
            </div>
            <p v-if="building.owner_name" class="text-sm text-navy-500 mb-0.5">المالك: {{ building.owner_name }}</p>
            <p v-if="building.address" class="text-sm text-navy-400 flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
              {{ building.address }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn-premium btn-outline text-sm" @click="toggleBuildingActive">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path v-if="building.is_active" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M18.363 18.363A9 9 0 005.637 5.637m12.726 12.726A9 9 0 015.637 5.637m12.726 12.726L5.637 5.637"/><path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              {{ building.is_active ? 'تعطيل' : 'تفعيل' }}
            </button>
            <button class="btn-premium btn-outline text-sm text-red-600 hover:bg-red-50" @click="confirmDeleteBuilding">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              حذف
            </button>
          </div>
        </div>

        <!-- Back link -->
        <div class="mb-4">
          <router-link :to="{ name: 'Buildings' }" class="text-sm text-navy-400 hover:text-gold-600 transition-colors flex items-center gap-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
            العقارات
          </router-link>
        </div>

        <!-- Tabs -->
        <div class="flex items-center gap-1 border-b border-ivory-300/60 mb-6 overflow-x-auto">
          <button
            v-for="tab in tabs" :key="tab.key"
            class="px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors"
            :class="activeTab === tab.key ? 'border-gold-500 text-gold-600' : 'border-transparent text-navy-400 hover:text-navy-600'"
            @click="activeTab = tab.key"
          >{{ tab.label }}</button>
        </div>

        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="space-y-6">
          <!-- KPI cards -->
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الطوابق</p>
              <p class="text-2xl font-bold text-navy-800 tabular-nums">{{ building.floors_count || 0 }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الوحدات</p>
              <p class="text-2xl font-bold text-navy-800 tabular-nums">{{ activeUnitsCount }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">مؤجرة</p>
              <p class="text-2xl font-bold text-emerald-600 tabular-nums">{{ rentedCount }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">فارغة</p>
              <p class="text-2xl font-bold text-gray-500 tabular-nums">{{ emptyCount }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">محجوزة</p>
              <p class="text-2xl font-bold text-amber-600 tabular-nums">{{ reservedCount }}</p>
            </Card>
          </div>

          <!-- Financial cards -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">المستحقات</p>
              <p class="text-xl font-bold text-navy-700 tabular-nums">{{ formatMoney(building.total_dues, currency) }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">إجمالي التحصيلات</p>
              <p class="text-xl font-bold text-emerald-600 tabular-nums">{{ formatMoney(building.total_receipts, currency) }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الرصيد</p>
              <p class="text-xl font-bold tabular-nums" :class="(building.balance_due || 0) > 0 ? 'text-red-600' : 'text-emerald-600'">{{ formatMoney(building.balance_due, currency) }}</p>
            </Card>
          </div>

          <!-- Occupancy bar -->
          <Card padding="md">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-navy-700">نسبة الإشغال</span>
              <span class="text-sm font-bold text-gold-600 tabular-nums">{{ occupancyRate }}%</span>
            </div>
            <div class="h-3 bg-ivory-200 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-gold-400 to-gold-600 rounded-full transition-all duration-500" :style="{ width: occupancyRate + '%' }"></div>
            </div>
          </Card>
        </div>

        <!-- Floors & Units Tab -->
        <div v-if="activeTab === 'floors'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-bold text-navy-800">شجرة العقار</h2>
            <div class="flex gap-2">
              <button class="btn-premium btn-outline text-sm" @click="addUnit()">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                إضافة وحدة
              </button>
              <button class="btn-premium btn-outline text-sm" @click="showFloorModal = true">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                إضافة طابق
              </button>
            </div>
          </div>

          <!-- Floor tree -->
          <div v-if="floors.length === 0 && unitsWithoutFloor.length === 0" class="text-center py-16">
            <p class="text-navy-400 text-sm mb-4">لا توجد طوابق أو وحدات</p>
            <button class="btn-premium btn-gold" @click="showFloorModal = true">+ إضافة طابق</button>
          </div>

          <BuildingUnitTree
            v-else
            :floors="floors"
            :units="units"
            @unit-click="openUnitDetails"
            @add-unit-to-floor="addUnitToFloor"
            @delete-floor="deleteFloor"
          />
        </div>

        <!-- Tenants Tab -->
        <div v-if="activeTab === 'tenants'">
          <Card padding="none">
            <div v-if="tenants.length === 0" class="text-center py-16 text-navy-400 text-sm">لا يوجد مستأجرون مسجلون في هذا المبنى.</div>
            <DataTable v-else :columns="tenantColumns">
              <TableRow v-for="t in tenants" :key="t.name">
                <TableCell>
                  <router-link :to="{ name: 'TenantDetail', params: { id: t.name } }" class="font-semibold text-navy-800 hover:text-gold-600">{{ t.full_name }}</router-link>
                </TableCell>
                <TableCell>{{ t.phone || '—' }}</TableCell>
                <TableCell>{{ t.unit_number || '—' }}</TableCell>
                <TableCell><StatusBadge :status="t.contract_status || '—'" /></TableCell>
              </TableRow>
            </DataTable>
          </Card>
        </div>

        <!-- Contracts Tab -->
        <div v-if="activeTab === 'contracts'" class="space-y-6">
          <div>
            <h3 class="text-sm font-bold text-navy-700 mb-3">العقود الحالية</h3>
            <Card padding="none">
              <div v-if="currentContracts.length === 0" class="text-center py-8 text-navy-400 text-sm">لا توجد عقود حالية</div>
              <DataTable v-else :columns="contractColumns">
                <TableRow v-for="c in currentContracts" :key="c.name">
                  <TableCell><router-link :to="{ name: 'ContractDetail', params: { id: c.name } }" class="font-semibold text-navy-800 hover:text-gold-600">{{ c.contract_number || c.name }}</router-link></TableCell>
                  <TableCell>{{ c.tenant_name || (c.tenant && c.tenant.full_name) || '—' }}</TableCell>
                  <TableCell>{{ (c.unit && c.unit.unit_number) || '—' }}</TableCell>
                  <TableCell>{{ formatDate(c.start_date) }}</TableCell>
                  <TableCell>{{ formatDate(c.end_date) }}</TableCell>
                  <TableCell><StatusBadge :status="c.status" /></TableCell>
                </TableRow>
              </DataTable>
            </Card>
          </div>
          <div>
            <h3 class="text-sm font-bold text-navy-700 mb-3">العقود القادمة</h3>
            <Card padding="none">
              <div v-if="upcomingContracts.length === 0" class="text-center py-8 text-navy-400 text-sm">لا توجد عقود قادمة</div>
              <DataTable v-else :columns="contractColumns">
                <TableRow v-for="c in upcomingContracts" :key="c.name">
                  <TableCell><router-link :to="{ name: 'ContractDetail', params: { id: c.name } }" class="font-semibold text-navy-800 hover:text-gold-600">{{ c.contract_number || c.name }}</router-link></TableCell>
                  <TableCell>{{ c.tenant_name || (c.tenant && c.tenant.full_name) || '—' }}</TableCell>
                  <TableCell>{{ (c.unit && c.unit.unit_number) || '—' }}</TableCell>
                  <TableCell>{{ formatDate(c.start_date) }}</TableCell>
                  <TableCell>{{ formatDate(c.end_date) }}</TableCell>
                  <TableCell><StatusBadge :status="c.status === 'active' ? 'upcoming' : c.status" /></TableCell>
                </TableRow>
              </DataTable>
            </Card>
          </div>
          <div>
            <h3 class="text-sm font-bold text-navy-700 mb-3">العقود السابقة</h3>
            <Card padding="none">
              <div v-if="pastContracts.length === 0" class="text-center py-8 text-navy-400 text-sm">لا توجد عقود سابقة</div>
              <DataTable v-else :columns="pastContractColumns">
                <TableRow v-for="c in pastContracts" :key="c.name">
                  <TableCell><router-link :to="{ name: 'ContractDetail', params: { id: c.name } }" class="font-semibold text-navy-800 hover:text-gold-600">{{ c.contract_number || c.name }}</router-link></TableCell>
                  <TableCell>{{ c.tenant_name || (c.tenant && c.tenant.full_name) || '—' }}</TableCell>
                  <TableCell>{{ (c.unit && c.unit.unit_number) || '—' }}</TableCell>
                  <TableCell><StatusBadge :status="c.status" /></TableCell>
                </TableRow>
              </DataTable>
            </Card>
          </div>
        </div>

        <!-- Statistics Tab -->
        <div v-if="activeTab === 'stats'" class="space-y-6">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">إجمالي الالتزامات</p>
              <p class="text-xl font-bold text-navy-700 tabular-nums">{{ formatMoney(building.total_dues, currency) }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">إجمالي التحصيلات</p>
              <p class="text-xl font-bold text-emerald-600 tabular-nums">{{ formatMoney(building.total_receipts, currency) }}</p>
            </Card>
            <Card padding="md">
              <p class="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-2">الرصيد المستحق</p>
              <p class="text-xl font-bold tabular-nums" :class="(building.balance_due || 0) > 0 ? 'text-red-600' : 'text-emerald-600'">{{ formatMoney(building.balance_due, currency) }}</p>
            </Card>
          </div>

          <!-- Status distribution -->
          <Card padding="md">
            <h3 class="text-sm font-bold text-navy-700 mb-4">توزيع حالات الوحدات</h3>
            <div class="space-y-3">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-navy-600">فارغة</span>
                  <span class="text-sm font-bold text-navy-800 tabular-nums">{{ emptyCount }}</span>
                </div>
                <div class="h-2 bg-ivory-200 rounded-full overflow-hidden">
                  <div class="h-full bg-gray-400 rounded-full" :style="{ width: statusPercent('empty') + '%' }"></div>
                </div>
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-navy-600">مؤجرة</span>
                  <span class="text-sm font-bold text-navy-800 tabular-nums">{{ rentedCount }}</span>
                </div>
                <div class="h-2 bg-ivory-200 rounded-full overflow-hidden">
                  <div class="h-full bg-emerald-500 rounded-full" :style="{ width: statusPercent('rented') + '%' }"></div>
                </div>
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-navy-600">محجوزة</span>
                  <span class="text-sm font-bold text-navy-800 tabular-nums">{{ reservedCount }}</span>
                </div>
                <div class="h-2 bg-ivory-200 rounded-full overflow-hidden">
                  <div class="h-full bg-amber-500 rounded-full" :style="{ width: statusPercent('reserved') + '%' }"></div>
                </div>
              </div>
            </div>
          </Card>

          <!-- Contract summary -->
          <Card padding="md">
            <h3 class="text-sm font-bold text-navy-700 mb-4">ملخص العقود</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="text-center">
                <p class="text-xs text-navy-400 mb-1">الإجمالي</p>
                <p class="text-xl font-bold text-navy-800 tabular-nums">{{ contracts.length }}</p>
              </div>
              <div class="text-center">
                <p class="text-xs text-navy-400 mb-1">نشطة</p>
                <p class="text-xl font-bold text-emerald-600 tabular-nums">{{ activeContractsCount }}</p>
              </div>
              <div class="text-center">
                <p class="text-xs text-navy-400 mb-1">منتهية</p>
                <p class="text-xl font-bold text-gray-500 tabular-nums">{{ contracts.filter(c => c.status === 'expired').length }}</p>
              </div>
              <div class="text-center">
                <p class="text-xs text-navy-400 mb-1">ملغاة</p>
                <p class="text-xl font-bold text-red-500 tabular-nums">{{ contracts.filter(c => c.status === 'cancelled').length }}</p>
              </div>
            </div>
          </Card>
        </div>

        <!-- Modals -->
        <FloorFormModal v-if="showFloorModal" :building-name="building.name" :floor-count="floors.length" @close="closeFloorModal" @saved="handleFloorSaved" />
        <UnitAddModal v-if="showUnitModal && !editingUnit" :building-name="building.name" :floors="floors" :existing-units="units" :preselected-floor="preselectedFloor" @close="closeUnitModal" @saved="handleUnitSaved" />
        <UnitEditModal v-if="showUnitModal && editingUnit" :unit="editingUnit" :floors="floors" @close="closeUnitModal" @saved="handleUnitSaved" />
        <UnitDetailsModal v-if="showUnitDetails" :unit="selectedUnit" :building-name="building.name" :floors="floors" @close="closeUnitDetails" @edit="editUnitFromDetails" @toggle-active="toggleUnitActive" @delete="deleteUnitFromDetails" />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { frappeRequest } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import PageSkeleton from '@/components/ui/PageSkeleton.vue'
import BuildingUnitTree from '@/components/buildings/BuildingUnitTree.vue'
import FloorFormModal from '@/components/buildings/FloorFormModal.vue'
import UnitAddModal from '@/components/buildings/UnitAddModal.vue'
import UnitEditModal from '@/components/buildings/UnitEditModal.vue'
import UnitDetailsModal from '@/components/buildings/UnitDetailsModal.vue'
import { callApi, formatMoney, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { getContractPeriodStatus } from '@/utils/contractUtils'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const tabs = [
  { key: 'overview', label: 'نظرة عامة' },
  { key: 'floors', label: 'الطوابق والوحدات' },
  { key: 'tenants', label: 'المستأجرون' },
  { key: 'contracts', label: 'العقود' },
  { key: 'stats', label: 'الإحصائيات' },
]

const building = ref(null)
const floors = ref([])
const units = ref([])
const contracts = ref([])
const tenants = ref([])
const loading = ref(true)
const activeTab = ref('overview')

const showFloorModal = ref(false)
const showUnitModal = ref(false)
const showUnitDetails = ref(false)
const editingUnit = ref(null)
const preselectedFloor = ref(null)
const selectedUnit = ref(null)

const tenantColumns = [
  { key: 'name', label: 'الاسم' },
  { key: 'phone', label: 'الهاتف' },
  { key: 'unit', label: 'الوحدة' },
  { key: 'status', label: 'حالة العقد' },
]

const contractColumns = [
  { key: 'number', label: 'رقم العقد' },
  { key: 'tenant', label: 'المستأجر' },
  { key: 'unit', label: 'الوحدة' },
  { key: 'start', label: 'تاريخ البداية' },
  { key: 'end', label: 'تاريخ النهاية' },
  { key: 'status', label: 'الحالة' },
]

const pastContractColumns = [
  { key: 'number', label: 'رقم العقد' },
  { key: 'tenant', label: 'المستأجر' },
  { key: 'unit', label: 'الوحدة' },
  { key: 'status', label: 'الحالة' },
]

// Computed
const activeUnits = computed(() => units.value.filter(u => u.is_active))
const activeUnitsCount = computed(() => activeUnits.value.length)
const rentedCount = computed(() => activeUnits.value.filter(u => u.status === 'rented').length)
const emptyCount = computed(() => activeUnits.value.filter(u => u.status === 'empty').length)
const reservedCount = computed(() => activeUnits.value.filter(u => u.status === 'reserved').length)

const occupancyRate = computed(() => {
  if (activeUnitsCount.value === 0) return 0
  return Math.round((rentedCount.value / activeUnitsCount.value) * 100)
})

const unitsByFloor = computed(() => {
  const map = {}
  for (const u of units.value) {
    // Source: page.tsx:327 — floor is an object {id, name}, use .id as key
    const key = u.floor?.id || u.floor || '__none'
    if (!map[key]) map[key] = []
    map[key].push(u)
  }
  // Sort each group by unit_number
  for (const key in map) {
    map[key].sort((a, b) => (a.unit_number || '').localeCompare(b.unit_number || ''))
  }
  return map
})

const unitsWithoutFloor = computed(() => unitsByFloor.value['__none'] || [])

const today = new Date()
today.setHours(0, 0, 0, 0)

// Source: page.tsx:696-709 — uses getContractPeriodStatus for classification
const currentContracts = computed(() => contracts.value.filter(c => {
  const period = getContractPeriodStatus(c.start_date, c.end_date, today)
  return ['active', 'draft'].includes(c.status) && period === 'current'
}))
const upcomingContracts = computed(() => contracts.value.filter(c => {
  const period = getContractPeriodStatus(c.start_date, c.end_date, today)
  return ['active', 'draft'].includes(c.status) && period === 'upcoming'
}))
const pastContracts = computed(() => contracts.value.filter(c => {
  const period = getContractPeriodStatus(c.start_date, c.end_date, today)
  return !['active', 'draft'].includes(c.status) || period === 'past'
}))

// Active contracts with current period (source: page.tsx:875-880)
const activeContractsCount = computed(() =>
  contracts.value.filter(c => {
    if (c.status !== 'active') return false
    return getContractPeriodStatus(c.start_date, c.end_date, today) === 'current'
  }).length
)

function statusPercent(status) {
  if (activeUnitsCount.value === 0) return 0
  const count = status === 'empty' ? emptyCount.value : status === 'rented' ? rentedCount.value : reservedCount.value
  return Math.round((count / activeUnitsCount.value) * 100)
}

function unitStatusDot(unit) {
  if (!unit.is_active) return 'bg-gray-400'
  const map = { empty: 'bg-gray-400', rented: 'bg-emerald-500', reserved: 'bg-amber-500', unavailable: 'bg-red-500' }
  return map[unit.status] || 'bg-gray-400'
}

const unitTypeLabels = {
  apartment: 'شقة', shop: 'محل', office: 'مكتب', warehouse: 'مستودع',
  room: 'غرفة', garage: 'كراج', independent: 'عقار مستقل', other: 'أخرى',
}
function unitTypeLabel(type) { return unitTypeLabels[type] || type || '' }

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${day}/${m}/${y}`
}

async function fetchBuilding() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.property.get_building', { name: route.params.id })
    building.value = res
    floors.value = res.floors || []
    // Source: page.tsx — units keep floor as {id, name} object from API
    // unitsByFloor uses u.floor?.id as key, matching floor.name (document ID)
    units.value = res.units || []
    contracts.value = res.contracts || []
    tenants.value = res.tenants || []
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function toggleBuildingActive() {
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.toggle_building_active',
      method: 'POST',
      params: { name: building.value.name, is_active: building.value.is_active ? 0 : 1 },
    })
    toast.success(building.value.is_active ? 'تم تعطيل العقار' : 'تم تفعيل العقار')
    fetchBuilding()
  } catch (e) {
    toast.error(extractError(e))
  }
}

async function confirmDeleteBuilding() {
  const ok = await confirm({
    title: 'حذف نهائي',
    message: 'سيتم حذف العقار نهائيًا. مسموح بالحذف فقط إذا لم يُستخدم العقار مطلقًا ولا توجد بيانات مرتبطة به.',
    variant: 'danger',
  })
  if (!ok) return
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.delete_building',
      method: 'POST',
      params: { name: building.value.name },
    })
    toast.success('تم حذف العقار')
    router.push({ name: 'Buildings' })
  } catch (e) {
    toast.error(extractError(e))
  }
}

function addUnit() { editingUnit.value = null; preselectedFloor.value = null; showUnitModal.value = true }
function addUnitToFloor(floor) { editingUnit.value = null; preselectedFloor.value = floor.name; showUnitModal.value = true }
function closeFloorModal() { showFloorModal.value = false }
function handleFloorSaved() { closeFloorModal(); fetchBuilding() }

async function deleteFloor(floor) {
  const ok = await confirm({
    title: 'حذف الطابق',
    message: `هل أنت متأكد من حذف الطابق "${floor.floor_name}"؟`,
    variant: 'danger',
  })
  if (!ok) return
  try {
    await frappeRequest({ url: '/api/method/rental.rental.api.property.delete_floor', method: 'POST', params: { name: floor.name } })
    toast.success('تم حذف الطابق')
    fetchBuilding()
  } catch (e) { toast.error(extractError(e)) }
}

function closeUnitModal() { showUnitModal.value = false; editingUnit.value = null }
function handleUnitSaved() { closeUnitModal(); fetchBuilding() }

async function openUnitDetails(unit) {
  selectedUnit.value = unit
  showUnitDetails.value = true
}
function closeUnitDetails() { showUnitDetails.value = false; selectedUnit.value = null }

function editUnitFromDetails(unit) {
  closeUnitDetails()
  editingUnit.value = unit
  showUnitModal.value = true
}

async function toggleUnitActive(unit) {
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.toggle_unit_active',
      method: 'POST',
      params: { name: unit.name, is_active: unit.is_active ? 0 : 1 },
    })
    toast.success(unit.is_active ? 'تم تعطيل الوحدة' : 'تم تفعيل الوحدة')
    closeUnitDetails()
    fetchBuilding()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteUnitFromDetails(unit) {
  const ok = await confirm({
    title: 'حذف نهائي',
    message: `هل أنت متأكد من حذف الوحدة "${unit.unit_number}" نهائياً؟ لا يمكن التراجع.`,
    variant: 'danger',
  })
  if (!ok) return
  try {
    await frappeRequest({ url: '/api/method/rental.rental.api.property.delete_unit', method: 'POST', params: { name: unit.name } })
    toast.success('تم حذف الوحدة')
    closeUnitDetails()
    fetchBuilding()
  } catch (e) { toast.error(extractError(e)) }
}

onMounted(fetchBuilding)
</script>
