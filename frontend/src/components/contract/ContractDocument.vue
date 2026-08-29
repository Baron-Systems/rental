<template>
  <div
    id="print-area"
    class="contract-document print-document relative mx-auto bg-white shadow-lg print:shadow-none max-w-[210mm] min-h-[297mm] p-8 md:p-12"
    dir="rtl"
  >
    <!-- Renewal banner -->
    <div
      v-if="isRenewal && previousContractNumber"
      class="mb-4 rounded-lg border border-blue-200 bg-blue-50/60 p-3 text-sm text-blue-700"
    >
      تجديد للعقد: <strong>{{ previousContractNumber }}</strong>
    </div>

    <!-- Print Header — only rendered in print mode -->
    <div
      v-if="showPrintHeader && lessorData"
      class="contract-print-header print-only print-keep-together"
    >
      <!-- Source: ContractDocument.tsx:359 — pass logo and name separately -->
      <PrintHeader :logo="lessorData?.logo" :name="lessorData?.name" />
    </div>

    <!-- Contract Title -->
    <div class="contract-title print-keep-together mb-5 border-b-2 border-navy-200 pb-4 text-center">
      <h1 class="mb-3 text-3xl font-bold tracking-wide text-navy-900">عقد إيجار</h1>
      <div class="flex items-center justify-between text-sm text-navy-500">
        <div class="flex items-center gap-2">
          <span>رقم العقد:</span>
          <strong class="font-bold text-navy-900">{{ form.contractNumber || form.contract_number || '—' }}</strong>
        </div>
        <div class="flex items-center gap-2">
          <span>تاريخ العقد:</span>
          <InlineField
            :value="form.contractDate || form.contract_date"
            @update:value="(v) => updateField('contractDate', v)"
            placeholder="تاريخ التوقيع"
            type="date"
            :preview="isPreview"
            :error="errors.contractDate || errors.contract_date"
            width="140px"
          />
        </div>
      </div>
    </div>

    <!-- Introduction -->
    <div class="mb-6 leading-loose text-navy-900">
      <p class="text-justify">
        إنه في يوم
        <InlineField
          :value="form.contractDate || form.contract_date"
          @update:value="(v) => updateField('contractDate', v)"
          placeholder="تاريخ العقد"
          type="date"
          :preview="isPreview"
          :error="errors.contractDate || errors.contract_date"
          width="140px"
        />
        ، تم الاتفاق والتراضي بين:
      </p>
    </div>

    <!-- Parties -->
    <div class="mb-6 space-y-4">
      <!-- Lessor -->
      <div class="contract-party print-keep-together card-v2 p-4">
        <h3 class="mb-2 font-bold text-navy-900">الطرف الأول: المؤجر</h3>
        <p class="leading-loose text-justify text-navy-900">
          <!-- Company lessor -->
          <template v-if="lessorData?.type === 'company'">
            <strong>{{ lessorData.name || '[لم يُحدد اسم الشركة]' }}</strong>، المسجلة تحت رقم
            <strong>{{ lessorData.identityOrRegistrationNumber || lessorData.landlord_id || '—' }}</strong>،
            ويمثلها السيد/ة <strong>{{ lessorData.representativeName || '—' }}</strong>
            بصفته/بصفتها <strong>{{ lessorData.representativeTitle || '—' }}</strong>،
            حامل/ة هوية رقم <strong>{{ lessorData.representativeId || '—' }}</strong>،
            ويشار إليها لاحقًا بـ <strong>«المؤجر» أو «الطرف الأول»</strong>.
          </template>
          <!-- Person lessor -->
          <template v-else>
            السيد/ة
            <strong v-if="lessorData?.name">{{ lessorData.name }}</strong>
            <span v-else class="text-navy-400">[لم يُحدد اسم المؤجر]</span>،
            حامل/ة هوية رقم
            <strong>{{ lessorData?.identityOrRegistrationNumber || lessorData?.landlord_id || '—' }}</strong>،
            ويشار إليه/إليها لاحقًا بـ <strong>«المؤجر» أو «الطرف الأول»</strong>.
          </template>
        </p>
      </div>

      <!-- Tenant -->
      <div class="contract-party print-keep-together card-v2 p-4">
        <h3 class="mb-2 font-bold text-navy-900">الطرف الثاني: المستأجر</h3>
        <div class="leading-loose text-justify text-navy-900">
          <InlineField
            v-if="!isPreview && !isRenewal"
            :value="form.tenantId || form.tenant"
            @update:value="(v) => updateField('tenantId', v)"
            placeholder="اختر المستأجر"
            type="search"
            :searchOptions="tenantOptions"
            :preview="false"
            :error="errors.tenantId || errors.tenant"
            width="180px"
          />
          <template v-if="!isPreview && !isRenewal"> </template>
          <!-- Tenant clause -->
          <span v-if="!selectedTenant" class="text-navy-400">[المستأجر لم يُحدد]</span>
          <template v-else>
            السيد/ة <strong>{{ selectedTenant.full_name || selectedTenant.fullName || selectedTenant.tenant_name }}</strong>،
            حامل/ة هوية رقم <strong>{{ selectedTenant.nationalId || selectedTenant.national_id || '—' }}</strong>،
            ويشار إليه/إليها لاحقًا بـ <strong>«المستأجر» أو «الطرف الثاني»</strong>.
          </template>
        </div>
        <div v-if="!isPreview && !selectedTenant" class="mt-2 text-xs text-navy-400">
          اختر المستأجر لإظهار بياناته تلقائياً
        </div>
      </div>
    </div>

    <!-- Warnings -->
    <div v-if="warnings.length > 0 && !isPreview" class="mb-4 space-y-1">
      <div
        v-for="(w, i) in warnings"
        :key="i"
        class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
      >
        <strong>تنبيه:</strong> {{ w }}
      </div>
    </div>

    <!-- Article 1: Unit -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند الأول: موضوع العقد</h3>

      <!-- Building / Floor / Unit Selection (edit mode only, not renewal) -->
      <div v-if="!isPreview && !isRenewal" class="mb-4 space-y-3">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900 whitespace-nowrap">العقار:</span>
          <select
            :value="form.buildingId || form.building"
            @change="(e) => updateField('buildingId', e.target.value)"
            class="select-v2"
          >
            <option value="">اختر العقار</option>
            <option v-for="b in buildingOptions" :key="b.value" :value="b.value">{{ b.label }}</option>
          </select>
        </div>

        <div v-if="form.buildingId || form.building" class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900 whitespace-nowrap">الطابق:</span>
          <select
            :value="form.floorId || form.floor"
            @change="(e) => updateField('floorId', e.target.value)"
            class="select-v2"
          >
            <option value="">اختر الطابق</option>
            <option v-for="f in floorOptions" :key="f.value" :value="f.value">{{ f.label }}</option>
          </select>
        </div>

        <div v-if="form.floorId || form.floor" class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900 whitespace-nowrap">الوحدة:</span>
          <select
            :value="form.unitId || form.unit"
            @change="(e) => updateField('unitId', e.target.value)"
            class="select-v2"
          >
            <option value="">اختر الوحدة</option>
            <option v-for="u in unitOptions" :key="u.value" :value="u.value">
              {{ u.label }}<template v-if="u.meta"> — {{ u.meta }}</template>
            </option>
          </select>
        </div>

        <div v-if="errors.unitId || errors.unit" class="text-sm text-red-600">
          {{ errors.unitId || errors.unit }}
        </div>
      </div>

      <!-- Auto-filled contract text -->
      <p v-if="selectedUnit" class="leading-loose text-justify text-navy-900">
        أجر الطرف الأول إلى الطرف الثاني الوحدة رقم
        <strong>{{ selectedUnit.unitNumber || selectedUnit.unit_number }}</strong>
        الواقعة في عقار <strong>{{ selectedBuilding?.building_name || selectedBuilding?.name }}</strong>،
        في <strong>{{ selectedUnitFloorName || '—' }}</strong>،
        من نوع <strong>{{ unitTypeLabel(selectedUnit.unitType || selectedUnit.unit_type) }}</strong><template
          v-if="selectedUnit.area || selectedUnit.unit_area"
        >، ومساحتها <strong>{{ selectedUnit.area || selectedUnit.unit_area }}</strong> م²</template><template
          v-if="selectedUnit.currentElectricityMeterReading || selectedUnit.current_electricity_meter_reading"
        >، وعليها قراءة عداد كهرباء <strong>{{ selectedUnit.currentElectricityMeterReading || selectedUnit.current_electricity_meter_reading }}</strong></template><template
          v-if="selectedUnit.currentWaterMeterReading || selectedUnit.current_water_meter_reading"
        >، وقراءة عداد مياه <strong>{{ selectedUnit.currentWaterMeterReading || selectedUnit.current_water_meter_reading }}</strong></template>.
      </p>
      <p v-else class="text-navy-400">
        {{ isPreview ? 'لم يُحدد الوحدة' : 'اختر العقار، ثم الطابق، ثم الوحدة' }}
      </p>
    </div>

    <!-- Article 2: Rent Value -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند الثاني: القيمة الإيجارية</h3>
      <div class="leading-loose text-justify text-navy-900">
        اتفق الطرفان على أن تكون القيمة الإيجارية {{ frequencyAdjective }} مبلغاً وقدره
        <InlineField
          :value="form.rentAmount || form.rent_amount"
          @update:value="(v) => updateField('rentAmount', v)"
          placeholder="قيمة الإيجار"
          type="number"
          :preview="isPreview"
          :error="errors.rentAmount || errors.rent_amount"
          width="100px"
        />
        {{ currencyLabel }}،
        <template v-if="isPreview">
          يستحق السداد {{ frequencyPaymentText }}.
        </template>
        <template v-else>
          تلتزم وفق دورية
          <InlineField
            :value="form.paymentFrequency || form.payment_frequency"
            @update:value="(v) => updateField('paymentFrequency', v)"
            placeholder="دورية الالتزام"
            type="select"
            :options="frequencyOptions"
            :preview="isPreview"
            :error="errors.paymentFrequency || errors.payment_frequency"
            width="120px"
          />.
        </template>
      </div>
      <div v-if="form.rentAmount || form.rent_amount" class="mt-2 text-sm font-medium text-navy-900">
        ({{ formatMoney(parseFloat(form.rentAmount || form.rent_amount) || 0, lessorData?.currency) }}
        {{ currencyLabel }}) — {{ numberToWordsArabic(parseFloat(form.rentAmount || form.rent_amount) || 0) }}
        {{ currencyLabel }} فقط لا غير.
      </div>
    </div>

    <!-- Article 3: Duration -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند الثالث: مدة العقد</h3>
      <p class="leading-loose text-justify text-navy-900">
        تبدأ مدة هذا العقد اعتباراً من تاريخ
        <strong>{{ (form.startDate || form.start_date) ? formatDate(form.startDate || form.start_date) : '-' }}</strong>
        وتنتهي بتاريخ
        <strong>{{ (form.endDate || form.end_date) ? formatDate(form.endDate || form.end_date) : '-' }}</strong>.
      </p>
      <div v-if="!isPreview" class="mt-3 flex flex-wrap items-center gap-4 card-v2 bg-navy-50/40 px-4 py-3">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900">عدد الدورات:</span>
          <input
            type="number"
            min="1"
            :value="form.cycles || '1'"
            @input="(e) => updateField('cycles', e.target.value)"
            class="input-v2 w-20"
            placeholder="الدورات"
          />
          <span class="text-xs text-navy-400">
            ({{ frequencyOptions.find((f) => f.value === (form.paymentFrequency || form.payment_frequency))?.label || 'دورة' }} لكل دورة)
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900">تاريخ البداية:</span>
          <!-- Source: ContractDocument.tsx:518-529 — plain span in preview, InlineField in edit -->
          <span v-if="isPreview" class="text-sm text-navy-900">{{ (form.startDate || form.start_date) ? formatDate(form.startDate || form.start_date) : '-' }}</span>
          <InlineField
            v-else
            :value="form.startDate || form.start_date"
            @update:value="(v) => updateField('startDate', v)"
            placeholder="اختر تاريخ بداية العقد"
            type="date"
            :preview="false"
            width="140px"
          />
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-navy-900">تاريخ النهاية:</span>
          <span class="text-sm text-navy-900">
            {{ (form.endDate || form.end_date) ? formatDate(form.endDate || form.end_date) : '-' }}
          </span>
          <span v-if="errors.endDate || errors.end_date" class="text-xs text-red-600">
            {{ errors.endDate || errors.end_date }}
          </span>
        </div>
      </div>
    </div>

    <!-- Article 4: Due Dates -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند الرابع: مواعيد الالتزامات</h3>
      <div class="leading-loose text-justify text-navy-900">
        يبدأ أول التزام تلقائيًا من تاريخ بداية العقد:
        <strong>{{ (form.startDate || form.start_date) ? formatDate(form.startDate || form.start_date) : '-' }}</strong>،
        ثم تتكرر الالتزامات وفق دورية <strong>{{ paymentFrequencyText }}</strong> ،
        على ألا يتم إنشاء أي التزام بعد تاريخ انتهاء العقد. يتم إنشاء الالتزامات في
        <InlineField
          :value="form.commitmentTiming || form.commitment_timing"
          @update:value="(v) => updateField('commitmentTiming', v)"
          placeholder="توقيت الالتزام"
          type="select"
          :options="commitmentTimingOptions"
          :preview="isPreview"
          width="140px"
        />.
      </div>
    </div>

    <!-- Payment Schedule Table -->
    <div v-if="schedule.length > 0" class="contract-article contract-table print-keep-together mb-6">
      <h3 class="mb-3 font-bold text-navy-900">جدول الدفعات الإيجارية</h3>
      <div class="overflow-hidden rounded-lg border border-navy-200">
        <table class="w-full text-sm print-table">
          <thead class="bg-navy-50/40 text-navy-900">
            <tr>
              <th class="px-3 py-2 text-right font-semibold">الرقم</th>
              <th class="px-3 py-2 text-right font-semibold">تاريخ الالتزام</th>
              <th class="px-3 py-2 text-right font-semibold">القيمة</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-navy-100">
            <tr v-for="row in schedule" :key="row.number" class="text-navy-900">
              <td class="px-3 py-2">{{ row.number }}</td>
              <td class="px-3 py-2">{{ formatDate(row.dueDate) }}</td>
              <td class="px-3 py-2 font-medium">{{ formatMoney(row.amount, lessorData?.currency) }} {{ currencyLabel }}</td>
            </tr>
          </tbody>
        </table>
        <div class="border-t border-navy-100 bg-navy-50/40 px-3 py-2 text-sm text-navy-500">
          <div class="flex flex-wrap gap-x-4 gap-y-1">
            <span>عدد الالتزامات: <strong>{{ schedule.length }}</strong></span>
            <span>قيمة كل التزام: <strong>{{ formatMoney(dueAmount, lessorData?.currency) }} {{ currencyLabel }}</strong></span>
            <span>إجمالي الالتزامات: <strong>{{ formatMoney(totalAmount, lessorData?.currency) }} {{ currencyLabel }}</strong></span>
            <span>أول تاريخ: <strong>{{ formatDate(schedule[0].dueDate) }}</strong></span>
            <span>آخر تاريخ: <strong>{{ formatDate(schedule[schedule.length - 1].dueDate) }}</strong></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Article 5: Obligations (Charges) -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند الخامس: الكهرباء والمياه والخدمات</h3>
      <ContractChargesSection
        v-model="chargesModel"
        :availableDueTypes="dueTypes"
        :unit="selectedUnit"
        :editable="!isPreview"
        :errors="errors"
        :contractStartDate="form.startDate || form.start_date || ''"
        :contractEndDate="form.endDate || form.end_date || ''"
        :currency="lessorData?.currency"
      />
    </div>

    <!-- Article 6: Terms -->
    <div class="contract-article mb-6">
      <h3 class="mb-2 font-bold text-navy-900">البند السادس: الشروط والأحكام</h3>
      <div v-if="isPreview" class="whitespace-pre-wrap leading-loose text-justify text-navy-900">
        {{ (form.terms) || defaultTerms }}
      </div>
      <textarea
        v-else
        :value="form.terms || defaultTerms"
        @input="(e) => updateField('terms', e.target.value)"
        rows="6"
        class="w-full rounded-lg border border-navy-200 bg-white px-3 py-2 text-sm leading-loose text-navy-900 shadow-sm focus:border-gold-500 focus:outline-none focus:ring-2 focus:ring-gold-200/30"
        dir="rtl"
      ></textarea>
    </div>

    <!-- Signatures -->
    <div class="contract-signatures print-keep-together mt-10 border-t-2 border-navy-200 pt-6">
      <div class="grid grid-cols-2 gap-8">
        <div class="text-center">
          <p class="mb-4 font-bold text-navy-900">الطرف الأول – المؤجر</p>
          <div class="mb-2">
            <span class="text-sm text-navy-400">الاسم:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
          <div>
            <span class="text-sm text-navy-400">التوقيع:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
        </div>
        <div class="text-center">
          <p class="mb-4 font-bold text-navy-900">الطرف الثاني – المستأجر</p>
          <div class="mb-2">
            <span class="text-sm text-navy-400">الاسم:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
          <div>
            <span class="text-sm text-navy-400">التوقيع:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
        </div>
      </div>
      <div class="mt-8 grid grid-cols-2 gap-8">
        <div class="text-center">
          <p class="mb-4 font-bold text-navy-900">الشاهد الأول</p>
          <div class="mb-2">
            <span class="text-sm text-navy-400">الاسم:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
          <div>
            <span class="text-sm text-navy-400">التوقيع:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
        </div>
        <div class="text-center">
          <p class="mb-4 font-bold text-navy-900">الشاهد الثاني</p>
          <div class="mb-2">
            <span class="text-sm text-navy-400">الاسم:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
          <div>
            <span class="text-sm text-navy-400">التوقيع:</span>
            <div class="mt-1 h-8 border-b border-navy-300"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import InlineField from '@/components/contract/InlineField.vue'
