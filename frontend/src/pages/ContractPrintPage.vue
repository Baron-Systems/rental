<template>
  <AppLayout>
    <div class="min-h-screen bg-navy-50/30 print:bg-white" dir="rtl">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل العقد...</p>
      </div>

      <div v-else-if="!contract" class="text-center py-20">
        <p class="text-navy-400">العقد غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Contracts' })">العودة للقائمة</button>
      </div>

      <div v-else class="contract-print-container mx-auto max-w-7xl px-4 py-6 print:p-0">
        <ContractDocument
          v-model="formData"
          :errors="{}"
          :warnings="[]"
          :tenants="tenants"
          :buildings="buildings"
          :floors="floors"
          :units="units"
          :dueTypes="dueTypes"
          mode="print"
          :dues="dues"
          :lessorData="lessorData"
        />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import ContractDocument from '@/components/contract/ContractDocument.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { getFrequencyCount } from '@/utils/contractUtils.js'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()

const lessorData = computed(() => session.state.account?.settings || null)

const contract = ref(null)
const loading = ref(true)

const tenants = ref([])
const buildings = ref([])
const floors = ref([])
const units = ref([])
const dueTypes = ref([])
const dues = ref([])

const formData = ref({
  contractNumber: '',
  contractDate: '',
  tenantId: '',
  buildingId: '',
  floorId: '',
  unitId: '',
  startDate: '',
  endDate: '',
  rentAmount: '',
  paymentFrequency: 'monthly',
  firstDueDate: '',
  cycles: '1',
  paymentMethod: '',
  commitmentTiming: 'start',
  contractCharges: [],
  terms: '',
  witnesses: '',
  status: 'draft',
})

async function loadData() {
  loading.value = true
  try {
    const [tenantsRes, buildingsRes, floorsRes, unitsRes, dueTypesRes, contractRes] = await Promise.all([
      callApi('rental.rental.api.tenant.get_tenants', { limit: 500 }).catch(() => ({ tenants: [] })),
      callApi('rental.rental.api.property.get_buildings', { simple: 1, include_inactive: 1, limit: 500 }).catch(() => []),
      callApi('rental.rental.api.property.get_floors', { limit: 500 }).catch(() => ({ floors: [] })),
      callApi('rental.rental.api.property.get_units', { include_inactive: 1, limit: 500 }).catch(() => ({ units: [] })),
      callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 0 }).catch(() => []),
      callApi('rental.rental.api.contract.get_contract', { name: route.params.id }),
    ])
    tenants.value = tenantsRes.tenants || tenantsRes || []
    buildings.value = buildingsRes.buildings || buildingsRes || []
    floors.value = floorsRes.floors || floorsRes || []
    units.value = unitsRes.units || unitsRes || []
    dueTypes.value = dueTypesRes.dueTypes || dueTypesRes || []

    const c = contractRes.contract || contractRes
    if (!c) {
      loading.value = false
      return
    }
    contract.value = c
    // Ensure the contract's unit is in the list even if inactive (source: print/page.tsx)
    let loadedUnit = units.value.find((u) => u.name === c.unit || u.id === c.unitId)
    if (!loadedUnit && c.unit) {
      try {
        const unitDoc = await callApi('rental.rental.api.property.get_unit', { name: c.unit })
        if (unitDoc) {
          units.value = [...units.value, unitDoc]
          loadedUnit = unitDoc
        }
      } catch { /* ignore */ }
    }
    const cycles = String(Math.max(1, getFrequencyCount(
      new Date(c.first_due_date || c.start_date),
      new Date(c.end_date),
      c.payment_frequency || 'monthly'
    )))

    formData.value = {
      contractNumber: c.contract_number || c.contractNumber || '',
      contractDate: (c.contract_date || c.contractDate || '').slice(0, 10),
      tenantId: c.tenant || c.tenantId || '',
      buildingId: c.building || c.buildingId || '',
      floorId: loadedUnit?.floor || loadedUnit?.floorId || c.unit?.floor || '',
      unitId: c.unit || c.unitId || '',
      startDate: (c.start_date || c.startDate || '').slice(0, 10),
      endDate: (c.end_date || c.endDate || '').slice(0, 10),
      rentAmount: String(c.rent_amount ?? c.rentAmount ?? ''),
      paymentFrequency: c.payment_frequency || c.paymentFrequency || 'monthly',
      firstDueDate: (c.first_due_date || c.firstDueDate || '').slice(0, 10),
      cycles,
      paymentMethod: c.payment_method || c.paymentMethod || '',
      commitmentTiming: c.commitment_timing || c.commitmentTiming || 'start',
      contractCharges: (c.contract_charges || c.contractCharges || []).map((charge) => ({
        id: charge.name || charge.id,
        dueTypeId: charge.due_type || charge.dueTypeId,
        dueTypeName: charge.due_type_name || charge.dueType?.name || '',
        dueTypeCode: charge.due_type_code || charge.dueType?.code || null,
        responsibility: charge.responsibility,
        paymentBy: charge.payment_by || charge.paymentBy || '',
        calculationMethod: charge.calculation_method || charge.calculationMethod || '',
        amount: charge.amount != null ? String(charge.amount) : undefined,
        frequency: charge.frequency || undefined,
        firstDueDate: charge.first_due_date ? new Date(charge.first_due_date).toISOString().split('T')[0] : undefined,
        commitmentTiming: charge.commitment_timing || charge.commitmentTiming || undefined,
        lastPeriodHandling: charge.last_period_handling || charge.lastPeriodHandling || undefined,
        lastPeriodAdjustmentAmount: charge.last_period_adjustment_amount != null ? String(charge.last_period_adjustment_amount) : undefined,
        openingMeterReading: charge.opening_meter_reading || charge.openingMeterReading || undefined,
      })),
      terms: c.terms || '',
      witnesses: c.witnesses || '',
      status: c.status || 'draft',
    }
    dues.value = (c.dues || []).map((d, i) => ({
      number: i + 1,
      dueDate: (d.due_date || d.dueDate || d.transaction_date || d.transactionDate || '').slice(0, 10),
      amount: Number(d.amount) || 0,
    }))
    loading.value = false
    // Auto-print after load
    await nextTick()
    setTimeout(() => window.print(), 500)
  } catch (e) {
    toast.error(extractError(e))
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
@media print {
  :deep(.app-layout > *:not(.contract-print-container)),
  :deep(.app-layout nav),
  :deep(.app-layout header) {
    display: none !important;
  }
  .contract-print-container {
    width: 100% !important;
    max-width: none !important;
  }
}
</style>
