<template>
  <Modal :model-value="true" :title="building ? 'تفعيل/تعطيل العقار' : 'إضافة عقار'" size="md" @update:model-value="$emit('close')">
    <form @submit.prevent="save" class="space-y-4">
      <!-- Create mode: full form -->
      <template v-if="!building">
        <FormField label="اسم العقار" required>
          <input v-model="form.building_name" type="text" required placeholder="اسم العقار *" class="input-premium" />
        </FormField>
        <FormField label="العنوان" required>
          <textarea v-model="form.address" rows="2" required placeholder="العنوان *" class="input-premium"></textarea>
        </FormField>
      </template>

      <!-- Edit mode: only toggle active -->
      <template v-else>
        <div class="space-y-4">
          <div class="bg-navy-50 border border-navy-100 rounded-xl p-4">
            <p class="text-sm text-navy-500 mb-1">اسم العقار</p>
            <p class="font-bold text-navy-800">{{ building.building_name }}</p>
          </div>
          <p class="text-xs text-navy-400">تعديل بيانات العقار غير مسموح به. يمكنك تعطيل/تفعيل العقار أو حذفه إذا لم يُستخدم.</p>
          <label class="flex items-center gap-2 cursor-pointer">
            <input v-model="form.is_active" type="checkbox" class="w-4 h-4 rounded text-gold-500 focus:ring-gold-400" />
            <span class="text-sm font-medium text-navy-700">نشط</span>
          </label>
        </div>
      </template>
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
import Modal from '@/components/ui/Modal.vue'
import FormField from '@/components/ui/FormField.vue'

const props = defineProps({
  building: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])

const form = ref({
  building_name: props.building?.building_name || '',
  address: props.building?.address || '',
  is_active: props.building?.is_active ?? 1,
})
const saving = ref(false)

async function save() {
  saving.value = true
  try {
    if (props.building) {
      // Edit mode: only send is_active
      await frappeRequest({
        url: '/api/method/rental.rental.api.property.update_building',
        method: 'POST',
        params: { name: props.building.name, is_active: form.value.is_active ? 1 : 0 },
      })
    } else {
      // Create mode: send all fields
      await frappeRequest({
        url: '/api/method/rental.rental.api.property.create_building',
        method: 'POST',
        params: form.value,
      })
    }
    emit('saved')
  } catch (e) {
    alert(extractError(e) || 'تعذّر حفظ البيانات')
  } finally {
    saving.value = false
  }
}
</script>
