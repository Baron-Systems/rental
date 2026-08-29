<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <PageHeader title="الالتزامات" description="إدارة الالتزامات المالية للمستأجرين" action-label="إضافة التزام" @action="openCreateModal(); showCreateForm = true">
        <template #actions>
          <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="printing || loading" @click="handlePrint">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
            <span>{{ printing ? 'جاري...' : 'طباعة' }}</span>
          </button>
        </template>
      </PageHeader>

      <!-- Stats -->
      <div v-if="stats" class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <StatCard label="إجمالي الالتزامات" :value="stats.total || 0" icon="receipt" color="navy" />
        <StatCard label="مسودات" :value="stats.draft || 0" icon="receipt" color="amber" />
        <StatCard label="مستحق حتى اليوم" :value="stats.due || 0" icon="receipt" color="green" />
        <StatCard label="مستقبلي" :value="stats.future || 0" icon="receipt" color="blue" />
        <StatCard label="ملغي" :value="stats.cancelled || 0" icon="receipt" color="red" />
      </div>

      <!-- Create due modal (source: dues/page.tsx:960-1184) -->
      <div v-if="showCreateForm" class="fixed inset-x-0 bottom-0 top-16 z-50 flex items-center justify-center p-4 md:p-6 print:hidden">
        <div class="absolute inset-0 bg-foreground/20 backdrop-blur-sm" @click="showCreateForm = false"></div>
        <div class="relative z-10 w-full max-w-2xl max-h-[calc(100%-32px)] md:max-h-[calc(100%-48px)] overflow-hidden rounded-[14px] border border-ivory-300 bg-white shadow-soft-lg animate-scale-in flex flex-col">
          <!-- Header -->
          <div class="shrink-0 p-6 pb-4 flex items-center justify-between">
            <div>
              <h3 class="text-base font-bold text-navy-900">إنشاء التزام</h3>
              <p class="mt-0.5 text-sm text-navy-400">إضافة التزام يدوي على عقد</p>
            </div>
            <button @click="showCreateForm = false" class="inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-navy-400 transition-colors hover:bg-ivory-200 hover:text-navy-700">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <form @submit.prevent="createDue" class="flex flex-col min-h-0 flex-1">
            <div class="flex-1 min-h-0 overflow-y-auto p-6 pt-4">
              <div v-if="createError" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ createError }}</div>

              <div class="space-y-4">
                <!-- Kind toggle (source: page.tsx:987-1004) -->
                <div class="space-y-2.5">
                  <label class="text-sm font-medium text-navy-800">نوع الالتزام</label>
                  <div class="inline-flex h-9 rounded-[10px] border border-ivory-300 bg-ivory-100 p-0.5">
                    <button type="button" @click="handleKindChange('contractual')" :class="['h-8 rounded-lg px-3 text-xs font-medium transition-colors', formMode === 'contractual' ? 'bg-blue-500 text-white shadow-sm' : 'text-navy-700 hover:text-navy-900 hover:bg-ivory-200/60']">التزام تعاقدي</button>
                    <button type="button" @click="handleKindChange('additional')" :class="['h-8 rounded-lg px-3 text-xs font-medium transition-colors', formMode === 'additional' ? 'bg-blue-500 text-white shadow-sm' : 'text-navy-700 hover:text-navy-900 hover:bg-ivory-200/60']">التزام إضافي</button>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <!-- Tenant (source: page.tsx:1008-1020) -->
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium text-navy-800">المستأجر <span class="text-red-500">*</span></label>
                    <SearchableTenantSelect
                      :model-value="newDue.tenantId"
                      :value-label="selectedFormTenantName"
                      placeholder="اختر المستأجر *"
                      @select="handleFormTenantSelect"
                    />
                  </div>

                  <!-- Contract (source: page.tsx:1022-1040) -->
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium text-navy-800">العقد <span class="text-red-500">*</span></label>
                    <select :value="newDue.contract" @change="handleContractChange($event.target.value)" class="input-premium" :disabled="!newDue.tenantId" required>
                      <option value="">{{ newDue.tenantId ? 'اختر العقد *' : 'اختر المستأجر أولاّ' }}</option>
                      <option v-for="c in formContracts" :key="c.name" :value="c.name">{{ formatContractOptionLabel(c) }}</option>
                    </select>
                    <span v-if="selectedFormContract" class="flex items-center gap-1 text-xs text-navy-400">
                      <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                      الوحدة {{ selectedFormContract.unit_number || selectedFormContract.unit?.unit_number || '—' }} — {{ selectedFormContract.building_name || selectedFormContract.building?.name || '—' }}
                    </span>
                  </div>

                  <!-- Due type (source: page.tsx:1042-1065) -->
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium text-navy-800">نوع الالتزام <span class="text-red-500">*</span></label>
                    <select :value="newDue.due_type" @change="handleDueTypeChange($event.target.value)" class="input-premium" :disabled="!newDue.contract" required>
                      <option value="">{{ newDue.contract ? (formMode === 'contractual' ? 'اختر نوع الالتزام *' : 'اختر نوع إضافي *') : 'اختر العقد أولاّ' }}</option>
                      <option v-for="opt in dueTypeOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    </select>
                    <span v-if="formMode === 'contractual' && selectedCharge && selectedCharge.calculation_method !== 'metered'" class="mt-1 text-xs text-navy-400">
                      طريقة الاحتساب: <span class="text-navy-800">{{ getCalculationMethodLabel(selectedCharge.calculation_method) }}</span>
                    </span>
                    <span v-if="formMode === 'additional' && newDue.contract && additionalDueTypes.length === 0" class="mt-1 text-xs text-amber-600">
                      لا توجد أنواع مخصصة فعالة لهذا العقد. يمكنك إضافتها من الإعدادات.
                    </span>
                  </div>

                  <!-- Date (source: page.tsx:1067-1078) -->
                  <div class="space-y-1.5">
                    <label class="text-sm font-medium text-navy-800">التاريخ <span class="text-red-500">*</span></label>
                    <input v-model="newDue.due_date" type="date" dir="ltr" class="input-premium" required />
                  </div>

                  <!-- Metered fields (source: page.tsx:1080-1138) -->
                  <template v-if="formMode === 'contractual' && selectedCharge?.calculation_method === 'metered'">
                    <div class="space-y-1.5 md:col-span-2 rounded-lg border border-ivory-300 bg-ivory-100/40 p-3">
                      <label class="text-sm font-medium text-navy-800">بيانات الاستهلاك</label>
                      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div class="space-y-1.5">
                          <label class="text-xs text-navy-400">القراءة السابقة</label>
                          <input :value="newDue.previous_meter_reading" type="text" readonly class="input-premium bg-ivory-100" />
                        </div>
                        <div class="space-y-1.5">
                          <label class="text-xs text-navy-400">القراءة الحالية <span class="text-red-500">*</span></label>
                          <input :value="newDue.current_meter_reading" @input="handleMeterInput($event.target.value, newDue.unit_price)" type="number" step="0.01" placeholder="أدخل القراءة الجديدة" class="input-premium" required />
                        </div>
                        <div class="space-y-1.5">
                          <label class="text-xs text-navy-400">الاستهلاك</label>
                          <input :value="newDue.meter_consumption" type="text" readonly class="input-premium bg-ivory-100" />
                        </div>
                        <div class="space-y-1.5">
                          <label class="text-xs text-navy-400">سعر الوحدة <span class="text-red-500">*</span></label>
                          <input :value="newDue.unit_price" @input="handleMeterInput(newDue.current_meter_reading, $event.target.value)" type="number" step="0.01" placeholder="مثال: 0.15" class="input-premium" required />
                        </div>
                        <div class="space-y-1.5 sm:col-span-2">
                          <label class="text-xs text-navy-400">المبلغ (تلقائي)</label>
                          <input :value="newDue.amount" type="text" readonly class="input-premium bg-ivory-100" />
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- Amount (non-metered) (source: page.tsx:1140-1153) -->
                  <template v-else>
                    <div class="space-y-1.5">
                      <label class="text-sm font-medium text-navy-800">المبلغ <span class="text-red-500">*</span></label>
                      <input v-model="newDue.amount" type="number" step="0.01" placeholder="أدخل المبلغ" class="input-premium" required />
                    </div>
                  </template>

                  <!-- Description (source: page.tsx:1156-1166) -->
                  <div class="space-y-1.5 md:col-span-2">
                    <label class="text-sm font-medium text-navy-800">{{ formMode === 'contractual' ? 'الوصف (اختياري)' : 'السبب *' }}</label>
                    <input v-model="newDue.description" type="text" :placeholder="formMode === 'contractual' ? 'أدخل الوصف' : 'أدخل سبب الالتزام الإضافي'" class="input-premium" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="shrink-0 px-6 py-4 border-t border-ivory-300/60">
              <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button type="button" class="btn-premium btn-outline" @click="showCreateForm = false">إلغاء</button>
                <button type="submit" class="btn-premium btn-gold" :disabled="creating">
                  <span v-if="creating" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
                  حفظ
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <!-- Inline edit modal -->
      <Card v-if="editingDue" padding="lg" class="mb-4 animate-slide-up">
        <template #title>تعديل التزام</template>
        <form @submit.prevent="saveEdit" class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="المبلغ" required>
              <input v-model.number="editForm.amount" type="number" step="0.01" required class="input-premium" />
            </FormField>
            <FormField label="تاريخ الاستحقاق" required>
              <input v-model="editForm.due_date" type="date" dir="ltr" required class="input-premium" />
            </FormField>
            <FormField label="الوصف">
              <input v-model="editForm.description" type="text" class="input-premium" />
            </FormField>
            <template v-if="editingDue.calculation_method === 'metered'">
              <FormField label="القراءة الحالية">
                <input v-model.number="editForm.current_meter_reading" type="number" step="0.01" class="input-premium" />
              </FormField>
              <FormField label="سعر الوحدة">
                <input v-model.number="editForm.unit_price" type="number" step="0.01" class="input-premium" />
              </FormField>
            </template>
          </div>
          <div class="flex gap-2 justify-end">
            <button type="button" class="btn-premium btn-outline" @click="editingDue = null">إلغاء</button>
            <button type="submit" class="btn-premium btn-gold" :disabled="savingEdit">
              <span v-if="savingEdit" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
              حفظ
            </button>
          </div>
        </form>
      </Card>

      <!-- Filters: Row 1 — Search + Status + Tenant + Advanced toggle -->
      <div class="flex flex-col gap-3 lg:flex-row lg:items-start mb-4">
        <div class="relative flex-1">
          <svg class="pointer-events-none absolute top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400 icon-start" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <input v-model="filters.search" type="text" placeholder="بحث برقم الالتزام..." class="input-premium has-icon-start" @input="debouncedFetch" />
        </div>
        <div class="w-full lg:w-44">
          <select v-model="filters.status" class="input-premium" @change="fetchDues()">
            <option value="">كل الحالات</option>
            <option value="draft">مسودة</option>
            <option value="due">مستحق</option>
            <option value="future">مستقبلي</option>
            <option value="cancelled">ملغي</option>
          </select>
        </div>
        <div class="w-full lg:w-64">
          <SearchableTenantSelect
            v-model="filters.tenantId"
            :value-label="selectedFilterTenantName"
            placeholder="اختر المستأجر"
            @select="handleFilterTenantSelect"
          />
        </div>
        <button class="btn-premium btn-outline inline-flex items-center gap-1.5 w-full lg:w-auto" @click="showAdvanced = !showAdvanced">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
          فلاتر إضافية
          <span v-if="activeAdvancedCount > 0" class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-gold-500 px-1.5 text-[10px] font-medium text-white">{{ activeAdvancedCount }}</span>
        </button>
      </div>

      <!-- Advanced filters -->
      <Card v-if="showAdvanced" padding="md" class="mb-4">
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div class="w-full min-w-0 space-y-1.5">
            <label class="text-xs text-navy-400">العقد</label>
            <div class="flex w-full min-w-0 items-center gap-2">
              <select v-model="filters.contractId" class="input-premium flex-1 min-w-0" :disabled="!filters.tenantId || filterContractsLoading" @change="fetchDues()">
                <option value="">كل العقود</option>
                <option v-for="c in filterContracts" :key="c.name" :value="c.name">{{ c.contract_number }} - {{ c.tenant_name || c.tenant }}</option>
              </select>
              <button v-if="filters.contractId" type="button" class="rounded-md p-1.5 text-navy-400 hover:bg-ivory-200 hover:text-navy-700" @click="clearContractFilter">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
          </div>
          <div class="w-full min-w-0 space-y-1.5">
            <label class="text-xs text-navy-400">نوع الالتزام</label>
            <select v-model="filters.dueTypeId" class="input-premium w-full" @change="fetchDues()">
              <option value="">كل الأنواع</option>
              <option v-for="dt in dueTypes" :key="dt.name" :value="dt.name">{{ dt.due_type_name }}</option>
            </select>
          </div>
          <div class="w-full min-w-0 space-y-1.5">
            <label class="text-xs text-navy-400">مصدر الالتزام</label>
            <select v-model="filters.sourceType" class="input-premium w-full" @change="fetchDues()">
              <option value="">كل المصادر</option>
              <option value="auto_contract">ناتج من العقد</option>
              <option value="manual_contract">يدوي تعاقدي</option>
              <option value="additional">إضافي</option>
            </select>
          </div>
          <div class="w-full min-w-0 space-y-1.5">
            <label class="text-xs text-navy-400">من تاريخ</label>
            <input v-model="filters.fromDate" type="date" dir="ltr" class="input-premium w-full" @change="fetchDues()" />
          </div>
          <div class="w-full min-w-0 space-y-1.5">
            <label class="text-xs text-navy-400">إلى تاريخ</label>
            <input v-model="filters.toDate" type="date" dir="ltr" class="input-premium w-full" @change="fetchDues()" />
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-ivory-300/60">
          <button v-if="filters.fromDate || filters.toDate" type="button" class="btn-premium btn-ghost text-sm" @click="clearDatePeriod">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            مسح الفترة
          </button>
          <button v-if="hasActiveFilters" type="button" class="btn-premium btn-ghost text-sm" @click="clearAllFilters">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            مسح الفلاتر
          </button>
        </div>
      </Card>

      <!-- Table -->
      <Card padding="none">
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-8 h-8 border-2 border-gold-400 border-t-transparent rounded-full animate-spin"></div>
        </div>
        <EmptyState v-else-if="dues.length === 0" title="لا توجد التزامات" />
        <DataTable v-else :columns="columns">
          <TableRow v-for="d in dues" :key="d.name" :class="d.status === 'cancelled' ? 'opacity-50' : ''">
            <TableCell>
              <router-link :to="`/dues/${d.name}`" class="font-semibold text-navy-800 hover:text-gold-600">{{ d.due_number || 'مسودة' }}</router-link>
            </TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-sm font-medium text-navy-800">
                <svg class="w-3.5 h-3.5 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                {{ d.tenant_name || d.tenant || '—' }}
              </div>
              <div class="flex items-center gap-1 text-xs text-navy-400 mt-0.5">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
                {{ d.building_name || '—' }} / {{ d.unit_number || '—' }}
              </div>
            </TableCell>
            <TableCell>{{ d.due_type_name || d.due_type || '—' }}</TableCell>
            <TableCell>
              <div class="flex items-center gap-1 text-sm text-navy-400">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                {{ formatDate(d.due_date) }}
              </div>
            </TableCell>
            <TableCell><span class="font-bold tabular-nums">{{ formatMoney(d.amount, currency) }}</span></TableCell>
            <TableCell><StatusBadge :status="temporalStatus(d)" :label="temporalLabel[temporalStatus(d)]" /></TableCell>
            <TableCell align="center">
              <div class="flex items-center justify-center gap-1">
                <router-link :to="`/dues/${d.name}`" class="w-8 h-8 rounded-lg flex items-center justify-center text-navy-500 hover:bg-gold-50 hover:text-gold-600 transition-colors" title="عرض">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
                <button v-if="d.status === 'draft' && ['manual', 'manual_contract', 'additional'].includes(d.source_type)" class="w-8 h-8 rounded-lg flex items-center justify-center text-gold-600 hover:bg-gold-50 transition-colors" title="تعديل" @click="startEdit(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                </button>
                <button v-if="d.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-emerald-600 hover:bg-emerald-50 transition-colors" title="اعتماد" @click="approveDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                </button>
                <button v-if="d.status === 'approved'" class="w-8 h-8 rounded-lg flex items-center justify-center text-amber-600 hover:bg-amber-50 transition-colors" title="إلغاء" @click="cancelDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
                <button v-if="d.status === 'draft'" class="w-8 h-8 rounded-lg flex items-center justify-center text-red-600 hover:bg-red-50 transition-colors" title="حذف" @click="deleteDue(d)">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            </TableCell>
          </TableRow>
        </DataTable>
        <div v-if="pagination" class="border-t border-ivory-300/60 px-4 py-3 text-xs text-navy-400 flex items-center justify-between">
          <span>إجمالي: {{ pagination.total }} التزام</span>
          <span v-if="filters.search">نتائج البحث: "{{ filters.search }}"</span>
        </div>
        <Pagination v-if="pagination" :page="pagination.page" :page-size="pagination.pageSize" :total="pagination.total" @change="onPageChange" />
      </Card>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Pagination from '@/components/ui/Pagination.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import FormField from '@/components/ui/FormField.vue'
