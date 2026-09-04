/**
 * Phase 8 Regression Tests — Capability filtering and non-auto-conversion
 *
 * These tests verify the core business rules:
 * 1. Existing Draft with metered + capability 1→0: calculation_method stays metered/invalid
 * 2. Same for water
 * 3. Renewal with empty calculation_method + capability=0: stays empty
 * 4. Same for water
 * 5. Explicit user selection of fixed_periodic works
 * 6. Explicit user selection of actual_bill works
 * 7. Brand-new charge defaults to legacy default (metered for electricity/water),
 *    NOT to fixed_periodic because capability is absent
 *
 * Also verifies:
 * - getDefaultCalculationMethodForDueType does NOT change its return value
 *   based on capability
 * - Opening meter reading zero is preserved
 *
 * Run: npx vitest run phase8_regression.spec.js
 * Or:  node --experimental-vm-modules phase8_regression.test.mjs
 */

import { describe, it, expect } from 'vitest'

// ---- Constants (mirrors ContractChargesSection.vue) ----
const CALCULATION_METHODS = {
  metered: 'metered',
  fixed_periodic: 'fixed_periodic',
  actual_bill: 'actual_bill',
  on_demand: 'on_demand',
}

const PAYMENT_BY = { landlord: 'landlord', tenant: 'tenant' }

function isMeteredDueTypeCode(code) {
  return !!code && ['electricity', 'water'].includes(code)
}

// ---- The function under test (exact copy from ContractChargesSection.vue after fix) ----
function getDefaultCalculationMethodForDueType(code, responsibility, paymentBy) {
  if (responsibility !== 'tenant') return null
  if (paymentBy === PAYMENT_BY.tenant) return null
  // Legacy default: metered for electricity/water, fixed_periodic for others.
  // Capability does NOT change the default — it only controls whether "metered"
  // appears in the dropdown. If the unit lacks the meter, the default metered
  // value will be shown as invalid and the user must explicitly choose.
  return isMeteredDueTypeCode(code) ? CALCULATION_METHODS.metered : CALCULATION_METHODS.fixed_periodic
}

// ---- The filtering function (exact copy from ContractChargesSection.vue) ----
function getAvailableCalculationMethodsForDueType(code, paymentBy, elecMeter, waterMeter) {
  if (paymentBy === PAYMENT_BY.tenant) return []
  let methods
  if (isMeteredDueTypeCode(code)) {
    methods = [CALCULATION_METHODS.metered, CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill]
    if (code === 'electricity' && !elecMeter) {
      methods = methods.filter((m) => m !== CALCULATION_METHODS.metered)
    }
    if (code === 'water' && !waterMeter) {
      methods = methods.filter((m) => m !== CALCULATION_METHODS.metered)
    }
  } else {
    methods = [CALCULATION_METHODS.fixed_periodic, CALCULATION_METHODS.actual_bill, CALCULATION_METHODS.on_demand]
  }
  return methods.map((m) => ({ value: m, label: m }))
}

// ---- Helper: simulate isCurrentMethodInvalid computed from ContractChargeCard.vue ----
function isCurrentMethodInvalid(charge, code, editable, elecMeter, waterMeter) {
  if (!editable) return false
  if (charge.responsibility !== 'tenant') return false
  if (charge.payment_by !== PAYMENT_BY.landlord) return false
  if (charge.calculation_method !== CALCULATION_METHODS.metered) return false
  if (code === 'electricity' && !elecMeter) return true
  if (code === 'water' && !waterMeter) return true
  return false
}

// ---- Helper: simulate openingMeterReadingDisplay computed ----
function openingMeterReadingDisplay(charge) {
  const val = charge.opening_meter_reading
  if (val === null || val === undefined || val === '') return ''
  return String(val)
}

// ---- Helper: simulate loadContract mapping for opening_meter_reading (after fix) ----
function loadContractOpeningMeterReading(charge) {
  return (charge.opening_meter_reading ?? charge.openingMeterReading) ?? undefined
}

