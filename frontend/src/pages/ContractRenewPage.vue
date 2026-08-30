<template>
  <AppLayout>
    <div class="min-h-screen bg-navy-50/30 print:bg-white" dir="rtl">
      <!-- Sticky header -->
      <div class="sticky top-0 z-40 border-b border-ivory-300 bg-white/90 backdrop-blur-md px-4 py-3 print:hidden">
        <div class="mx-auto flex max-w-7xl items-center justify-between">
          <div class="flex items-center gap-3">
            <router-link :to="`/contracts/${route.params.id}`" class="btn-premium btn-ghost text-navy-400">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
              <span class="hidden sm:inline">العقد</span>
            </router-link>
            <div class="h-6 w-px bg-navy-200"></div>
            <h1 class="text-lg font-bold text-navy-900">تجديد العقد {{ previousContractNumber }}</h1>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل بيانات العقد السابق...</p>
      </div>

      <div v-else>
        <!-- General error -->
        <div v-if="errors.general" class="mx-auto max-w-7xl px-4 pt-4 print:hidden">
          <div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <p class="font-bold mb-1">تعذر حفظ التجديد</p>
            <p>{{ errors.general }}</p>
          </div>
        </div>

        <div class="mx-auto max-w-7xl px-4 py-6 print:p-0">
          <div class="flex flex-col gap-6 lg:flex-row">
            <!-- Document -->
            <div class="contract-print-container flex-1">
              <ContractDocument
                v-model="form"
                :errors="errors"
                :warnings="warnings"
                :tenants="tenants"
                :buildings="buildings"
                :floors="floors"
                :units="units"
                :dueTypes="dueTypes"
                :mode="printing ? 'print' : viewMode"
                :isRenewal="true"
                :previousContractNumber="previousContractNumber"
                :lessorData="lessorData"
              />
            </div>

            <!-- Sidebar - Desktop -->
            <div class="hidden w-80 shrink-0 lg:block print:hidden">
              <div class="sticky top-20 space-y-4">
                <ContractSummary
                  :formData="form"
                  :tenants="tenants"
                  :units="units"
                  :buildings="buildings"
                  :errors="errors"
                  :warnings="warnings"
                  :isSaving="saving"
                  mode="create"
                  status="draft"
                  :viewMode="viewMode"
                  :isRenewal="true"
                  :previousContractNumber="previousContractNumber"
                  :currency="lessorData?.currency || 'ILS'"
                  @save="handleSave"
                  @preview="togglePreview"
                  @print="handlePrint"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Mobile Bottom Sheet Trigger -->
        <div class="fixed bottom-0 left-0 right-0 border-t border-ivory-300 bg-white p-3 lg:hidden print:hidden z-30">
          <div class="flex items-center justify-between gap-2">
            <button class="btn-premium btn-outline flex-1" @click="showMobileSummary = !showMobileSummary">
              ملخص التجديد
            </button>
            <button class="btn-premium btn-gold flex-[2]" :disabled="saving" @click="handleSave(false)">
              <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              {{ saving ? 'جاري الحفظ...' : 'حفظ التجديد' }}
            </button>
          </div>
        </div>

        <!-- Mobile Bottom Sheet -->
        <div v-if="showMobileSummary" class="fixed inset-0 z-50 lg:hidden print:hidden">
          <div class="absolute inset-0 bg-navy-950/30" @click="showMobileSummary = false"></div>
          <div class="absolute bottom-0 left-0 right-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white p-4 shadow-2xl">
            <div class="mb-3 flex items-center justify-center">
              <div class="h-1.5 w-12 rounded-full bg-navy-300"></div>
            </div>
            <ContractSummary
              :formData="form"
              :tenants="tenants"
              :units="units"
              :buildings="buildings"
              :errors="errors"
              :warnings="warnings"
              :isSaving="saving"
              mode="create"
              status="draft"
              :viewMode="viewMode"
              :isRenewal="true"
              :previousContractNumber="previousContractNumber"
              :currency="lessorData?.currency || 'ILS'"
              @save="handleSave"
              @preview="() => { togglePreview(); showMobileSummary = false }"
              @print="handlePrint"
            />
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import ContractDocument from '@/components/contract/ContractDocument.vue'
import ContractSummary from '@/components/contract/ContractSummary.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { getFrequencyCount } from '@/utils/contractUtils.js'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()

const lessorData = computed(() => session.state.account?.settings || null)

const loading = ref(true)
const saving = ref(false)
const printing = ref(false)
const viewMode = ref('edit')
const showMobileSummary = ref(false)
const previousContractNumber = ref('')

const errors = ref({})
const warnings = ref([])

const tenants = ref([])
const buildings = ref([])
const floors = ref([])
const units = ref([])
const dueTypes = ref([])