import SearchableTenantSelect from '@/components/ui/SearchableTenantSelect.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'

const session = useSession()
const router = useRouter()
const toast = useToast()
const { confirm } = useConfirm()

const currency = computed(() => session.state.account?.settings?.currency || 'ILS')

const columns = [
  { key: 'number', label: 'رقم الالتزام' },
  { key: 'tenant', label: 'المستأجر / الوحدة' },
  { key: 'type', label: 'النوع' },
  { key: 'date', label: 'تاريخ الالتزام' },
  { key: 'amount', label: 'المبلغ' },
  { key: 'status', label: 'الحالة الزمنية' },
  { key: 'actions', label: '', align: 'center' },
]

const dues = ref([])
const loading = ref(true)
const pagination = ref(null)
const stats = ref(null)
const showCreateForm = ref(false)
const creating = ref(false)
const dueTypes = ref([])

// Filters state (source: page.tsx:276-284)
const filters = ref({
  search: '',
  status: '',
  sourceType: '',
  fromDate: '',
  toDate: '',
  tenantId: '',
  contractId: '',
  dueTypeId: '',
})
const printing = ref(false)
const showAdvanced = ref(false)
const selectedFilterTenantName = ref('')
const filterContracts = ref([])
const filterContractsLoading = ref(false)

