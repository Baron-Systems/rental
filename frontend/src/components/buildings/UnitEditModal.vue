<template>
  <Modal :model-value="true" title="تعديل وحدة" size="lg" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="رقم الوحدة" required>
          <input v-model="form.unit_number" type="text" required placeholder="101" class="input-premium" :disabled="!editableFields.includes('unit_number')" :class="{ 'opacity-60': !editableFields.includes('unit_number') }" />
        </FormField>
        <FormField label="نوع الوحدة">
          <select v-model="form.unit_type" required class="input-premium" @change="onUnitTypeChange">
            <option value="">— اختر —</option>
            <option v-for="t in unitTypes" :key="t.name" :value="t.name">{{ t.type_name }}</option>
            <!-- Include current type even if disabled -->
            <option v-if="currentTypeDisabled && form.unit_type" :value="form.unit_type">
              {{ currentTypeName }} (معطل)
            </option>
          </select>
        </FormField>
        <FormField label="الطابق">
          <select v-model="form.floor" class="input-premium" :disabled="!editableFields.includes('floor')" :class="{ 'opacity-60': !editableFields.includes('floor') }">
            <option value="">بدون طابق</option>
            <option v-for="f in props.floors" :key="f.name" :value="f.name">{{ f.floor_name }}</option>
          </select>
        </FormField>
        <FormField label="المساحة">
          <div class="relative" dir="ltr">
            <input v-model.number="form.area" type="number" step="any" placeholder="120" class="input-premium has-icon-start" :disabled="!editableFields.includes('area')" :class="{ 'opacity-60': !editableFields.includes('area') }" />
            <span class="absolute top-1/2 -translate-y-1/2 text-xs font-medium text-navy-400 icon-start">م²</span>
          </div>
        </FormField>
      </div>

      <!-- Dynamic attributes + meter fields -->
      <UnitAttributeFields
        v-if="form.unit_type && attrsReady"
        ref="attrFields"
        :unit-type="form.unit_type"
        :existing-values="existingAttrValues"
        :existing-meter-form="existingMeterForm"
        :editable-fields="editableFields"
        :show-meter-fields="true"
        @update:attribute-values="onAttrValuesUpdate"
        @update:meter-form="onMeterFormUpdate"
      />

      <FormField label="ملاحظات">
        <textarea v-model="form.notes" rows="2" placeholder="أي ملاحظات إضافية..." class="input-premium" :disabled="!editableFields.includes('notes')" :class="{ 'opacity-60': !editableFields.includes('notes') }"></textarea>
      </FormField>
    </form>
    <template #footer>
      <button class="btn-premium btn-outline" @click="$emit('close')">إلغاء</button>
      <button class="btn-premium btn-gold" :disabled="saving" @click="save">
        <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
        حفظ التغييرات
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { extractError, callApi } from '@/composables/useApi'
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'
import UnitAttributeFields from '@/components/buildings/UnitAttributeFields.vue'

