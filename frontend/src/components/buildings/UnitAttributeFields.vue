<template>
  <div class="space-y-4">
    <!-- Dynamic attributes grouped by category -->
    <div v-if="groupedAttributes.length" class="space-y-4">
      <div v-for="group in groupedAttributes" :key="group.category">
        <p v-if="group.category && group.label" class="text-xs font-semibold text-navy-400 mb-2">{{ group.label }}</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField
            v-for="attr in group.attributes"
            :key="attr.attribute"
            :label="attr.attribute_name"
            :required="attr.is_required"
          >
            <!-- Text -->
            <input
              v-if="attr.data_type === 'Text'"
              v-model="localValues[attr.attribute]"
              type="text"
              class="input-premium"
              :placeholder="attr.attribute_name"
            />
            <!-- Integer -->
            <input
              v-else-if="attr.data_type === 'Integer'"
              v-model.number="localValues[attr.attribute]"
              type="number"
              step="1"
              dir="ltr"
              class="input-premium"
              placeholder="0"
            />
            <!-- Decimal -->
            <div v-else-if="attr.data_type === 'Decimal'" class="relative" dir="ltr">
              <input
                v-model.number="localValues[attr.attribute]"
                type="number"
                step="any"
                class="input-premium"
                placeholder="0.0"
              />
            </div>
            <!-- Check (checkbox/switch) -->
            <label v-else-if="attr.data_type === 'Check'" class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                :checked="localValues[attr.attribute] === true || localValues[attr.attribute] === 1"
                class="rounded border-ivory-400 text-gold-500 focus:ring-gold-400 w-4 h-4"
                @change="localValues[attr.attribute] = $event.target.checked ? 1 : 0"
              />
              <span class="text-sm text-navy-700">{{ localValues[attr.attribute] ? 'نعم' : 'لا' }}</span>
            </label>
            <!-- Select -->
            <select
              v-else-if="attr.data_type === 'Select'"
              v-model="localValues[attr.attribute]"
              class="input-premium"
            >
              <option value="">— اختر —</option>
              <option v-for="opt in selectOptions(attr.options)" :key="opt" :value="opt">{{ opt }}</option>
            </select>
            <!-- Date -->
            <input
              v-else-if="attr.data_type === 'Date'"
              v-model="localValues[attr.attribute]"
              type="date"
              dir="ltr"
              class="input-premium"
            />
          </FormField>
        </div>
      </div>
    </div>

    <!-- Meter native fields (conditional on capability) -->
    <div v-if="showMeterFields" class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-ivory-200">
      <!-- Electricity meter fields -->
      <template v-if="electricityMeterEnabled">
        <FormField label="رقم عداد الكهرباء">
          <input
            v-model="meterForm.electricity_meter_number"
            type="text"
            dir="ltr"
            placeholder="رقم العداد"
            class="input-premium"
            :disabled="!editableFields.includes('current_electricity_meter_reading')"
            :class="{ 'opacity-60': !editableFields.includes('current_electricity_meter_reading') }"
          />
        </FormField>
        <FormField label="آخر قراءة كهرباء">
          <input
            v-model="meterForm.current_electricity_meter_reading"
            type="text"
            dir="ltr"
            placeholder="أدخل قراءة العداد"
            class="input-premium"
            :disabled="!editableFields.includes('current_electricity_meter_reading')"
            :class="{ 'opacity-60': !editableFields.includes('current_electricity_meter_reading') }"
          />
        </FormField>
      </template>

      <!-- Water meter fields -->
      <template v-if="waterMeterEnabled">
        <FormField label="رقم عداد المياه">
          <input
            v-model="meterForm.water_meter_number"
            type="text"
            dir="ltr"
            placeholder="رقم العداد"
            class="input-premium"
            :disabled="!editableFields.includes('current_water_meter_reading')"
            :class="{ 'opacity-60': !editableFields.includes('current_water_meter_reading') }"
          />
        </FormField>
        <FormField label="آخر قراءة مياه">
          <input
            v-model="meterForm.current_water_meter_reading"
            type="text"
            dir="ltr"
            placeholder="أدخل قراءة العداد"
            class="input-premium"
            :disabled="!editableFields.includes('current_water_meter_reading')"
            :class="{ 'opacity-60': !editableFields.includes('current_water_meter_reading') }"
          />
        </FormField>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import FormField from '@/components/ui/FormField.vue'
import { callApi } from '@/composables/useApi'