// Computed: active advanced count (source: page.tsx:381-384)
const activeAdvancedCount = computed(() =>
  [filters.value.contractId, filters.value.dueTypeId, filters.value.sourceType, filters.value.fromDate, filters.value.toDate].filter(Boolean).length
)

// Computed: has active filters (source: page.tsx:386-396)
const hasActiveFilters = computed(() =>
  filters.value.status !== '' ||
  filters.value.tenantId !== '' ||
  filters.value.contractId !== '' ||
  filters.value.dueTypeId !== '' ||
  filters.value.sourceType !== '' ||
  filters.value.fromDate !== '' ||
  filters.value.toDate !== ''
)

const newDue = ref({
  tenantId: '',
  contract: '',
  due_type: '',
  amount: '',
  due_date: new Date().toISOString().split('T')[0],
  description: '',
  due_kind: 'contractual',
  previous_meter_reading: '',
  current_meter_reading: '',
  meter_consumption: '',
  unit_price: '',
})
const formMode = ref('contractual')  // 'contractual' | 'additional'
const formContracts = ref([])        // contracts for selected tenant
const contractCharges = ref([])      // charges for selected contract
const selectedFormTenantName = ref('')
const createError = ref('')

const editingDue = ref(null)
const editForm = ref({ amount: null, due_date: '', description: '', current_meter_reading: null, unit_price: null })
const savingEdit = ref(false)

