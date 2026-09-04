<template>
  <Modal :model-value="true" title="إضافة وحدة" size="lg" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="رقم الوحدة" required>
          <input v-model="form.unit_number" type="text" required placeholder="101" class="input-premium" />
        </FormField>
        <FormField label="نوع الوحدة" required :error="unitTypeError">
          <select
            ref="unitTypeSelect"
            v-model="form.unit_type"
            required
            class="input-premium"
            :class="{ 'border-red-500': unitTypeError }"
            @change="onUnitTypeChange"
          >
            <option value="">— اختر —</option>
            <option v-for="t in unitTypes" :key="t.name" :value="t.name">{{ t.type_name }}</option>
          </select>
        </FormField>
        <FormField label="الطابق">
          <select v-model="form.floor" class="input-premium">
            <option value="">بدون طابق</option>
            <option v-for="f in props.floors" :key="f.name" :value="f.name">{{ f.floor_name }}</option>
          </select>
        </FormField>
        <FormField label="المساحة">
          <div class="relative" dir="ltr">
            <input v-model.number="form.area" type="number" step="any" placeholder="120" class="input-premium has-icon-start" />
            <span class="absolute top-1/2 -translate-y-1/2 text-xs font-medium text-navy-400 icon-start">م²</span>
          </div>
        </FormField>
      </div>

      <!-- Dynamic attributes + meter fields -->
      <UnitAttributeFields
        v-if="form.unit_type"
        :unit-type="form.unit_type"
        :existing-values="{}"
        :existing-meter-form="{}"
        :show-meter-fields="true"
        @update:attribute-values="attrValues = $event"
        @update:meter-form="meterForm = $event"
      />

      <FormField label="ملاحظات">
        <textarea v-model="form.notes" rows="2" placeholder="أي ملاحظات إضافية..." class="input-premium"></textarea>
      </FormField>
    </form>
    <template #footer>
      <button class="btn-premium btn-outline" @click="$emit('close')">إلغاء</button>
      <button class="btn-premium btn-gold" :disabled="saving" @click="save">
        <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
        حفظ
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { extractError } from '@/composables/useApi'
import { callApi } from '@/composables/useApi'
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'
import UnitAttributeFields from '@/components/buildings/UnitAttributeFields.vue'

const props = defineProps({
  buildingName: { type: String, required: true },
  floors: { type: Array, default: () => [] },
  existingUnits: { type: Array, default: () => [] },
  preselectedFloor: { type: String, default: null },
})
const emit = defineEmits(['close', 'saved'])

const form = ref({
  unit_number: '',
  unit_type: '',
  floor: props.preselectedFloor || '',
  area: null,
  notes: '',
  building: props.buildingName,
})
const saving = ref(false)
const unitTypes = ref([])
const unitTypeError = ref('')
const unitTypeSelect = ref(null)
const attrValues = ref({})
const meterForm = ref({
  electricity_meter_number: '',
  current_electricity_meter_reading: '',
  water_meter_number: '',
  current_water_meter_reading: '',
})

const suggestedUnitNumber = computed(() => {
  if (!props.existingUnits || props.existingUnits.length === 0) return '1'
  const nums = props.existingUnits
    .map(u => parseInt((u.unit_number || '').match(/\d+/)?.[0] || '0', 10))
    .filter(n => !isNaN(n))
  if (nums.length === 0) return '1'
  return String(Math.max(...nums) + 1)
})

async function fetchUnitTypes() {
  try {
    const res = await callApi('rental.rental.api.property.get_active_unit_types')
    unitTypes.value = res.unitTypes || []
  } catch { unitTypes.value = [] }
}

function onUnitTypeChange() {
  // Reset attribute values when type changes — existing values are not loaded for new units
  attrValues.value = {}
  // Clear validation error when a valid type is selected
  if (form.value.unit_type) {
    unitTypeError.value = ''
  }
}

onMounted(() => {
  if (!form.value.unit_number) {
    form.value.unit_number = suggestedUnitNumber.value
  }
  fetchUnitTypes()
})

async function save() {
  // Frontend validation: unit_type is required before sending to backend
  if (!form.value.unit_type) {
    unitTypeError.value = 'نوع الوحدة مطلوب'
    unitTypeSelect.value?.focus()
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value }
    // Clean empty/null from core fields
    Object.keys(payload).forEach(k => {
      if (payload[k] === '' || payload[k] === null) delete payload[k]
    })

    // Add meter fields only if capabilities are enabled
    if (meterForm.value.electricity_meter_number) {
      payload.electricity_meter_number = meterForm.value.electricity_meter_number
    }
    if (meterForm.value.current_electricity_meter_reading) {
      payload.current_electricity_meter_reading = meterForm.value.current_electricity_meter_reading
    }
    if (meterForm.value.water_meter_number) {
      payload.water_meter_number = meterForm.value.water_meter_number
    }
    if (meterForm.value.current_water_meter_reading) {
      payload.current_water_meter_reading = meterForm.value.current_water_meter_reading
    }

    // Add attribute values as JSON string
    const cleanAttrValues = {}
    for (const [k, v] of Object.entries(attrValues.value)) {
      if (v !== null && v !== '' && v !== undefined) {
        cleanAttrValues[k] = v
      }
    }
    if (Object.keys(cleanAttrValues).length > 0) {
      payload.attribute_values = JSON.stringify(cleanAttrValues)
    }

    await frappeRequest({
      url: '/api/method/rental.rental.api.property.create_unit',
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
