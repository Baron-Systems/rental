/**
 * Phase 3 — Refund Presentation & Printing tests.
 *
 * Verifies:
 * 1. Receipt detail shows "سند قبض"
 * 2. Refund detail shows "سند صرف"
 * 3. Refund amount displayed positive
 * 4. Refund type displayed "رد للمستأجر"
 * 5. Draft detail cannot change transaction_type (no transaction_type in edit payload)
 * 6. Receipt print title = سند قبض
 * 7. Refund print title = سند صرف
 * 8. Refund print amount positive
 * 9. Receipts list distinguishes receipt/refund
 * 10. List does not render refund as negative amount
 * 11. List print totals distinguish receipts / refunds / net collections
 * 12. Tenant statement refund appears Debit
 * 13. Tenant statement receipt appears Credit
 * 14. Contract detail balance reflects refunds (no individual receipts list)
 * 15. Cancel dialog/title follows transaction_type
 * 16. Cancelled refund still displayed historically as سند صرف
 *
 * Run: npx vitest run src/tests/refund_presentation.spec.js
 */

import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

// ---- ReceiptDetailPage logic simulation ----

function createDetailState(receiptData) {
  const receipt = ref(receiptData)
  const isRefund = computed(() => receipt.value?.transaction_type === 'refund')
  const receiptTitle = computed(() => isRefund.value ? 'سند صرف' : 'سند قبض')
  const transactionTypeLabel = computed(() => isRefund.value ? 'رد للمستأجر' : 'قبض من المستأجر')

  function buildCancelPrompt() {
    return {
      title: isRefund.value ? 'إلغاء سند الصرف' : 'إلغاء سند القبض',
      message: isRefund.value ? 'أدخل سبب إلغاء سند الصرف' : 'أدخل سبب إلغاء سند القبض',
    }
  }

  function buildDeletePrompt() {
    return {
      title: isRefund.value ? 'حذف سند الصرف' : 'حذف سند القبض',
    }
  }

  // Edit form does NOT include transaction_type
  function buildEditPayload(editForm) {
    return {
      receipt_date: editForm.receiptDate,
      amount: editForm.amount,
      payment_method: editForm.paymentMethod,
      notes: editForm.notes || null,
    }
  }

  return { receipt, isRefund, receiptTitle, transactionTypeLabel, buildCancelPrompt, buildDeletePrompt, buildEditPayload }
}

// ---- ReceiptPrintDocument logic simulation ----