const props = defineProps({
  unitType: { type: String, default: '' },
  // Existing attribute values: { attr_name: value, ... }
  existingValues: { type: Object, default: () => ({}) },
  // Existing meter form data
  existingMeterForm: { type: Object, default: () => ({}) },
  // Editable fields (for edit mode meter reading protection)
  editableFields: { type: Array, default: () => [] },
  // Whether to show meter fields section
  showMeterFields: { type: Boolean, default: true },
})
const emit = defineEmits(['update:attributeValues', 'update:meterForm'])

// State
const typeAttributes = ref([])
const localValues = ref({})
const meterForm = ref({
  electricity_meter_number: '',
  current_electricity_meter_reading: '',
  water_meter_number: '',
  current_water_meter_reading: '',
})

// Category labels
const CATEGORY_LABELS = {
  internal: 'مواصفات داخلية',
  external: 'مواصفات خارجية',
  services: 'خدمات',
  commercial: 'مواصفات تجارية',
  warehouse: 'مواصفات مستودع',
  office: 'مواصفات مكتبية',
  other: 'مواصفات أخرى',
  '': '',
}

// Computed: electricity_meter capability enabled?
const electricityMeterEnabled = computed(() => {
  // Find the electricity_meter attribute in typeAttributes
  const elecAttr = typeAttributes.value.find(a => a.capability_code === 'electricity_meter')
  if (!elecAttr) return false
  const val = localValues.value[elecAttr.attribute]
  return val === true || val === 1
})

const waterMeterEnabled = computed(() => {
  const waterAttr = typeAttributes.value.find(a => a.capability_code === 'water_meter')
  if (!waterAttr) return false
  const val = localValues.value[waterAttr.attribute]
  return val === true || val === 1
})

// Group attributes by category for display
const groupedAttributes = computed(() => {
  const groups = {}
  for (const attr of typeAttributes.value) {
    const cat = attr.category || ''
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(attr)
  }
  // Return in a stable order
  const order = ['internal', 'external', 'services', 'commercial', 'warehouse', 'office', 'other', '']
  return order
    .filter(cat => groups[cat])
    .map(cat => ({
      category: cat,
      label: CATEGORY_LABELS[cat] || cat,
      attributes: groups[cat],
    }))
})

// Parse select options (newline-separated string)
function selectOptions(optionsStr) {
  if (!optionsStr) return []
  return optionsStr.split('\n').map(o => o.trim()).filter(Boolean)
}

// Load type attributes when unit type changes
async function loadTypeAttributes() {
  if (!props.unitType) {
    typeAttributes.value = []
    return
  }
  try {
    const res = await callApi('rental.rental.api.property.get_unit_type_attributes_for_unit', {
      unit_type: props.unitType,
    })
    typeAttributes.value = res.attributes || []
  } catch {
    typeAttributes.value = []
  }
}

// Initialize values when attributes or existing values change
function initValues() {
  // For each type attribute, initialize from existing values or set default
  for (const attr of typeAttributes.value) {
    if (attr.attribute in props.existingValues) {
      // Use existing value — preserve 0, false, etc. correctly
      localValues.value[attr.attribute] = props.existingValues[attr.attribute]
    } else {
      // Default: Check → 0 (unchecked), others → null
      if (attr.data_type === 'Check') {
        localValues.value[attr.attribute] = 0
      } else {
        localValues.value[attr.attribute] = null
      }
    }
  }
}

// Initialize meter form from existing data
function initMeterForm() {
  meterForm.value = {
    electricity_meter_number: props.existingMeterForm?.electricity_meter_number || '',
    current_electricity_meter_reading: props.existingMeterForm?.current_electricity_meter_reading || '',
    water_meter_number: props.existingMeterForm?.water_meter_number || '',
    current_water_meter_reading: props.existingMeterForm?.current_water_meter_reading || '',
  }
}

// Watch for unit type changes
watch(() => props.unitType, async () => {
  await loadTypeAttributes()
  initValues()
}, { immediate: true })

// Watch for existing values changes (e.g. when loading edit data)
watch(() => props.existingValues, () => {
  initValues()
}, { deep: true })

watch(() => props.existingMeterForm, () => {
  initMeterForm()
}, { deep: true, immediate: true })

// Emit changes
watch(localValues, () => {
  emit('update:attributeValues', { ...localValues.value })
}, { deep: true })

watch(meterForm, () => {
  emit('update:meterForm', { ...meterForm.value })
}, { deep: true })

// Expose for parent to get current values
defineExpose({
  getAttributeValues: () => ({ ...localValues.value }),
  getMeterForm: () => ({ ...meterForm.value }),
  electricityMeterEnabled,
  waterMeterEnabled,
})
</script>