const props = defineProps({
  unit: { type: Object, required: true },
  floors: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const editableFields = ref([
  'unit_type', 'area', 'rooms_count', 'bathrooms_count', 'notes',
  'unit_number', 'building', 'floor',
  'current_electricity_meter_reading', 'current_water_meter_reading',
])

const form = ref({
  unit_number: props.unit?.unit_number || '',
  unit_type: props.unit?.unit_type || '',
  floor: props.unit?.floor?.id || props.unit?.floor || '',
  area: props.unit?.area ?? null,
  notes: props.unit?.notes || '',
})

const saving = ref(false)
const unitTypes = ref([])
const attrFields = ref(null)
const attrsReady = ref(false)

// Existing attribute values loaded from backend (preserving 0, false, etc.)
const existingAttrValues = ref({})
const existingMeterForm = ref({})

// Current values being edited
const currentAttrValues = ref({})
const currentMeterForm = ref({})

// Track if current unit type is disabled (for edit display)
const currentTypeDisabled = ref(false)
const currentTypeName = ref('')

const attrFieldsComponent = computed(() => attrFields.value)

async function fetchUnitTypes() {
  try {
    const res = await callApi('rental.rental.api.property.get_active_unit_types')
    unitTypes.value = res.unitTypes || []
    // Check if current unit type is in the active list
    if (form.value.unit_type) {
      const found = unitTypes.value.find(t => t.name === form.value.unit_type)
      if (!found) {
        currentTypeDisabled.value = true
        // Fetch the type name
        try {
          const unitData = await callApi('rental.rental.api.property.get_unit', { name: props.unit.name })
          currentTypeName.value = unitData.unit_type_name || ''
        } catch { currentTypeName.value = '' }
      } else {
        currentTypeName.value = found.type_name
      }
    }
  } catch { unitTypes.value = [] }
}

async function fetchUnitData() {
  try {
    const res = await callApi('rental.rental.api.property.get_unit', { name: props.unit.name })
    // Load attribute values — preserve 0, false correctly
    const vals = {}
    if (res.attribute_values) {
      for (const [k, v] of Object.entries(res.attribute_values)) {
        vals[k] = v.value
      }
    }
    existingAttrValues.value = vals

    // Load meter form data
    existingMeterForm.value = {
      electricity_meter_number: res.electricity_meter_number || '',
      current_electricity_meter_reading: res.current_electricity_meter_reading || '',
      water_meter_number: res.water_meter_number || '',
      current_water_meter_reading: res.current_water_meter_reading || '',
    }

    attrsReady.value = true
  } catch {
    attrsReady.value = true
  }
}

function onUnitTypeChange() {
  // When unit type changes, we keep existing values but the component
  // will only show attributes for the new type. Hidden values are preserved
  // in existingAttrValues and will be sent to backend on save.
  // The component re-initializes from existingAttrValues for the new type's attributes.
}

function onAttrValuesUpdate(vals) {
  currentAttrValues.value = vals
}

function onMeterFormUpdate(meter) {
  currentMeterForm.value = meter
}

onMounted(async () => {
  // Fetch permissions
  try {
    const res = await frappeRequest({
      url: '/api/method/rental.rental.api.property.get_unit_permissions',
      params: { name: props.unit.name },
    })
    const perms = res?.message || res
    if (perms?.editable_fields) {
      editableFields.value = perms.editable_fields
    }
  } catch { /* ignore */ }

  await Promise.all([fetchUnitTypes(), fetchUnitData()])
})

async function save() {
  saving.value = true
  try {
    const payload = { name: props.unit.name, ...form.value }
    // Clean empty/null from core fields (but keep 0 for numeric fields)
    Object.keys(payload).forEach(k => {
      if (k !== 'name' && k !== 'area' && payload[k] === '') delete payload[k]
      if (k !== 'name' && payload[k] === null && k !== 'area') delete payload[k]
    })
    if (payload.floor === '') payload.floor = null

    // Add meter fields — only send if they have values
    // Important: don't send empty strings for meter fields that are hidden
    // (capability disabled). The backend won't clear them unless explicitly sent.
    const meterVals = currentMeterForm.value
    if (meterVals.electricity_meter_number !== undefined) {
      payload.electricity_meter_number = meterVals.electricity_meter_number || null
    }
    if (meterVals.water_meter_number !== undefined) {
      payload.water_meter_number = meterVals.water_meter_number || null
    }
    // Only send meter readings if they're editable (not locked by active metered contract)
    if (editableFields.value.includes('current_electricity_meter_reading')) {
      payload.current_electricity_meter_reading = meterVals.current_electricity_meter_reading || null
    }
    if (editableFields.value.includes('current_water_meter_reading')) {
      payload.current_water_meter_reading = meterVals.current_water_meter_reading || null
    }

    // Add attribute values — merge current with existing to preserve hidden values
    // CRITICAL: Only send values that are not None. Hidden attributes keep their stored values.
    const allAttrValues = { ...existingAttrValues.value, ...currentAttrValues.value }
    const cleanAttrValues = {}
    for (const [k, v] of Object.entries(allAttrValues)) {
      if (v !== null && v !== '' && v !== undefined) {
        cleanAttrValues[k] = v
      }
    }
    if (Object.keys(cleanAttrValues).length > 0) {
      payload.attribute_values = JSON.stringify(cleanAttrValues)
    }

    await frappeRequest({
      url: '/api/method/rental.rental.api.property.update_unit',
      method: 'POST',
      params: payload,
    })
    emit('saved')
  } catch (e) {
    alert(extractError(e) || 'تعذّر حفظ البيانات')
  } finally {
    saving.value = false
  }
}
</script>