import PrintHeader from '@/components/print/PrintHeader.vue'
import ContractChargesSection from '@/components/contract/ContractChargesSection.vue'
import { formatMoney, formatDate, callApi } from '@/composables/useApi'
import { calculateContractEndDate as computeContractEndDate, buildPeriodicSchedule } from '@/utils/contractUtils.js'

const props = defineProps({
  modelValue: { type: Object, required: true }, // formData (v-model)
  errors: { type: Object, default: () => ({}) },
  tenants: { type: Array, default: () => [] },
  buildings: { type: Array, default: () => [] },
  floors: { type: Array, default: () => [] },
  units: { type: Array, default: () => [] },
  dueTypes: { type: Array, default: null },
  mode: { type: String, default: 'edit' }, // 'edit' | 'preview' | 'print'
  warnings: { type: Array, default: () => [] },
  dues: { type: Array, default: null },
  isNewContract: { type: Boolean, default: false },
  isRenewal: { type: Boolean, default: false },
  previousContractNumber: { type: String, default: '' },
  lessorData: { type: Object, default: null },
  showPrintHeader: { type: Boolean, default: null },
})

const emit = defineEmits(['update:modelValue'])

const isPreview = computed(() => props.mode === 'preview' || props.mode === 'print')
const isPrint = computed(() => props.mode === 'print')
const showPrintHeader = computed(() =>
  props.showPrintHeader !== null ? props.showPrintHeader : isPrint.value
)