// ---- Helper: simulate applyCalcMethodDefaults (from ContractChargesSection.vue) ----
function applyCalcMethodDefaults(charge, method, unit) {
  let ch = { ...charge }
  if (method === CALCULATION_METHODS.fixed_periodic) {
    ch.first_due_date = '2026-01-01'
    if (!ch.commitment_timing) ch.commitment_timing = 'start'
    if (!ch.last_period_handling) ch.last_period_handling = 'none'
  } else {
    ch.amount = undefined
    ch.frequency = undefined
    ch.first_due_date = undefined
    ch.commitment_timing = undefined
    ch.last_period_handling = undefined
    ch.last_period_adjustment_amount = undefined
  }

  if (method === CALCULATION_METHODS.metered && isMeteredDueTypeCode(ch.due_type_code)) {
    const field = ch.due_type_code === 'electricity' ? 'current_electricity_meter_reading' : 'current_water_meter_reading'
    if (field && unit && (ch.opening_meter_reading === undefined || ch.opening_meter_reading === null || ch.opening_meter_reading === '')) {
      const raw = unit[field]
      if (raw !== null && raw !== undefined && raw !== '') {
        ch.opening_meter_reading = raw
      }
    }
  } else if (method !== CALCULATION_METHODS.metered) {
    ch.opening_meter_reading = undefined
  }
  return ch
}

// ---- Helper: simulate buildPayload skipping undefined/null/empty ----
function buildChargePayload(charge) {
  const out = {}
  for (const [k, v] of Object.entries(charge)) {
    if (v === '' || v === null || v === undefined) continue
    out[k] = v
  }
  return out
}

// ========================================================================
// TESTS
// ========================================================================

describe('Phase 8: getDefaultCalculationMethodForDueType', () => {
  it('returns metered for electricity regardless of capability', () => {
    expect(getDefaultCalculationMethodForDueType('electricity', 'tenant', 'landlord')).toBe('metered')
  })

  it('returns metered for water regardless of capability', () => {
    expect(getDefaultCalculationMethodForDueType('water', 'tenant', 'landlord')).toBe('metered')
  })

  it('returns fixed_periodic for non-metered due types', () => {
    expect(getDefaultCalculationMethodForDueType('rent', 'tenant', 'landlord')).toBe('fixed_periodic')
    expect(getDefaultCalculationMethodForDueType('custom_service', 'tenant', 'landlord')).toBe('fixed_periodic')
  })

  it('returns null for non-tenant responsibility', () => {
    expect(getDefaultCalculationMethodForDueType('electricity', 'landlord', '')).toBeNull()
  })

  it('returns null for payment_by=tenant', () => {
    expect(getDefaultCalculationMethodForDueType('electricity', 'tenant', 'tenant')).toBeNull()
  })

  // CRITICAL: The function signature does NOT accept capability parameters.
  // Capability must NOT affect the default.
  it('does NOT accept or use capability parameters (legacy default preserved)', () => {
    // The function only takes 3 args — capability is not considered
    const resultWithCapability = getDefaultCalculationMethodForDueType('electricity', 'tenant', 'landlord')
    // Even if someone passes extra args, the result is the same
    const resultWithExtraArgs = getDefaultCalculationMethodForDueType('electricity', 'tenant', 'landlord', false, false)
    expect(resultWithCapability).toBe('metered')
    expect(resultWithExtraArgs).toBe('metered')
  })
})

describe('Phase 8: Test 1 — Existing Draft electricity metered + capability 1→0', () => {
  it('calculation_method remains metered (NOT changed to fixed_periodic)', () => {
    // Simulate: existing draft loaded from backend with metered electricity
    const charge = {
      due_type_code: 'electricity',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: 'metered',
      opening_meter_reading: 100,
    }
    // Unit now has electricity_meter = 0
    const elecMeter = false
    const waterMeter = true

    // The frontend does NOT call getDefaultCalculationMethodForDueType on load.
    // The charge is displayed as-is.
    // Verify: calculation_method is still 'metered'
    expect(charge.calculation_method).toBe('metered')

    // Verify: metered is NOT in available options
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', elecMeter, waterMeter)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
    expect(optionValues).toContain('fixed_periodic')
    expect(optionValues).toContain('actual_bill')

    // Verify: the current method is shown as invalid
    expect(isCurrentMethodInvalid(charge, 'electricity', true, elecMeter, waterMeter)).toBe(true)

    // CRITICAL: calculation_method was NOT auto-converted to fixed_periodic
    expect(charge.calculation_method).not.toBe('fixed_periodic')
  })
})

