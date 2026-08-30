<template>
  <AppLayout>
    <div class="min-h-screen bg-navy-50/30 print:bg-white" dir="rtl">
      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل معاينة العقد...</p>
      </div>

      <div v-else-if="!contract" class="text-center py-20">
        <p class="text-navy-400">العقد غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Contracts' })">العودة للقائمة</button>
      </div>

      <div v-else>
        <!-- Sticky header (hidden in print) -->
        <div class="sticky top-0 z-40 border-b border-ivory-300 bg-white/90 backdrop-blur-md px-4 py-3 print:hidden">
          <div class="mx-auto flex max-w-7xl items-center justify-between">
            <div class="flex items-center gap-3">
              <router-link :to="`/contracts/${contract.name}`" class="btn-premium btn-ghost text-navy-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
                <span class="hidden sm:inline">عودة للعقد</span>
              </router-link>
              <div class="h-6 w-px bg-navy-200"></div>
              <h1 class="text-lg font-bold text-navy-900">معاينة العقد {{ contract.contract_number }}</h1>
            </div>
            <button class="btn-premium btn-gold inline-flex items-center gap-1.5" @click="handlePrint">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              طباعة
            </button>
          </div>
        </div>

        <!-- Contract document -->
        <div id="contract-document" class="contract-print-container mx-auto max-w-7xl print:p-0 p-4">
          <ContractDocument
            v-model="formData"
            :errors="{}"
            :warnings="[]"
            :tenants="tenants"
            :buildings="buildings"
            :floors="floors"
            :units="units"
            :dueTypes="dueTypes"
            :mode="printing ? 'print' : 'preview'"
            :dues="dues"
            :lessorData="lessorData"
          />
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
const printing = ref(false)

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
    // Ensure the contract's unit is in the list even if inactive (source: preview/page.tsx)
    const unitIdValue = c.unit?.name || c.unitId || (typeof c.unit === 'string' ? c.unit : '')
    let loadedUnit = units.value.find((u) => u.name === unitIdValue || u.unit_number === c.unit_number)
    if (!loadedUnit && unitIdValue) {
      try {
        const unitDoc = await callApi('rental.rental.api.property.get_unit', { name: unitIdValue })
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
      tenantId: c.tenant?.name || c.tenantId || (typeof c.tenant === 'string' ? c.tenant : ''),
      buildingId: c.building?.name || c.buildingId || (typeof c.building === 'string' ? c.building : ''),
      floorId: loadedUnit?.floor || loadedUnit?.floorId || c.unit?.floor || '',
      unitId: unitIdValue,
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
        due_type: charge.due_type || charge.dueTypeId,
        due_type_name: charge.due_type_name || charge.dueTypeName || charge.dueType?.name || '',
        due_type_code: charge.due_type_code || charge.dueTypeCode || charge.dueType?.code || null,
        responsibility: charge.responsibility,
        payment_by: charge.payment_by || charge.paymentBy || '',
        calculation_method: charge.calculation_method || charge.calculationMethod || '',
        amount: charge.amount != null ? String(charge.amount) : undefined,
        frequency: charge.frequency || undefined,
        first_due_date: charge.first_due_date ? new Date(charge.first_due_date).toISOString().split('T')[0] : (charge.firstDueDate || undefined),
        commitment_timing: charge.commitment_timing || charge.commitmentTiming || undefined,
        last_period_handling: charge.last_period_handling || charge.lastPeriodHandling || undefined,
        last_period_adjustment_amount: charge.last_period_adjustment_amount != null ? String(charge.last_period_adjustment_amount) : (charge.lastPeriodAdjustmentAmount != null ? String(charge.lastPeriodAdjustmentAmount) : undefined),
        opening_meter_reading: charge.opening_meter_reading || charge.openingMeterReading || undefined,
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
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

function handlePrint() {
  printing.value = true
  setTimeout(() => {
    window.print()
    setTimeout(() => { printing.value = false }, 500)
  }, 200)
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
