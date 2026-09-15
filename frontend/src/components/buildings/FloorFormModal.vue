<template>
  <Modal :model-value="true" title="إضافة طابق" size="sm" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <FormField label="اسم الطابق" required :error="errors.floor_name">
        <input v-model="form.floor_name" type="text" placeholder="اسم الطابق *" class="input-premium" @input="errors.floor_name = ''" />
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
import { ref } from 'vue'
import { frappeRequest } from 'frappe-ui'
import { extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'

const toast = useToast()

const props = defineProps({
  buildingName: { type: String, required: true },
  floorCount: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'saved'])

// Source: page.tsx:341 — sortOrder auto-set to building.floors.length
const form = ref({
  floor_name: '',
  sort_order: props.floorCount,
  building: props.buildingName,
})
const saving = ref(false)
const errors = ref({ floor_name: '' })

function validateFloor() {
  errors.value.floor_name = ''
  if (!form.value.floor_name.trim()) {
    errors.value.floor_name = 'اسم الطابق مطلوب'
    return false
  }
  return true
}

async function save() {
  if (!validateFloor()) return
  saving.value = true
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.create_floor',
      method: 'POST',
      params: form.value,
    })
    emit('saved')
  } catch (e) {
    toast.error(extractError(e) || 'تعذّر حفظ البيانات')
  } finally {
    saving.value = false
  }
}
</script>
