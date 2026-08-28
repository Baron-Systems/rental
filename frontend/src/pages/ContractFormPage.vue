<template>
  <AppLayout>
    <div class="min-h-screen bg-navy-50/30 print:bg-white" dir="rtl">
      <!-- General error -->
      <div v-if="errors.general" class="mx-auto max-w-7xl px-4 pt-4 print:hidden">
        <div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <p class="font-bold mb-1">تعذر حفظ العقد</p>
          <p>{{ errors.general }}</p>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-sm text-navy-400 mr-3">جاري تحميل بيانات العقد...</p>
      </div>

      <div v-else class="mx-auto max-w-7xl px-4 py-6 print:p-0">
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
              :dues="dues"
              :isNewContract="!isEdit"
              :isRenewal="isRenewal"
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
                :mode="isEdit ? 'edit' : 'create'"
                :status="form.status || 'draft'"
                :viewMode="viewMode"
                :dues="dues"
                :isRenewal="isRenewal"
                :previousContractNumber="previousContractNumber"
                :currency="lessorData?.currency || 'ILS'"
                @save="handleSaveClick"
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
            ملخص العقد
          </button>
          <button class="btn-premium btn-gold flex-[2]" :disabled="saving" @click="handleSaveClick(false)">
            <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
            {{ saving ? 'جاري الحفظ...' : (isEdit ? 'حفظ التعديلات' : 'حفظ العقد') }}
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
            :mode="isEdit ? 'edit' : 'create'"
            :status="form.status || 'draft'"
            :viewMode="viewMode"
            :dues="dues"
            :isRenewal="isRenewal"
            :previousContractNumber="previousContractNumber"
            :currency="lessorData?.currency || 'ILS'"
            @save="handleSaveClick"
            @preview="() => { togglePreview(); showMobileSummary = false }"
            @print="handlePrint"
          />
        </div>
      </div>

      <!-- Past Contract Dues Dialog -->
      <PastContractDuesDialog
        v-model="showDuesDialog"
        :isLoading="saving"
        @confirm="handleApproveWithDuesChoice"
        @cancel="cancelDuesDialog"
      />
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import ContractDocument from '@/components/contract/ContractDocument.vue'
import ContractSummary from '@/components/contract/ContractSummary.vue'
import PastContractDuesDialog from '@/components/PastContractDuesDialog.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const isEdit = computed(() => !!route.params.id)
const isRenewal = computed(() => !!route.query.renew_from)
const loading = ref(false)
const saving = ref(false)
const printing = ref(false)
const viewMode = ref('edit') // 'edit' | 'preview'
const showMobileSummary = ref(false)
const showDuesDialog = ref(false)
const pendingContractId = ref(null)
const previousContractNumber = ref('')

const errors = ref({})
const warnings = ref([])

const tenants = ref([])
const buildings = ref([])
const floors = ref([])
const units = ref([])
const dueTypes = ref([])
const dues = ref([])
const lessorData = computed(() => session.state.account?.settings || null)

// ---- Form data (camelCase keys to match ContractDocument) ----
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

// ---- Load initial data ----
async function loadInitialData() {
  try {
    const [tenantsRes, buildingsRes, floorsRes, unitsRes, dueTypesRes] = await Promise.all([
      callApi('rental.rental.api.tenant.get_tenants', { limit: 500 }).catch(() => ({ tenants: [] })),
      callApi('rental.rental.api.property.get_buildings', { simple: 1, include_inactive: 1, limit: 500 }).catch(() => []),
      callApi('rental.rental.api.property.get_floors', { limit: 500 }).catch(() => ({ floors: [] })),
      callApi('rental.rental.api.property.get_units', { limit: 500 }).catch(() => ({ units: [] })),
      callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 0 }).catch(() => []),
    ])
    tenants.value = tenantsRes.tenants || tenantsRes || []
    buildings.value = buildingsRes.buildings || buildingsRes || []
    floors.value = floorsRes.floors || floorsRes || []
    units.value = unitsRes.units || unitsRes || []
    dueTypes.value = dueTypesRes.dueTypes || dueTypesRes || []
  } catch (e) {
    toast.error(extractError(e))
  }
}