// ---- Create form computed (source: page.tsx:314-338) ----
const selectedFormContract = computed(() =>
  formContracts.value.find((c) => c.name === newDue.value.contract) || null
)

const isContractualMode = computed(() => formMode.value === 'contractual')

// Additional due types: non-system, active, not already in contract charges (source: page.tsx:317-321)
const additionalDueTypes = computed(() => {
  if (!selectedFormContract.value) return []
  const contractDueTypeIds = new Set((selectedFormContract.value.contract_charges || []).map((c) => c.due_type || c.due_type_id))
  return dueTypes.value.filter((dt) => !dt.is_system && dt.is_active && !contractDueTypeIds.has(dt.name))
})

// Selected charge for contractual mode (source: page.tsx:323-326)
const selectedCharge = computed(() =>
  isContractualMode.value ? contractCharges.value.find((c) => c.due_type_id === newDue.value.due_type) : null
)

// Due type options based on mode (source: page.tsx:333-338)
const dueTypeOptions = computed(() => {
  if (isContractualMode.value) {
    return contractCharges.value.map((c) => ({ value: c.due_type_id, label: c.due_type_name || '' }))
  }
  return additionalDueTypes.value.map((dt) => ({ value: dt.name, label: dt.due_type_name || '' }))
})

// ---- Helpers (source: page.tsx:172-194, 510-534) ----
function formatContractOptionLabel(c) {
  const building = c.building_name || c.building?.name || '—'
  const unit = c.unit_number || c.unit?.unit_number || '—'
  return `${c.contract_number} — ${building} — الوحدة ${unit}`
}

