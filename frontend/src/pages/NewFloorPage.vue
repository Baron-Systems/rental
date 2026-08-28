<template>
  <AppLayout>
    <div class="p-6 lg:p-8 max-w-2xl" dir="rtl">
      <!-- Custom header (no PageHeader per spec §21) -->
      <div class="flex items-center gap-3 mb-6">
        <h1 class="text-2xl font-bold text-navy-900">طابق جديد</h1>
      </div>

      <Card padding="lg">
        <form @submit.prevent="save" class="space-y-5">
          <FormField label="العقار" required>
            <select v-model="form.building" required class="input-premium">
              <option value="">اختر العقار *</option>
              <option v-for="b in buildings" :key="b.name" :value="b.name">{{ b.building_name }}</option>
            </select>
          </FormField>
          <FormField label="اسم الطابق" required>
            <input v-model="form.floor_name" type="text" required class="input-premium" placeholder="اسم الطابق *" />
          </FormField>
          <FormField label="ترتيب العرض">
            <input v-model.number="form.sort_order" type="number" dir="ltr" class="input-premium" placeholder="ترتيب العرض" />
          </FormField>

          <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
            <p class="text-xs font-bold text-red-700 mb-1">تعذّر إنشاء الطابق</p>
            {{ error }}
          </div>

          <div class="flex items-center justify-end gap-3 pt-4 border-t border-ivory-300/60">
            <button type="button" class="btn-premium btn-outline" @click="router.push({ name: 'Floors' })">إلغاء</button>
            <button type="submit" class="btn-premium btn-gold" :disabled="saving">
              <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
          </div>
        </form>
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { frappeRequest } from 'frappe-ui'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import FormField from '@/components/ui/FormField.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const toast = useToast()

const buildings = ref([])
const saving = ref(false)
const error = ref('')
const form = ref({ building: '', floor_name: '', sort_order: 0 })

async function loadBuildings() {
  try {
    const res = await callApi('rental.rental.api.property.get_buildings', { simple: 1, include_inactive: 1, limit: 100 })
    buildings.value = res || []
  } catch { buildings.value = [] }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    await frappeRequest({
      url: '/api/method/rental.rental.api.property.create_floor',
      method: 'POST',
      params: form.value,
    })
    toast.success('تم إنشاء الطابق')
    router.push({ name: 'Floors' })
  } catch (e) {
    error.value = extractError(e)
  } finally {
    saving.value = false
  }
}

onMounted(loadBuildings)
</script>