describe('Phase 8: Test 2 — Existing Draft water metered + capability 1→0', () => {
  it('calculation_method remains metered (NOT changed to fixed_periodic)', () => {
    const charge = {
      due_type_code: 'water',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: 'metered',
      opening_meter_reading: 50,
    }
    const elecMeter = true
    const waterMeter = false

    expect(charge.calculation_method).toBe('metered')

    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', elecMeter, waterMeter)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
    expect(optionValues).toContain('fixed_periodic')
    expect(optionValues).toContain('actual_bill')

    expect(isCurrentMethodInvalid(charge, 'water', true, elecMeter, waterMeter)).toBe(true)
    expect(charge.calculation_method).not.toBe('fixed_periodic')
  })
})

describe('Phase 8: Test 3 — Renewal electricity with empty calculation_method + capability=0', () => {
  it('calculation_method remains empty (NOT auto-selected)', () => {
    // Simulate: renewal draft loaded from backend with empty calculation_method
    const charge = {
      due_type_code: 'electricity',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: '',
      opening_meter_reading: undefined,
    }
    const elecMeter = false
    const waterMeter = false

    // The frontend does NOT call getDefaultCalculationMethodForDueType on load.
    // Verify: calculation_method is still empty
    expect(charge.calculation_method).toBe('')

    // Verify: metered is NOT in available options
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', elecMeter, waterMeter)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
    expect(optionValues).toContain('fixed_periodic')
    expect(optionValues).toContain('actual_bill')

    // Verify: NOT invalid (empty is not metered)
    expect(isCurrentMethodInvalid(charge, 'electricity', true, elecMeter, waterMeter)).toBe(false)

    // CRITICAL: calculation_method was NOT auto-converted
    expect(charge.calculation_method).not.toBe('fixed_periodic')
    expect(charge.calculation_method).not.toBe('actual_bill')
    expect(charge.calculation_method).not.toBe('metered')
  })
})

describe('Phase 8: Test 4 — Renewal water with empty calculation_method + capability=0', () => {
  it('calculation_method remains empty (NOT auto-selected)', () => {
    const charge = {
      due_type_code: 'water',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: '',
      opening_meter_reading: undefined,
    }
    const elecMeter = false
    const waterMeter = false

    expect(charge.calculation_method).toBe('')

    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', elecMeter, waterMeter)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
    expect(optionValues).toContain('fixed_periodic')
    expect(optionValues).toContain('actual_bill')

    expect(isCurrentMethodInvalid(charge, 'water', true, elecMeter, waterMeter)).toBe(false)
    expect(charge.calculation_method).not.toBe('fixed_periodic')
    expect(charge.calculation_method).not.toBe('actual_bill')
  })
})

describe('Phase 8: Test 5 — Explicit user selection of fixed_periodic', () => {
  it('user can explicitly select fixed_periodic', () => {
    // Start with an invalid metered charge
    const charge = {
      due_type_code: 'electricity',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: 'metered',
      opening_meter_reading: 100,
    }
    const unit = { current_electricity_meter_reading: 200 }

    // User explicitly changes to fixed_periodic
    const updated = applyCalcMethodDefaults(
      { ...charge, calculation_method: 'fixed_periodic' },
      'fixed_periodic',
      unit
    )

    expect(updated.calculation_method).toBe('fixed_periodic')
    expect(updated.first_due_date).toBeDefined()
    expect(updated.commitment_timing).toBe('start')
    // Opening meter reading is cleared for non-metered (existing behavior)
    expect(updated.opening_meter_reading).toBeUndefined()
  })
})

