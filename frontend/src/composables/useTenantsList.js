/**
 * useTenantsList composable
 *
 * Source: TENANTS_MIGRATION_SPEC §41
 * Manages tenant list state: fetch, search, filters, pagination, stats, print.
 */

import { ref, computed } from 'vue'
import { callApi, extractError } from './useApi'
import { useToast } from './useToast'

export function useTenantsList() {
  const toast = useToast()

  const tenants = ref([])
  const loading = ref(true)
  const printing = ref(false)
  const pagination = ref(null)
  const stats = ref(null)
  const buildings = ref([])
  const units = ref([])
  const showAdvanced = ref(false)
  const filters = ref({
    search: '',
    contractState: 'all',
    buildingId: '',
    unitId: '',
  })

  const activeAdvancedCount = computed(() => {
    let n = 0
    if (filters.value.contractState !== 'all') n++
    if (filters.value.buildingId) n++
    if (filters.value.unitId) n++
    return n
  })

  async function loadBuildings() {
    try {
      const res = await callApi('rental.rental.api.property.get_buildings', {
        simple: 1,
        include_inactive: 1,
      })
      buildings.value = Array.isArray(res) ? res : (res.buildings || [])
    } catch {
      buildings.value = []
    }
  }

  async function loadUnits() {
    if (!filters.value.buildingId) {
      units.value = []
      return
    }
    try {
      const res = await callApi('rental.rental.api.property.get_units', {
        building: filters.value.buildingId,
        simple: 1,
        include_inactive: 1,
      })
      units.value = Array.isArray(res) ? res : (res.units || [])
    } catch {
      units.value = []
    }
  }

  async function fetchTenants(page = 1) {
    loading.value = true
    try {
      const res = await callApi('rental.rental.api.tenant.get_tenants', {
        page,
        search: filters.value.search || undefined,
        contract_state: filters.value.contractState !== 'all' ? filters.value.contractState : undefined,
        building: filters.value.buildingId || undefined,
        unit: filters.value.unitId || undefined,
        limit: 15,
      })
      tenants.value = res.tenants || []
      pagination.value = res.pagination
      stats.value = res.stats
      if (res.pagination && res.pagination.totalPages > 0 && page > res.pagination.totalPages) {
        fetchTenants(res.pagination.totalPages)
      }
    } catch (e) {
      toast.error(extractError(e) || 'حدث خطأ أثناء تحميل المستأجرين')
    } finally {
      loading.value = false
    }
  }

  async function fetchPrintData() {
    printing.value = true
    try {
      const res = await callApi('rental.rental.api.tenant.get_tenants', {
        print: 1,
        search: filters.value.search || undefined,
        contract_state: filters.value.contractState !== 'all' ? filters.value.contractState : undefined,
        building: filters.value.buildingId || undefined,
        unit: filters.value.unitId || undefined,
      })
      return res
    } catch (e) {
      toast.error(extractError(e) || 'حدث خطأ أثناء تجهيز التقرير')
      return null
    } finally {
      printing.value = false
    }
  }

  function clearFilters() {
    filters.value = { search: '', contractState: 'all', buildingId: '', unitId: '' }
    units.value = []
    fetchTenants(1)
  }

  function clearBuilding() {
    filters.value.buildingId = ''
    filters.value.unitId = ''
    units.value = []
    fetchTenants(1)
  }

  function clearUnit() {
    filters.value.unitId = ''
    fetchTenants(1)
  }

  return {
    tenants,
    loading,
    printing,
    pagination,
    stats,
    buildings,
    units,
    showAdvanced,
    filters,
    activeAdvancedCount,
    loadBuildings,
    loadUnits,
    fetchTenants,
    fetchPrintData,
    clearFilters,
    clearBuilding,
    clearUnit,
  }
}