// Normalized form data accessor — supports both camelCase and snake_case keys
const form = computed(() => props.modelValue || {})

// ---- Due types (fetch if not provided) ----
const fetchedDueTypes = ref([])
const dueTypes = computed(() => props.dueTypes || fetchedDueTypes.value)

// Source: ContractDocument.tsx:223-228 — fetch due types if not provided as prop
onMounted(() => {
  if (props.dueTypes) return
  callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 0 })
    .then((res) => { fetchedDueTypes.value = res.dueTypes || res || [] })
    .catch(() => {})
})

// ---- Constants ----
const PAYMENT_FREQUENCIES = [
  { value: 'once', label: 'مرة واحدة' },
  { value: 'monthly', label: 'شهري' },
  { value: 'bi_monthly', label: 'كل شهرين' },
  { value: 'quarterly', label: 'ربع سنوي' },
  { value: 'semi_annual', label: 'نصف سنوي' },
  { value: 'annual', label: 'سنوي' },
]

// Source: ContractDocument.tsx:13-16 — exact match, no extra types
const UNIT_TYPE_LABELS = {
  apartment: 'شقة', shop: 'محل', office: 'مكتب', warehouse: 'مستودع',
  room: 'غرفة', garage: 'كراج', independent: 'عقار مستقل', other: 'أخرى',
}

