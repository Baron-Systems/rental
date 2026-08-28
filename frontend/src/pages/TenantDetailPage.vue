<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="text-navy-400">جاري تحميل بيانات المستأجر...</div>
      </div>

      <div v-else-if="!tenant" class="text-center py-20">
        <p class="text-navy-400 text-lg">المستأجر غير موجود</p>
        <p class="text-navy-300 text-sm mt-1">تعذر العثور على بيانات المستأجر المطلوب.</p>
      </div>

      <div v-else class="animate-fade-in space-y-6">
        <!-- Hero / Profile -->
        <div class="flex flex-col sm:flex-row sm:items-start gap-4">
          <button class="text-navy-500 hover:text-navy-800 inline-flex items-center gap-1 text-sm" @click="router.push({ name: 'Tenants' })">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            المستأجرين
          </button>
          <div class="w-16 h-16 rounded-full bg-ivory-200 flex items-center justify-center text-navy-400 shrink-0">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
          </div>
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold text-navy-900">{{ tenant.full_name }}</h1>
            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-navy-500">
              <span v-if="tenant.national_id">رقم الهوية: {{ tenant.national_id }}</span>
              <span v-if="tenant.phone" dir="ltr">{{ tenant.phone }}</span>
              <span v-if="tenant.workplace">{{ tenant.workplace }}</span>
              <span v-if="tenant.guarantor_name">الكفيل: {{ tenant.guarantor_name }}<span v-if="tenant.guarantor_phone"> ({{ tenant.guarantor_phone }})</span></span>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <router-link :to="{ name: 'TenantEdit', params: { id: tenant.name } }" class="btn-premium btn-outline">تعديل</router-link>
            <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="printing" @click="handlePrint">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              <span>{{ printing ? 'جاري التجهيز...' : 'طباعة' }}</span>
            </button>
          </div>
        </div>

        <!-- Financial Stats (3 StatCards) -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard label="إجمالي المستحقات" :value="formatMoney(tenant.balance?.totalDues, currency)" icon="receipt" color="navy" />
          <StatCard label="إجمالي الدفعات" :value="formatMoney(tenant.balance?.totalReceipts, currency)" icon="banknote" color="green" />
          <StatCard label="الرصيد" :value="formatMoney(tenant.balance?.balance, currency)" icon="wallet" :color="balanceColor" />
        </div>

        <!-- Statement Section -->
        <Card padding="none">
          <template #title>
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-5 py-4 border-b border-ivory-300/60">
              <div>
                <h2 class="font-bold text-navy-800">كشف الحساب</h2>
                <span class="text-xs text-navy-400">{{ statement?.lines?.length || 0 }} حركة</span>
              </div>
              <div class="flex items-center gap-2">
                <label class="text-xs text-navy-400">العقد</label>
                <select v-model="statementFilter.contractId" class="input-premium text-sm" :disabled="!tenant.contracts?.length" @change="handleContractFilterChange">
                  <option value="">كل العقود</option>
                  <option v-for="c in tenant.contracts" :key="c.name" :value="c.name">{{ contractLabel(c) }}</option>
                </select>
              </div>
            </div>
          </template>

          <div v-if="statementLoading" class="text-center py-12 text-navy-400 text-sm">جاري تحميل كشف الحساب...</div>
          <div v-else-if="!statement?.lines?.length" class="text-center py-12">
            <p class="text-navy-400 font-medium">لا توجد حركات</p>
            <p class="text-navy-300 text-sm mt-1">لا توجد حركات في كشف الحساب.</p>
          </div>
          <DataTable v-else :columns="statementColumns">
            <TableRow v-for="(line, i) in statement.lines" :key="i">
              <TableCell>{{ line.reference || '—' }}</TableCell>
              <TableCell>{{ formatDate(line.date) }}</TableCell>
              <TableCell>{{ line.typeName || line.type }}</TableCell>
              <TableCell v-if="!statementFilter.contractId">{{ line.unit || '—' }}</TableCell>
              <TableCell><span v-if="line.debit > 0" class="text-red-600 font-medium tabular-nums">{{ formatMoney(line.debit, currency) }}</span><span v-else class="text-navy-300">-</span></TableCell>
              <TableCell><span v-if="line.credit > 0" class="text-emerald-600 font-medium tabular-nums">{{ formatMoney(line.credit, currency) }}</span><span v-else class="text-navy-300">-</span></TableCell>
              <TableCell><span class="font-bold tabular-nums">{{ formatMoney(line.balance, currency) }}</span></TableCell>
            </TableRow>
          </DataTable>

          <!-- Statement pagination -->
          <div v-if="statement?.pagination && statement.pagination.totalPages > 1" class="flex items-center justify-center gap-3 px-4 py-3 border-t border-ivory-300/60 text-sm">
            <button class="btn-premium btn-ghost px-2 py-1" :disabled="statement.pagination.page <= 1" @click="fetchStatement(statement.pagination.page - 1)">السابق</button>
            <span class="text-navy-500">صفحة {{ statement.pagination.page }} من {{ statement.pagination.totalPages }}</span>
            <button class="btn-premium btn-ghost px-2 py-1" :disabled="statement.pagination.page >= statement.pagination.totalPages" @click="fetchStatement(statement.pagination.page + 1)">التالي</button>
          </div>
        </Card>

        <!-- Contracts Section -->
        <Card padding="none">
          <template #title>
            <div class="flex items-center justify-between px-5 py-4 border-b border-ivory-300/60">
              <h2 class="font-bold text-navy-800">العقود</h2>
              <span class="text-xs text-navy-400">{{ tenant.contracts?.length || 0 }} عقد</span>
            </div>
          </template>
          <div v-if="!tenant.contracts?.length" class="text-center py-12">
            <p class="text-navy-400 font-medium">لا توجد عقود</p>
            <p class="text-navy-300 text-sm mt-1">لا توجد عقود مسجلة لهذا المستأجر.</p>
          </div>
          <DataTable v-else :columns="contractColumns">
            <TableRow v-for="c in tenant.contracts" :key="c.name">
              <TableCell>
                <router-link :to="`/contracts/${c.name}`" class="font-semibold text-navy-800 hover:text-gold-600">{{ c.contract_number }}</router-link>
              </TableCell>
              <TableCell>
                <div class="flex flex-col text-sm">
                  <span class="inline-flex items-center gap-1 text-navy-700">
                    <svg class="w-3 h-3 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
                    {{ c.building_name || '—' }}
                  </span>
                  <span class="inline-flex items-center gap-1 text-navy-400 text-xs">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg>
                    {{ c.unit_number || '—' }}
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <span class="inline-flex items-center gap-1 text-sm text-navy-600">
                  <svg class="w-3 h-3 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                  {{ formatDate(c.start_date) }} - {{ formatDate(c.end_date) }}
                </span>
              </TableCell>
              <TableCell><StatusBadge :status="c.status" /></TableCell>
              <TableCell><span class="font-bold tabular-nums" :class="balanceNumberClass(c.balance)">{{ formatMoney(c.balance, currency) }}</span></TableCell>
              <TableCell>
                <router-link :to="`/contracts/${c.name}/preview`" target="_blank" class="text-navy-500 hover:text-gold-600" title="معاينة">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                </router-link>
              </TableCell>
            </TableRow>
          </DataTable>
        </Card>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { callApi, formatMoney, formatDate, extractError } from '@/composables/useApi'
