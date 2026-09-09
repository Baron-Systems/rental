<template>
  <div class="space-y-3">
    <!-- Unit Types list -->
    <Card padding="md">
      <template #title>
        <span class="flex items-center gap-2">
          <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
          أنواع الوحدات
        </span>
      </template>

      <!-- Inline add -->
      <div class="mb-3 flex gap-2">
        <input
          v-model="newTypeName"
          type="text"
          placeholder="اسم نوع الوحدة الجديد"
          class="input-premium flex-1"
          @keydown.enter="addUnitType"
        />
        <button class="btn-premium btn-gold" @click="addUnitType">إضافة</button>
      </div>

      <!-- List -->
      <div class="space-y-2">
        <div
          v-for="ut in unitTypes"
          :key="ut.name"
          class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 rounded-lg border border-ivory-300/50 bg-ivory-50/50 px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-navy-800">{{ ut.type_name }}</span>
            <span
              class="text-xs px-2 py-0.5 rounded-full font-medium"
              :class="ut.is_system
                ? 'bg-gold-100 text-gold-700'
                : 'bg-ivory-200 text-navy-500'"
            >
              {{ ut.is_system ? 'نظامي' : 'مخصص' }}
            </span>
            <span v-if="ut.unit_count > 0" class="text-xs text-navy-400">
              {{ ut.unit_count }} وحدة
            </span>
            <span v-if="ut.attribute_count > 0" class="text-xs text-navy-400">
              {{ ut.attribute_count }} خاصية
            </span>
          </div>
          <div class="flex items-center gap-2">
            <!-- Manage attributes -->
            <button
              class="text-xs px-2 py-1 rounded-md font-medium transition-colors bg-navy-50 text-navy-600 hover:bg-navy-100"
              @click="openAttributesDialog(ut)"
            >
              الخصائص
            </button>
            <!-- Edit (custom only) -->
            <button
              v-if="!ut.is_system"
              class="flex items-center justify-center h-7 w-7 rounded-md text-navy-500 hover:bg-ivory-200 transition-colors"
              title="تعديل"
              @click="openEditDialog(ut)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
            </button>
            <!-- Toggle active -->
            <button
              class="text-xs px-2 py-1 rounded-md font-medium transition-colors"
              :class="ut.is_active
                ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                : 'bg-ivory-200 text-navy-400 hover:bg-ivory-300'"
              @click="toggleUnitType(ut)"
            >
              {{ ut.is_active ? 'نشط' : 'معطل' }}
            </button>
            <!-- Delete (custom only) -->
            <button
              v-if="!ut.is_system"
              class="flex items-center justify-center h-7 w-7 rounded-md text-red-600/80 hover:bg-red-50 hover:text-red-700 transition-colors"
              title="حذف"
              @click="deleteUnitType(ut)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </div>
        </div>
      </div>
      <div v-if="!unitTypes.length" class="text-center py-8 text-navy-400 text-sm">
        <p class="font-medium">لا توجد أنواع وحدات</p>
        <p class="text-xs mt-1">لم يتم إضافة أي أنواع وحدات بعد.</p>
      </div>
    </Card>

    <!-- Edit Dialog -->
    <Modal v-model="editDialogOpen" title="تعديل نوع الوحدة" size="sm">
      <div class="space-y-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-navy-500">اسم نوع الوحدة <span class="text-red-500">*</span></label>
          <input v-model="editForm.type_name" type="text" class="input-premium" />
        </div>
        <div class="space-y-1">
          <label class="text-xs font-medium text-navy-500">ترتيب العرض</label>
          <input v-model.number="editForm.display_order" type="number" min="0" class="input-premium" />
        </div>
      </div>
      <template #footer>
        <button class="btn-premium btn-outline" @click="editDialogOpen = false">إلغاء</button>
        <button class="btn-premium btn-gold" :disabled="editSaving" @click="saveEdit">
          {{ editSaving ? 'جاري الحفظ...' : 'حفظ' }}
        </button>
      </template>
    </Modal>

    <!-- Attributes Management Dialog -->
    <Modal v-model="attrDialogOpen" :title="`خصائص: ${attrDialogType?.type_name || ''}`" size="lg">
      <div v-if="attrDialogLoading" class="flex items-center justify-center py-12">
        <div class="w-6 h-6 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
      <div v-else class="space-y-3">
        <!-- Add attribute -->
        <div class="flex gap-2">
          <select v-model="newAttrSelection" class="input-premium flex-1">
            <option value="">— اختر خاصية للإضافة —</option>
            <option v-for="a in availableAttrs" :key="a.name" :value="a.name">
              {{ a.attribute_name }}
            </option>
          </select>
          <button class="btn-premium btn-gold" :disabled="!newAttrSelection" @click="addAttrToDraft">
            إضافة
          </button>
        </div>

        <!-- Assigned attributes list (Drag & Drop) -->
        <div class="space-y-2">
          <div
            v-for="(attr, idx) in draftAttrs"
            :key="attr.attribute"
            class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 rounded-lg border bg-ivory-50/50 px-4 py-3 transition-all"
            :class="{
              'border-ivory-300/50': dragIndex !== idx,
              'border-gold-400 bg-gold-50/30 shadow-sm': dragIndex === idx,
              'border-gold-400 border-t-4': dragOverIndex === idx && dragIndex !== idx,
            }"
            @dragover.prevent="onDragOver(idx)"
            @dragleave="onDragLeave(idx)"
            @drop.prevent="onDrop(idx)"
          >
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <!-- Drag Handle -->
              <span
                class="drag-handle cursor-grab active:cursor-grabbing text-navy-300 hover:text-navy-500 select-none text-lg leading-none flex-shrink-0"
                draggable="true"
                @dragstart="onDragStart(idx, $event)"
                @dragend="onDragEnd"
                title="اسحب لإعادة الترتيب"
              >
                ⠿
              </span>
              <span class="text-sm font-medium text-navy-800">{{ attr.attribute_name }}</span>
              <span
                v-if="attr.is_system"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-gold-100 text-gold-700"
              >نظامي</span>
              <span class="text-xs text-navy-400">{{ dataTypeLabel(attr.data_type) }}</span>
              <span
                v-if="attr.capability_code"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-600"
              >عداد</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Required toggle (local draft) -->
              <label class="flex items-center gap-1 text-xs text-navy-500 cursor-pointer">
                <input
                  type="checkbox"
                  :checked="attr.is_required"
                  class="rounded border-ivory-400 text-gold-500 focus:ring-gold-400"
                  @change="toggleRequired(attr, $event.target.checked)"
                />
                إلزامي
              </label>
              <!-- Remove (local draft) -->
              <button
                class="flex items-center justify-center h-7 w-7 rounded-md text-red-600/80 hover:bg-red-50 hover:text-red-700 transition-colors"
                title="إزالة"
                @click="removeAttrFromDraft(attr)"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
          </div>
          <div v-if="!draftAttrs.length" class="text-center py-6 text-navy-400 text-sm">
            <p>لا توجد خصائص مضافة لهذا النوع بعد.</p>
          </div>
        </div>
        <p class="text-xs text-navy-400 bg-ivory-100 rounded-lg p-3">
          ملاحظة: إزالة خاصية من نوع الوحدة لا يحذف القيم المخزنة من الوحدات الموجودة.
        </p>
      </div>
      <template #footer>
        <button class="btn-premium btn-outline" @click="cancelAttrDialog">إلغاء</button>
        <button class="btn-premium btn-outline" :disabled="attrSaving" @click="resetAttrPreferences">
          <span v-if="attrSaving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
          {{ attrSaving ? 'جاري الحفظ...' : 'إعادة الافتراضي' }}
        </button>
        <button class="btn-premium btn-gold" :disabled="attrSaving" @click="saveAttrDraft">
          <span v-if="attrSaving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
          {{ attrSaving ? 'جاري الحفظ...' : 'تم' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Card from '@/components/ui/Card.vue'
import Modal from '@/components/ui/Modal.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const toast = useToast()
const { confirm } = useConfirm()

const unitTypes = ref([])
const newTypeName = ref('')

// Edit dialog
const editDialogOpen = ref(false)
const editSaving = ref(false)
const editForm = ref({ name: '', type_name: '', display_order: 0 })

// Attributes dialog
const attrDialogOpen = ref(false)
const attrDialogLoading = ref(false)
const attrDialogType = ref(null)
const draftAttrs = ref([])       // local draft — changes are not sent until "تم"
const availableAttrs = ref([])
const newAttrSelection = ref('')
const attrSaving = ref(false)
const originalAssignedAttrs = ref([])  // full original list from backend (for save payload)

// Drag & Drop state
const dragIndex = ref(null)
const dragOverIndex = ref(null)

const DATA_TYPE_LABELS = {
  Text: 'نص',
  Integer: 'رقم صحيح',
  Decimal: 'رقم عشري',
  Check: 'نعم/لا',
  Select: 'قائمة منسدلة',
  Date: 'تاريخ',
}

function dataTypeLabel(dt) {
  return DATA_TYPE_LABELS[dt] || dt
}

async function fetchUnitTypes() {
  try {
    const res = await callApi('rental.rental.api.unit_settings.get_unit_types', { include_inactive: 1 })
    unitTypes.value = res.unitTypes || []
  } catch { unitTypes.value = [] }
}

async function addUnitType() {
  if (!newTypeName.value.trim()) return
  try {
    await callApi('rental.rental.api.unit_settings.create_unit_type', {
      type_name: newTypeName.value,
    })
    newTypeName.value = ''
    fetchUnitTypes()
    toast.success('تم إضافة نوع الوحدة')
  } catch (e) { toast.error(extractError(e)) }
}

async function toggleUnitType(ut) {
  try {
    await callApi('rental.rental.api.unit_settings.update_unit_type', {
      name: ut.name,
      is_active: ut.is_active ? 0 : 1,
    })
    fetchUnitTypes()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteUnitType(ut) {
  const ok = await confirm({
    title: 'حذف نوع الوحدة',
    message: `هل أنت متأكد من حذف "${ut.type_name}"؟`,
    variant: 'warning',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.unit_settings.delete_unit_type', { name: ut.name })
    fetchUnitTypes()
    toast.success('تم حذف نوع الوحدة')
  } catch (e) { toast.error(extractError(e)) }
}

function openEditDialog(ut) {
  editForm.value = {
    name: ut.name,
    type_name: ut.type_name,
    display_order: ut.display_order || 0,
  }
  editDialogOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.type_name.trim()) {
    toast.error('اسم نوع الوحدة مطلوب')
    return
  }
  editSaving.value = true
  try {
    await callApi('rental.rental.api.unit_settings.update_unit_type', {
      name: editForm.value.name,
      type_name: editForm.value.type_name,
      display_order: editForm.value.display_order,
    })
    editDialogOpen.value = false
    fetchUnitTypes()
    toast.success('تم حفظ التعديلات')
  } catch (e) { toast.error(extractError(e)) } finally { editSaving.value = false }
}

// --- Attributes management (local draft + Drag & Drop) ---

async function openAttributesDialog(ut) {
  attrDialogType.value = ut
  attrDialogOpen.value = true
  attrDialogLoading.value = true
  newAttrSelection.value = ''
  draftAttrs.value = []
  originalAssignedAttrs.value = []
  dragIndex.value = null
  dragOverIndex.value = null
  try {
    const [assigned, available] = await Promise.all([
      callApi('rental.rental.api.unit_settings.get_unit_type_attributes', { unit_type: ut.name }),
      callApi('rental.rental.api.unit_settings.get_available_attributes', { unit_type: ut.name }),
    ])
    // Sort by display_order then attribute_name (matching backend sort)
    const attrs = (assigned.attributes || []).slice().sort((a, b) => {
      const ao = a.display_order || 0
      const bo = b.display_order || 0
      if (ao !== bo) return ao - bo
      return (a.attribute_name || '').localeCompare(b.attribute_name || '')
    })
    draftAttrs.value = attrs
    originalAssignedAttrs.value = assigned.attributes || []
    availableAttrs.value = available.attributes || []
  } catch (e) {
    toast.error(extractError(e))
    draftAttrs.value = []
    originalAssignedAttrs.value = []
    availableAttrs.value = []
  } finally { attrDialogLoading.value = false }
}

// Add to draft (appended at end) — no API call
function addAttrToDraft() {
  if (!newAttrSelection.value) return
  const attrName = newAttrSelection.value
  // Prevent duplicates in draft
  if (draftAttrs.value.some(a => a.attribute === attrName)) {
    toast.error('الخاصية مضافة بالفعل')
    return
  }
  // Find attribute details from available list
  const details = availableAttrs.value.find(a => a.name === attrName)
  if (!details) return
  draftAttrs.value.push({
    attribute: details.name,
    attribute_name: details.attribute_name,
    data_type: details.data_type,
    is_system: details.is_system,
    capability_code: details.capability_code,
    is_required: 0,
    is_active: 1,
    display_order: draftAttrs.value.length,
  })
  // Remove from available list
  availableAttrs.value = availableAttrs.value.filter(a => a.name !== attrName)
  newAttrSelection.value = ''
}

// Remove from draft — no API call
function removeAttrFromDraft(attr) {
  draftAttrs.value = draftAttrs.value.filter(a => a.attribute !== attr.attribute)
  // Re-add to available list
  availableAttrs.value.push({
    name: attr.attribute,
    attribute_name: attr.attribute_name,
    data_type: attr.data_type,
    is_system: attr.is_system,
    capability_code: attr.capability_code,
  })
}

// Toggle is_required in draft — no API call
function toggleRequired(attr, checked) {
  attr.is_required = checked ? 1 : 0
}

// --- Drag & Drop handlers (native HTML5 DnD, handle-only) ---

function onDragStart(idx, event) {
  dragIndex.value = idx
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(idx))
  // Set a custom drag image (the row itself)
  // Slight transparency for visual feedback
}

function onDragOver(idx) {
  if (dragIndex.value === null) return
  dragOverIndex.value = idx
}

function onDragLeave(idx) {
  if (dragOverIndex.value === idx) {
    dragOverIndex.value = null
  }
}

function onDrop(idx) {
  if (dragIndex.value === null || dragIndex.value === idx) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  // Reorder draftAttrs: move item from dragIndex to idx
  const item = draftAttrs.value.splice(dragIndex.value, 1)[0]
  draftAttrs.value.splice(idx, 0, item)
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

// --- Save (called by "تم" button) ---

async function saveAttrDraft() {
  if (!attrDialogType.value) return
  attrSaving.value = true
  try {
    // Build payload from ALL originally assigned attributes.
    // Attributes still in draft → is_active=1 with new order.
    // Attributes removed from draft → is_active=0 (preserving original order as fallback).
    const draftMap = new Map()
    draftAttrs.value.forEach((attr, idx) => {
      draftMap.set(attr.attribute, { ...attr, display_order: idx })
    })

    const payload = originalAssignedAttrs.value.map((orig) => {
      const draft = draftMap.get(orig.attribute)
      if (draft) {
        return {
          attribute: orig.attribute,
          is_required: draft.is_required ? 1 : 0,
          is_active: 1,
          display_order: draft.display_order,
        }
      }
      // Removed from draft → hidden preference override
      return {
        attribute: orig.attribute,
        is_required: orig.is_required ? 1 : 0,
        is_active: 0,
        display_order: orig.display_order || 0,
      }
    })

    await callApi('rental.rental.api.unit_settings.save_user_unit_type_preferences', {
      unit_type: attrDialogType.value.name,
      attributes: JSON.stringify(payload),
    })
    attrDialogOpen.value = false
    fetchUnitTypes()
    toast.success('تم حفظ التغييرات')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    attrSaving.value = false
  }
}

async function resetAttrPreferences() {
  if (!attrDialogType.value) return
  attrSaving.value = true
  try {
    await callApi('rental.rental.api.unit_settings.reset_user_unit_preferences', {
      unit_type: attrDialogType.value.name,
    })
    // Reload dialog data so defaults are shown
    await openAttributesDialog(attrDialogType.value)
    toast.success('تمت إعادة الافتراضيات')
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    attrSaving.value = false
  }
}

// Cancel — close without saving
function cancelAttrDialog() {
  attrDialogOpen.value = false
  draftAttrs.value = []
  originalAssignedAttrs.value = []
  dragIndex.value = null
  dragOverIndex.value = null
}

onMounted(() => { fetchUnitTypes() })
defineExpose({ fetchUnitTypes })
</script>