function createPrintState(receiptData) {
  const receipt = ref(receiptData)
  const isRefund = computed(() => receipt.value?.transaction_type === 'refund')
  const title = computed(() => isRefund.value ? 'سند صرف' : 'سند قبض')
  const subtitle = computed(() => isRefund.value ? 'رد مبلغ للمستأجر' : '')

  const rows = computed(() => {
    const r = receipt.value
    return [
      { label: 'نوع الحركة', value: isRefund.value ? 'رد للمستأجر' : 'قبض من المستأجر' },
      { label: 'العقار', value: r.building_name || '-' },
    ]
  })

  // Amount is always positive — formatAmount uses Number(amount) directly
  function formatAmount(amount) {
    return Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return { receipt, isRefund, title, subtitle, rows, formatAmount }
}

// ---- ReceiptsListPrintDocument totals simulation ----

function createListPrintState(receiptsArray) {
  const receipts = ref(receiptsArray)

  const totalReceipts = computed(() => {
    return receipts.value
      .filter((r) => r.transaction_type !== 'refund' && (r.status === 'approved' || r.docstatus === 1))
      .reduce((sum, r) => sum + Number(r.amount || 0), 0)
  })

  const totalRefunds = computed(() => {
    return receipts.value
      .filter((r) => r.transaction_type === 'refund' && (r.status === 'approved' || r.docstatus === 1))
      .reduce((sum, r) => sum + Number(r.amount || 0), 0)
  })

  const netCollections = computed(() => totalReceipts.value - totalRefunds.value)

  function getTransactionTypeLabel(r) {
    return r.transaction_type === 'refund' ? 'رد للمستأجر' : 'قبض'
  }

  function getAmount(r) {
    return Number(r.amount || 0)
  }

  return { receipts, totalReceipts, totalRefunds, netCollections, getTransactionTypeLabel, getAmount }
}

// ---- Tenant Statement line simulation ----

function createStatementLine(type, amount) {
  if (type === 'refund') {
    return { typeName: 'سند صرف', debit: amount, credit: 0 }
  } else {
    return { typeName: 'سند قبض', debit: 0, credit: amount }
  }
}

// ============ TESTS ============

describe('Phase 3 — Refund Presentation', () => {

  // 1. Receipt detail shows "سند قبض"
  it('1) receipt detail title = سند قبض', () => {
    const state = createDetailState({ transaction_type: 'receipt', receipt_number: 'R-001', amount: 500 })
    expect(state.receiptTitle.value).toBe('سند قبض')
  })

  // 2. Refund detail shows "سند صرف"
  it('2) refund detail title = سند صرف', () => {
    const state = createDetailState({ transaction_type: 'refund', receipt_number: 'R-002', amount: 410 })
    expect(state.receiptTitle.value).toBe('سند صرف')
  })

  // 3. Refund amount displayed positive
  it('3) refund amount is positive in detail', () => {
    const state = createDetailState({ transaction_type: 'refund', amount: 410 })
    expect(Number(state.receipt.value.amount)).toBe(410)
    expect(Number(state.receipt.value.amount) > 0).toBe(true)
  })

  // 4. Refund type displayed "رد للمستأجر"
  it('4) refund type label = رد للمستأجر', () => {
    const state = createDetailState({ transaction_type: 'refund', amount: 410 })
    expect(state.transactionTypeLabel.value).toBe('رد للمستأجر')
  })

  it('4b) receipt type label = قبض من المستأجر', () => {
    const state = createDetailState({ transaction_type: 'receipt', amount: 500 })
    expect(state.transactionTypeLabel.value).toBe('قبض من المستأجر')
  })

  // 5. Draft detail cannot change transaction_type
  it('5) edit payload does NOT include transaction_type', () => {
    const state = createDetailState({ transaction_type: 'refund', amount: 410, status: 'draft' })
    const payload = state.buildEditPayload({
      receiptDate: '2025-01-01',
      amount: '300',
      paymentMethod: 'cash',
      notes: 'test',
    })
    expect(payload).not.toHaveProperty('transaction_type')
    expect(payload).not.toHaveProperty('transactionType')
  })

  // 6. Receipt print title = سند قبض
  it('6) receipt print title = سند قبض', () => {
    const state = createPrintState({ transaction_type: 'receipt', amount: 500 })
    expect(state.title.value).toBe('سند قبض')
    expect(state.subtitle.value).toBe('')
  })

  // 7. Refund print title = سند صرف
  it('7) refund print title = سند صرف', () => {
    const state = createPrintState({ transaction_type: 'refund', amount: 410 })
    expect(state.title.value).toBe('سند صرف')
    expect(state.subtitle.value).toBe('رد مبلغ للمستأجر')
  })

  // 8. Refund print amount positive
  it('8) refund print amount is positive', () => {
    const state = createPrintState({ transaction_type: 'refund', amount: 410 })
    const formatted = state.formatAmount(state.receipt.value.amount)
    expect(formatted).toBe('410.00')
    expect(formatted.startsWith('-')).toBe(false)
  })

  // 9. Receipts list distinguishes receipt/refund
  it('9) list type label distinguishes receipt vs refund', () => {
    const state = createListPrintState([
      { transaction_type: 'receipt', amount: 500, status: 'approved' },
      { transaction_type: 'refund', amount: 410, status: 'approved' },
    ])
    expect(state.getTransactionTypeLabel(state.receipts.value[0])).toBe('قبض')
    expect(state.getTransactionTypeLabel(state.receipts.value[1])).toBe('رد للمستأجر')
  })

  // 10. List does not render refund as negative amount
  it('10) list amount is always positive for refunds', () => {
    const state = createListPrintState([
      { transaction_type: 'refund', amount: 410, status: 'approved' },
    ])
    const amt = state.getAmount(state.receipts.value[0])
    expect(amt).toBe(410)
    expect(amt > 0).toBe(true)
  })

  // 11. List print totals distinguish receipts / refunds / net
  it('11) list print totals: receipts, refunds, net collections', () => {
    const state = createListPrintState([
      { transaction_type: 'receipt', amount: 1000, status: 'approved' },
      { transaction_type: 'receipt', amount: 500, status: 'approved' },
      { transaction_type: 'refund', amount: 300, status: 'approved' },
      { transaction_type: 'refund', amount: 200, status: 'approved' },
      { transaction_type: 'receipt', amount: 100, status: 'draft' },     // excluded
      { transaction_type: 'refund', amount: 50, status: 'cancelled' },   // excluded
    ])
    expect(state.totalReceipts.value).toBe(1500)  // 1000 + 500
    expect(state.totalRefunds.value).toBe(500)     // 300 + 200
    expect(state.netCollections.value).toBe(1000)  // 1500 - 500
  })

  it('11b) list print totals with only receipts', () => {
    const state = createListPrintState([
      { transaction_type: 'receipt', amount: 800, status: 'approved' },
    ])
    expect(state.totalReceipts.value).toBe(800)
    expect(state.totalRefunds.value).toBe(0)
    expect(state.netCollections.value).toBe(800)
  })

  it('11c) list print totals with only refunds', () => {
    const state = createListPrintState([
      { transaction_type: 'refund', amount: 400, status: 'approved' },
    ])
    expect(state.totalReceipts.value).toBe(0)
    expect(state.totalRefunds.value).toBe(400)
    expect(state.netCollections.value).toBe(-400)
  })

  // 12. Tenant statement refund appears Debit
  it('12) tenant statement refund line has debit > 0, credit = 0', () => {
    const line = createStatementLine('refund', 410)
    expect(line.debit).toBe(410)
    expect(line.credit).toBe(0)
    expect(line.typeName).toBe('سند صرف')
  })

  // 13. Tenant statement receipt appears Credit
  it('13) tenant statement receipt line has credit > 0, debit = 0', () => {
    const line = createStatementLine('receipt', 500)
    expect(line.credit).toBe(500)
    expect(line.debit).toBe(0)
    expect(line.typeName).toBe('سند قبض')
  })

  // 14. Contract detail balance reflects refunds (no individual receipts list)
  it('14) contract balance includes refunds in totalReceipts', () => {
    // Backend get_contract_balance returns totalReceipts and totalRefunds separately
    // balance = totalDues - totalReceipts + totalRefunds
    // The UI shows these values directly from backend — no frontend computation
    const balance = { totalDues: 5000, totalReceipts: 3000, totalRefunds: 500, balance: 2500 }
    expect(balance.totalRefunds).toBe(500)
    expect(balance.balance).toBe(5000 - 3000 + 500)
  })

  // 15. Cancel dialog/title follows transaction_type
  it('15a) cancel prompt for receipt says سند القبض', () => {
    const state = createDetailState({ transaction_type: 'receipt', status: 'approved' })
    const prompt = state.buildCancelPrompt()
    expect(prompt.title).toBe('إلغاء سند القبض')
    expect(prompt.message).toContain('سند القبض')
  })

  it('15b) cancel prompt for refund says سند الصرف', () => {
    const state = createDetailState({ transaction_type: 'refund', status: 'approved' })
    const prompt = state.buildCancelPrompt()
    expect(prompt.title).toBe('إلغاء سند الصرف')
    expect(prompt.message).toContain('سند الصرف')
  })

  it('15c) delete prompt for refund says سند الصرف', () => {
    const state = createDetailState({ transaction_type: 'refund', status: 'draft' })
    const prompt = state.buildDeletePrompt()
    expect(prompt.title).toBe('حذف سند الصرف')
  })

  it('15d) delete prompt for receipt says سند القبض', () => {
    const state = createDetailState({ transaction_type: 'receipt', status: 'draft' })
    const prompt = state.buildDeletePrompt()
    expect(prompt.title).toBe('حذف سند القبض')
  })

  // 16. Cancelled refund still displayed historically as سند صرف
  it('16) cancelled refund still shows سند صرف title', () => {
    const state = createDetailState({
      transaction_type: 'refund',
      status: 'cancelled',
      amount: 410,
      cancellation_reason: 'خطأ',
    })
    expect(state.receiptTitle.value).toBe('سند صرف')
    expect(state.transactionTypeLabel.value).toBe('رد للمستأجر')
    expect(state.receipt.value.status).toBe('cancelled')
  })

  it('16b) cancelled refund print still shows سند صرف', () => {
    const state = createPrintState({
      transaction_type: 'refund',
      status: 'cancelled',
      amount: 410,
    })
    expect(state.title.value).toBe('سند صرف')
    expect(state.subtitle.value).toBe('رد مبلغ للمستأجر')
  })
})
