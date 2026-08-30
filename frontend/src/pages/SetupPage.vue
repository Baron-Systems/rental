<template>
  <!-- Loading state (source: page.tsx:156-167) -->
  <div v-if="loading" class="min-h-screen flex items-center justify-center p-4" dir="rtl"
       style="background: linear-gradient(135deg, #012350);">
    <div class="text-center">
      <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
           style="background: #b38942;">
        <svg class="h-6 w-6 text-navy-900 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
      </div>
      <p class="text-white/60">جاري التحميل...</p>
    </div>
  </div>

  <!-- Success state (source: page.tsx:169-183) -->
  <div v-else-if="showSuccess"
       class="min-h-screen flex items-center justify-center p-4 transition-opacity duration-500"
       :class="isFadingOut ? 'opacity-0' : 'opacity-100'" dir="rtl"
       style="background: linear-gradient(135deg, #012350);">
    <div class="text-center">
      <div class="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500 animate-scale-in">
        <svg class="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="animate-fade-in">
        <h1 class="text-2xl font-bold text-white">تم الإعداد بنجاح</h1>
        <p class="mt-2 text-sm text-white/60">جاري فتح لوحة التحكم...</p>
      </div>
    </div>
  </div>

  <!-- Main wizard (source: page.tsx:185-508) -->
  <div v-else class="min-h-screen flex items-center justify-center p-4" dir="rtl"
       style="background: linear-gradient(135deg, #012350);">
    <div class="absolute top-0 left-0 w-96 h-96 rounded-full opacity-10 blur-3xl"
         style="background: radial-gradient(circle, #b38942, transparent);"></div>
    <div class="absolute bottom-0 right-0 w-96 h-96 rounded-full opacity-10 blur-3xl"
         style="background: radial-gradient(circle, #c89a55, transparent);"></div>

    <div class="relative w-full max-w-2xl animate-scale-in">
      <!-- Header (source: page.tsx:188-195) -->
      <div class="mb-8 text-center">
        <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl shadow-soft-lg"
             style="background: #b38942;">
          <svg class="h-6 w-6 text-navy-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white tracking-tight">إعداد النظام لأول مرة</h1>
        <p class="mt-2 text-sm text-white/60">أكمل البيانات التالية لتفعيل النظام</p>
      </div>

      <!-- Progress (source: page.tsx:197-223) -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <template v-for="(s, i) in steps" :key="s.id">
            <div class="flex flex-1 items-center">
              <div class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors"
                   :class="step >= s.id
                     ? 'bg-gold-500 text-navy-900'
                     : 'bg-white/10 text-white/40'">
                <svg v-if="step > s.id" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
                <span v-else>{{ s.id }}</span>
              </div>
              <span class="mr-2 text-xs font-medium hidden sm:block"
                    :class="step >= s.id ? 'text-gold-400' : 'text-white/40'">
                {{ s.title }}
              </span>
              <div v-if="i < steps.length - 1"
                   class="mx-3 h-px flex-1 transition-colors"
                   :class="step > s.id ? 'bg-gold-500' : 'bg-white/10'"></div>
            </div>
          </template>
        </div>
      </div>

      <!-- Card -->
      <div class="card-premium p-6 shadow-soft-md">
        <!-- Step 1: Type (source: page.tsx:228-265) -->
        <div v-if="step === 1" class="space-y-6">
          <h2 class="text-lg font-semibold text-navy-800">اختر نوع المؤجر</h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <button type="button"
                    @click="updateField('lessor_type', 'person')"
                    class="flex flex-col items-center gap-3 rounded-xl border-2 p-6 transition-all text-center"
                    :class="form.lessor_type === 'person'
                      ? 'border-gold-500 bg-gold-50 text-navy-800'
                      : 'border-ivory-300 bg-white text-navy-400 hover:border-ivory-300'">
              <!-- User icon -->
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <div>
                <div class="font-semibold">شخص</div>
                <div class="text-xs mt-1 opacity-80">المؤجر فرد طبيعي</div>
              </div>
            </button>
            <button type="button"
                    @click="updateField('lessor_type', 'company')"
                    class="flex flex-col items-center gap-3 rounded-xl border-2 p-6 transition-all text-center"
                    :class="form.lessor_type === 'company'
                      ? 'border-gold-500 bg-gold-50 text-navy-800'
                      : 'border-ivory-300 bg-white text-navy-400 hover:border-ivory-300'">
              <!-- Building2 icon -->
              <svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0H5m14 0h2m-2 0h-2m-7 0V9m0 12V5m0 16H7m4-12h.01M7 9h.01M7 13h.01M7 17h.01" />
              </svg>
              <div>
                <div class="font-semibold">شركة / مؤسسة</div>
                <div class="text-xs mt-1 opacity-80">المؤجر كيان اعتباري</div>
              </div>
            </button>
          </div>
          <p v-if="errors.lessor_type" class="text-sm text-red-600">{{ errors.lessor_type }}</p>
        </div>

        <!-- Step 2: Data (source: page.tsx:268-359) -->
        <div v-if="step === 2" class="space-y-4">
          <h2 class="text-lg font-semibold text-navy-800">
            {{ form.lessor_type === 'company' ? 'بيانات الشركة / المؤسسة' : 'بيانات المؤجر' }}
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">
                {{ form.lessor_type === 'company' ? 'اسم الشركة / المؤسسة' : 'الاسم الكامل' }}
                <span class="text-red-600">*</span>
              </label>
              <input type="text"
                     :value="form.landlord_name"
                     @input="updateField('landlord_name', $event.target.value)"
                     class="input-premium w-full"
                     :placeholder="form.lessor_type === 'company' ? 'اسم الشركة' : 'الاسم الكامل'" />
              <p v-if="errors.landlord_name" class="text-xs text-red-600">{{ errors.landlord_name }}</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">
                {{ form.lessor_type === 'company' ? 'رقم التسجيل / السجل التجاري' : 'رقم الهوية' }}
                <span class="text-red-600">*</span>
              </label>
              <input type="text"
                     :value="form.landlord_id"
                     @input="updateField('landlord_id', $event.target.value)"
                     class="input-premium w-full"
                     :placeholder="form.lessor_type === 'company' ? 'رقم السجل' : 'رقم الهوية'" />
              <p v-if="errors.landlord_id" class="text-xs text-red-600">{{ errors.landlord_id }}</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">الهاتف</label>
              <input type="text"
                     :value="form.landlord_phone"
                     @input="updateField('landlord_phone', $event.target.value)"
                     class="input-premium w-full"
                     placeholder="رقم الهاتف" />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">العنوان</label>
              <input type="text"
                     :value="form.landlord_address"
                     @input="updateField('landlord_address', $event.target.value)"
                     class="input-premium w-full"
                     placeholder="العنوان الكامل" />
            </div>
          </div>
          <!-- Representative fields (company only) — order: name → title → id (source: page.tsx:321-357) -->
          <div v-if="form.lessor_type === 'company'"
               class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">اسم المفوض <span class="text-red-600">*</span></label>
              <input type="text"
                     :value="form.landlord_representative_name"
                     @input="updateField('landlord_representative_name', $event.target.value)"
                     class="input-premium w-full"
                     placeholder="اسم المفوض" />
              <p v-if="errors.landlord_representative_name" class="text-xs text-red-600">{{ errors.landlord_representative_name }}</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">صفة المفوض <span class="text-red-600">*</span></label>
              <input type="text"
                     :value="form.landlord_representative_title"
                     @input="updateField('landlord_representative_title', $event.target.value)"
                     class="input-premium w-full"
                     placeholder="مثلاً: مدير عام" />
              <p v-if="errors.landlord_representative_title" class="text-xs text-red-600">{{ errors.landlord_representative_title }}</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium text-navy-700">رقم هوية المفوض <span class="text-red-600">*</span></label>
              <input type="text"
                     :value="form.landlord_representative_id"
                     @input="updateField('landlord_representative_id', $event.target.value)"
                     class="input-premium w-full"
                     placeholder="رقم هوية المفوض" />
              <p v-if="errors.landlord_representative_id" class="text-xs text-red-600">{{ errors.landlord_representative_id }}</p>
            </div>
          </div>
        </div>

        <!-- Step 3: Logo & Currency (source: page.tsx:362-400) -->
        <div v-if="step === 3" class="space-y-6">
          <h2 class="text-lg font-semibold text-navy-800">الشعار والعملة</h2>
          <div class="space-y-1.5">
            <label class="text-sm font-medium text-navy-700">شعار المؤجر (اختياري)</label>
            <div v-if="form.company_logo"
                 class="relative block h-32 w-full max-w-sm overflow-hidden rounded-[10px] border border-ivory-300 bg-ivory-100">
              <img :src="form.company_logo" alt="شعار المؤجر" class="h-full w-full object-contain" />
              <button type="button"
                      @click="updateField('company_logo', '')"
                      class="absolute top-1 left-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-white shadow-sm hover:bg-red-500">
                <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <label v-else
                   class="flex cursor-pointer items-center gap-2 rounded-[10px] border border-dashed border-ivory-300 bg-ivory-100 px-4 py-3 text-sm text-navy-400 hover:bg-ivory-200 transition-colors max-w-sm">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span>اضغط لرفع صورة الشعار</span>
              <input type="file" accept="image/*" class="hidden" @change="handleFileChange" />
            </label>
          </div>
          <div class="space-y-1.5">
            <label class="text-sm font-medium text-navy-700">العملة الأساسية <span class="text-red-600">*</span></label>
            <select :value="form.currency"
                    @change="updateField('currency', $event.target.value)"
                    class="input-premium block w-full max-w-sm text-right">
              <option value="ILS">شيكل (₪)</option>
              <option value="JOD">دينار أردني (JD)</option>
              <option value="USD">دولار ($)</option>
            </select>
            <p v-if="errors.currency" class="text-xs text-red-600">{{ errors.currency }}</p>
          </div>
        </div>

        <!-- Step 4: Summary (source: page.tsx:403-478) -->
        <div v-if="step === 4" class="space-y-4">
          <h2 class="text-lg font-semibold text-navy-800">ملخص الإعداد</h2>
          <div class="card-premium p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 text-right">
              <div class="space-y-1">
                <span class="text-xs text-navy-400">نوع المؤجر</span>
                <p class="text-sm font-medium text-navy-800">
                  {{ form.lessor_type === 'company' ? 'شركة / مؤسسة' : 'شخص' }}
                </p>
              </div>
              <div class="space-y-1">
                <span class="text-xs text-navy-400">
                  {{ form.lessor_type === 'company' ? 'اسم الشركة / المؤسسة' : 'الاسم الكامل' }}
                </span>
                <p class="text-sm font-medium text-navy-800">{{ form.landlord_name }}</p>
              </div>
              <div class="space-y-1">
                <span class="text-xs text-navy-400">
                  {{ form.lessor_type === 'company' ? 'رقم التسجيل / السجل التجاري' : 'رقم الهوية' }}
                </span>
                <p class="text-sm font-medium text-navy-800">{{ form.landlord_id }}</p>
              </div>
              <div v-if="form.landlord_phone" class="space-y-1">
                <span class="text-xs text-navy-400">الهاتف</span>
                <p class="text-sm font-medium text-navy-800">{{ form.landlord_phone }}</p>
              </div>
              <div v-if="form.landlord_address" class="space-y-1">
                <span class="text-xs text-navy-400">العنوان</span>
                <p class="text-sm font-medium text-navy-800">{{ form.landlord_address }}</p>
              </div>
              <template v-if="form.lessor_type === 'company'">
                <div class="space-y-1">
                  <span class="text-xs text-navy-400">اسم المفوض</span>
                  <p class="text-sm font-medium text-navy-800">{{ form.landlord_representative_name }}</p>
                </div>
                <div class="space-y-1">
                  <span class="text-xs text-navy-400">صفة المفوض</span>
                  <p class="text-sm font-medium text-navy-800">{{ form.landlord_representative_title }}</p>
                </div>
                <div v-if="form.landlord_representative_id" class="space-y-1">
                  <span class="text-xs text-navy-400">رقم هوية المفوض</span>
                  <p class="text-sm font-medium text-navy-800">{{ form.landlord_representative_id }}</p>
                </div>
              </template>
              <div class="space-y-1">
                <span class="text-xs text-navy-400">العملة الأساسية</span>
                <p class="text-sm font-medium text-navy-800">
                  {{ form.currency === 'ILS' ? 'شيكل (₪)' : form.currency === 'JOD' ? 'دينار أردني (JD)' : 'دولار ($)' }}
                </p>
              </div>
              <div class="space-y-1">
                <span class="text-xs text-navy-400">الشعار</span>
                <img v-if="form.company_logo"
                     :src="form.company_logo"
                     alt="شعار المؤجر"
                     class="h-12 w-12 rounded-[10px] border border-ivory-300 object-contain bg-white" />
                <p v-else class="text-sm text-navy-400">لم يتم إضافة شعار</p>
              </div>
            </div>
          </div>
          <p v-if="errors.submit" class="text-sm text-red-600 text-center">{{ errors.submit }}</p>
        </div>

        <!-- Navigation (source: page.tsx:480-504) -->
        <div class="mt-8 flex items-center justify-between"
             :class="step === 4 && 'border-t border-ivory-300/50 pt-6'">
          <button type="button"
                  @click="prevStep"
                  :disabled="step === 1"
                  class="btn-premium btn-ghost"
                  :class="step === 1 && 'invisible'">
            <!-- ChevronRight (RTL: previous points right) -->
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            السابق
          </button>
          <button v-if="step < 4" type="button" @click="nextStep"
                  class="btn-premium btn-gold">
            التالي
            <!-- ChevronLeft (RTL: next points left) -->
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button v-else type="button"
                  @click="completeSetup"
                  :disabled="saving"
                  class="btn-premium btn-gold">
            <span v-if="saving">جاري الحفظ...</span>
            <template v-else>
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              إكمال الإعداد
            </template>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '@/composables/useSession'