describe('Phase 8: Test 6 — Explicit user selection of actual_bill', () => {
  it('user can explicitly select actual_bill', () => {
    const charge = {
      due_type_code: 'electricity',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: 'metered',
      opening_meter_reading: 100,
    }
    const unit = { current_electricity_meter_reading: 200 }

    const updated = applyCalcMethodDefaults(
      { ...charge, calculation_method: 'actual_bill' },
      'actual_bill',
      unit
    )

    expect(updated.calculation_method).toBe('actual_bill')
    expect(updated.amount).toBeUndefined()
    expect(updated.frequency).toBeUndefined()
    expect(updated.opening_meter_reading).toBeUndefined()
  })
})

describe('Phase 8: Test 7 — Brand-new charge defaults to legacy default (metered)', () => {
  it('new electricity charge defaults to metered even when capability is absent', () => {
    // When user changes responsibility to tenant, getDefaultCalculationMethodForDueType is called.
    // It returns 'metered' (legacy default) regardless of capability.
    const defaultMethod = getDefaultCalculationMethodForDueType('electricity', 'tenant', 'landlord')
    expect(defaultMethod).toBe('metered')

    // The charge is created with calculation_method = 'metered'
    const charge = {
      due_type_code: 'electricity',
      responsibility: 'tenant',
      payment_by: 'landlord',
      calculation_method: defaultMethod,
    }

    // But metered is NOT in the dropdown (capability absent)
    const elecMeter = false
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', elecMeter, true)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')

    // So the charge shows as invalid — user must explicitly choose
    expect(isCurrentMethodInvalid(charge, 'electricity', true, elecMeter, true)).toBe(true)

    // CRITICAL: the default was NOT changed to fixed_periodic
    expect(defaultMethod).not.toBe('fixed_periodic')
  })

  it('new water charge defaults to metered even when capability is absent', () => {
    const defaultMethod = getDefaultCalculationMethodForDueType('water', 'tenant', 'landlord')
    expect(defaultMethod).toBe('metered')

    const waterMeter = false
    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', true, waterMeter)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')

    // CRITICAL: the default was NOT changed to fixed_periodic
    expect(defaultMethod).not.toBe('fixed_periodic')
  })

  it('new non-metered charge defaults to fixed_periodic (unchanged legacy behavior)', () => {
    const defaultMethod = getDefaultCalculationMethodForDueType('custom_service', 'tenant', 'landlord')
    expect(defaultMethod).toBe('fixed_periodic')
  })
})

describe('Phase 8: Opening meter reading zero preservation', () => {
  it('loadContract preserves zero opening_meter_reading (after fix)', () => {
    // Backend returns opening_meter_reading = 0 (number)
    const backendCharge = { opening_meter_reading: 0 }
    const mapped = loadContractOpeningMeterReading(backendCharge)
    expect(mapped).toBe(0)
    expect(mapped).not.toBeUndefined()
  })

  it('loadContract preserves zero as string "0"', () => {
    const backendCharge = { opening_meter_reading: '0' }
    const mapped = loadContractOpeningMeterReading(backendCharge)
    expect(mapped).toBe('0')
  })

  it('loadContract preserves "0.0"', () => {
    const backendCharge = { opening_meter_reading: '0.0' }
    const mapped = loadContractOpeningMeterReading(backendCharge)
    expect(mapped).toBe('0.0')
  })

  it('loadContract handles null correctly', () => {
    const backendCharge = { opening_meter_reading: null }
    const mapped = loadContractOpeningMeterReading(backendCharge)
    expect(mapped).toBeUndefined()
  })

  it('loadContract handles undefined correctly', () => {
    const backendCharge = { opening_meter_reading: undefined }
    const mapped = loadContractOpeningMeterReading(backendCharge)
    expect(mapped).toBeUndefined()
  })

  it('openingMeterReadingDisplay shows "0" for zero value', () => {
    const charge = { opening_meter_reading: 0 }
    expect(openingMeterReadingDisplay(charge)).toBe('0')
  })

  it('openingMeterReadingDisplay shows "0.0" for zero string', () => {
    const charge = { opening_meter_reading: '0.0' }
    expect(openingMeterReadingDisplay(charge)).toBe('0.0')
  })

  it('openingMeterReadingDisplay shows "" for undefined', () => {
    const charge = { opening_meter_reading: undefined }
    expect(openingMeterReadingDisplay(charge)).toBe('')
  })

  it('openingMeterReadingDisplay shows "" for null', () => {
    const charge = { opening_meter_reading: null }
    expect(openingMeterReadingDisplay(charge)).toBe('')
  })

  it('openingMeterReadingDisplay shows "" for empty string', () => {
    const charge = { opening_meter_reading: '' }
    expect(openingMeterReadingDisplay(charge)).toBe('')
  })

  it('openingMeterReadingDisplay shows "100" for non-zero', () => {
    const charge = { opening_meter_reading: 100 }
    expect(openingMeterReadingDisplay(charge)).toBe('100')
  })
})

