<template>
  <div class="space-y-3">
    <!-- Unit Attributes list -->
    <Card padding="md">
      <template #title>
        <span class="flex items-center gap-2">
          <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
          خصائص الوحدات
        </span>
      </template>

      <!-- Add button -->
      <div class="mb-3">
        <button class="btn-premium btn-gold" @click="openCreateDialog">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          إضافة خاصية جديدة
        </button>
      </div>

      <!-- List -->
      <div class="space-y-2">
        <div
          v-for="attr in unitAttributes"
          :key="attr.name"
          class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 rounded-lg border border-ivory-300/50 bg-ivory-50/50 px-4 py-3"
        >
          <div class="flex items-center gap-3 flex-wrap">
            <span class="text-sm font-medium text-navy-800">{{ attr.attribute_name }}</span>
            <span
              class="text-xs px-2 py-0.5 rounded-full font-medium"
              :class="attr.is_system
                ? 'bg-gold-100 text-gold-700'
                : 'bg-ivory-200 text-navy-500'"
            >
              {{ attr.is_system ? 'نظامي' : 'مخصص' }}
            </span>
            <span class="text-xs text-navy-400">{{ dataTypeLabel(attr.data_type) }}</span>
            <span
              v-if="attr.capability_code"
              class="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-600"
            >عداد</span>
            <span v-if="attr.type_assignment_count > 0" class="text-xs text-navy-400">
              مستخدم في {{ attr.type_assignment_count }} نوع
            </span>
          </div>
          <div class="flex items-center gap-2">
            <!-- Edit (custom only) -->
            <button
              v-if="!attr.is_system"
              class="flex items-center justify-center h-7 w-7 rounded-md text-navy-500 hover:bg-ivory-200 transition-colors"
              title="تعديل"
              @click="openEditDialog(attr)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            </button>
            <!-- Toggle active -->
            <button
              class="text-xs px-2 py-1 rounded-md font-medium transition-colors"
              :class="attr.is_active
                ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                : 'bg-ivory-200 text-navy-400 hover:bg-ivory-300'"
              @click="toggleAttribute(attr)"
            >
              {{ attr.is_active ? 'نشط' : 'معطل' }}
            </button>
            <!-- Delete (custom only) -->
            <button
              v-if="!attr.is_system"
              class="flex items-center justify-center h-7 w-7 rounded-md text-red-600/80 hover:bg-red-50 hover:text-red-700 transition-colors"
              title="حذف"
              @click="deleteAttribute(attr)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
        </div>
      </div>
      <div v-if="!unitAttributes.length" class="text-center py-8 text-navy-400 text-sm">
        <p class="font-medium">لا توجد خصائص وحدات</p>
        <p class="text-xs mt-1">لم يتم إضافة أي خصائص وحدات بعد.</p>
      </div>
    </Card>

    <!-- Create / Edit Dialog -->
    <Modal v-model="formDialogOpen" :title="formMode === 'create' ? 'إضافة خاصية جديدة' : 'تعديل الخاصية'" size="md">
      <div class="space-y-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-navy-500">اسم الخاصية <span class="text-red-500">*</span></label>
          <input v-model="form.attribute_name" type="text" class="input-premium" placeholder="مثلاً: مساحة البلكونة" />
        </div>
        <div class="space-y-1">
          <label class="text-xs font-medium text-navy-500">نوع البيانات <span class="text-red-500">*</span></label>
          <select v-model="form.data_type" class="input-premium" :disabled="formMode === 'edit' && hasStoredValues">
            <option v-for="dt in dataTypes" :key="dt.value" :value="dt.value">{{ dt.label }}</option>
          </select>
          <p v-if="formMode === 'edit' && hasStoredValues" class="text-xs text-amber-600">
            لا يمكن تغيير نوع البيانات لخاصية تحتوي على قيم مخزنة.
          </p>
        </div>
        <div v-if="form.data_type === 'Select'" class="space-y-1">
          <label class="text-xs font-medium text-navy-500">الخيارات <span class="text-red-500">*</span></label>
          <textarea
            v-model="form.options"
            rows="4"
            class="input-premium resize-y"
            placeholder="اكتب كل خيار في سطر منفصل"
          ></textarea>
          <p class="text-xs text-navy-400">اكتب كل خيار في سطر منفصل.</p>
        </div>
        <div class="space-y-1">
          <label class="text-xs font-medium text-navy-500">التصنيف</label>
          <select v-model="form.category" class="input-premium">
            <option value="">— بدون تصنيف —</option>
            <option v-for="c in categories" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1">
            <label class="text-xs font-medium text-navy-500">ترتيب العرض</label>
            <input v-model.number="form.display_order" type="number" min="0" class="input-premium" />
          </div>
          <div class="space-y-1">
            <label class="text-xs font-medium text-navy-500">الحالة</label>
            <select v-model="form.is_active" class="input-premium">
              <option :value="1">نشط</option>
              <option :value="0">معطل</option>
            </select>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-premium btn-outline" @click="formDialogOpen = false">إلغاء</button>
        <button class="btn-premium btn-gold" :disabled="formSaving" @click="saveForm">
          {{ formSaving ? 'جاري الحفظ...' : 'حفظ' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from '@/components/ui/Card.vue'
import Modal from '@/components/ui/Modal.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const toast = useToast()
const { confirm } = useConfirm()

const unitAttributes = ref([])

// Form dialog
const formDialogOpen = ref(false)
const formMode = ref('create') // 'create' | 'edit'
const formSaving = ref(false)
const editingName = ref('')
const editingValueCount = ref(0)

const form = ref({
  attribute_name: '',
  data_type: 'Text',
  options: '',
  category: '',
  is_active: 1,
  display_order: 0,
})

const dataTypes = [
  { value: 'Text', label: 'نص' },
  { value: 'Integer', label: 'رقم صحيح' },
  { value: 'Decimal', label: 'رقم عشري' },
  { value: 'Check', label: 'نعم/لا' },
  { value: 'Select', label: 'قائمة منسدلة' },
  { value: 'Date', label: 'تاريخ' },
]

const categories = [
  { value: 'internal', label: 'داخلي' },
  { value: 'external', label: 'خارجي' },
  { value: 'services', label: 'خدمات' },
  { value: 'commercial', label: 'تجاري' },
  { value: 'warehouse', label: 'مستودع' },
  { value: 'office', label: 'مكتبي' },
  { value: 'other', label: 'أخرى' },
]

const DATA_TYPE_LABELS = {
  Text: 'نص',
  Integer: 'رقم صحيح',
  Decimal: 'رقم عشري',
  Check: 'نعم/لا',
  Select: 'قائمة منسدلة',
  Date: 'تاريخ',
}

const hasStoredValues = computed(() => editingValueCount.value > 0)

function dataTypeLabel(dt) {
  return DATA_TYPE_LABELS[dt] || dt
}

async function fetchUnitAttributes() {
  try {
    const res = await callApi('rental.rental.api.unit_settings.get_unit_attributes', { include_inactive: 1 })
    unitAttributes.value = res.unitAttributes || []
  } catch { unitAttributes.value = [] }
}

function openCreateDialog() {
  formMode.value = 'create'
  editingName.value = ''
  editingValueCount.value = 0
  form.value = {
    attribute_name: '',
    data_type: 'Text',
    options: '',
    category: '',
    is_active: 1,
    display_order: 0,
  }
  formDialogOpen.value = true
}

function openEditDialog(attr) {
  formMode.value = 'edit'
  editingName.value = attr.name
  editingValueCount.value = attr.value_count || 0
  form.value = {
    attribute_name: attr.attribute_name,
    data_type: attr.data_type,
    options: attr.options || '',
    category: attr.category || '',
    is_active: attr.is_active,
    display_order: attr.display_order || 0,
  }
  formDialogOpen.value = true
}

async function saveForm() {
  if (!form.value.attribute_name.trim()) {
    toast.error('اسم الخاصية مطلوب')
    return
  }
  if (form.value.data_type === 'Select' && (!form.value.options || !form.value.options.trim())) {
    toast.error('الخيارات مطلوبة عند اختيار نوع البيانات "قائمة منسدلة"')
    return
  }

  formSaving.value = true
  try {
    if (formMode.value === 'create') {
      await callApi('rental.rental.api.unit_settings.create_unit_attribute', {
        attribute_name: form.value.attribute_name,
        data_type: form.value.data_type,
        options: form.value.data_type === 'Select' ? form.value.options : null,
        category: form.value.category || null,
        is_active: form.value.is_active,
        display_order: form.value.display_order,
      })
      toast.success('تم إضافة الخاصية')
    } else {
      await callApi('rental.rental.api.unit_settings.update_unit_attribute', {
        name: editingName.value,
        attribute_name: form.value.attribute_name,
        data_type: form.value.data_type,
        options: form.value.data_type === 'Select' ? form.value.options : null,
        category: form.value.category || null,
        is_active: form.value.is_active,
        display_order: form.value.display_order,
      })
      toast.success('تم حفظ التعديلات')
    }
    formDialogOpen.value = false
    fetchUnitAttributes()
  } catch (e) { toast.error(extractError(e)) } finally { formSaving.value = false }
}

async function toggleAttribute(attr) {
  try {
    await callApi('rental.rental.api.unit_settings.update_unit_attribute', {
      name: attr.name,
      is_active: attr.is_active ? 0 : 1,
    })
    fetchUnitAttributes()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteAttribute(attr) {
  const ok = await confirm({
    title: 'حذف الخاصية',
    message: `هل أنت متأكد من حذف "${attr.attribute_name}"؟`,
    variant: 'warning',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.unit_settings.delete_unit_attribute', { name: attr.name })
    fetchUnitAttributes()
    toast.success('تم حذف الخاصية')
  } catch (e) { toast.error(extractError(e)) }
}

onMounted(() => { fetchUnitAttributes() })
defineExpose({ fetchUnitAttributes })
</script>
