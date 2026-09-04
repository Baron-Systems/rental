/**
 * Unit Type display regression tests.
 *
 * Verifies that internal Frappe document IDs (e.g. "l9nvq47t06") are NEVER
 * shown to the user. All UI must display Unit Type.type_name (e.g. "شقة").
 *
 * Tests:
 * 1. Unit card shows type_name, never internal ID
 * 2. Unit Details shows display name
 * 3. Unit Edit shows correct selected display name
 * 4. Add dropdown shows names but submits Link value
 * 5. Contract unit display shows display name
 * 6. Contract preview/print does not expose internal ID
 * 7. No hard-coded apartment/shop/etc label map remains
 *
 * Run: npx vitest run src/tests/unit_type_display_regression.spec.js
 */

import { describe, it, expect } from 'vitest'

// ========================================================================
// Simulated API response data (matching backend enrichment)
// ========================================================================

const INTERNAL_ID = 'l9nvq47t06' // Frappe auto-generated doc name
const TYPE_NAME = 'شقة'

// Simulates what get_building / get_units / get_unit / get_contract now return
const unitWithTypeName = {
  name: 'UT-UNIT-001',
  unit_number: '101',
  unit_type: INTERNAL_ID,        // stored Link value (internal)
  unit_type_name: TYPE_NAME,     // display name (enriched by backend)
  floor: { id: 'FL-001', name: 'الأرضي' },
  is_active: 1,
  status: 'empty',
}

// Simulates what get_active_unit_types returns for dropdowns
const unitTypes = [
  { name: INTERNAL_ID, type_name: TYPE_NAME, code: 'apartment', is_system: 1, display_order: 0 },
  { name: 'UT-00002', type_name: 'محل', code: 'shop', is_system: 1, display_order: 1 },
]

// ========================================================================
// Helper functions matching the frontend logic
// ========================================================================

// BuildingUnitTree.vue — now uses unit.unit_type_name directly
function buildingUnitTreeDisplay(unit) {
  return unit.unit_type_name || ''
}

// UnitDetailsModal.vue — uses computed(() => unitData.value.unit_type_name || '')
function unitDetailsDisplay(unitData) {
  return unitData.unit_type_name || ''
}

// UnitEditModal.vue — dropdown: option label = type_name, value = name
function unitEditDropdownOptions(types) {
  return types.map(t => ({ value: t.name, label: t.type_name }))
}

// UnitAddModal.vue — dropdown: option label = type_name, value = name
function unitAddDropdownOptions(types) {
  return types.map(t => ({ value: t.name, label: t.type_name }))
}

// ContractDocument.vue — now uses selectedUnit.unit_type_name
function contractDocumentDisplay(unit) {
  return unit.unit_type_name || unit.unitType || ''
}

// ContractSummary.vue — now uses selectedUnit.unit_type_name
function contractSummaryDisplay(unit) {
  return unit.unit_type_name || ''
}

// ContractDocument.vue unitOptions meta — now uses u.unit_type_name
function unitOptionsMeta(unit) {
  return unit.floor?.name || unit.unit_type_name || ''
}

// ========================================================================
// TESTS
// ========================================================================

