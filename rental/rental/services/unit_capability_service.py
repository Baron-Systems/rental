"""Central capability helper for meter capabilities.

Capabilities are determined by Unit Attribute Value records where:
1. A System Attribute with ``capability_code`` exists and is active
2. The unit has a Unit Attribute Value for that attribute with ``value_check=1``

Capabilities do NOT depend on:
- Meter number fields (electricity_meter_number, water_meter_number)
- Current meter readings
- Unit type attribute mappings

This module provides:
- ``unit_has_capability(unit, capability_code)`` — core check
- ``unit_has_electricity_meter(unit)`` — convenience
- ``unit_has_water_meter(unit)`` — convenience
- ``can_use_metered_for_due_type(unit, due_type_code)`` — map due_type → capability
- ``has_blocking_metered_contract(unit, due_type_code)`` — for removal protection
- ``validate_capability_removal(unit, capability_code)`` — throw on protected removal
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import to_calendar_day


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METER_CAPABILITY_CODES = {
	"electricity_meter": "electricity",
	"water_meter": "water",
}

# Reverse map: due_type_code → capability_code
CAPABILITY_TO_DUE_TYPE = {
	"electricity": "electricity_meter",
	"water": "water_meter",
}


# ---------------------------------------------------------------------------
# Core capability checks
# ---------------------------------------------------------------------------


def unit_has_capability(unit_name: str, capability_code: str) -> bool:
	"""True only if:
	1. A System Attribute with capability_code exists and is active
	2. The unit has a Unit Attribute Value for that attribute with value_check=1

	Does NOT depend on meter number, current reading, or unit type mapping.
	"""
	attr = frappe.db.get_value(
		"Unit Attribute",
		{"capability_code": capability_code, "is_system": 1, "is_active": 1},
		["name", "data_type"],
		as_dict=True,
	)
	if not attr or attr.data_type != "Check":
		return False

	val = frappe.db.get_value(
		"Unit Attribute Value",
		{"unit": unit_name, "attribute": attr.name},
		"value_check",
	)
	return bool(val)


def unit_has_electricity_meter(unit_name: str) -> bool:
	"""Convenience: check electricity_meter capability."""
	return unit_has_capability(unit_name, "electricity_meter")


def unit_has_water_meter(unit_name: str) -> bool:
	"""Convenience: check water_meter capability."""
	return unit_has_capability(unit_name, "water_meter")


def can_use_metered_for_due_type(unit_name: str, due_type_code: str) -> bool:
	"""Map due_type_code to capability and check.

	Returns False for non-metered due types (rent, custom types).
	"""
	cap = CAPABILITY_TO_DUE_TYPE.get(due_type_code)
	if not cap:
		return False
	return unit_has_capability(unit_name, cap)


# ---------------------------------------------------------------------------
# Blocking contract check (for capability removal protection)
# ---------------------------------------------------------------------------


def has_blocking_metered_contract(unit_name: str, due_type_code: str) -> bool:
	"""Check if an approved metered contract still depends on this capability.

	Blocks capability removal ONLY when the unit has an approved metered
	contract that still needs the capability:

	- **current approved metered** → BLOCK
	  (status=active, start_date <= today, end_date >= today)
	- **future approved metered** → BLOCK
	  (status=active, start_date > today)

	Does NOT block for:
	- Draft (not yet approved)
	- Cancelled (no longer active)
	- Evicted (no longer active)
	- Expired (no longer active)
	- Archived (is_archived=1)

	Charge filters match ``has_active_metered_contract``:
	- responsibility = "tenant"
	- payment_by in ["landlord", None]
	- calculation_method = "metered"
	"""
	due_type_name = frappe.db.get_value(
		"Rental Due Type",
		{"due_type_code": due_type_code},
		"name",
	)
	if not due_type_name:
		return False

	today = to_calendar_day(frappe.utils.today())

	# Find active, non-archived contracts for this unit.
	# "active" status means approved by the landlord.
	# This covers both current (start_date <= today) and future (start_date > today).
	contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": unit_name,
			"status": "active",
			"is_archived": 0,
		},
		fields=["name"],
	)

	for c in contracts:
		charges = frappe.get_all(
			"Contract Charge",
			filters={
				"parent": c.name,
				"parenttype": "Lease Contract",
				"due_type": due_type_name,
				"responsibility": "tenant",
				"payment_by": ["in", ["landlord", None]],
				"calculation_method": "metered",
			},
			fields=["name"],
		)
		if charges:
			return True

	return False


def validate_capability_removal(unit_name: str, capability_code: str) -> None:
	"""Throw if trying to remove a capability while a blocking contract exists."""
	due_type_code = METER_CAPABILITY_CODES.get(capability_code)
	if not due_type_code:
		return

	if has_blocking_metered_contract(unit_name, due_type_code):
		frappe.throw(
			frappe._(
				"Cannot remove meter capability '{0}' because this unit has an active "
				"or future-approved metered contract using this due type."
			).format(capability_code),
			frappe.ValidationError,
		)