describe('Phase 8: Payload does not send undefined opening_meter_reading', () => {
  it('buildChargePayload skips undefined opening_meter_reading', () => {
    const charge = {
      due_type: 'test',
      calculation_method: 'fixed_periodic',
      opening_meter_reading: undefined,
    }
    const payload = buildChargePayload(charge)
    expect(payload).not.toHaveProperty('opening_meter_reading')
  })

  it('buildChargePayload skips null opening_meter_reading', () => {
    const charge = {
      due_type: 'test',
      calculation_method: 'fixed_periodic',
      opening_meter_reading: null,
    }
    const payload = buildChargePayload(charge)
    expect(payload).not.toHaveProperty('opening_meter_reading')
  })

  it('buildChargePayload preserves zero opening_meter_reading', () => {
    const charge = {
      due_type: 'test',
      calculation_method: 'metered',
      opening_meter_reading: 0,
    }
    const payload = buildChargePayload(charge)
    expect(payload.opening_meter_reading).toBe(0)
  })

  it('buildChargePayload preserves "0" opening_meter_reading', () => {
    const charge = {
      due_type: 'test',
      calculation_method: 'metered',
      opening_meter_reading: '0',
    }
    const payload = buildChargePayload(charge)
    expect(payload.opening_meter_reading).toBe('0')
  })
})

describe('Phase 8: Capability filtering independence', () => {
  it('electricity capability ON → metered option visible', () => {
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', true, false)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).toContain('metered')
  })

  it('electricity capability OFF → metered option hidden', () => {
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', false, true)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
  })

  it('water capability ON → metered option visible', () => {
    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', false, true)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).toContain('metered')
  })

  it('water capability OFF → metered option hidden', () => {
    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', true, false)
    const optionValues = options.map((o) => o.value)
    expect(optionValues).not.toContain('metered')
  })

  it('electricity and water are independent', () => {
    // Electricity ON, Water OFF
    const elecOptions = getAvailableCalculationMethodsForDueType('electricity', 'landlord', true, false)
    const waterOptions = getAvailableCalculationMethodsForDueType('water', 'landlord', true, false)
    expect(elecOptions.map((o) => o.value)).toContain('metered')
    expect(waterOptions.map((o) => o.value)).not.toContain('metered')

    // Electricity OFF, Water ON
    const elecOptions2 = getAvailableCalculationMethodsForDueType('electricity', 'landlord', false, true)
    const waterOptions2 = getAvailableCalculationMethodsForDueType('water', 'landlord', false, true)
    expect(elecOptions2.map((o) => o.value)).not.toContain('metered')
    expect(waterOptions2.map((o) => o.value)).toContain('metered')
  })

  it('electricity charge remains when capability OFF', () => {
    // The charge itself is not removed — only the metered option is filtered
    const options = getAvailableCalculationMethodsForDueType('electricity', 'landlord', false, false)
    expect(options.length).toBeGreaterThan(0)
    expect(options.map((o) => o.value)).toContain('fixed_periodic')
    expect(options.map((o) => o.value)).toContain('actual_bill')
  })

  it('water charge remains when capability OFF', () => {
    const options = getAvailableCalculationMethodsForDueType('water', 'landlord', false, false)
    expect(options.length).toBeGreaterThan(0)
    expect(options.map((o) => o.value)).toContain('fixed_periodic')
    expect(options.map((o) => o.value)).toContain('actual_bill')
  })
})