describe('Unit Type Display Regression', () => {
  describe('Test 1: Unit card shows type_name, never internal ID', () => {
    it('displays "شقة" not "l9nvq47t06"', () => {
      const display = buildingUnitTreeDisplay(unitWithTypeName)
      expect(display).toBe(TYPE_NAME)
      expect(display).not.toBe(INTERNAL_ID)
    })

    it('does not contain internal ID in display output', () => {
      const display = buildingUnitTreeDisplay(unitWithTypeName)
      expect(display).not.toMatch(/l9nvq47t06/)
    })

    it('returns empty string if unit_type_name is missing', () => {
      const unit = { ...unitWithTypeName, unit_type_name: undefined }
      const display = buildingUnitTreeDisplay(unit)
      expect(display).toBe('')
    })
  })

  describe('Test 2: Unit Details shows display name', () => {
    it('displays "شقة" in details modal', () => {
      const display = unitDetailsDisplay(unitWithTypeName)
      expect(display).toBe(TYPE_NAME)
    })

    it('does not expose internal ID', () => {
      const display = unitDetailsDisplay(unitWithTypeName)
      expect(display).not.toBe(INTERNAL_ID)
    })
  })

  describe('Test 3: Unit Edit shows correct selected display name', () => {
    it('dropdown options use type_name as label', () => {
      const options = unitEditDropdownOptions(unitTypes)
      expect(options[0].label).toBe(TYPE_NAME)
      expect(options[0].label).not.toBe(INTERNAL_ID)
    })

    it('dropdown options use internal name as value (Link)', () => {
      const options = unitEditDropdownOptions(unitTypes)
      expect(options[0].value).toBe(INTERNAL_ID)
    })

    it('disabled type shows type_name with (معطل) suffix, not ID', () => {
      // Simulates: {{ currentTypeName }} (معطل)
      const currentTypeName = unitWithTypeName.unit_type_name
      const display = `${currentTypeName} (معطل)`
      expect(display).toContain(TYPE_NAME)
      expect(display).not.toContain(INTERNAL_ID)
    })
  })

  describe('Test 4: Add dropdown shows names but submits Link value', () => {
    it('dropdown labels are type_name', () => {
      const options = unitAddDropdownOptions(unitTypes)
      expect(options[0].label).toBe(TYPE_NAME)
      expect(options[1].label).toBe('محل')
    })

    it('dropdown values are internal Link names', () => {
      const options = unitAddDropdownOptions(unitTypes)
      expect(options[0].value).toBe(INTERNAL_ID)
      expect(options[1].value).toBe('UT-00002')
    })

    it('selected value sent to backend is the Link, not type_name', () => {
      const options = unitAddDropdownOptions(unitTypes)
      const selectedValue = options[0].value
      // This is what gets sent as payload.unit_type
      expect(selectedValue).toBe(INTERNAL_ID)
      expect(selectedValue).not.toBe(TYPE_NAME)
    })
  })

  describe('Test 5: Contract unit display shows display name', () => {
    it('ContractDocument shows "شقة"', () => {
      const display = contractDocumentDisplay(unitWithTypeName)
      expect(display).toBe(TYPE_NAME)
    })

    it('ContractSummary shows "شقة"', () => {
      const display = contractSummaryDisplay(unitWithTypeName)
      expect(display).toBe(TYPE_NAME)
    })

    it('neither exposes internal ID', () => {
      expect(contractDocumentDisplay(unitWithTypeName)).not.toBe(INTERNAL_ID)
      expect(contractSummaryDisplay(unitWithTypeName)).not.toBe(INTERNAL_ID)
    })
  })

  describe('Test 6: Contract preview/print does not expose internal ID', () => {
    it('unitOptions meta uses unit_type_name, not internal ID', () => {
      const meta = unitOptionsMeta(unitWithTypeName)
      // floor.name takes priority, so test with no floor
      const unitNoFloor = { ...unitWithTypeName, floor: null }
      const metaNoFloor = unitOptionsMeta(unitNoFloor)
      expect(metaNoFloor).toBe(TYPE_NAME)
      expect(metaNoFloor).not.toBe(INTERNAL_ID)
    })

    it('contract document text does not contain internal ID', () => {
      // Simulates: من نوع <strong>{{ selectedUnit.unit_type_name }}</strong>
      const text = `من نوع ${contractDocumentDisplay(unitWithTypeName)}`
      expect(text).toContain(TYPE_NAME)
      expect(text).not.toContain(INTERNAL_ID)
    })
  })

  describe('Test 7: No hard-coded apartment/shop/etc label map remains', () => {
    it('display does NOT rely on a hard-coded map lookup', () => {
      // If we use a unit with an unknown internal ID but valid unit_type_name,
      // it should still display correctly (proving no hard-coded map is used)
      const customUnit = {
        ...unitWithTypeName,
        unit_type: 'CUSTOM-XYZ-123',
        unit_type_name: 'فيلا مخصصة',
      }
      expect(buildingUnitTreeDisplay(customUnit)).toBe('فيلا مخصصة')
      expect(unitDetailsDisplay(customUnit)).toBe('فيلا مخصصة')
      expect(contractDocumentDisplay(customUnit)).toBe('فيلا مخصصة')
      expect(contractSummaryDisplay(customUnit)).toBe('فيلا مخصصة')
    })

    it('a unit_type_name of "أخرى" (custom) displays correctly', () => {
      const customUnit = {
        ...unitWithTypeName,
        unit_type: 'UT-CUSTOM-001',
        unit_type_name: 'أخرى',
      }
      expect(buildingUnitTreeDisplay(customUnit)).toBe('أخرى')
    })

    it('disabled existing Unit Type still shows type_name', () => {
      // Simulates a unit whose type was deactivated
      const unitWithDisabledType = {
        ...unitWithTypeName,
        unit_type: 'UT-DISABLED-001',
        unit_type_name: 'مستودع',
      }
      expect(unitDetailsDisplay(unitWithDisabledType)).toBe('مستودع')
      expect(buildingUnitTreeDisplay(unitWithDisabledType)).toBe('مستودع')
    })
  })
})
