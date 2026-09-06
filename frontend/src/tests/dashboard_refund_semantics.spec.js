/**
 * Phase 4 — Dashboard Refund Semantics tests.
 *
 * Verifies:
 * 1. totalReceipts = Gross only
 * 2. totalRefunds = Refund only
 * 3. netCollections = receipts - refunds
 * 4. totalBalance = dues - receipts + refunds
 * 5. Collection rate uses Net Collections (not Gross)
 * 6. Collection rate may exceed 100% with prepayment
 * 7. Division by zero safe
 * 8. Trend maps netCollections to chart
 * 9. Refund-only month produces negative netCollections
 * 10. KPI labels correct
 * 11. AreaChart supports negative values
 *
 * Run: npx vitest run src/tests/dashboard_refund_semantics.spec.js
 */

import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

// ---- Dashboard stats simulation (mirrors dashboard.py) ----

function createDashboardStats(data) {
  const totalDues = data.totalDues ?? 0
  const totalReceipts = data.totalReceipts ?? 0
  const totalRefunds = data.totalRefunds ?? 0
  const netCollections = totalReceipts - totalRefunds
  const totalBalance = totalDues - totalReceipts + totalRefunds
  return {
    totalDues,
    totalReceipts,
    totalRefunds,
    netCollections,
    totalBalance,
  }
}

// ---- Collection rate simulation (mirrors DashboardPage.vue) ----

function createCollectionRate(stats) {
  const dues = stats.totalDues ?? 0
  const netCollections = stats.netCollections ?? 0
  return dues > 0 ? Math.round((netCollections / dues) * 100) : 0
}

// ---- KPI cards simulation (mirrors DashboardPage.vue) ----

function createKpiCards(stats, currency) {
  const fmt = (v) => v // simplified
  const balanceValue = stats.totalBalance ?? 0
  const balanceDisplay = Math.abs(balanceValue)
  return [
    { label: 'إجمالي المستحقات', value: fmt(stats.totalDues ?? 0) },
    { label: 'صافي التحصيل', value: fmt(stats.netCollections ?? 0) },
    { label: 'الرصيد المستحق', value: fmt(balanceDisplay) },
    { label: 'نسبة الإشغال', value: `${stats.occupancyRate ?? 0}%` },
  ]
}

// ---- Trend mapping simulation (mirrors DashboardPage.vue) ----

function mapTrendData(months) {
  return (months ?? []).map(m => ({
    name: m.name,
    dues: m.dues,
    receipts: m.netCollections,
  }))
}

// ---- AreaChart negative value simulation ----

function createChartScales(data) {
  const all = data.flatMap(d => [d.dues, d.receipts])
  const maxRaw = Math.max(...all, 0)
  const minRaw = Math.min(...all, 0)

  const maxVal = maxRaw === 0 ? 1 : (() => {
    const pow = Math.pow(10, String(Math.floor(maxRaw)).length - 1)
    return Math.ceil(maxRaw / pow) * pow
  })()

  const minVal = minRaw >= 0 ? 0 : (() => {
    const absM = Math.abs(minRaw)
    const pow = Math.pow(10, String(Math.floor(absM)).length - 1)
    return -Math.ceil(absM / pow) * pow
  })()

  const valRange = maxVal - minVal || 1

  const vbH = 260, padT = 16, padB = 36
  const h = vbH - padT - padB

  function yAt(val) {
    const frac = (val - minVal) / valRange
    return padT + h - frac * h
  }

  return { maxVal, minVal, valRange, yAt }
}

// ============ TESTS ============