// ---- Load contract for edit mode ----
async function loadContract() {
  if (!isEdit.value) {
    // For new contracts, fetch default contract number and terms
    try {
      const settingsRes = await callApi('rental.rental.api.settings.get_settings').catch(() => ({}))
      const settings = settingsRes.settings || settingsRes || []
      const getVal = (key) => {
        const raw = Array.isArray(settings) ? settings.find((x) => x.setting_key === key || x.settingKey === key) : null
        const v = raw?.setting_value ?? raw?.settingValue
        return typeof v === 'object' && v !== null ? v.value : v
      }
      const prefix = getVal('contract_prefix') || 'CNT'
      const counter = getVal('contract_counter') || 1
      const nextNum = String(counter).padStart(4, '0')
      const defaultTerms = getVal('default_contract_terms') || ''
      form.value.contractNumber = `${prefix}-${nextNum}`
      form.value.terms = defaultTerms
    } catch { /* ignore */ }
    return
  }

  loading.value = true
  try {
    const res = await callApi('rental.rental.api.contract.get_contract', { name: route.params.id })
    const c = res.contract || res
    if (c) {
      previousContractNumber.value = c.previous_contract_number || c.previousContract?.contractNumber || ''
      const loadedUnit = units.value.find((u) => u.name === c.unit || u.uu.id === c.unitId)
      form.value = {
        contractNumber: c.contract_number || c.contractNumber || '',
        contractDate: (c.contract_date || c.contractDate || '').slice(0, 10),
        tenantId: c.tenant || c.tenantId || '',
        buildingId: c.building || c.buildingId || '',
        floorId: loadedUnit?.floor || loadedUnit?.floorId || '',
        unitId: c.unit || c.unitId || '',
        startDate: (c.start_date || c.startDate || '').slice(0, 10),
        endDate: (c.end_date || c.endDate || '').slice(0, 10),
        rentAmount: String(c.rent_amount ?? c.rentAmount ?? ''),
        paymentFrequency: c.payment_frequency || c.paymentFrequency || 'monthly',
        firstDueDate: (c.first_due_date || c.firstDueDate || '').slice(0, 10),
        cycles: String(c.cycles || '1'),
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
      // Map dues
      dues.value = (c.dues || []).map((d, i) => ({
        number: i + 1,
        dueDate: (d.due_date || d.dueDate || d.transaction_date || '').slice(0, 10),
        amount: Number(d.amount) || 0,
      }))
    }
  } catch (e) {
    toast.error(extractError(e))
    router.push({ name: 'Contracts' })
  } finally {
    loading.value = false
  }
}

// ---- Auto-build default charges when unit is selected (new contract only) ----
watch(
  () => [form.value.unitId, dueTypes.value, units.value],
  () => {
    if (isEdit.value) return // Don't override existing charges
    if (!form.value.unitId || dueTypes.value.length === 0) return
    if (form.value.contractCharges && form.value.contractCharges.length > 0) return
    const unit = units.value.find((u) => u.name === form.value.unitId)
    const defaults = buildDefaultCharges(dueTypes.value, unit)
    if (defaults.length > 0) {
      form.value.contractCharges = defaults
    }
  },
  { immediate: true }
)

function buildDefaultCharges(dueTypes, unit) {
  // Source: ContractChargesSection.tsx:150-163 buildDefaultCharges
  // Only electricity & water, responsibility='landlord', no paymentBy/calculationMethod
  // Rent is excluded (handled by due generation)
  // Uses snake_case keys to match ContractChargesSection.vue / ContractChargeCard.vue
  if (!dueTypes || dueTypes.length === 0) return []
  const defaults = []
  for (const code of ['electricity', 'water']) {
    const dt = dueTypes.find((d) => (d.code || d.due_type_code) === code)
    if (!dt) continue
    defaults.push({
      due_type: dt.name || dt.id,
      due_type_name: dt.due_type_name || dt.name,
      due_type_code: code,
      responsibility: 'landlord',
      payment_by: '',
      calculation_method: '',
      amount: undefined,
      frequency: undefined,
      first_due_date: undefined,
      commitment_timing: undefined,
      last_period_handling: undefined,
      last_period_adjustment_amount: undefined,
      opening_meter_reading: undefined,
    })
  }
  return defaults
}

// ---- Validation ----
function validate() {
  const newErrors = {}
  if (!form.value.tenantId) newErrors.tenantId = 'المستأجر مطلوب'
  if (!form.value.unitId) newErrors.unitId = 'الوحدة مطلوبة'
  if (!form.value.startDate) newErrors.startDate = 'تاريخ بداية العقد مطلوب'
  if (!isEdit.value && (!form.value.cycles || parseInt(form.value.cycles, 10) <= 0)) {
    newErrors.cycles = 'عدد الدورات مطلوب'
  }
  if (!form.value.rentAmount) {
    newErrors.rentAmount = 'قيمة الإيجار مطلوبة'
  } else if (parseFloat(form.value.rentAmount) <= 0) {
    // Source: validation.ts:168-172 — separate message for non-positive rent
    newErrors.rentAmount = 'قيمة الإيجار يجب أن تكون أكبر من صفر'
  }
  // Edit mode requires end date (source: edit/page.tsx:150)
  if (isEdit.value && !form.value.endDate) {
    newErrors.endDate = 'تاريخ النهاية مطلوب'
  }
  if (form.value.startDate && form.value.endDate) {
    const start = new Date(form.value.startDate)
    const end = new Date(form.value.endDate)
    if (start >= end) newErrors.endDate = 'تاريخ النهاية يجب أن يكون بعد تاريخ بداية العقد'
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

// ---- Save handlers ----
function handleSaveClick(asDraft = false) {
  // For new contract, asDraft means save only; otherwise save+approve
  if (isEdit.value) {
    saveEdit()
  } else {
    saveNew(asDraft)
  }
}

async function saveNew(asDraft) {
  const isValid = validate()
  if (!isValid && !asDraft) return

  // Validate due types loaded
  const hasElectricity = dueTypes.value.some((dt) => (dt.code || dt.due_type_code) === 'electricity')
  const hasWater = dueTypes.value.some((dt) => (dt.code || dt.due_type_code) === 'water')
  if (!hasElectricity || !hasWater) {
    errors.value = { general: 'لم يتم تحميل أنواع الالتزام النظامية (كهرباء / مياه). يرجى الانتظار أو تحديث الصفحة.' }
    return
  }

  const invalidCharge = form.value.contractCharges?.find((c) => !(c.due_type || c.dueTypeId))
  if (invalidCharge) {
    errors.value = { general: 'بيانات خدمات العقد غير مكتملة (نوع الالتزام مطلوب لكل خدمة).' }
    return
  }

  saving.value = true
  errors.value = {}
  try {
    const payload = buildPayload()
    const result = await callApi('rental.rental.api.contract.create_contract', payload)
    const contractName = result.name || result.contract?.name || result
    if (asDraft) {
      router.push({ name: 'ContractDetail', params: { id: contractName } })
    } else {
      // Source: new/page.tsx:145-153 — use server response requiresDuesChoice
      const requiresDuesChoice = result.requires_dues_choice || result.requiresDuesChoice
      if (requiresDuesChoice) {
        pendingContractId.value = contractName
        showDuesDialog.value = true
        saving.value = false
        return
      }
      // Approve immediately
      await callApi('rental.rental.api.contract.approve_contract', { name: contractName, generate_dues: 1 })
      router.push({ name: 'ContractDetail', params: { id: contractName } })
    }
  } catch (e) {
    errors.value = { general: extractError(e) }
  } finally {
    saving.value = false
  }
}

async function saveEdit() {
  const hasElectricity = dueTypes.value.some((dt) => (dt.code || dt.due_type_code) === 'electricity')
  const hasWater = dueTypes.value.some((dt) => (dt.code || dt.due_type_code) === 'water')
  if (!hasElectricity || !hasWater) {
    errors.value = { general: 'لم يتم تحميل أنواع الالتزام النظامية (كهرباء / مياه). يرجى الانتظار أو تحديث الصفحة.' }
    return
  }
  const invalidCharge = form.value.contractCharges?.find((c) => !(c.due_type || c.dueTypeId))
  if (invalidCharge) {
    errors.value = { general: 'بيانات خدمات العقد غير مكتملة (نوع الالتزام مطلوب لكل خدمة).' }
    return
  }
  saving.value = true
  errors.value = {}
  try {
    const payload = buildPayload()
    // For renewal, don't send tenant/building/unit/start
    if (isRenewal.value) {
      delete payload.tenantId
      delete payload.buildingId
      delete payload.floorId
      delete payload.unitId
      delete payload.firstDueDate
      delete payload.startDate
      delete payload.renewedFromContractId
    }
    await callApi('rental.rental.api.contract.update_contract', { name: route.params.id, ...payload })
    router.push({ name: 'ContractDetail', params: { id: route.params.id } })
  } catch (e) {
    errors.value = { general: extractError(e) }
  } finally {
    saving.value = false
  }
}

function buildPayload() {
  const payload = { ...form.value }
  // Remove contractNumber (auto-generated)
  delete payload.contractNumber
  // Convert camelCase to snake_case for backend
  const converted = {}
  for (const [k, v] of Object.entries(payload)) {
    const snake = k.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase())
    if (v === '' || v === null || v === undefined) continue
    converted[snake] = v
  }
  // Convert contractCharges to contract_charges with snake_case keys
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

async function handleApproveWithDuesChoice(generateDues) {
  if (!pendingContractId.value) return
  saving.value = true
  try {
    await callApi('rental.rental.api.contract.approve_contract', {
      name: pendingContractId.value,
      generate_dues: generateDues ? 1 : 0,
    })
    showDuesDialog.value = false
    router.push({ name: 'ContractDetail', params: { id: pendingContractId.value } })
  } catch (e) {
    errors.value = { general: extractError(e) }
  } finally {
    saving.value = false
    pendingContractId.value = null
  }
}

function cancelDuesDialog() {
  showDuesDialog.value = false
  pendingContractId.value = null
  saving.value = false
}

// ---- Preview / Print ----
function togglePreview() {
  viewMode.value = viewMode.value === 'preview' ? 'edit' : 'preview'
}

function handlePrint() {
  printing.value = true
  // Wait for render then print
  setTimeout(() => {
    window.print()
    setTimeout(() => { printing.value = false }, 500)
  }, 200)
}

onMounted(async () => {
  await loadInitialData()
  await loadContract()
})
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