import { extractError } from '@/composables/useApi'

// ---------------------------------------------------------------------------
// Form model  (source: page.tsx:9-33 — SetupForm + defaultForm)
// ---------------------------------------------------------------------------
const defaultForm = {
  lessor_type: 'person',
  landlord_name: '',
  landlord_id: '',
  landlord_phone: '',
  landlord_address: '',
  company_logo: '',
  currency: 'ILS',
  landlord_representative_name: '',
  landlord_representative_id: '',
  landlord_representative_title: '',
}

// Steps (source: page.tsx:35-40)
const steps = [
  { id: 1, title: 'نوع المؤجر' },
  { id: 2, title: 'بيانات المؤجر' },
  { id: 3, title: 'الشعار والعملة' },
  { id: 4, title: 'الإكمال' },
]

const router = useRouter()
const session = useSession()

const step = ref(1)
const form = reactive({ ...defaultForm })
const errors = reactive({})
const loading = ref(true)
const saving = ref(false)
const showSuccess = ref(false)
const isFadingOut = ref(false)

let fadeTimer = null
let navTimer = null

// ---------------------------------------------------------------------------
// Validation  (source: page.tsx:92-111 + validation.ts:342-424)
// ---------------------------------------------------------------------------
const LANDLORD_ID_RE = /^\d{4,20}$/