import { useSession } from '@/composables/useSession'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const route = useRoute()
const session = useSession()
const toast = useToast()
const currency = computed(() => session.state.account?.settings?.currency || 'ILS')
const lessorLogo = computed(() => session.state.account?.settings?.logo || '')
const lessorName = computed(() => session.state.account?.settings?.landlord_name || '')

const tenant = ref(null)
const statement = ref(null)
const loading = ref(true)
const statementLoading = ref(false)
const printing = ref(false)

const statementFilter = ref({ contractId: '' })

const statementColumns = computed(() => {
  const cols = [
    { key: 'ref', label: 'المرجع' },
    { key: 'date', label: 'التاريخ' },
    { key: 'type', label: 'النوع' },
  ]
  if (!statementFilter.value.contractId) {
    cols.push({ key: 'unit', label: 'الوحدة' })
  }
  cols.push({ key: 'debit', label: 'المبلغ المستحق' })
  cols.push({ key: 'credit', label: 'المبلغ المدفوع' })
  cols.push({ key: 'balance', label: 'الرصيد' })
  return cols
})

const contractColumns = [
  { key: 'number', label: 'رقم العقد' },
  { key: 'builing', label: 'العقار / الوحدة' },
  { key: 'period', label: 'الفترة' },
  { key: 'status', label: 'الحالة' },
  { key: 'balance', label: 'الرصيد' },
  { key: 'preview', label: '' },
]