// Source: settings.ts:125-131 getCurrencyLabel — exact match, no extra currencies
const CURRENCY_LABELS = { ILS: 'شيكل', JOD: 'دينار أردني', USD: 'دولار' }

const commitmentTimingOptions = [
  { label: 'بداية الدورة', value: 'start' },
  { label: 'نهاية الدورة', value: 'end' },
]

const frequencyOptions = PAYMENT_FREQUENCIES

const currencyLabel = computed(() => {
  const c = props.lessorData?.currency
  return c ? (CURRENCY_LABELS[c] || c) : 'شيكل'
})

// ---- Helpers ----
function unitTypeLabel(type) {
  return UNIT_TYPE_LABELS[type] || type || '—'
}

function getCurrencyLabel(currency) {
  return CURRENCY_LABELS[currency] || currency || ''
}

// Source: utils.ts:244-258 getFrequencyInterval — includes all aliases
function getFrequencyMonths(freq) {
  const map = {
    weekly: 0, once: 0, one_time: 0,
    monthly: 1, bi_monthly: 2, bimonthly: 2,
    quarterly: 3, semi_annual: 6, semiannual: 6, annual: 12,
  }
  return map[freq] ?? 0
}

function paymentFrequencyTextFn(freq) {
  return frequencyOptions.find((f) => f.value === freq)?.label || freq || ''
}

