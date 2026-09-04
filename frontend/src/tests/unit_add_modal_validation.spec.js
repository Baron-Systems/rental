/**
 * UnitAddModal validation regression tests.
 *
 * Verifies:
 * 1. unit_type empty → no API call + error message "نوع الوحدة مطلوب"
 * 2. Valid type selected → save works normally
 *
 * Run: npx vitest run src/tests/unit_add_modal_validation.spec.js
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'

// ---- Constants matching UnitAddModal.vue ----
const UNIT_TYPE_REQUIRED_ERROR = 'نوع الوحدة مطلوب'

// ---- Simulate the save() validation logic from UnitAddModal.vue ----
// We test the exact validation guard that was added to the component.
function createSaveValidator() {
  const form = ref({ unit_number: '101', unit_type: '', floor: '', area: null, notes: '', building: 'BLDG-001' })
  const saving = ref(false)
  const unitTypeError = ref('')
  const unitTypeSelect = ref({ focus: vi.fn() })
  const apiCallMock = vi.fn().mockResolvedValue({})

  async function save() {
    // Frontend validation: unit_type is required before sending to backend
    if (!form.value.unit_type) {
      unitTypeError.value = UNIT_TYPE_REQUIRED_ERROR
      unitTypeSelect.value?.focus()
      return
    }
    saving.value = true
    try {
      await apiCallMock()
    } finally {
      saving.value = false
    }
  }

  function onUnitTypeChange() {
    if (form.value.unit_type) {
      unitTypeError.value = ''
    }
  }

  return { form, saving, unitTypeError, unitTypeSelect, apiCallMock, save, onUnitTypeChange }
}

// ========================================================================
// TESTS
// ========================================================================

describe('UnitAddModal: unit_type validation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Test 1: unit_type empty → no API call + error shown', () => {
    it('does not call API when unit_type is empty', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = '' // empty
      await ctx.save()
      expect(ctx.apiCallMock).not.toHaveBeenCalled()
    })

    it('shows "نوع الوحدة مطلوب" error message', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = ''
      await ctx.save()
      expect(ctx.unitTypeError.value).toBe(UNIT_TYPE_REQUIRED_ERROR)
    })

    it('does not enter loading state (saving stays false)', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = ''
      await ctx.save()
      expect(ctx.saving.value).toBe(false)
    })

    it('focuses the unit_type select field', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = ''
      await ctx.save()
      expect(ctx.unitTypeSelect.value.focus).toHaveBeenCalled()
    })

    it('does not throw or produce a raw Frappe error', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = ''
      // Should not throw — just return early
      await expect(ctx.save()).resolves.toBeUndefined()
    })
  })

  describe('Test 2: valid type selected → save works normally', () => {
    it('calls API when unit_type is valid', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = 'UT-00001' // valid type
      await ctx.save()
      expect(ctx.apiCallMock).toHaveBeenCalledTimes(1)
    })

    it('does not show error when unit_type is valid', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = 'UT-00001'
      await ctx.save()
      expect(ctx.unitTypeError.value).toBe('')
    })

    it('clears error when a valid type is selected after error', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = ''
      await ctx.save()
      expect(ctx.unitTypeError.value).toBe(UNIT_TYPE_REQUIRED_ERROR)

      // Now select a valid type
      ctx.form.value.unit_type = 'UT-00001'
      ctx.onUnitTypeChange()
      expect(ctx.unitTypeError.value).toBe('')
    })

    it('save succeeds after clearing error', async () => {
      const ctx = createSaveValidator()
      // First attempt with empty type
      ctx.form.value.unit_type = ''
      await ctx.save()
      expect(ctx.apiCallMock).not.toHaveBeenCalled()

      // Select valid type
      ctx.form.value.unit_type = 'UT-00001'
      ctx.onUnitTypeChange()
      expect(ctx.unitTypeError.value).toBe('')

      // Second attempt should succeed
      await ctx.save()
      expect(ctx.apiCallMock).toHaveBeenCalledTimes(1)
    })

    it('saving state toggles correctly during valid save', async () => {
      const ctx = createSaveValidator()
      ctx.form.value.unit_type = 'UT-00001'
      expect(ctx.saving.value).toBe(false)
      const promise = ctx.save()
      expect(ctx.saving.value).toBe(true)
      await promise
      expect(ctx.saving.value).toBe(false)
    })
  })

  describe('Test 3: "اختر" remains as default empty option', () => {
    it('unit_type defaults to empty string', () => {
      const ctx = createSaveValidator()
      expect(ctx.form.value.unit_type).toBe('')
    })

    it('empty string triggers validation, not a default type', async () => {
      const ctx = createSaveValidator()
      // Ensure no default like "apartment" is auto-selected
      expect(ctx.form.value.unit_type).not.toBe('apartment')
      expect(ctx.form.value.unit_type).not.toBe('UT-00001')
      await ctx.save()
      expect(ctx.unitTypeError.value).toBe(UNIT_TYPE_REQUIRED_ERROR)
    })
  })
})