function getCalculationMethodLabel(method) {
  switch (method) {
    case 'metered': return 'حسب قراءة العداد'
    case 'actual_bill': return 'حسب قيمة الفاتورة'
    case 'on_demand': return 'حسب الحاجة'
    case 'fixed_periodic': return 'دوري ثابت (تلقائي)'
    default: return '—'
  }
}

function calculateMeterFields(prev, curr, price) {
  const p = parseFloat(prev || '0')
  const c = parseFloat(curr || '0')
  const pr = parseFloat(price || '0')
  const consumption = (!isNaN(c) && !isNaN(p)) ? String(c - p) : ''
  const amount = (consumption && !isNaN(pr)) ? (parseFloat(consumption) * pr).toFixed(2) : ''
  return { consumption, amount }
}

function roundMoney(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100
}

// ---- Create form handlers (source: page.tsx:542-757) ----
async function loadContractsForTenant(tenantId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      tenant: tenantId, status: 'active,expired', include_charges: 1, limit: 100,
    })
    formContracts.value = res.contracts || []
  } catch { formContracts.value = [] }
}

async function loadContractCharges(contractId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_contract_due_types', { name: contractId })
    contractCharges.value = res.charges || []
  } catch { contractCharges.value = [] }
}

async function loadPreviousReading(contractId, dueTypeId) {
  try {
    const res = await callApi('rental.rental.api.contract.get_previous_reading', { name: contractId, due_type: dueTypeId })
    return res.previous_meter_reading || '0'
  } catch { return '0' }
}

