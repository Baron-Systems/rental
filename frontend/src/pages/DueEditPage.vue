<template>
  <AppLayout>
    <div class="p-6 lg:p-8 max-w-2xl" dir="rtl">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div v-else-if="!due" class="text-center py-20">
        <p class="text-navy-400">الالتزام غير موجود</p>
        <button class="btn-premium btn-outline mt-4" @click="router.push({ name: 'Dues' })">العودة للقائمة</button>
      </div>

      <div v-else>
        <PageHeader title="تعديل التزام" :back-href="`/dues/${due.name}`" />

        <Card padding="lg">
          <form @submit.prevent="save" class="space-y-5">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <FormField label="نوع الالتزام" required>
                <select v-model="form.due_type" required class="input-premium">
                  <option v-for="dt in dueTypes" :key="dt.name" :value="dt.name">{{ dt.due_type_name }}</option>
                </select>
              </FormField>
              <FormField label="المبلغ" required>
                <input v-model.number="form.amount" type="number" step="0.01" required class="input-premium" />
              </FormField>
              <FormField label="تاريخ الاستحقاق" required>
                <input v-model="form.due_date" type="date" dir="ltr" required class="input-premium" />
              </FormField>
              <FormField label="الوصف">
                <input v-model="form.description" type="text" class="input-premium" />
              </FormField>
              <!-- Meter reading fields (if metered) -->
              <template v-if="due.calculation_method === 'metered'">
                <FormField label="القراءة السابقة">
                  <input v-model.number="form.previous_meter_reading" type="number" step="0.01" class="input-premium" />
                </FormField>
                <FormField label="القراءة الحالية">
                  <input v-model.number="form.current_meter_reading" type="number" step="0.01" class="input-premium" />
                </FormField>
                <FormField label="سعر الوحدة">
                  <input v-model.number="form.unit_price" type="number" step="0.01" class="input-premium" />
                </FormField>
              </template>
            </div>

            <div class="flex gap-2 justify-end pt-4 border-t border-ivory-300/60">
              <button type="button" class="btn-premium btn-outline" @click="router.push({ name: 'DueDetail', params: { id: due.name } })">إلغاء</button>
              <button type="submit" class="btn-premium btn-gold" :disabled="saving">
                <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
                حفظ
              </button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import FormField from '@/components/ui/FormField.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const due = ref(null)
const dueTypes = ref([])
const loading = ref(true)
const saving = ref(false)

const form = ref({
  due_type: '', amount: null, due_date: '', description: '',
  previous_meter_reading: null, current_meter_reading: null, unit_price: null,
})

async function fetchDue() {
  loading.value = true
  try {
    due.value = await callApi('rental.rental.api.due.get_due', { name: route.params.id })
    form.value = {
      due_type: due.value.due_type || '',
      amount: due.value.amount || null,
      due_date: due.value.due_date || '',
      description: due.value.description || '',
      previous_meter_reading: due.value.previous_meter_reading ?? null,
      current_meter_reading: due.value.current_meter_reading ?? null,
      unit_price: due.value.unit_price ?? null,
    }
    // Load due types
    const dtRes = await callApi('rental.rental.api.settings.get_due_types')
    dueTypes.value = (dtRes.dueTypes || dtRes || []).filter(dt => !dt.is_system || dt.due_type_code !== 'rent')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form.value }
    Object.keys(payload).forEach(k => { if (payload[k] === '' || payload[k] === null) delete payload[k] })
    await callApi('rental.rental.api.due.update_due', { name: route.params.id, ...payload })
    toast.success('تم تحديث الالتزام')
    router.push({ name: 'DueDetail', params: { id: route.params.id } })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    saving.value = false
  }
}

onMounted(fetchDue)
</script>