const balanceColor = computed(() => {
  const bal = tenant.value?.balance?.balance ?? 0
  if (bal > 0) return 'red'
  if (bal < 0) return 'green'
  return 'muted'
})

function balanceNumberClass(bal) {
  if (bal > 0) return 'text-red-600'
  if (bal < 0) return 'text-emerald-600'
  return 'text-navy-500'
}

function contractLabel(c) {
  const parts = [c.contract_number]
  if (c.building_name) parts.push(c.building_name)
  if (c.unit_number) parts.push(c.unit_number)
  return parts.join(' — ')
}

async function fetchTenant() {
  loading.value = true
  try {
    tenant.value = await callApi('rental.rental.api.tenant.get_tenant', { name: route.params.id })
    // Initial statement (first page, all contracts)
    statement.value = tenant.value.statement
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    loading.value = false
  }
}

async function fetchStatement(page = 1) {
  statementLoading.value = true
  try {
    statement.value = await callApi('rental.rental.api.tenant.get_tenant_statement_api', {
      name: route.params.id,
      contract: statementFilter.value.contractId || undefined,
      page,
    })
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    statementLoading.value = false
  }
}

function handleContractFilterChange() {
  fetchStatement(1)
}

async function handlePrint() {
  if (printing.value) return
  printing.value = true
  try {
    const data = await callApi('rental.rental.api.tenant.get_tenant_statement_api', {
      name: route.params.id,
      contract: statementFilter.value.contractId || undefined,
      print: 1,
    })
    _openPrintWindow(data, tenant.value, !!statementFilter.value.contractId)
  } catch (e) {
    toast.error(extractError(e) || 'حدث خطأ أثناء تجهيز التقرير')
  } finally {
    printing.value = false
  }
}