async function handleFormTenantSelect(item) {
  if (item) {
    selectedFormTenantName.value = item.full_name || item.name
    newDue.value = { ...newDue.value, tenantId: item.name, contract: '', due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }
  } else {
    selectedFormTenantName.value = ''
    newDue.value = { ...newDue.value, tenantId: '', contract: '', due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }
  }
  contractCharges.value = []
  formContracts.value = []
  if (item?.name) await loadContractsForTenant(item.name)
}

async function handleContractChange(contractId) {
  if (!contractId) {
    newDue.value = { ...newDue.value, contract: '', due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }
    contractCharges.value = []
    return
  }
  const contract = formContracts.value.find((c) => c.name === contractId)
  if (!contract) return
  newDue.value = { ...newDue.value, contract: contractId, due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }
  await loadContractCharges(contractId)
}

async function handleDueTypeChange(dueTypeId) {
  const charge = isContractualMode.value ? contractCharges.value.find((c) => c.due_type_id === dueTypeId) : null
  const updates = { due_type: dueTypeId, previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '' }
  if (isContractualMode.value && charge?.calculation_method === 'metered' && newDue.value.contract) {
    const prev = await loadPreviousReading(newDue.value.contract, dueTypeId)
    updates.previous_meter_reading = prev
  }
  newDue.value = { ...newDue.value, ...updates }
}

function handleKindChange(mode) {
  formMode.value = mode
  newDue.value = { ...newDue.value, due_type: '', previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '', amount: '', description: '' }
  if (newDue.value.contract) {
    loadContractCharges(newDue.value.contract)
  }
}

function handleMeterInput(currentMeterReading, unitPrice) {
  const { consumption, amount } = calculateMeterFields(newDue.value.previous_meter_reading, currentMeterReading, unitPrice)
  newDue.value = { ...newDue.value, current_meter_reading, unit_price, meter_consumption: consumption, amount }
}

function openCreateModal() {
  newDue.value = {
    tenantId: '', contract: '', due_type: '',
    amount: '', due_date: new Date().toISOString().split('T')[0],
    description: '', due_kind: 'contractual',
    previous_meter_reading: '', current_meter_reading: '', meter_consumption: '', unit_price: '',
  }
  selectedFormTenantName.value = ''
  formContracts.value = []
  contractCharges.value = []
  formMode.value = 'contractual'
  createError.value = ''
}

// Temporal status: maps docstatus + due_date to upcoming/pending/draft/cancelled (source: page.tsx:94-100)
function temporalStatus(d) {
  if (d.status === 'draft') return 'draft'
  if (d.status === 'cancelled') return 'cancelled'
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const dueDate = new Date(d.due_date)
  dueDate.setHours(0, 0, 0, 0)
  if (dueDate > today) return 'upcoming'
  return 'pending'
}

// Source: page.tsx:94-100 — explicit labels for temporal status (مستقبلي/مستحق)
const temporalLabel = {
  draft: 'مسودة',
  cancelled: 'ملغي',
  upcoming: 'مستقبلي',
  pending: 'مستحق',
}

function startEdit(d) {
  editingDue.value = d
  editForm.value = {
    amount: d.amount,
    due_date: d.due_date || '',
    description: d.description || '',
    current_meter_reading: d.current_meter_reading ?? null,
    unit_price: d.unit_price ?? null,
  }
}

async function saveEdit() {
  savingEdit.value = true
  try {
    const payload = {}
    if (editForm.value.amount !== null) payload.amount = editForm.value.amount
    if (editForm.value.due_date) payload.due_date = editForm.value.due_date
    if (editForm.value.description !== undefined) payload.description = editForm.value.description
    if (editingDue.value.calculation_method === 'metered') {
      if (editForm.value.current_meter_reading !== null) payload.current_meter_reading = editForm.value.current_meter_reading
      if (editForm.value.unit_price !== null) payload.unit_price = editForm.value.unit_price
    }
    await callApi('rental.rental.api.due.update_due', { name: editingDue.value.name, ...payload })
    toast.success('تم تحديث الالتزام')
    editingDue.value = null
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) } finally { savingEdit.value = false }
}