const paymentFrequencyText = computed(() =>
  paymentFrequencyTextFn(form.value.paymentFrequency || form.value.payment_frequency)
)

function getFrequencyAdjective(freq) {
  if (!freq) return 'لكل دورة'
  const months = getFrequencyMonths(freq)
  if (months === 0) return 'دفعة واحدة'
  if (months === 1) return 'الشهرية'
  if (months === 2) return 'كل شهرين'
  if (months === 3) return 'ربع السنوية'
  if (months === 6) return 'نصف السنوية'
  if (months === 12) return 'السنوية'
  return `كل ${months} أشهر`
}

const frequencyAdjective = computed(() =>
  getFrequencyAdjective(form.value.paymentFrequency || form.value.payment_frequency)
)

function getFrequencyPaymentText(freq) {
  const months = getFrequencyMonths(freq)
  if (months === 0) return 'دفعة واحدة'
  if (months === 1) return 'شهرياً'
  if (months === 2) return 'كل شهرين'
  if (months === 3) return 'كل ثلاثة أشهر'
  if (months === 6) return 'كل ستة أشهر'
  if (months === 12) return 'مرة واحدة كل سنة'
  return `كل ${months} أشهر`
}

const frequencyPaymentText = computed(() =>
  getFrequencyPaymentText(form.value.paymentFrequency || form.value.payment_frequency)
)

