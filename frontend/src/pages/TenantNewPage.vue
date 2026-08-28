<template>
  <AppLayout>
    <div class="p-6 lg:p-8 max-w-3xl" dir="rtl">
      <PageHeader title="مستأجر جديد" back-href="/tenants" />

      <Card padding="lg">
        <form @submit.prevent="save" class="space-y-6">
          <!-- Inline error alert -->
          <Alert v-if="error" :show="true" type="error" title="تعذر حفظ المستأجر" :message="error" />

          <!-- Basic Info -->
          <div>
            <h3 class="text-sm font-bold text-navy-800 mb-4 flex items-center gap-2">
              <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
              البيانات الأساسية
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <FormField label="الاسم الكامل" required>
                <input v-model="form.full_name" type="text" required maxlength="100" class="input-premium" placeholder="الاسم الكامل" />
              </FormField>
              <FormField label="رقم الهوية" required>
                <input v-model="form.national_id" type="text" required maxlength="50" class="input-premium" placeholder="رقم الهوية" />
              </FormField>
              <FormField label="رقم الهاتف">
                <input v-model="form.phone" type="tel" dir="ltr" maxlength="20" class="input-premium" placeholder="رقم الهاتف" />
              </FormField>
              <FormField label="جهة العمل">
                <input v-model="form.workplace" type="text" maxlength="100" class="input-premium" placeholder="جهة العمل" />
              </FormField>
            </div>
          </div>

          <!-- Guarantor -->
          <div class="pt-4 border-t border-ivory-300/60">
            <h3 class="text-sm font-bold text-navy-800 mb-4 flex items-center gap-2">
              <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
              بيانات الكفيل
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <FormField label="اسم الكفيل">
                <input v-model="form.guarantor_name" type="text" maxlength="100" class="input-premium" placeholder="اسم الكفيل" />
              </FormField>
              <FormField label="هاتف الكفيل">
                <input v-model="form.guarantor_phone" type="tel" dir="ltr" maxlength="20" class="input-premium" placeholder="هاتف الكفيل" />
              </FormField>
            </div>
          </div>

          <div class="flex gap-2 justify-end pt-4 border-t border-ivory-300/60">
            <button type="button" class="btn-premium btn-outline" @click="cancel">إلغاء</button>
            <button type="submit" class="btn-premium btn-gold" :disabled="saving">
              <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              {{ saving ? 'جاري الحفظ...' : 'حفظ المستأجر' }}
            </button>
          </div>
        </form>
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import FormField from '@/components/ui/FormField.vue'
import Alert from '@/components/ui/Alert.vue'
import { callApi, extractError } from '@/composables/useApi'

const router = useRouter()

const saving = ref(false)
const error = ref('')

const form = ref({
  full_name: '', national_id: '', phone: '',
  workplace: '', guarantor_name: '', guarantor_phone: '',
})

function cancel() {
  router.push({ name: 'Tenants' })
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const payload = { ...form.value }
    Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k] })
    await callApi('rental.rental.api.tenant.create_tenant', payload)
    router.push({ name: 'Tenants' })
  } catch (e) {
    error.value = extractError(e) || 'حدث خطأ'
  } finally {
    saving.value = false
  }
}
</script>