let debounceTimer = null
function debouncedFetch() { clearTimeout(debounceTimer); debounceTimer = setTimeout(() => fetchDues(), 400) }

async function fetchDues(page = 1) {
  loading.value = true
  try {
    const res = await callApi('rental.rental.api.due.get_dues', {
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      source_type: filters.value.sourceType || undefined,
      from_date: filters.value.fromDate || undefined,
      to_date: filters.value.toDate || undefined,
      tenant: filters.value.tenantId || undefined,
      contract: filters.value.contractId || undefined,
      due_type: filters.value.dueTypeId || undefined,
      page, limit: 15,
    })
    dues.value = res.dues || []
    pagination.value = res.pagination
    stats.value = res.stats
  } catch (e) { toast.error(extractError(e)) } finally { loading.value = false }
}

// Load filter contracts for tenant (source: page.tsx:516-524)
async function loadFilterContractsForTenant(tenantId) {
  filterContractsLoading.value = true
  filterContracts.value = []
  try {
    const res = await callApi('rental.rental.api.contract.get_contracts', {
      tenant: tenantId,
      status: 'active,expired,cancelled,evicted',
      limit: 100,
    })
    filterContracts.value = res.contracts || []
  } catch { /* ignore */ } finally { filterContractsLoading.value = false }
}

// Handle tenant select in filters (source: page.tsx:564-571)
function handleFilterTenantSelect(item) {
  if (item) {
    selectedFilterTenantName.value = item.full_name || item.name
    filters.value.tenantId = item.name
    filters.value.contractId = ''
    filterContracts.value = []
    loadFilterContractsForTenant(item.name)
  } else {
    selectedFilterTenantName.value = ''
    filters.value.tenantId = ''
    filters.value.contractId = ''
    filterContracts.value = []
  }
  fetchDues()
}

function clearContractFilter() {
  filters.value.contractId = ''
  fetchDues()
}

function clearDatePeriod() {
  filters.value.fromDate = ''
  filters.value.toDate = ''
  fetchDues()
}

function clearAllFilters() {
  filters.value = {
    search: '',
    status: '',
    sourceType: '',
    fromDate: '',
    toDate: '',
    tenantId: '',
    contractId: '',
    dueTypeId: '',
  }
  selectedFilterTenantName.value = ''
  filterContracts.value = []
  fetchDues()
}

async function loadFormData() {
  try {
    // Source: dues/page.tsx:508 — old program calls fetch('/api/settings/due-types?includeSystem=true&includeInactive=true')
    const dtRes = await callApi('rental.rental.api.settings.get_due_types', { include_system: 1, include_inactive: 1 })
    dueTypes.value = (dtRes.dueTypes || []).filter(dt => !dt.is_system || dt.due_type_code !== 'rent')
  } catch { /* ignore */ }
}