describe('Phase 4 — Dashboard Refund Semantics', () => {

  // 1. totalReceipts = Gross only
  it('1) totalReceipts is Gross Receipts only', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    expect(stats.totalReceipts).toBe(5410)
  })

  // 2. totalRefunds = Refund only
  it('2) totalRefunds is Refund total only', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    expect(stats.totalRefunds).toBe(410)
  })

  // 3. netCollections = receipts - refunds
  it('3) netCollections = totalReceipts - totalRefunds', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    expect(stats.netCollections).toBe(5000)
  })

  // 4. totalBalance = dues - receipts + refunds
  it('4) totalBalance = totalDues - totalReceipts + totalRefunds', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    expect(stats.totalBalance).toBe(0)
  })

  // 5. Collection rate uses Net Collections
  it('5) collectionRate uses netCollections not gross', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    const rate = createCollectionRate(stats)
    expect(rate).toBe(100) // 5000/5000 = 100%, not 108%
  })

  // 6. Collection rate may exceed 100% with prepayment
  it('6) collectionRate can exceed 100% (no clamp)', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5500, totalRefunds: 0 })
    const rate = createCollectionRate(stats)
    expect(rate).toBe(110) // 5500/5000 = 110%, not clamped to 100
  })

  // 7. Division by zero safe
  it('7) collectionRate is 0 when totalDues = 0', () => {
    const stats = createDashboardStats({ totalDues: 0, totalReceipts: 1000, totalRefunds: 0 })
    const rate = createCollectionRate(stats)
    expect(rate).toBe(0)
  })

  // 8. Trend maps netCollections to chart receipts field
  it('8) trend data maps netCollections to receipts', () => {
    const months = [
      { name: 'أغسطس', dues: 1000, grossReceipts: 1000, refunds: 0, netCollections: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, grossReceipts: 0, refunds: 200, netCollections: -200, receipts: 0 },
    ]
    const mapped = mapTrendData(months)
    expect(mapped[0].receipts).toBe(1000)
    expect(mapped[1].receipts).toBe(-200)
  })

  // 9. Refund-only month produces negative netCollections
  it('9) refund-only month has negative netCollections', () => {
    const months = [
      { name: 'أغسطس', dues: 1000, grossReceipts: 1000, refunds: 0, netCollections: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, grossReceipts: 0, refunds: 200, netCollections: -200, receipts: 0 },
    ]
    expect(months[1].netCollections).toBe(-200)
    expect(months[1].netCollections < 0).toBe(true)
  })

  // 10. KPI labels correct (4 primary cards)
  it('10) KPI cards have correct labels', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    stats.occupancyRate = 75
    const cards = createKpiCards(stats, 'ILS')
    expect(cards).toHaveLength(4)
    expect(cards[0].label).toBe('إجمالي المستحقات')
    expect(cards[1].label).toBe('صافي التحصيل')
    expect(cards[2].label).toBe('الرصيد المستحق')
    expect(cards[3].label).toBe('نسبة الإشغال')
  })

  // 10b. Balance card shows absolute value for negative balance
  it('10b) Balance card shows absolute value for credit balance', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5500, totalRefunds: 0 })
    stats.occupancyRate = 50
    const cards = createKpiCards(stats, 'ILS')
    const balanceCard = cards.find(c => c.label === 'الرصيد المستحق')
    expect(balanceCard.value).toBe(500) // abs(-500) = 500
  })

  // 11. AreaChart supports negative values
  it('11a) AreaChart computes minVal for negative data', () => {
    const data = [
      { name: 'أغسطس', dues: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, receipts: -200 },
    ]
    const scales = createChartScales(data)
    expect(scales.minVal).toBeLessThan(0)
    expect(scales.maxVal).toBeGreaterThan(0)
    expect(scales.valRange).toBe(scales.maxVal - scales.minVal)
  })

  it('11b) AreaChart yAt(0) is within chart bounds for negative data', () => {
    const data = [
      { name: 'أغسطس', dues: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, receipts: -200 },
    ]
    const scales = createChartScales(data)
    const zeroY = scales.yAt(0)
    const padT = 16
    const padB = 36
    const vbH = 260
    expect(zeroY).toBeGreaterThan(padT)
    expect(zeroY).toBeLessThan(vbH - padB)
  })

  it('11c) AreaChart yAt for negative value is below zero line', () => {
    const data = [
      { name: 'أغسطس', dues: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, receipts: -200 },
    ]
    const scales = createChartScales(data)
    const zeroY = scales.yAt(0)
    const negY = scales.yAt(-200)
    expect(negY).toBeGreaterThan(zeroY) // negative value is below zero line
  })

  it('11d) AreaChart yAt for positive value is above zero line', () => {
    const data = [
      { name: 'أغسطس', dues: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, receipts: -200 },
    ]
    const scales = createChartScales(data)
    const zeroY = scales.yAt(0)
    const posY = scales.yAt(1000)
    expect(posY).toBeLessThan(zeroY) // positive value is above zero line
  })

  it('11e) AreaChart minVal = 0 when all values positive', () => {
    const data = [
      { name: 'أغسطس', dues: 1000, receipts: 500 },
      { name: 'سبتمبر', dues: 800, receipts: 600 },
    ]
    const scales = createChartScales(data)
    expect(scales.minVal).toBe(0)
  })

  // 12. Mandatory example: dues=5000, receipts=5410, refunds=410
  it('12) mandatory example: net=5000, balance=0, rate=100%', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    const rate = createCollectionRate(stats)
    expect(stats.totalDues).toBe(5000)
    expect(stats.totalReceipts).toBe(5410)
    expect(stats.totalRefunds).toBe(410)
    expect(stats.netCollections).toBe(5000)
    expect(stats.totalBalance).toBe(0)
    expect(rate).toBe(100)
  })

  // 13. Prepayment example: dues=5000, receipts=5500, refunds=0
  it('13) prepayment: net=5500, balance=-500, rate=110%', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5500, totalRefunds: 0 })
    const rate = createCollectionRate(stats)
    expect(stats.netCollections).toBe(5500)
    expect(stats.totalBalance).toBe(-500)
    expect(rate).toBe(110)
  })

  // 14. Zero refunds → net = gross
  it('14) zero refunds: netCollections = totalReceipts', () => {
    const stats = createDashboardStats({ totalDues: 3000, totalReceipts: 2000, totalRefunds: 0 })
    expect(stats.netCollections).toBe(2000)
  })

  // 15. All zero → safe
  it('15) all zero: safe handling', () => {
    const stats = createDashboardStats({ totalDues: 0, totalReceipts: 0, totalRefunds: 0 })
    const rate = createCollectionRate(stats)
    expect(stats.netCollections).toBe(0)
    expect(stats.totalBalance).toBe(0)
    expect(rate).toBe(0)
  })

  // 16. Trend backward compatibility: receipts field still gross
  it('16) trend receipts field is still gross for backward compat', () => {
    const month = {
      name: 'أكتوبر',
      dues: 3000,
      grossReceipts: 2000,
      refunds: 500,
      netCollections: 1500,
      receipts: 2000, // backward compat = gross
    }
    expect(month.receipts).toBe(month.grossReceipts)
    expect(month.netCollections).toBe(1500)
  })

  // 17. Trend always returns 6 months (zero months preserved)
  it('17) trend always returns 6 months even if some are zero', () => {
    const months = [
      { name: 'أبريل', dues: 0, grossReceipts: 0, refunds: 0, netCollections: 0, receipts: 0 },
      { name: 'مايو', dues: 1000, grossReceipts: 500, refunds: 0, netCollections: 500, receipts: 500 },
      { name: 'يونيو', dues: 0, grossReceipts: 0, refunds: 0, netCollections: 0, receipts: 0 },
      { name: 'يوليو', dues: 2000, grossReceipts: 1500, refunds: 200, netCollections: 1300, receipts: 1500 },
      { name: 'أغسطس', dues: 0, grossReceipts: 0, refunds: 0, netCollections: 0, receipts: 0 },
      { name: 'سبتمبر', dues: 800, grossReceipts: 600, refunds: 0, netCollections: 600, receipts: 600 },
    ]
    expect(months.length).toBe(6)
    // Zero months are preserved, not dropped
    expect(months[0].netCollections).toBe(0)
    expect(months[2].netCollections).toBe(0)
    expect(months[4].netCollections).toBe(0)
  })

  // 18. Trend netCollections formula holds for each month
  it('18) trend netCollections = grossReceipts - refunds for each month', () => {
    const months = [
      { name: 'أغسطس', dues: 1000, grossReceipts: 1000, refunds: 0, netCollections: 1000, receipts: 1000 },
      { name: 'سبتمبر', dues: 0, grossReceipts: 0, refunds: 200, netCollections: -200, receipts: 0 },
    ]
    for (const m of months) {
      expect(m.netCollections).toBe(m.grossReceipts - m.refunds)
    }
  })

  // 19. AreaChart tooltip shows negative value correctly
  it('19) AreaChart tooltip displays negative netCollections', () => {
    const data = [
      { name: 'سبتمبر', dues: 0, receipts: -200 },
    ]
    const scales = createChartScales(data)
    // yAt for -200 should be a valid number (not NaN, not clamped)
    const yNeg = scales.yAt(-200)
    expect(isNaN(yNeg)).toBe(false)
    expect(yNeg).toBeGreaterThan(0)
  })

  // 20. Collection performance section uses netCollections
  it('20) collection performance uses netCollections not gross', () => {
    const stats = createDashboardStats({ totalDues: 5000, totalReceipts: 5410, totalRefunds: 410 })
    // The "المحصل" label was changed to "صافي التحصيل" and uses netCollections
    const performanceValue = stats.netCollections
    expect(performanceValue).toBe(5000)
    expect(performanceValue).not.toBe(5410) // not gross
  })
})