function validateStep() {
  // Clear errors for current step fields
  for (const k of Object.keys(errors)) delete errors[k]

  if (step.value === 1) {
    if (!form.lessor_type) errors.lessor_type = 'يرجى اختيار نوع المؤجر'
  }

  if (step.value === 2) {
    // setupCompleteSchema fields relevant to step 2
    if (!form.landlord_name.trim()) errors.landlord_name = 'اسم المؤجر مطلوب'
    if (!form.landlord_id || !LANDLORD_ID_RE.test(form.landlord_id)) {
      errors.landlord_id = 'رقم الهوية أو التسجيل غير صالح'
    }
    if (form.lessor_type === 'company') {
      if (!form.landlord_representative_name.trim()) {
        errors.landlord_representative_name = 'اسم المفوض مطلوب'
      }
      // Source: validation.ts:353-356 + 409-414.
      // Empty → "مطلوب", non-empty invalid → "غير صالح".
      if (!form.landlord_representative_id) {
        errors.landlord_representative_id = 'رقم هوية المفوض مطلوب'
      } else if (!LANDLORD_ID_RE.test(form.landlord_representative_id)) {
        errors.landlord_representative_id = 'رقم هوية المفوض غير صالح'
      }
      if (!form.landlord_representative_title.trim()) {
        errors.landlord_representative_title = 'صفة المفوض مطلوبة'
      }
    }
  }

  if (step.value === 3) {
    if (!form.currency) errors.currency = 'العملة مطلوبة'
  }

  return Object.keys(errors).length === 0
}