async function createDue() {
  createError.value = ''
  // Validation (source: page.tsx:690-732)
  if (!newDue.value.tenantId) { createError.value = 'المستأجر مطلوب'; return }
  if (!newDue.value.contract) { createError.value = 'العقد مطلوب'; return }
  if (!newDue.value.due_type) { createError.value = 'نوع الالتزام مطلوب'; return }

  const payload = {
    contract: newDue.value.contract,
    due_type: newDue.value.due_type,
    due_date: newDue.value.due_date,
    description: newDue.value.description,
    due_kind: formMode.value,
  }

  if (isContractualMode.value) {
    if (!selectedCharge.value) { createError.value = 'نوع الالتزام غير موجود في العقد'; return }
    if (selectedCharge.value.disabled_reason) { createError.value = 'لا يمكن إنشاء هذا النوع يدويًا'; return }

    if (selectedCharge.value.calculation_method === 'metered') {
      if (!newDue.value.current_meter_reading || String(newDue.value.current_meter_reading).trim() === '') { createError.value = 'القراءة الحالية مطلوبة'; return }
      if (!newDue.value.unit_price || String(newDue.value.unit_price).trim() === '') { createError.value = 'سعر الوحدة مطلوب'; return }
      const prev = parseFloat(newDue.value.previous_meter_reading || '0')
      const curr = parseFloat(newDue.value.current_meter_reading)
      if (isNaN(curr) || curr < prev) { createError.value = 'القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة'; return }
      payload.current_meter_reading = newDue.value.current_meter_reading
      payload.previous_meter_reading = newDue.value.previous_meter_reading
      payload.unit_price = newDue.value.unit_price
    } else if (selectedCharge.value.calculation_method === 'actual_bill' || selectedCharge.value.calculation_method === 'on_demand') {
      if (!newDue.value.amount || String(newDue.value.amount).trim() === '') { createError.value = 'المبلغ مطلوب'; return }
      const amount = parseFloat(newDue.value.amount)
      if (isNaN(amount) || amount <= 0) { createError.value = 'المبلغ يجب أن يكون أكبر من صفر'; return }
      payload.amount = newDue.value.amount
    } else {
      createError.value = 'طريقة الاحتساب غير صالحة للإنشاء اليدوي'; return
    }
  } else {
    if (!newDue.value.description || String(newDue.value.description).trim() === '') { createError.value = 'يرجى إدخال سبب الالتزام الإضافي'; return }
    if (!newDue.value.amount || String(newDue.value.amount).trim() === '') { createError.value = 'المبلغ مطلوب'; return }
    const amount = parseFloat(newDue.value.amount)
    if (isNaN(amount) || amount <= 0) { createError.value = 'المبلغ يجب أن يكون أكبر من صفر'; return }
    payload.amount = newDue.value.amount
  }

  creating.value = true
  try {
    await callApi('rental.rental.api.due.create_due', payload)
    toast.success('تم إنشاء الالتزام')
    showCreateForm.value = false
    openCreateModal()
    fetchDues(pagination.value?.page || 1)
  } catch (e) {
    createError.value = extractError(e)
  } finally { creating.value = false }
}

async function approveDue(d) {
  const ok = await confirm({ title: 'اعتماد التزام', message: `اعتماد الالتزام "${d.due_number}"؟`, variant: 'warning', confirmLabel: 'اعتماد' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.approve_due', { name: d.name })
    toast.success('تم الاعتماد')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

async function cancelDue(d) {
  const reason = prompt('سبب الإلغاء:')
  if (!reason) return
  try {
    await callApi('rental.rental.api.due.cancel_due_api', { name: d.name, reason })
    toast.success('تم الإلغاء')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

async function deleteDue(d) {
  const ok = await confirm({ title: 'حذف التزام', message: `حذف الالتزام "${d.due_number}"؟`, variant: 'danger', confirmLabel: 'حذف' })
  if (!ok) return
  try {
    await callApi('rental.rental.api.due.delete_due', { name: d.name })
    toast.success('تم الحذف')
    fetchDues(pagination.value?.page || 1)
  } catch (e) { toast.error(extractError(e)) }
}

function onPageChange(page) { fetchDues(page) }

async function handlePrint() {
  printing.value = true
  try {
    const res = await callApi('rental.rental.api.due.get_dues', {
      search: filters.value.search || undefined,
      status: filters.value.status || undefined,
      source_type: filters.value.sourceType || undefined,
      from_date: filters.value.fromDate || undefined,
      to_date: filters.value.toDate || undefined,
      tenant: filters.value.tenantId || undefined,
      contract: filters.value.contractId || undefined,
      due_type: filters.value.dueTypeId || undefined,
      print: 1, limit: 1000,
    })
    const printDues = res.dues || []
    const printTotal = res.print?.totalAmount || null
    const printWin = window.open('', '_blank')
    printWin.document.write(`<html dir="rtl"><head><title>قائمة الالتزامات</title></head><body>`)
    printWin.document.write(`<h1>قائمة الالتزامات</h1>`)
    printWin.document.write(`<table border="1" style="width:100%;border-collapse:collapse;font-size:12px">`)
    printWin.document.write(`<tr><th>رقم</th><th>المستأجر</th><th>النوع</th><th>التاريخ</th><th>المبلغ</th><th>الحالة</th></tr>`)
    for (const d of printDues) {
      printWin.document.write(`<tr><td>${d.due_number}</td><td>${d.tenant_name||'—'}</td><td>${d.due_type_name||'—'}</td><td>${d.transaction_date||'—'}</td><td>${d.amount||0}</td><td>${d.status}</td></tr>`)
    }
    printWin.document.write(`</table>`)
    if (printTotal) printWin.document.write(`<p style="text-align:right;font-weight:bold;margin-top:12px">الإجمالي: ${printTotal}</p>`)
    printWin.document.write(`</body></html>`)
    printWin.document.close()
    printWin.print()
  } catch (e) { toast.error(extractError(e)) } finally { printing.value = false }
}

onMounted(() => { fetchDues(); loadFormData() })
</script>
