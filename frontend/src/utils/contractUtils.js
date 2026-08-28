/**
 * Contract utility helpers — ported from Rental_Management_olde/src/lib/utils.ts.
 *
 * Provides period status, eligibility checks (renew/evict/archive), and date math
 * used by ContractsPage, ContractDetailPage, ContractFormPage, ContractRenewPage,
 * ContractPreviewPage, and ContractPrintPage.
 */

/**
 * Parse a YYYY-MM-DD (or ISO) string into a UTC calendar day to avoid timezone
 * shifts when comparing dates.
 */
export function toCalendarDay(date) {
  if (date === null || date === undefined || date === '') {
    return new Date(Date.UTC(1970, 0, 1))
  }
  if (typeof date === 'string') {
    const [datePart] = date.split('T')
    const match = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (match) {
      const [, y, m, d] = match
      return new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)))
    }
  }
  const d = new Date(date)
  if (Number.isNaN(d.getTime())) return new Date(Date.UTC(1970, 0, 1))
  return new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
}

export function calendarDayDiff(a, b) {
  const msPerDay = 1000 * 60 * 60 * 24
  return Math.round((toCalendarDay(b).getTime() - toCalendarDay(a).getTime()) / msPerDay)
}

export function previousCalendarDay(date) {
  const base = new Date(date)
  return new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate() - 1))
}

export function addCalendarMonths(date, months, anchorDay) {
  const base = toCalendarDay(date)
  const day = anchorDay ?? base.getUTCDate()
  const targetMonth = base.getUTCMonth() + months
  const year = base.getUTCFullYear() + Math.floor(targetMonth / 12)
  const month = ((targetMonth % 12) + 12) % 12
  const lastDayOfMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  const targetDay = Math.min(day, lastDayOfMonth)
  return new Date(Date.UTC(year, month, targetDay))
}