// ---- Form data (camelCase to match ContractDocument) ----
const form = ref({
  contractNumber: '',
  contractDate: new Date().toISOString().split('T')[0],
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

// ---- Validation ----
function validate() {
  const newErrors = {}
  if (!form.value.firstDueDate) newErrors.firstDueDate = 'تاريخ أول التزام مطلوب'
  if (!form.value.cycles || parseInt(form.value.cycles, 10) <= 0) {
    newErrors.cycles = 'عدد الدورات مطلوب'
  }
  if (!form.value.rentAmount) {
    newErrors.rentAmount = 'قيمة الإيجار مطلوبة'
  } else if (parseFloat(form.value.rentAmount) <= 0) {
    newErrors.rentAmount = 'قيمة الإيجار يجب أن تكون أكبر من صفر'
  }
  if (form.value.firstDueDate && form.value.endDate) {
    const firstDue = new Date(form.value.firstDueDate)
    const end = new Date(form.value.endDate)
    if (firstDue >= end) newErrors.endDate = 'تاريخ النهاية يجب أن يكون بعد تاريخ أول التزام'
  }
  errors.value = newErrors
  return Object.keys(newErrors).length === 0
}

watch(() => ({ ...form.value }), () => {
  if (errors.value.general) {
    const { general, ...rest } = errors.value
    errors.value = rest
  }
  validate()
}, { deep: true })

// ---- Load original contract ----
async function loadOriginal() {
  loading.value = true
  try {
    // Load supporting data in parallel
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
    previousContractNumber.value = c.contract_number || c.contractNumber || ''

    // Calculate first due date = original end + 1 day
    const end = new Date(c.end_date || c.endDate)
    const firstDue = new Date(end)
    firstDue.setDate(firstDue.getDate() + 1)
    const firstDueStr = firstDue.toISOString().split('T')[0]

    const unitIdValue = c.unit?.name || c.unitId || (typeof c.unit === 'string' ? c.unit : '')
    const loadedUnit = units.value.find((u) => u.name === unitIdValue || u.unit_number === c.unit_number)

    // Calculate cycles from original contract (source: renew/page.tsx:89)
    const cycles = String(Math.max(1, getFrequencyCount(new Date(c.start_date || c.startDate), new Date(c.end_date || c.endDate), c.payment_frequency || c.paymentFrequency || 'monthly')))

    form.value = {
      contractNumber: '',
      contractDate: new Date().toISOString().split('T')[0],
      tenantId: c.tenant?.name || c.tenantId || (typeof c.tenant === 'string' ? c.tenant : ''),
      buildingId: c.building?.name || c.buildingId || (typeof c.building === 'string' ? c.building : ''),
      floorId: loadedUnit?.floor || loadedUnit?.floorId || '',
      unitId: unitIdValue,
      startDate: firstDueStr,
      endDate: '',
      rentAmount: String(c.rent_amount ?? c.rentAmount ?? ''),
      paymentFrequency: c.payment_frequency || c.paymentFrequency || 'monthly',
      firstDueDate: firstDueStr,
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
        opening_meter_reading: undefined,
      })),
      terms: c.terms || '',
      witnesses: '',
      status: 'draft',
    }
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

// ---- Save ----
async function handleSave(asDraft = false) {
  const isValid = validate()
  if (!isValid && !asDraft) return
  saving.value = true
  errors.value = {}
  try {
    const payload = buildPayload()
    // For renewal, remove tenant/building/unit/start (inherited from original)
    delete payload.tenant_id
    delete payload.building_id
    delete payload.floor_id
    delete payload.unit_id
    delete payload.first_due_date
    delete payload.start_date

    const result = await callApi('rental.rental.api.contract.renew_contract', {
      name: route.params.id,
      ...payload,
    })
    const newId = result.name || result.contract?.name || result
    router.push({ name: 'ContractDetail', params: { id: newId } })
  } catch (e) {
    errors.value = { general: extractError(e) }
  } finally {
    saving.value = false
  }
}

function buildPayload() {
  const payload = { ...form.value }
  delete payload.contractNumber
  const converted = {}
  for (const [k, v] of Object.entries(payload)) {
    const snake = k.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase())
    if (v === '' || v === null || v === undefined) continue
    converted[snake] = v
  }
  if (converted.contract_charges && Array.isArray(converted.contract_charges)) {
    converted.contract_charges = converted.contract_charges.map((c) => {
      const out = {}
      for (const [k, v] of Object.entries(c)) {
        const snake = k.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase())
        if (v === '' || v === null || v === undefined) continue
        out[snake] = v
      }
      return out
    })
  }
  return converted
}

// ---- Preview / Print ----
function togglePreview() {
  viewMode.value = viewMode.value === 'preview' ? 'edit' : 'preview'
}

function handlePrint() {
  printing.value = true
  setTimeout(() => {
    window.print()
    setTimeout(() => { printing.value = false }, 500)
  }, 200)
}

onMounted(loadOriginal)
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