// ---------------------------------------------------------------------------
// Navigation  (source: page.tsx:113-119)
// ---------------------------------------------------------------------------
function nextStep() {
  if (validateStep()) step.value = Math.min(step.value + 1, 4)
}

function prevStep() {
  step.value = Math.max(step.value - 1, 1)
}

// ---------------------------------------------------------------------------
// Field update  (source: page.tsx:87-90)
// ---------------------------------------------------------------------------
function updateField(key, value) {
  form[key] = value
  delete errors[key]
}

// ---------------------------------------------------------------------------
// File upload  (source: page.tsx:145-154)
// Original uses base64 data URL; Frappe native approach uses upload_file API
// to get a file URL. UX is identical: preview + remove button.
// ---------------------------------------------------------------------------
async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '1')
  formData.append('doctype', 'Rental Settings')
  formData.append('fieldname', 'logo')

  try {
    const res = await fetch('/api/method/upload_file', {
      method: 'POST',
      body: formData,
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    })
    const data = await res.json()
    const fileUrl = data?.message?.file_url || ''
    if (fileUrl) updateField('company_logo', fileUrl)
  } catch {
    // ignore upload errors — user can retry
  }
}

// ---------------------------------------------------------------------------
// Complete setup  (source: page.tsx:121-143)
// ---------------------------------------------------------------------------
async function completeSetup() {
  saving.value = true
  delete errors.submit
  try {
    await session.completeSetup({
      lessor_type: form.lessor_type,
      landlord_name: form.landlord_name,
      landlord_id: form.landlord_id,
      landlord_phone: form.landlord_phone || '',
      landlord_address: form.landlord_address || '',
      company_logo: form.company_logo || '',
      currency: form.currency,
      landlord_representative_name: form.landlord_representative_name || '',
      landlord_representative_id: form.landlord_representative_id || '',
      landlord_representative_title: form.landlord_representative_title || '',
    })
    showSuccess.value = true
  } catch (err) {
    errors.submit = extractError(err) || 'تعذر حفظ الإعدادات. يرجى المحاولة مرة أخرى.'
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------------------
// Success → redirect  (source: page.tsx:52-62)
// ---------------------------------------------------------------------------
onMounted(async () => {
  // Pre-fetch existing settings (source: page.tsx:64-85)
  try {
    const data = await session.getSetup()
    const s = data?.setup || {}
    form.lessor_type = s.lessor_type === 'company' ? 'company' : 'person'
    form.landlord_name = s.landlord_name || ''
    form.landlord_id = s.landlord_id || ''
    form.landlord_phone = s.landlord_phone || ''
    form.landlord_address = s.landlord_address || ''
    form.company_logo = s.company_logo || ''
    form.currency = s.currency || 'ILS'
    form.landlord_representative_name = s.landlord_representative_name || ''
    form.landlord_representative_id = s.landlord_representative_id || ''
    form.landlord_representative_title = s.landlord_representative_title || ''
  } catch {
    // ignore — use defaults
  } finally {
    loading.value = false
  }
})

// Watch showSuccess for fade + redirect (source: page.tsx:52-62)
watch(showSuccess, (val) => {
  if (!val) return
  fadeTimer = setTimeout(() => { isFadingOut.value = true }, 1500)
  navTimer = setTimeout(() => {
    router.replace({ name: 'Dashboard' })
  }, 2000)
})

onUnmounted(() => {
  clearTimeout(fadeTimer)
  clearTimeout(navTimer)
})
</script>
