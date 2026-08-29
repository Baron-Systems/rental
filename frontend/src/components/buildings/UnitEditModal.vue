<template>
  <Modal :model-value="true" title="تعديل وحدة" size="lg" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="رقم الوحدة" required>
          <input v-model="form.unit_number" type="text" required placeholder="101" class="input-premium" :disabled="!editableFields.includes('unit_number')" :class="{ 'opacity-60': !editableFields.includes('unit_number') }" />
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
        <FormField label="عدد الغرف">
          <input v-model.number="form.rooms_count" type="number" dir="ltr" placeholder="0" class="input-premium" :disabled="!editableFields.includes('rooms_count')" :class="{ 'opacity-60': !editableFields.includes('rooms_count') }" />
        </FormField>
        <FormField label="عدد الحمامات">
          <input v-model.number="form.bathrooms_count" type="number" dir="ltr" placeholder="0" class="input-premium" :disabled="!editableFields.includes('bathrooms_count')" :class="{ 'opacity-60': !editableFields.includes('bathrooms_count') }" />
        </FormField>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="آخر قراءة كهرباء">
          <input v-model="form.current_electricity_meter_reading" type="text" dir="ltr" placeholder="أدخل قراءة العداد" class="input-premium" :disabled="!editableFields.includes('current_electricity_meter_reading')" :class="{ 'opacity-60': !editableFields.includes('current_electricity_meter_reading') }" />
        </FormField>
        <FormField label="آخر قراءة مياه">
          <input v-model="form.current_water_meter_reading" type="text" dir="ltr" placeholder="أدخل قراءة العداد" class="input-premium" :disabled="!editableFields.includes('current_water_meter_reading')" :class="{ 'opacity-60': !editableFields.includes('current_water_meter_reading') }" />
        </FormField>
      </div>
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
import { ref, onMounted } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { extractError } from '@/composables/useApi'
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'

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
  // Source: page.tsx:479 — floor is {id, name} object, use .id for select value
  floor: props.unit?.floor?.id || props.unit?.floor || '',
  area: props.unit?.area ?? null,
  rooms_count: props.unit?.rooms_count ?? null,
  bathrooms_count: props.unit?.bathrooms_count ?? null,
  current_electricity_meter_reading: props.unit?.current_electricity_meter_reading ?? '',
  current_water_meter_reading: props.unit?.current_water_meter_reading ?? '',
  notes: props.unit?.notes || '',
})
const saving = ref(false)

onMounted(async () => {
  try {
    const res = await frappeRequest({
      url: '/api/method/rental.rental.api.property.get_unit_permissions',
      params: { name: props.unit.name },
    })
    const perms = res?.message || res
    if (perms?.editable_fields) {
      editableFields.value = perms.editable_fields
    }
  } catch { /* ignore — default to all editable */ }
})

async function save() {
  saving.value = true
  try {
    const payload = { name: props.unit.name, ...form.value }
    Object.keys(payload).forEach(k => {
      if (k !== 'name' && (payload[k] === '' || payload[k] === null)) delete payload[k]
    })
    if (payload.floor === '') payload.floor = null
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