// ---- Field update (emits v-model update) ----
function updateField(field, value) {
  const next = { ...form.value, [field]: value }
  // Cascade logic matching the original
  if (field === 'buildingId' || field === 'building') {
    next.floorId = ''
    next.floor = ''
    next.unitId = ''
    next.unit = ''
  }
  if (field === 'floorId' || field === 'floor') {
    next.unitId = ''
    next.unit = ''
  }
  if (field === 'unitId' || field === 'unit') {
    const u = props.units.find((x) => (x.id || x.name) === value)
    if (u) {
      next.buildingId = u.buildingId || u.building || next.buildingId
      next.building = u.building || u.buildingId || next.building
      next.floorId = u.floorId || u.floor || ''
      next.floor = u.floor || u.floorId || ''
    }
  }
  if (field === 'startDate' || field === 'start_date') {
    next.firstDueDate = value
    next.first_due_date = value
  }
  emit('update:modelValue', next)
}

// ---- Charges v-model bridge ----
const chargesModel = computed({
  get: () => form.value.contractCharges || form.value.contract_charges || [],
  set: (val) => {
    emit('update:modelValue', { ...form.value, contractCharges: val, contract_charges: val })
  },
})

// ---- Auto-calc end date & first due date ----
// Source: ContractDocument.tsx:268-282 — clears endDate/firstDueDate when conditions missing
watch(
  () => [
    form.value.startDate || form.value.start_date,
    form.value.firstDueDate || form.value.first_due_date,
    form.value.cycles,
    form.value.paymentFrequency || form.value.payment_frequency,
  ],
  ([startDate, _firstDue, cycles, freq]) => {
    let endDate = ''
    let firstDueDate = ''
    const cyclesNum = parseInt(cycles || '1', 10)

    // Source: route.ts:274 — only compute when all conditions met
    if (startDate && cyclesNum > 0 && freq) {
      endDate = computeContractEndDate(startDate, freq, cyclesNum)
      firstDueDate = startDate
    }

    const currentEnd = form.value.endDate || form.value.end_date
    const currentFirstDue = form.value.firstDueDate || form.value.first_due_date
    // Source: route.ts:279 — update only if something changed
    if (endDate !== currentEnd || startDate !== (form.value.startDate || form.value.start_date) || firstDueDate !== currentFirstDue) {
      emit('update:modelValue', {
        ...form.value,
        startDate,
        start_date: startDate,
        endDate,
        end_date: endDate,
        firstDueDate,
        first_due_date: firstDueDate,
      })
    }
  },
  { immediate: false }
)

