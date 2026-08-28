<template>
  <Modal :model-value="true" title="إضافة وحدة" size="lg" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="رقم الوحدة" required>
          <input v-model="form.unit_number" type="text" required placeholder="101" class="input-premium" />
        </FormField>
        <FormField label="نوع الوحدة">
          <select v-model="form.unit_type" required class="input-premium">
            <option value="apartment">شقة</option>
            <option value="shop">محل</option>
            <option value="office">مكتب</option>
            <option value="warehouse">مستودع</option>
            <option value="room">غرفة</option>
            <option value="garage">كراج</option>
            <option value="independent">عقار مستقل</option>
            <option value="other">أخرى</option>
          </select>
        </FormField>
        <FormField label="الطابق">
          <select v-model="form.floor" class="input-premium">
            <option value="">بدون طابق</option>
            <option v-for="f in props.floors" :key="f.name" :value="f.name">{{ f.floor_name }}</option>
          </select>
        </FormField>
        <FormField label="المساحة">
          <div class="relative">
            <input v-model.number="form.area" type="number" step="any" dir="ltr" placeholder="120" class="input-premium pl-10" />
            <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-xs font-medium text-navy-400">م²</span>
          </div>
        </FormField>
        <FormField label="عدد الغرف">
          <input v-model.number="form.rooms_count" type="number" dir="ltr" placeholder="0" class="input-premium" />
        </FormField>
        <FormField label="عدد الحمامات">
          <input v-model.number="form.bathrooms_count" type="number" dir="ltr" placeholder="0" class="input-premium" />
        </FormField>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="آخر قراءة كهرباء">
          <input v-model="form.current_electricity_meter_reading" type="text" dir="ltr" placeholder="أدخل قراءة العداد" class="input-premium" />
        </FormField>
        <FormField label="آخر قراءة مياه">
          <input v-model="form.current_water_meter_reading" type="text" dir="ltr" placeholder="أدخل قراءة العداد" class="input-premium" />
        </FormField>
      </div>
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
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'

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
  rooms_count: null,
  bathrooms_count: null,
  current_electricity_meter_reading: '',
  current_water_meter_reading: '',
  notes: '',
  building: props.buildingName,
})
const saving = ref(false)

const suggestedUnitNumber = computed(() => {
  if (!props.existingUnits || props.existingUnits.length === 0) return '1'
  const nums = props.existingUnits
    .map(u => parseInt((u.unit_number || '').match(/\d+/)?.[0] || '0', 10))
    .filter(n => !isNaN(n))
  if (nums.length === 0) return '1'
  return String(Math.max(...nums) + 1)
})

// Apply suggested unit number on mount (source: page.tsx:305-315, 490)
onMounted(() => {
  if (!form.value.unit_number) {
    form.value.unit_number = suggestedUnitNumber.value
  }
})

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    Object.keys(payload).forEach(k => {
      if (payload[k] === '' || payload[k] === null) delete payload[k]
    })
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