export function addDays(date, days) {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

export function roundMoney(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100
}

/**
 * Returns 'upcoming' | 'current' | 'past' for a contract period.
 * Source: utils.ts:86 getContractPeriodStatus
 */
export function getContractPeriodStatus(startDate, endDate, today) {
  const d = toCalendarDay(today ?? new Date())
  const s = toCalendarDay(startDate)
  const e = toCalendarDay(endDate)
  if (s > d) return 'upcoming'
  if (e < d) return 'past'
  return 'current'
}

const contractStatusLabels = {
  draft: 'مسودة',
  active: 'نشط',
  upcoming: 'قادم',
  expired: 'منتهي',
  cancelled: 'ملغي',
  evicted: 'تم الإخلاء',
}

/**
 * Returns { status, label } for display, applying period-based override for
 * active contracts (upcoming / expired).
 * Source: StatusBadge.tsx:100 getContractDisplayStatus
 */
export function getContractDisplayStatus(contract) {
  if (contract.status === 'active') {
    const period = getContractPeriodStatus(contract.start_date || contract.startDate, contract.end_date || contract.endDate)
    if (period === 'upcoming') return { status: 'upcoming', label: contractStatusLabels.upcoming }
    if (period === 'past') return { status: 'expired', label: contractStatusLabels.expired }
    return { status: 'active', label: contractStatusLabels.active }
  }
  return { status: contract.status, label: contractStatusLabels[contract.status] || contract.status }
}

/**
 * Source: utils.ts:180 canRenewContract
 */
export function canRenewContract(contract, today = new Date()) {
  const isArchived = contract.is_archived ?? contract.isArchived
  const isHistorical = contract.is_historical ?? contract.isHistorical
  const closedByRenewalAt = contract.closed_by_renewal_at ?? contract.closedByRenewalAt
  const renewals = contract.renewals || []
  const status = contract.status
  const startDate = contract.start_date || contract.startDate
  const endDate = contract.end_date || contract.endDate

  if (isArchived || isHistorical || closedByRenewalAt) return false
  if (renewals.some((r) => r.status !== 'cancelled' && r.status !== 'evicted')) return false

  if (status === 'active') {
    const now = toCalendarDay(today)
    const start = toCalendarDay(startDate)
    const end = toCalendarDay(endDate)
    if (now < start || now > end) return false
    const daysLeft = calendarDayDiff(now, end)
    return daysLeft <= 30
  }

  if (status === 'expired') return true

  return false
}

/**
 * Source: utils.ts:202 canEvictContract
 */
export function canEvictContract(contract) {
  const isArchived = contract.is_archived ?? contract.isArchived
  const isHistorical = contract.is_historical ?? contract.isHistorical
  const closedByRenewalAt = contract.closed_by_renewal_at ?? contract.closedByRenewalAt
  const renewals = contract.renewals || []
  const status = contract.status
  const startDate = contract.start_date || contract.startDate
  const cancelledAt = contract.cancelled_at ?? contract.cancelledAt

  if (isArchived || isHistorical || closedByRenewalAt) return false

  const hasApprovedRenewal = renewals.some(
    (r) => r.status !== 'draft' && r.status !== 'cancelled' && r.status !== 'evicted'
  )
  if (hasApprovedRenewal) return false

  if (status === 'expired') return true
  if (status === 'cancelled' && cancelledAt) {
    return toCalendarDay(cancelledAt) >= toCalendarDay(startDate)
  }
  return false
}

/**
 * Source: utils.ts:220 canArchiveContract
 */
export function canArchiveContract(contract) {
  const isArchived = contract.is_archived ?? contract.isArchived
  const isHistorical = contract.is_historical ?? contract.isHistorical
  const closedByRenewalAt = contract.closed_by_renewal_at ?? contract.closedByRenewalAt
  const status = contract.status
  const startDate = contract.start_date || contract.startDate
  const cancelledAt = contract.cancelled_at ?? contract.cancelledAt

  if (isArchived) return false
  if (status === 'evicted') return true
  if (status === 'expired' && (isHistorical || closedByRenewalAt)) return true
  if (status === 'cancelled' && cancelledAt && toCalendarDay(cancelledAt) < toCalendarDay(startDate)) {
    return true
  }
  return false
}

/**
 * Source: utils.ts:116 calculateContractEndDate
 */
export function calculateContractEndDate(startDate, paymentFrequency, cycles) {
  const start = typeof startDate === 'string' ? new Date(startDate) : startDate
  const months = getFrequencyMonths(paymentFrequency)
  if (months === 0) return start.toISOString().split('T')[0]
  const anchorDay = start.getUTCDate()
  const nextBoundary = addCalendarMonths(start, cycles * months, anchorDay)
  return previousCalendarDay(nextBoundary).toISOString().split('T')[0]
}

export function getFrequencyMonths(frequency) {
  const map = {
    once: 0,
    one_time: 0,
    weekly: 0,
    monthly: 1,
    bi_monthly: 2,
    bimonthly: 2,
    quarterly: 3,
    semi_annual: 6,
    semiannual: 6,
    annual: 12,
  }
  return map[frequency] ?? 0
}

export function getFrequencyInterval(frequency) {
  switch (frequency) {
    case 'weekly': return { months: 0, days: 7 }
    case 'once':
    case 'one_time': return { months: 0, days: 0 }
    case 'monthly': return { months: 1, days: 0 }
    case 'bi_monthly':
    case 'bimonthly': return { months: 2, days: 0 }
    case 'quarterly': return { months: 3, days: 0 }
    case 'semi_annual':
    case 'semiannual': return { months: 6, days: 0 }
    case 'annual': return { months: 12, days: 0 }
    default: return { months: 0, days: 0 }
  }
}

/**
 * Build the periodic schedule of due dates between start and end.
 * Source: utils.ts:282 buildPeriodicSchedule
 */
export function buildPeriodicSchedule(options) {
  const { startDate, endDate, frequency, commitmentTiming, amount = 0, maxCount } = options
  const start = toCalendarDay(startDate)
  const end = toCalendarDay(endDate)
  const interval = getFrequencyInterval(frequency)
  const isEndTiming = commitmentTiming === 'end'
  const schedule = []

  // Single payment (once / one_time)
  if (interval.months === 0 && interval.days === 0) {
    if (start <= end) {
      const dueDate = isEndTiming ? end : start
      schedule.push({
        index: 0,
        dueDate,
        periodStart: new Date(start),
        periodEnd: new Date(end),
        amount,
        periodLabel: 'دفعة واحدة',
      })
    }
    return schedule
  }

  // Day-based frequency (weekly)
  if (interval.days > 0) {
    for (let i = 0; ; i++) {
      if (maxCount !== undefined && schedule.length >= maxCount) break
      const periodStart = addDays(start, i * interval.days)
      const periodEnd = addDays(start, (i + 1) * interval.days - 1)
      const dueDate = isEndTiming ? periodEnd : periodStart
      const dueDateDay = toCalendarDay(dueDate)
      if (dueDateDay > end) break
      schedule.push({
        index: i,
        dueDate: dueDateDay,
        periodStart: toCalendarDay(periodStart),
        periodEnd: toCalendarDay(periodEnd),
        amount,
        periodLabel: '',
      })
    }
    return schedule
  }

  // Month-based frequency
  const anchorDay = start.getUTCDate()
  for (let i = 0; ; i++) {
    if (maxCount !== undefined && schedule.length >= maxCount) break
    const periodStart = addCalendarMonths(start, i * interval.months, anchorDay)
    const nextBoundary = addCalendarMonths(start, (i + 1) * interval.months, anchorDay)
    const periodEnd = previousCalendarDay(nextBoundary)
    const dueDate = isEndTiming ? periodEnd : periodStart
    const dueDateDay = toCalendarDay(dueDate)
    if (dueDateDay > end) break
    schedule.push({
      index: i,
      dueDate: dueDateDay,
      periodStart: toCalendarDay(periodStart),
      periodEnd: toCalendarDay(periodEnd),
      amount,
      periodLabel: '',
    })
  }

  return schedule
}

/**
 * Returns the number of cycles between start and end for a given frequency.
 * Source: utils.ts:347 getFrequencyCount
 */
export function getFrequencyCount(startDate, endDate, frequency, commitmentTiming = 'start') {
  const schedule = buildPeriodicSchedule({ startDate, endDate, frequency, commitmentTiming, amount: 0 })
  return Math.max(0, schedule.length)
}

/**
 * Calculate the rent payment schedule for a contract.
 * Source: utils.ts:597 calculateContractDueSchedule
 */
export function calculateContractDueSchedule(baseDate, endDate, rentAmount, paymentFrequency, count, commitmentTiming) {
  return buildPeriodicSchedule({
    startDate: baseDate,
    endDate,
    frequency: paymentFrequency,
    commitmentTiming,
    amount: rentAmount,
    maxCount: count,
  })
}

/**
 * isApprovedHistorical — a historical contract that has been approved (not draft).
 * Source: contracts/page.tsx:143
 */
export function isApprovedHistorical(contract) {
  const isHistorical = contract.is_historical ?? contract.isHistorical
  const startDate = contract.start_date || contract.startDate
  const endDate = contract.end_date || contract.endDate
  return getContractPeriodStatus(startDate, endDate) === 'past' && contract.status !== 'draft'
}

/**
 * hasApprovedRenewal — any renewal that is not draft/cancelled/evicted.
 * Source: utils.ts:208
 */
export function hasApprovedRenewal(contract) {
  const renewals = contract.renewals || []
  return renewals.some(
    (r) => r.status !== 'draft' && r.status !== 'cancelled' && r.status !== 'evicted'
  )
}

// ---- Fixed Periodic Charge Analysis (source: utils.ts:423-563) ----

export const FIXED_PERIODIC_FREQUENCIES = ['monthly', 'bi_monthly', 'quarterly', 'semi_annual', 'annual']

function dateToISO(date) {
  return date.toISOString().split('T')[0]
}

/**
 * Analyze a fixed-periodic charge and produce its due schedule + partial period info.
 * Source: utils.ts:423-563 analyzeFixedPeriodicCharge
 */
export function analyzeFixedPeriodicCharge(charge, endDate) {
  const empty = {
    dues: [],
    partialPeriod: { exists: false, startDate: null, endDate: null, handling: 'none', amount: 0 },
  }

  if (!charge.amount || !charge.frequency || !charge.first_due_date || !endDate) return empty
  const amount = parseFloat(String(charge.amount).replace(/,/g, ''))
  if (isNaN(amount) || amount <= 0) return empty

  const start = toCalendarDay(charge.first_due_date)
  const end = toCalendarDay(endDate)
  if (start > end) return empty

  const interval = getFrequencyInterval(charge.frequency)
  const handling = charge.last_period_handling || 'none'
  const manualAmount = charge.last_period_adjustment_amount
    ? parseFloat(String(charge.last_period_adjustment_amount).replace(/,/g, ''))
    : NaN
  const isEndTiming = charge.commitment_timing === 'end'

  // Single-period services (once) — single due at end of contract
  if (interval.months === 0 && interval.days === 0) {
    const dueDate = isEndTiming ? end : start
    return {
      dues: [{ dueDate: dateToISO(dueDate), amount, periodStart: dateToISO(start), periodEnd: dateToISO(end) }],
      partialPeriod: { exists: false, startDate: null, endDate: null, handling, amount: 0 },
    }
  }

  const anchorDay = start.getUTCDate()
  const fullCycles = []

  for (let i = 0; i <= 1000; i++) {
    const nextBoundary = interval.days > 0
      ? toCalendarDay(new Date(start.getTime() + (i + 1) * interval.days * 86400000))
      : addCalendarMonths(start, (i + 1) * interval.months, anchorDay)
    const cycleEnd = previousCalendarDay(nextBoundary)
    if (cycleEnd > end) break

    const cycleStart = interval.days > 0
      ? toCalendarDay(new Date(start.getTime() + i * interval.days * 86400000))
      : addCalendarMonths(start, i * interval.months, anchorDay)
    const dueDate = isEndTiming ? new Date(cycleEnd) : new Date(cycleStart)

    fullCycles.push({ startDate: cycleStart, endDate: cycleEnd, dueDate, amount })
  }

  const fullCycleCount = fullCycles.length
  const partialStart = interval.days > 0
    ? toCalendarDay(new Date(start.getTime() + fullCycleCount * interval.days * 86400000))
    : addCalendarMonths(start, fullCycleCount * interval.months, anchorDay)
  const partialExists = partialStart < end

  let settlementAmount = 0
  if (partialExists) {
    if (handling === 'prorated') {
      const nextBoundary = interval.days > 0
        ? toCalendarDay(new Date(start.getTime() + (fullCycleCount + 1) * interval.days * 86400000))
        : addCalendarMonths(start, (fullCycleCount + 1) * interval.months, anchorDay)
      const fullPeriodDays = Math.max(1, calendarDayDiff(partialStart, nextBoundary))
      const partialDays = Math.max(0, calendarDayDiff(partialStart, end))
      settlementAmount = roundMoney((amount * partialDays) / fullPeriodDays)
    } else if (handling === 'manual' && !isNaN(manualAmount) && manualAmount >= 0) {
      settlementAmount = manualAmount
    }
  }

  const dues = fullCycles.map((cycle) => ({
    dueDate: dateToISO(cycle.dueDate),
    amount: cycle.amount,
    periodStart: dateToISO(cycle.startDate),
    periodEnd: dateToISO(cycle.endDate),
  }))

  if (partialExists && handling !== 'none') {
    const nextBoundary = interval.days > 0
      ? toCalendarDay(new Date(start.getTime() + (fullCycleCount + 1) * interval.days * 86400000))
      : addCalendarMonths(start, (fullCycleCount + 1) * interval.months, anchorDay)
    const lastDayOfPartial = previousCalendarDay(nextBoundary)
    const partialDueDate = isEndTiming
      ? new Date(Math.min(end.getTime(), lastDayOfPartial.getTime()))
      : new Date(partialStart)
    dues.push({
      dueDate: dateToISO(partialDueDate),
      amount: settlementAmount,
      periodStart: dateToISO(partialStart),
      periodEnd: dateToISO(end),
    })
  }

  return {
    dues,
    partialPeriod: {
      exists: partialExists,
      startDate: partialExists ? dateToISO(partialStart) : null,
      endDate: partialExists ? dateToISO(end) : null,
      handling,
      amount: settlementAmount,
    },
  }
}

/**
 * Build the due schedule for a fixed-periodic charge.
 * Source: utils.ts:565-570 buildFixedPeriodicSchedule
 */
export function buildFixedPeriodicSchedule(charge, endDate) {
  return analyzeFixedPeriodicCharge(charge, endDate).dues
}

/**
 * Returns the list of fixed-periodic frequencies that produce at least 1 due
 * for the given date range.
 * Source: utils.ts:396-414 getAvailableFixedPeriodicFrequencies
 * Note: Ignores commitmentTiming/lastPeriodHandling (always uses 'start' and 'none').
 */
export function getAvailableFixedPeriodicFrequencies(startDate, endDate, _commitmentTiming, _lastPeriodHandling) {
  if (!startDate || !endDate) return []
  const start = toCalendarDay(startDate)
  const end = toCalendarDay(endDate)
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return []
  if (start > end) return []

  return FIXED_PERIODIC_FREQUENCIES.filter((frequency) => {
    const schedule = buildFixedPeriodicSchedule(
      {
        amount: '1',
        frequency,
        first_due_date: startDate,
        commitment_timing: 'start',
        last_period_handling: 'none',
      },
      endDate
    )
    return schedule.length >= 1
  })
}
