<template>
  <AppLayout>
    <div class="p-6 lg:p-8" dir="rtl">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="text-navy-400">جاري تحميل كشف الحساب...</div>
      </div>

      <div v-else-if="tenant" class="space-y-6">
        <PageHeader :title="`كشف حساب: ${tenant.full_name}`" :back-href="`/tenants/${tenant.name}`">
          <template #actions>
            <button class="btn-premium btn-outline inline-flex items-center gap-1.5" :disabled="printing" @click="handlePrint">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              <span>{{ printing ? 'جاري التجهيز...' : 'طباعة' }}</span>
            </button>
          </template>
        </PageHeader>

        <!-- Contract filter -->
        <Card padding="md">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <label class="text-sm font-medium text-navy-700">تصفية حسب العقد</label>
            <select v-model="filters.contractId" class="input-premium sm:max-w-sm" :disabled="!tenant.contracts?.length || (tenant.contracts?.length || 0) <= 1" @change="handleContractFilterChange">
              <option value="">كل العقود</option>
              <option v-for="c in tenant.contracts" :key="c.name" :value="c.name">{{ contractLabel(c) }}</option>
            </select>
          </div>
        </Card>

        <!-- Summary stat cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="الرصيد الافتتاحي" :value="formatMoney(statement?.openingBalance, currency)" icon="wallet" color="muted" />
          <StatCard label="إجمالي الالتزامات" :value="formatMoney(statement?.totalDues, currency)" icon="receipt" color="red" />
          <StatCard label="إجمالي الدفعات" :value="formatMoney(statement?.totalReceipts, currency)" icon="banknote" color="green" />
          <StatCard label="الرصيد الختامي" :value="formatMoney(statement?.closingBalance, currency)" icon="wallet" :color="closingColor" />
        </div>

        <!-- Statement table -->
        <Card padding="none">
          <div v-if="statementLoading" class="text-center py-12 text-navy-400 text-sm">جاري تحميل كشف الحساب...</div>
          <div v-else-if="!statement?.lines?.length" class="text-center py-12">
            <p class="text-navy-400 font-medium">لا توجد حركات</p>
            <p class="text-navy-300 text-sm mt-1">لا توجد حركات في كشف الحساب.</p>
          </div>
          <DataTable v-else :columns="columns">
            <TableRow v-for="(line, i) in statement.lines" :key="i">
              <TableCell>{{ line.reference || '—' }}</TableCell>
              <TableCell>{{ formatDate(line.date) }}</TableCell>
              <TableCell>{{ line.typeName || line.type }}</TableCell>
              <TableCell v-if="!filters.contractId">{{ line.unit || '—' }}</TableCell>
              <TableCell><span v-if="line.debit > 0" class="text-red-600 font-medium tabular-nums">{{ formatMoney(line.debit, currency) }}</span><span v-else class="text-navy-300">-</span></TableCell>
              <TableCell><span v-if="line.credit > 0" class="text-emerald-600 font-medium tabular-nums">{{ formatMoney(line.credit, currency) }}</span><span v-else class="text-navy-300">-</span></TableCell>
              <TableCell><span class="font-bold tabular-nums">{{ formatMoney(line.balance, currency) }}</span></TableCell>
            </TableRow>
          </DataTable>

          <!-- Pagination -->
          <div v-if="statement?.pagination" class="border-t border-ivory-300/60 px-4 py-3 text-xs text-navy-400 flex items-center justify-between">
            <span>إجمالي: {{ statement.pagination.total }} حركة</span>
          </div>
          <Pagination v-if="statement?.pagination" :page="statement.pagination.page" :page-size="statement.pagination.pageSize" :total="statement.pagination.total" @change="onPageChange" />
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
import StatCard from '@/components/ui/StatCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import TableRow from '@/components/ui/TableRow.vue'
import TableCell from '@/components/ui/TableCell.vue'
import Pagination from '@/components/ui/Pagination.vue'
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

const filters = ref({ contractId: '' })

const columns = computed(() => {
  const cols = [
    { key: 'ref', label: 'المرجع' },
    { key: 'date', label: 'التاريخ' },
    { key: 'type', label: 'النوع' },
  ]
  if (!filters.value.contractId) {
    cols.push({ key: 'unit', label: 'الوحدة' })
  }
  cols.push({ key: 'debit', label: 'المستحق' })
  cols.push({ key: 'credit', label: 'المدفوع' })
  cols.push({ key: 'balance', label: 'الرصيد' })
  return cols
})

const closingColor = computed(() => {
  const bal = statement.value?.closingBalance ?? 0
  if (bal > 0) return 'red'
  if (bal < 0) return 'green'
  return 'muted'
})

function contractLabel(c) {
  const parts = [c.contract_number]
  if (c.building_name) parts.push(c.building_name)
  if (c.unit_number) parts.push(c.unit_number)
  return parts.join(' — ')
}

async function loadTenant() {
  try {
    tenant.value = await callApi('rental.rental.api.tenant.get_tenant', { name: route.params.id })
    return true
  } catch (e) {
    toast.error(extractError(e))
    return false
  }
}

async function fetchStatement(page = 1) {
  statementLoading.value = true
  try {
    statement.value = await callApi('rental.rental.api.tenant.get_tenant_statement_api', {
      name: route.params.id,
      contract: filters.value.contractId || undefined,
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

function onPageChange(page) {
  fetchStatement(page)
}

async function handlePrint() {
  if (printing.value) return
  printing.value = true
  try {
    const data = await callApi('rental.rental.api.tenant.get_tenant_statement_api', {
      name: route.params.id,
      contract: filters.value.contractId || undefined,
      print: 1,
    })
    _openPrintWindow(data, tenant.value, !!filters.value.contractId)
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
  const selectedContract = singleContract ? tenantDoc.contracts?.find(c => c.name === filters.value.contractId) : null

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

onMounted(async () => {
  loading.value = true
  const ok = await loadTenant()
  if (ok) await fetchStatement(1)
  loading.value = false
})
</script>
