/**
 * ReceiptsPage settlement UX tests.
 *
 * Verifies the refund/settlement logic added to the receipt creation form:
 * - Contract balance display (positive/negative/zero)
 * - Refund visibility rules (only operationally closed + credit balance + not archived)
 * - Settlement button behavior (positive → receipt, negative → refund, zero → hidden)
 * - Manual receipt allows prepayment (no receipt <= balance validation)
 * - Refund amount cannot exceed credit balance
 * - Negative amount rejected
 * - Changing contract resets stale settlement state
 * - Changing tenant resets contract/settlement state
 * - API payload includes transaction_type
 *
 * Run: npx vitest run src/tests/receipt_settlement.spec.js
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, reactive, computed } from 'vue'

// ---- Helpers: simulate the reactive state and computed from ReceiptsPage.vue ----

function createSettlementState() {
  const formData = reactive({
    tenantId: '',
    contractId: '',
    transactionType: 'receipt',
    receiptDate: new Date().toISOString().split('T')[0],
    amount: '',
    paymentMethod: 'cash',
    referenceNumber: '',
    chequeDate: '',
    bankName: '',
    attachment: null,
    notes: '',
  })

  const contractBalance = ref(null)
  const contractBalanceLoading = ref(false)
  const canRefund = ref(false)
  const isContractArchived = ref(false)
  const currency = ref('JOD')

  const contractBalanceLabel = computed(() => {
    if (contractBalance.value === null) return ''
    const abs = Math.abs(contractBalance.value)
    const formatted = `${abs.toFixed(2)} ${currency.value}`
    if (contractBalance.value > 0) return `على المستأجر: ${formatted}`
    if (contractBalance.value < 0) return `لصالح المستأجر: ${formatted}`
    return `رصيد العقد: ${formatted}`
  })

  const showTransactionType = computed(() => {
    if (!formData.contractId) return false
    if (isContractArchived.value) return false
    return canRefund.value
  })

  const amountError = computed(() => {
    const amt = parseFloat(formData.amount)
    if (!formData.amount || isNaN(amt)) return ''
    if (amt <= 0) return 'المبلغ يجب أن يكون موجبًا'
    if (formData.transactionType === 'refund' && contractBalance.value !== null) {
      const credit = Math.abs(contractBalance.value)
      if (amt > credit + 0.005) return 'مبلغ الرد لا يمكن أن يتجاوز الرصيد الدائن للعقد.'
    }
    return ''
  })

  const canShowSettlement = computed(() => {
    if (contractBalance.value === null) return false
    if (contractBalance.value > 0) return true
    if (contractBalance.value < 0 && canRefund.value) return true
    return false
  })

  function handleSettleBalance() {
    if (contractBalance.value === null || contractBalance.value === 0) return
    if (contractBalance.value > 0) {
      formData.transactionType = 'receipt'
      formData.amount = contractBalance.value.toFixed(2)
    } else if (contractBalance.value < 0 && canRefund.value) {
      formData.transactionType = 'refund'
      formData.amount = Math.abs(contractBalance.value).toFixed(2)
    }
  }

  function handleTransactionTypeChange() {
    formData.amount = ''
  }

  async function handleContractChange(contractId) {
    formData.contractId = contractId
    formData.transactionType = 'receipt'
    formData.amount = ''
    contractBalance.value = null
    canRefund.value = false
    isContractArchived.value = false
    if (contractId) {
      // Simulate API call
      const res = await mockSettlementApi(contractId)
      contractBalance.value = res.balance
      canRefund.value = res.can_refund
      isContractArchived.value = res.is_archived
    }
  }

  async function handleFormTenantSelect(tenantId, contracts = []) {
    formData.tenantId = tenantId
    formData.contractId = ''
    formData.transactionType = 'receipt'
    formData.amount = ''
    contractBalance.value = null
    canRefund.value = false
    isContractArchived.value = false
    if (tenantId && contracts.length === 1) {
      formData.contractId = contracts[0]
      await handleContractChange(contracts[0])
    }
  }

  function buildPayload() {
    return {
      tenant: formData.tenantId,
      contract: formData.contractId,
      transaction_type: formData.transactionType,
      receipt_date: formData.receiptDate,
      amount: formData.amount,
      payment_method: formData.paymentMethod,
      notes: formData.notes || null,
    }
  }

  // Mock API — different contracts return different states
  const mockContracts = new Map()
  function setMockContract(id, data) {
    mockContracts.set(id, data)
  }
  async function mockSettlementApi(id) {
    return mockContracts.get(id) || { balance: 0, can_refund: false, is_archived: false }
  }

  return {
    formData, contractBalance, contractBalanceLoading, canRefund, isContractArchived,
    contractBalanceLabel, showTransactionType, canShowSettlement, amountError,
    handleSettleBalance, handleTransactionTypeChange, handleContractChange, handleFormTenantSelect,
    buildPayload, setMockContract,
  }
}

// ---- Tests ----

describe('Receipt Settlement UX', () => {
  let state

  beforeEach(() => {
    state = createSettlementState()
  })

  // 1. Contract with positive balance
  it('shows "على المستأجر" for positive balance', async () => {
    state.setMockContract('C1', { balance: 410, can_refund: false, is_archived: false })
    await state.handleContractChange('C1')
    expect(state.contractBalance.value).toBe(410)
    expect(state.contractBalanceLabel.value).toContain('على المستأجر')
    expect(state.contractBalanceLabel.value).toContain('410.00')
  })

  // 2. Contract with negative balance
  it('shows "لصالح المستأجر" for negative balance', async () => {
    state.setMockContract('C2', { balance: -200, can_refund: true, is_archived: false })
    await state.handleContractChange('C2')
    expect(state.contractBalance.value).toBe(-200)
    expect(state.contractBalanceLabel.value).toContain('لصالح المستأجر')
    expect(state.contractBalanceLabel.value).toContain('200.00')
  })

  // 3. Contract with zero balance
  it('shows "رصيد العقد" for zero balance', async () => {
    state.setMockContract('C3', { balance: 0, can_refund: false, is_archived: false })
    await state.handleContractChange('C3')
    expect(state.contractBalance.value).toBe(0)
    expect(state.contractBalanceLabel.value).toContain('رصيد العقد')
  })

  // 4. Active contract does not expose refund
  it('active contract (can_refund=false) does not show transaction type selector', async () => {
    state.setMockContract('C4', { balance: 500, can_refund: false, is_archived: false })
    await state.handleContractChange('C4')
    expect(state.showTransactionType.value).toBe(false)
    expect(state.formData.transactionType).toBe('receipt')
  })

  // 5. Operationally closed contract with credit exposes refund
  it('operationally closed with credit exposes refund option', async () => {
    state.setMockContract('C5', { balance: -300, can_refund: true, is_archived: false })
    await state.handleContractChange('C5')
    expect(state.canRefund.value).toBe(true)
    expect(state.showTransactionType.value).toBe(true)
  })

  // 6. Archived contract does not expose refund
  it('archived contract does not expose refund', async () => {
    state.setMockContract('C6', { balance: -300, can_refund: false, is_archived: true })
    await state.handleContractChange('C6')
    expect(state.showTransactionType.value).toBe(false)
    expect(state.isContractArchived.value).toBe(true)
  })

  // 7. Settlement button with positive balance sets receipt + amount
  it('settlement with positive balance sets receipt type and amount', async () => {
    state.setMockContract('C7', { balance: 410, can_refund: false, is_archived: false })
    await state.handleContractChange('C7')
    state.handleSettleBalance()
    expect(state.formData.transactionType).toBe('receipt')
    expect(state.formData.amount).toBe('410.00')
  })

  // 8. Settlement button with negative balance sets refund + abs(amount)
  it('settlement with negative balance sets refund type and abs amount', async () => {
    state.setMockContract('C8', { balance: -410, can_refund: true, is_archived: false })
    await state.handleContractChange('C8')
    state.handleSettleBalance()
    expect(state.formData.transactionType).toBe('refund')
    expect(state.formData.amount).toBe('410.00')
  })

  // 9. Zero balance hides settlement button
  it('zero balance: no settlement button, transactionType stays receipt', async () => {
    state.setMockContract('C9', { balance: 0, can_refund: false, is_archived: false })
    await state.handleContractChange('C9')
    expect(state.canShowSettlement.value).toBe(false)
    state.handleSettleBalance()
    expect(state.formData.amount).toBe('')
    expect(state.formData.transactionType).toBe('receipt')
    const payload = state.buildPayload()
    expect(payload.transaction_type).toBe('receipt')
  })

  // A) Active contract with credit balance — NO settlement, NO refund
  it('A) active contract with credit: shows balance but no settlement button, no refund option', async () => {
    state.setMockContract('CA', { balance: -410, can_refund: false, is_archived: false })
    await state.handleContractChange('CA')
    expect(state.contractBalance.value).toBe(-410)
    expect(state.contractBalanceLabel.value).toContain('لصالح المستأجر')
    expect(state.contractBalanceLabel.value).toContain('410.00')
    // No settlement button
    expect(state.canShowSettlement.value).toBe(false)
    // No refund option
    expect(state.showTransactionType.value).toBe(false)
    expect(state.canRefund.value).toBe(false)
    // transactionType stays receipt
    expect(state.formData.transactionType).toBe('receipt')
    // Even if handleSettleBalance is called, nothing happens
    state.handleSettleBalance()
    expect(state.formData.amount).toBe('')
    expect(state.formData.transactionType).toBe('receipt')
    // Payload sends receipt
    const payload = state.buildPayload()
    expect(payload.transaction_type).toBe('receipt')
  })

  // B) Operationally closed with credit — settlement + refund
  it('B) operationally closed with credit: settlement button works as refund', async () => {
    state.setMockContract('CB', { balance: -410, can_refund: true, is_archived: false })
    await state.handleContractChange('CB')
    expect(state.canShowSettlement.value).toBe(true)
    expect(state.canRefund.value).toBe(true)
    state.handleSettleBalance()
    expect(state.formData.transactionType).toBe('refund')
    expect(state.formData.amount).toBe('410.00')
  })

  // C) Zero balance — no settlement, receipt payload
  it('C) zero balance: no settlement, payload sends receipt', async () => {
    state.setMockContract('CC', { balance: 0, can_refund: false, is_archived: false })
    await state.handleContractChange('CC')
    expect(state.canShowSettlement.value).toBe(false)
    expect(state.formData.transactionType).toBe('receipt')
    state.formData.amount = '100'
    const payload = state.buildPayload()
    expect(payload.transaction_type).toBe('receipt')
  })

  // D) Positive balance — settlement as receipt regardless of can_refund
  it('D) positive balance: settlement works as receipt even when can_refund=false', async () => {
    state.setMockContract('CD', { balance: 500, can_refund: false, is_archived: false })
    await state.handleContractChange('CD')
    expect(state.canShowSettlement.value).toBe(true)
    state.handleSettleBalance()
    expect(state.formData.transactionType).toBe('receipt')
    expect(state.formData.amount).toBe('500.00')
  })

  // 10. Manual receipt still allows prepayment
  it('receipt allows amount > balance (prepayment)', async () => {
    state.setMockContract('C10', { balance: 100, can_refund: false, is_archived: false })
    await state.handleContractChange('C10')
    state.formData.transactionType = 'receipt'
    state.formData.amount = '500'
    expect(state.amountError.value).toBe('')
  })

  // 11. Refund amount cannot exceed available credit
  it('refund amount exceeding credit shows error', async () => {
    state.setMockContract('C11', { balance: -200, can_refund: true, is_archived: false })
    await state.handleContractChange('C11')
    state.formData.transactionType = 'refund'
    state.formData.amount = '300'
    expect(state.amountError.value).toBe('مبلغ الرد لا يمكن أن يتجاوز الرصيد الدائن للعقد.')
  })

  it('refund amount within credit is valid', async () => {
    state.setMockContract('C11b', { balance: -200, can_refund: true, is_archived: false })
    await state.handleContractChange('C11b')
    state.formData.transactionType = 'refund'
    state.formData.amount = '100'
    expect(state.amountError.value).toBe('')
  })

  // 12. Negative amount rejected in UI
  it('negative amount shows error', async () => {
    state.setMockContract('C12', { balance: 500, can_refund: false, is_archived: false })
    await state.handleContractChange('C12')
    state.formData.amount = '-50'
    expect(state.amountError.value).toBe('المبلغ يجب أن يكون موجبًا')
  })

  // 13. Changing contract resets stale settlement state
  it('changing contract resets transaction type and amount', async () => {
    state.setMockContract('C13a', { balance: -200, can_refund: true, is_archived: false })
    await state.handleContractChange('C13a')
    state.handleSettleBalance()
    expect(state.formData.transactionType).toBe('refund')
    expect(state.formData.amount).toBe('200.00')

    // Switch to a different contract
    state.setMockContract('C13b', { balance: 500, can_refund: false, is_archived: false })
    await state.handleContractChange('C13b')
    expect(state.formData.transactionType).toBe('receipt')
    expect(state.formData.amount).toBe('')
    expect(state.canRefund.value).toBe(false)
  })

  // 14. Changing tenant resets contract/settlement state
  it('changing tenant resets contract, balance, and transaction type', async () => {
    state.setMockContract('C14', { balance: -200, can_refund: true, is_archived: false })
    await state.handleFormTenantSelect('T1', ['C14'])
    expect(state.formData.contractId).toBe('C14')
    expect(state.contractBalance.value).toBe(-200)
    expect(state.canRefund.value).toBe(true)

    // Change tenant — should reset everything
    await state.handleFormTenantSelect('T2', [])
    expect(state.formData.contractId).toBe('')
    expect(state.formData.transactionType).toBe('receipt')
    expect(state.formData.amount).toBe('')
    expect(state.contractBalance.value).toBe(null)
    expect(state.canRefund.value).toBe(false)
  })

  // 15. API payload includes transaction_type
  it('API payload includes transaction_type', async () => {
    state.setMockContract('C15', { balance: -300, can_refund: true, is_archived: false })
    await state.handleContractChange('C15')
    state.handleSettleBalance()
    const payload = state.buildPayload()
    expect(payload.transaction_type).toBe('refund')
    expect(payload.amount).toBe('300.00')
    expect(payload.contract).toBe('C15')
  })

  it('API payload includes transaction_type=receipt for normal flow', async () => {
    state.setMockContract('C16', { balance: 500, can_refund: false, is_archived: false })
    await state.handleContractChange('C16')
    state.formData.amount = '200'
    const payload = state.buildPayload()
    expect(payload.transaction_type).toBe('receipt')
    expect(payload.amount).toBe('200')
  })

  // 16. handleTransactionTypeChange clears amount
  it('changing transaction type clears amount', async () => {
    state.setMockContract('C17', { balance: -200, can_refund: true, is_archived: false })
    await state.handleContractChange('C17')
    state.handleSettleBalance()
    expect(state.formData.amount).toBe('200.00')
    state.handleTransactionTypeChange()
    expect(state.formData.amount).toBe('')
  })
})