// ---- Tenant selection ----
const tenantOptions = computed(() =>
  props.tenants.map((t) => ({
    label: t.full_name || t.fullName || t.tenant_name || t.name,
    value: t.id || t.name,
    meta: t.nationalId || t.national_id || t.phone || '',
  }))
)

const selectedTenant = computed(() => {
  const id = form.value.tenantId || form.value.tenant
  return props.tenants.find((t) => (t.id || t.name) === id) || null
})

// ---- Building / Floor / Unit options ----
const buildingOptions = computed(() => {
  const formBuildingId = form.value.buildingId || form.value.building
  const withUnits = props.buildings.filter(
    (b) => (b.id || b.name) === formBuildingId || props.units.some((u) => (u.buildingId || u.building) === (b.id || b.name))
  )
  return withUnits.map((b) => ({ label: b.building_name || b.name, value: b.id || b.name }))
})

const selectedBuilding = computed(() => {
  const id = form.value.buildingId || form.value.building
  return props.buildings.find((b) => (b.id || b.name) === id) || null
})

const floorOptions = computed(() => {
  const formBuildingId = form.value.buildingId || form.value.building
  return props.floors
    .filter((f) => (f.buildingId || f.building) === formBuildingId)
    .map((f) => ({ label: f.floor_name || f.name, value: f.id || f.name }))
})

// Source: ContractDocument.tsx:303 — exact match, no 'unavailable' label
const unitStatusLabels = { empty: 'فارغة', rented: 'مؤجرة', reserved: 'محجوزة' }

// Source: ContractDocument.tsx:305-311 — strict equality on floorId, no OR fallback
const unitOptions = computed(() => {
  const formBuildingId = form.value.buildingId || form.value.building
  const formFloorId = form.value.floorId || form.value.floor
  const available = props.units.filter(
    (u) =>
      (u.isActive !== false && u.is_active !== false && u.is_active !== 0) &&
      (u.buildingId || u.building) === formBuildingId &&
      (u.floorId || u.floor || '') === (formFloorId || '') &&
      u.status !== 'unavailable'
  )
  return available.map((u) => ({
    label: `${u.unitNumber || u.unit_number} — ${unitStatusLabels[u.status] || u.status || ''}`,
    value: u.id || u.name,
    meta: u.floor?.name || u.unitType || u.unit_type || '',
  }))
})

const selectedUnit = computed(() => {
  const id = form.value.unitId || form.value.unit
  return props.units.find((u) => (u.id || u.name) === id) || null
})

const selectedUnitFloorName = computed(() => {
  const u = selectedUnit.value
  if (!u) return ''
  if (u.floor?.name) return u.floor.name
  if (u.floor_name) return u.floor_name
  const f = props.floors.find((fl) => (fl.id || fl.name) === (u.floorId || u.floor))
  return f?.floor_name || f?.name || '—'
})

// ---- Payment schedule ----
function getPaymentSchedule(formData) {
  const baseDate = formData.firstDueDate || formData.first_due_date || formData.startDate || formData.start_date
  if (!baseDate || !(formData.endDate || formData.end_date) || !(formData.rentAmount || formData.rent_amount) || !(formData.paymentFrequency || formData.payment_frequency)) return []
  const end = formData.endDate || formData.end_date
  const rent = parseFloat(formData.rentAmount || formData.rent_amount) || 0
  const cycles = parseInt(formData.cycles || '1', 10)
  const freq = formData.paymentFrequency || formData.payment_frequency
  const timing = formData.commitmentTiming || formData.commitment_timing || 'start'
  const sched = buildPeriodicSchedule({
    startDate: baseDate,
    endDate: end,
    frequency: freq,
    commitmentTiming: timing,
    amount: rent,
    maxCount: cycles,
  })
  return sched.map((item) => ({
    number: item.index + 1,
    dueDate: item.dueDate.toISOString().split('T')[0],
    amount: item.amount,
  }))
}