function _openPrintWindow(data, tenantDoc, singleContract) {
  const w = window.open('', '_blank', 'width=900,height=700')
  if (!w) { toast.error('يرجى السماح بالنوافذ المنبثقة للطباعة'); return }
  const cur = currency.value
  const showUnitCol = !singleContract
  const selectedContract = singleContract ? tenantDoc.contracts?.find(c => c.name === statementFilter.value.contractId) : null

  const rows = (data.lines || []).map(l => `
    <tr>
      <td>${l.reference || '—'}</td>
      <td>${formatDate(l.date)}</td>
      <td>${l.typeName || l.type}</td>
      ${showUnitCol ? `<td>${l.unit || '—'}</td>` : ''}
      <td class="num ${l.debit > 0 ? 'red' : ''}">${l.debit > 0 ? formatMoney(l.debit, cur) : '-'}</td>
      <td class="num ${l.credit > 0 ? 'green' : ''}">${l.credit > 0 ? formatMoney(l.credit, cur) : '-'}</td>
      <td class="num bold">${formatMoney(l.balance, cur)}</td>
    </tr>`).join('')

  const contractHeader = selectedContract
    ? `<div class="space-y-1.5"><div><span class="label">العقار:</span> ${selectedContract.building_name || '—'}</div><div><span class="label">الوحدة:</span> ${selectedContract.unit_number || '—'}</div><div><span class="label">تاريخ إصدار التقرير:</span> ${formatDate(new Date().toISOString())}</div></div>`
    : `<div class="space-y-1.5"><div><span class="label">نطاق الكشف:</span> جميع العقود</div><div><span class="label">تاريخ إصدار التقرير:</span> ${formatDate(new Date().toISOString())}</div></div>`

  const tenantMeta = `<div class="space-y-1.5"><div><span class="label">اسم المستأجر:</span> <b>${tenantDoc.full_name}</b></div><div><span class="label">رقم الهوية:</span> ${tenantDoc.national_id || '-'}</div>${selectedContract ? `<div><span class="label">رقم العقد:</span> ${selectedContract.contract_number}</div>` : ''}</div>`

  const balanceColor = data.closingBalance > 0 ? 'red' : data.closingBalance < 0 ? 'green' : ''

  w.document.write(`<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8">
    <title>كشف حساب المستأجر</title><style>
      body{font-family:Arial,sans-serif;padding:24px;color:#1a2238}
      h1{font-size:20px;margin:0 0 4px;text-align:center} h2{font-size:14px;color:#64748b;font-weight:normal;margin:0 0 8px}
      .meta{font-size:13px;color:#475569;margin-bottom:16px;display:flex;justify-content:space-between;gap:16px}
      .meta .label{color:#64748b;font-weight:bold}
      .meta > div{flex:1}
      table{width:100%;border-collapse:collapse;font-size:12px}
      th,td{border:1px solid #e2e8f0;padding:6px 8px;text-align:right}
      th{background:#f1f5f9} .num{text-align:left} .bold{font-weight:bold}
      .red{color:#dc2626} .green{color:#059669}
      .empty-title{font-weight:bold;margin-bottom:4px}
      .empty-desc{font-size:12px}
      .totals{margin-top:16px;border-top:2px solid #1a2238;padding-top:12px}
      .totals-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;font-size:13px}
      .totals-grid > div{text-align:center}
      .totals-grid .label{color:#1a2238;font-weight:bold;display:block;margin-bottom:4px}
      .totals-grid .value{font-size:16px;font-weight:bold}
      .print-header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:8px;margin-bottom:12px}
      .print-header .logo{height:65px;width:auto;object-fit:contain}
      .print-header .name{font-size:17px;font-weight:bold;color:#1a2238}
      .report-title{font-size:22px;font-weight:bold;text-align:center;margin:8px 0 12px;border-bottom:2px solid #1a2238;padding-bottom:8px}
    </style></head><body>
    <div class="print-header">
      <div>${lessorLogo.value ? `<img src="${lessorLogo.value}" alt="شعار المؤجر" class="logo" />` : ''}</div>
      <div>${lessorName.value ? `<span class="name">${lessorName.value}</span>` : ''}</div>
    </div>
    <h1 class="report-title">كشف حساب المستأجر</h1>
    <div class="meta">
      ${tenantMeta}
      ${contractHeader}
    </div>
    <table><thead><tr><th>المرجع</th><th>التاريخ</th><th>النوع</th>${showUnitCol ? '<th>الوحدة</th>' : ''}<th class="num">المستحق</th><th class="num">المدفوع</th><th class="num">الرصيد</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="' + (showUnitCol ? 7 : 6) + '" style="text-align:center;color:#94a3b8;padding:16px"><div class="empty-title">لا توجد حركات</div><div class="empty-desc">لا توجد حركات في كشف الحساب.</div></td></tr>'}</tbody></table>
    <div class="totals">
      <div class="totals-grid">
        <div><span class="label">إجمالي المستحقات</span><span class="value red">${formatMoney(data.totalDues, cur)}</span></div>
        <div><span class="label">إجمالي المدفوعات</span><span class="value green">${formatMoney(data.totalReceipts, cur)}</span></div>
        <div><span class="label">الرصيد الحالي</span><span class="value ${balanceColor}">${formatMoney(data.closingBalance, cur)}</span></div>
      </div>
    </div>
    <script>window.onload=function(){window.print()}<\/script>
    </body></html>`)
  w.document.close()
}

onMounted(fetchTenant)
</script>
