<template>
  <AppLayout>
    <div class="p-6 lg:p-8 max-w-5xl mx-auto" dir="rtl">
      <PageHeader title="الإعدادات" description="إدارة إعدادات النظام والمؤسسة" />

      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
      </div>

      <div v-else class="animate-fade-in">
        <div class="flex flex-col lg:flex-row gap-5">
          <!-- Sidebar tabs -->
          <div class="w-full lg:w-60 shrink-0">
            <Card padding="none" class="overflow-hidden flex flex-row lg:flex-col overflow-x-auto">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                class="flex w-full items-center gap-3 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap"
                :class="activeTab === tab.key
                  ? 'bg-gold-50 text-gold-700 border-b-2 lg:border-b-0 lg:border-r-2 border-gold-500'
                  : 'text-navy-400 hover:bg-ivory-100'"
                @click="activeTab = tab.key"
              >
                <span class="w-4 h-4 shrink-0" v-html="tab.icon"></span>
                {{ tab.label }}
              </button>
            </Card>
          </div>

          <!-- Tab content -->
          <div class="flex-1 min-w-0">
            <!-- General tab -->
            <div v-if="activeTab === 'general'">
              <!-- Status bar -->
              <div class="mb-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div class="text-sm text-navy-400">
                  <span v-if="saved" class="text-emerald-600 font-medium">تم الحفظ بنجاح!</span>
                  <span v-else-if="editMode" class="text-gold-700 font-medium">وضع التعديل</span>
                  <span v-else>بيانات المؤجر والإعدادات المالية</span>
                </div>
                <div class="flex items-center gap-2">
                  <template v-if="editMode">
                    <button class="btn-premium btn-outline" @click="cancelEdit">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                      إلغاء
                    </button>
                    <button class="btn-premium btn-gold" :disabled="saving" @click="saveGeneral">
                      <span v-if="saving" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
                      <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                      {{ saving ? 'جاري الحفظ...' : 'حفظ التغييرات' }}
                    </button>
                  </template>
                  <template v-else>
                    <button class="btn-premium btn-gold" @click="startEdit">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                      تعديل البيانات
                    </button>
                  </template>
                </div>
              </div>

              <div class="space-y-3">
                <!-- هوية المؤجر -->
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      هوية المؤجر
                    </span>
                  </template>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <!-- نوع المؤجر -->
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">نوع المؤجر</label>
                      <select v-if="editMode" v-model="form.landlord_type" class="input-premium" @change="onLessorTypeChange">
                        <option value="person">شخص</option>
                        <option value="company">شركة / مؤسسة</option>
                      </select>
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_type === 'company' ? 'شركة / مؤسسة' : 'شخص' }}
                      </p>
                    </div>
                    <!-- الاسم -->
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">
                        {{ form.landlord_type === 'company' ? 'اسم الشركة / المؤسسة' : 'الاسم الكامل' }}
                        <span v-if="editMode" class="text-red-500">*</span>
                      </label>
                      <input v-if="editMode" v-model="form.landlord_name" type="text"
                        :placeholder="form.landlord_type === 'company' ? 'اسم الشركة' : 'الاسم الكامل'"
                        class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_name || '—' }}
                      </p>
                    </div>
                    <!-- رقم الهوية -->
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">
                        {{ form.landlord_type === 'company' ? 'رقم التسجيل / السجل التجاري' : 'رقم الهوية' }}
                        <span v-if="editMode" class="text-red-500">*</span>
                      </label>
                      <input v-if="editMode" v-model="form.landlord_id" type="text"
                        :placeholder="form.landlord_type === 'company' ? 'رقم السجل' : 'رقم الهوية'"
                        class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_id || '—' }}
                      </p>
                    </div>
                  </div>
                </Card>

                <!-- بيانات التواصل -->
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      بيانات التواصل
                    </span>
                  </template>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">الهاتف</label>
                      <input v-if="editMode" v-model="form.landlord_phone" type="text" dir="ltr" placeholder="رقم الهاتف" class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center" dir="ltr">
                        {{ form.landlord_phone || '—' }}
                      </p>
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">العنوان</label>
                      <input v-if="editMode" v-model="form.landlord_address" type="text" placeholder="العنوان الكامل" class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_address || '—' }}
                      </p>
                    </div>
                  </div>
                </Card>

                <!-- بيانات المفوض (only for company) -->
                <Card v-if="form.landlord_type === 'company'" padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      بيانات المفوض
                    </span>
                  </template>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">اسم المفوض <span v-if="editMode" class="text-red-500">*</span></label>
                      <input v-if="editMode" v-model="form.landlord_representative_name" type="text" placeholder="اسم المفوض" class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_representative_name || '—' }}
                      </p>
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">صفة المفوض <span v-if="editMode" class="text-red-500">*</span></label>
                      <input v-if="editMode" v-model="form.landlord_representative_title" type="text" placeholder="مثلاً: مدير عام" class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_representative_title || '—' }}
                      </p>
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">رقم هوية المفوض <span v-if="editMode" class="text-red-500">*</span></label>
                      <input v-if="editMode" v-model="form.landlord_representative_id" type="text" placeholder="رقم هوية المفوض" class="input-premium" />
                      <p v-else class="rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800 min-h-[40px] flex items-center">
                        {{ form.landlord_representative_id || '—' }}
                      </p>
                    </div>
                  </div>
                </Card>

                <!-- هوية الطباعة -->
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      هوية الطباعة
                    </span>
                  </template>
                  <div v-if="editMode" class="space-y-1">
                    <label class="text-xs font-medium text-navy-500">شعار المؤجر</label>
                    <div v-if="form.logo" class="relative block h-32 w-full max-w-sm overflow-hidden rounded-[10px] border border-ivory-300 bg-ivory-100">
                      <img :src="form.logo" alt="شعار المؤسسة" class="h-full w-full object-contain" />
                      <button type="button" class="absolute top-1 left-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-white shadow-sm hover:bg-red-700" @click="form.logo = ''">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                      </button>
                    </div>
                    <label v-else class="flex cursor-pointer items-center gap-2 rounded-[10px] border border-dashed border-ivory-400 bg-ivory-100 px-4 py-3 text-sm text-navy-400 hover:bg-ivory-200 transition-colors">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
                      <span>اضغط لرفع صورة الشعار</span>
                      <input type="file" accept="image/*" class="hidden" @change="handleLogoUpload" />
                    </label>
                  </div>
                  <div v-else class="space-y-1">
                    <label class="text-xs font-medium text-navy-500">شعار المؤجر</label>
                    <img v-if="form.logo" :src="form.logo" alt="شعار المؤجر" class="h-32 w-full max-w-sm rounded-[10px] border border-ivory-300 object-contain bg-ivory-100" />
                    <p v-else class="text-sm text-navy-400">لم يتم إضافة شعار</p>
                  </div>
                </Card>

                <!-- الإعدادات المالية -->
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      الإعدادات المالية
                    </span>
                  </template>
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">العملة الأساسية</label>
                      <select v-if="editMode && !currencyLocked" v-model="form.currency" class="input-premium">
                        <option v-for="c in currencies" :key="c.value" :value="c.value">{{ c.label }}</option>
                      </select>
                      <div v-else class="space-y-1">
                        <div class="flex items-center gap-2 rounded-[10px] border border-ivory-300 bg-ivory-100 px-3 py-2 text-sm text-navy-800">
                          <span>{{ currencyLabel }}</span>
                          <svg v-if="currencyLocked" class="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                        </div>
                        <p v-if="currencyLocked" class="flex items-start gap-1.5 text-xs text-amber-600">
                          <svg class="w-3 h-3 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                          <span>لا يمكن تغيير العملة الأساسية بعد بدء المعاملات المالية.</span>
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>

                <!-- Submit error -->
                <div v-if="errors.submit" class="card-premium p-4 text-sm text-red-700 bg-red-50 border-red-200">
                  {{ errors.submit }}
                </div>
              </div>
            </div>

            <!-- Contracts tab -->
            <div v-if="activeTab === 'contracts'">
              <div class="mb-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <div class="text-sm text-navy-400">
                  <span v-if="savedContract" class="text-emerald-600 font-medium">تم الحفظ بنجاح!</span>
                  <span v-else>قم بإجراء التعديلات ثم اضغط حفظ</span>
                </div>
                <button class="btn-premium btn-gold" :disabled="savingContract" @click="saveContractSettings">
                  <span v-if="savingContract" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
                  <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  {{ savingContract ? 'جاري الحفظ...' : 'حفظ التغييرات' }}
                </button>
              </div>

              <div class="space-y-3">
                <!-- إعدادات العقود -->
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      إعدادات العقود
                    </span>
                  </template>
                  <div class="grid grid-cols-1 gap-3">
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">عدد الأيام للتنبيه قبل انتهاء العقد</label>
                      <input v-model.number="contractForm.contract_alert_days" type="number" min="0" placeholder="30" class="input-premium" />
                    </div>
                    <div class="space-y-1">
                      <label class="text-xs font-medium text-navy-500">الشروط والأحكام الافتراضية للعقد</label>
                      <textarea v-model="contractForm.default_contract_terms" rows="8" placeholder="اكتب هنا الشروط والأحكام الافتراضية التي ستظهر في العقود..." class="input-premium resize-y"></textarea>
                    </div>
                  </div>
                </Card>
              </div>
            </div>

            <!-- Due types tab -->
            <div v-if="activeTab === 'due_types'">
              <div class="space-y-3">
                <Card padding="md">
                  <template #title>
                    <span class="flex items-center gap-2">
                      <span class="w-1 h-4 rounded-full bg-gradient-to-b from-gold-400 to-gold-600"></span>
                      أنواع الالتزامات
                    </span>
                  </template>
                  <!-- Inline add -->
                  <div class="mb-3 flex gap-2">
                    <input v-model="newTypeName" type="text" placeholder="اسم نوع الالتزام الجديد" class="input-premium flex-1" @keydown.enter="addDueType" />
                    <button class="btn-premium btn-gold" @click="addDueType">
                      إضافة
                    </button>
                  </div>
                  <!-- List -->
                  <div class="space-y-2">
                    <div v-for="dt in dueTypes" :key="dt.name"
                      class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 rounded-lg border border-ivory-300/50 bg-ivory-50/50 px-4 py-3">
                      <div class="flex items-center gap-3">
                        <span class="text-sm font-medium text-navy-800">{{ dt.due_type_name }}</span>
                        <span class="text-xs px-2 py-0.5 rounded-full font-medium bg-ivory-200 text-navy-500">
                          {{ dt.is_system ? 'نظامي' : 'مخصص' }}
                        </span>
                      </div>
                      <div class="flex items-center gap-2">
                        <button
                          class="text-xs px-2 py-1 rounded-md font-medium transition-colors"
                          :class="dt.is_active
                            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                            : 'bg-ivory-200 text-navy-400 hover:bg-ivory-300'"
                          @click="toggleDueType(dt)"
                        >
                          {{ dt.is_active ? 'نشط' : 'معطل' }}
                        </button>
                        <button
                          class="flex items-center justify-center h-7 w-7 rounded-md text-red-600/80 hover:bg-red-50 hover:text-red-700 transition-colors"
                          title="حذف"
                          @click="deleteDueType(dt)"
                        >
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div v-if="!dueTypes.length" class="text-center py-8 text-navy-400 text-sm">
                    <p class="font-medium">لا توجد أنواع التزامات</p>
                    <p class="text-xs mt-1">لم يتم إضافة أي أنواع التزامات.</p>
                  </div>
                </Card>
              </div>
            </div>

            <!-- Account tab -->
            <div v-if="activeTab === 'account'">
              <div class="space-y-3">
                <!-- تسجيل الخروج -->
                <Card padding="md">
                  <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                    <div>
                      <p class="text-sm font-medium text-navy-800">تسجيل الخروج من النظام</p>
                      <p class="text-xs text-navy-400">سيتم إعادة توجيهك إلى صفحة تسجيل الدخول</p>
                    </div>
                    <button class="btn-premium btn-ghost text-red-600" @click="handleLogout">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                      تسجيل الخروج
                    </button>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import { callApi, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const router = useRouter()
const session = useSession()
const toast = useToast()
const { confirm } = useConfirm()

const tabs = [
  { key: 'general', label: 'الإعدادات العامة', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
  { key: 'contracts', label: 'إعدادات العقود', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>' },
  { key: 'due_types', label: 'أنواع الالتزامات', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>' },
  { key: 'account', label: 'الحساب', icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>' },
]

const currencies = [
  { value: 'ILS', label: 'شيكل (₪)' },
  { value: 'USD', label: 'دولار ($)' },
  { value: 'JOD', label: 'دينار أردني (JD)' },
]

const CONFIRMATION_TITLE = 'تأكيد تعديل بيانات قانونية'
const CONFIRMATION_MESSAGE = 'سيتم استخدام البيانات الجديدة في العقود الجديدة والتجديدات القادمة فقط، ولن تتغير بيانات العقود المعتمدة سابقًا. هل تريد المتابعة؟'

const legalSensitiveKeys = [
  'landlord_type', 'landlord_name', 'landlord_id',
  'landlord_representative_name', 'landlord_representative_id', 'landlord_representative_title',
]

const activeTab = ref('general')
const loading = ref(true)
const editMode = ref(false)
const saving = ref(false)
const saved = ref(false)
const savingContract = ref(false)
const savedContract = ref(false)
const settings = ref(null)
const dueTypes = ref([])
const newTypeName = ref('')
const errors = ref({})

const form = ref({
  landlord_type: 'person', landlord_name: '', landlord_id: '',
  landlord_phone: '', landlord_address: '',
  landlord_representative_name: '', landlord_representative_id: '',
  landlord_representative_title: '',
  logo: '', currency: 'ILS',
})

const originalForm = ref(null)

const contractForm = ref({
  contract_alert_days: 30,
  default_contract_terms: '',
})

const currencyLocked = computed(() => !!settings.value?.meta?.locked)
const currencyLabel = computed(() => {
  const c = currencies.find(c => c.value === form.value.currency)
  return c ? c.label : form.value.currency
})

async function fetchSettings() {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.settings.get_settings')
    settings.value = res
    if (res) {
      form.value = {
        landlord_type: res.landlord_type || 'person',
        landlord_name: res.landlord_name || '',
        landlord_id: res.landlord_id || '',
        landlord_phone: res.landlord_phone || '',
        landlord_address: res.landlord_address || '',
        landlord_representative_name: res.landlord_representative_name || '',
        landlord_representative_id: res.landlord_representative_id || '',
        landlord_representative_title: res.landlord_representative_title || '',
        logo: res.logo || '',
        currency: res.currency || 'ILS',
      }
      contractForm.value = {
        contract_alert_days: res.contract_alert_days ?? 30,
        default_contract_terms: res.default_contract_terms || '',
      }
    }
  } catch { /* ignore */ } finally { loading.value = false }
}

async function fetchDueTypes() {
  try {
    const res = await callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 1 })
    dueTypes.value = res.dueTypes || []
  } catch { dueTypes.value = [] }
}

function startEdit() {
  originalForm.value = { ...form.value }
  editMode.value = true
  errors.value = {}
}

function cancelEdit() {
  if (originalForm.value) {
    form.value = { ...originalForm.value }
  }
  originalForm.value = null
  editMode.value = false
  errors.value = {}
}

function onLessorTypeChange() {
  if (form.value.landlord_type === 'person') {
    form.value.landlord_representative_name = ''
    form.value.landlord_representative_id = ''
    form.value.landlord_representative_title = ''
  } else if (originalForm.value) {
    form.value.landlord_representative_name = originalForm.value.landlord_representative_name
    form.value.landlord_representative_id = originalForm.value.landlord_representative_id
    form.value.landlord_representative_title = originalForm.value.landlord_representative_title
  }
}

function hasLegalSensitiveChanges() {
  if (!originalForm.value) return false
  return legalSensitiveKeys.some(key => {
    const a = String(originalForm.value[key] ?? '').trim()
    const b = String(form.value[key] ?? '').trim()
    return a !== b
  })
}

function validateGeneral() {
  const e = {}
  if (!form.value.landlord_name || !form.value.landlord_name.trim()) {
    e.landlord_name = 'اسم المؤجر مطلوب'
  }
  if (!form.value.landlord_id) {
    e.landlord_id = 'رقم الهوية أو التسجيل غير صالح'
  } else if (!/^\d{4,20}$/.test(String(form.value.landlord_id).trim())) {
    e.landlord_id = 'رقم الهوية أو التسجيل غير صالح'
  }
  if (form.value.landlord_type === 'company') {
    if (!form.value.landlord_representative_name || !form.value.landlord_representative_name.trim()) {
      e.landlord_representative_name = 'اسم المفوض مطلوب'
    }
    if (!form.value.landlord_representative_id) {
      e.landlord_representative_id = 'رقم هوية المفوض مطلوب'
    } else if (!/^\d{4,20}$/.test(String(form.value.landlord_representative_id).trim())) {
      e.landlord_representative_id = 'رقم هوية المفوض غير صالح'
    }
    if (!form.value.landlord_representative_title || !form.value.landlord_representative_title.trim()) {
      e.landlord_representative_title = 'صفة المفوض مطلوبة'
    }
  }
  errors.value = e
  return Object.keys(e).length === 0
}

async function saveGeneral(confirmed = false) {
  if (!validateGeneral()) {
    toast.error('يرجى تصحيح الأخطاء قبل الحفظ')
    return
  }

  // Legal-sensitive confirmation
  if (!confirmed && settings.value?.meta?.hasApprovedContract && hasLegalSensitiveChanges()) {
    const ok = await confirm({
      title: CONFIRMATION_TITLE,
      message: CONFIRMATION_MESSAGE,
      variant: 'warning',
      confirmLabel: 'تأكيد وحفظ',
    })
    if (!ok) return
    return saveGeneral(true)
  }

  saving.value = true
  try {
    const res = await callApi('rental.rental.api.settings.update_settings', { ...form.value, confirmed: confirmed ? 1 : 0 })
    // Check if backend needs confirmation
    if (res && res.needsConfirmation && !confirmed) {
      const ok = await confirm({
        title: CONFIRMATION_TITLE,
        message: res.error || CONFIRMATION_MESSAGE,
        variant: 'warning',
        confirmLabel: 'تأكيد وحفظ',
      })
      if (ok) return saveGeneral(true)
      return
    }
    editMode.value = false
    originalForm.value = null
    saved.value = true
    setTimeout(() => saved.value = false, 2000)
    window.dispatchEvent(new CustomEvent('settings-saved'))
    toast.success('تم حفظ الإعدادات بنجاح')
    fetchSettings()
  } catch (e) {
    const msg = extractError(e)
    if (msg.includes('لا يمكن تغيير العملة')) {
      errors.value = { submit: msg }
    }
    toast.error(msg)
  } finally { saving.value = false }
}

async function saveContractSettings() {
  savingContract.value = true
  try {
    await callApi('rental.rental.api.settings.update_settings', { ...contractForm.value })
    savedContract.value = true
    setTimeout(() => savedContract.value = false, 2000)
    window.dispatchEvent(new CustomEvent('settings-saved'))
    toast.success('تم حفظ إعدادات العقود')
    fetchSettings()
  } catch (e) { toast.error(extractError(e)) } finally { savingContract.value = false }
}

async function addDueType() {
  if (!newTypeName.value.trim()) return
  try {
    await callApi('rental.rental.api.settings.create_due_type', { due_type_name: newTypeName.value })
    newTypeName.value = ''
    fetchDueTypes()
  } catch (e) { toast.error(extractError(e)) }
}

async function toggleDueType(dt) {
  try {
    await callApi('rental.rental.api.settings.update_due_type', { name: dt.name, is_active: dt.is_active ? 0 : 1 })
    fetchDueTypes()
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteDueType(dt) {
  const ok = await confirm({
    title: 'حذف نوع الالتزام',
    message: 'هل أنت متأكد من حذف هذا النوع؟',
    variant: 'warning',
    confirmLabel: 'حذف',
  })
  if (!ok) return
  try {
    await callApi('rental.rental.api.settings.delete_due_type', { name: dt.name })
    fetchDueTypes()
  } catch (e) { toast.error(extractError(e)) }
}

async function handleLogout() {
  try {
    await session.logout()
    router.push({ name: 'Login' })
  } catch { /* ignore */ }
}

async function handleLogoUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  if (!file.type.startsWith('image/')) return
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '1')
  formData.append('doctype', 'Rental Settings')
  formData.append('fieldname', 'logo')
  try {
    const res = await fetch('/api/method/upload_file', {
      method: 'POST', body: formData,
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    })
    const data = await res.json()
    form.value.logo = data.message.file_url
  } catch {
    toast.error('فشل رفع الشعار')
  }
}

onMounted(() => { fetchSettings(); fetchDueTypes() })
</script>