// Source: ContractDocument.tsx:343 — dues || getPaymentSchedule(formData)
// In the old program, `dues` is undefined for new contracts, so it falls through
// to getPaymentSchedule. In the new program, `dues` is initialized as [] (empty
// array) which is truthy in JS. We must check length > 0 to fall through correctly.
const schedule = computed(() => {
  if (props.dues && props.dues.length > 0) return props.dues
  return getPaymentSchedule(form.value)
})

const totalAmount = computed(() => schedule.value.reduce((sum, s) => sum + (s.amount || 0), 0))
const dueAmount = computed(() => (schedule.value.length > 0 ? schedule.value[0].amount : 0))

// ---- Default terms ----
const defaultTerms = `1. يلتزم المستأجر باستخدام الوحدة للغرض المتفق عليه وعدم استخدامها لغرض غير مشروع.
2. لا يجوز للمستأجر تأجير الوحدة لطرف آخر دون موافقة خطية مسبقة من المؤجر.
3. يلتزم المستأجر بالمحافظة على الوحدة وعدم إجراء أي تعديلات دون إذن.
4. يلتزم المستأجر بسداد المبالغ المستحقة في مواعيدها المحددة.
5. يلتزم المستأجر بإخلاء الوحدة عند انتهاء مدة العقد أو إنهائه وفقاً للأنظمة.
6. في حال التأخر في سداد الإيجار لأكثر من 15 يوماً، يحق للمؤجر اتخاذ الإجراءات القانونية.`

// ---- Number to words (Arabic) ----
function numberToWordsArabic(n) {
  if (n === 0) return 'صفر'
  const ones = ['', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة', 'عشرة', 'أحد عشر', 'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر', 'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر']
  const tens = ['', '', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون']
  const hundreds = ['', 'مائة', 'مائتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة', 'سبعمائة', 'ثمانمائة', 'تسعمائة']

  function convertLessThanThousand(num) {
    if (num === 0) return ''
    if (num < 20) return ones[num]
    if (num < 100) {
      const t = Math.floor(num / 10)
      const o = num % 10
      return o > 0 ? `${ones[o]} و${tens[t]}` : tens[t]
    }
    const h = Math.floor(num / 100)
    const rem = num % 100
    if (rem === 0) return hundreds[h]
    return `${hundreds[h]} و${convertLessThanThousand(rem)}`
  }

  const parts = []
  let remaining = Math.floor(n)

  if (remaining >= 1000000) {
    const m = Math.floor(remaining / 1000000)
    parts.push(`${convertLessThanThousand(m)} مليون${m > 2 ? 'ات' : m === 2 ? 'ان' : ''}`)
    remaining %= 1000000
  }
  if (remaining >= 1000) {
    const th = Math.floor(remaining / 1000)
    if (th === 1) parts.push('ألف')
    else if (th === 2) parts.push('ألفان')
    else if (th >= 3 && th <= 10) parts.push(`${convertLessThanThousand(th)} آلاف`)
    else parts.push(`${convertLessThanThousand(th)} ألف`)
    remaining %= 1000
  }
  if (remaining > 0) {
    parts.push(convertLessThanThousand(remaining))
  }

  return parts.join(' و ')
}
</script>

<style scoped>
.contract-document {
  font-family: 'Tajawal', 'Cairo', sans-serif;
}
.card-v2 {
  background: #faf9f6;
  border: 1px solid #e7e5e0;
  border-radius: 0.5rem;
}
.select-v2 {
  border: 1px solid #d4d0c8;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  background: #fff;
}
.input-v2 {
  border: 1px solid #d4d0c8;
  border-radius: 0.375rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  background: #fff;
}
/* Number input-v2: reserve space for browser spinner at inline-end */
input[type="number"].input-v2 {
  padding-inline-end: 1.25rem;
}
.print-only {
  display: none;
}
@media print {
  .print-only {
    display: block;
  }
  .print-keep-together {
    break-inside: avoid;
  }
  #print-area {
    box-shadow: none !important;
    padding: 0 !important;
    max-width: 100% !important;
  }
}
</style>
