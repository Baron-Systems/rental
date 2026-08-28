"""Unit action permissions engine.

Ported from ``src/services/unit-permissions.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import to_calendar_day
from rental.rental.services.contract_charge_service import has_active_metered_contract


# ---------------------------------------------------------------------------
# Get unit action permissions  (source: getUnitActionPermissions)
# ---------------------------------------------------------------------------


def get_unit_action_permissions(unit_name: str) -> dict:
	"""Return the full permissions object for a unit.

	Source: ``getUnitActionPermissions``.
	"""
	unit = frappe.db.get_value(
		"Rental Unit", unit_name,
		["name", "is_active", "building", "rental_account"],
		as_dict=True,
	)
	if not unit:
		return {
			"can_edit": False,
			"editable_fields": [],
			"can_disable": False,
			"can_delete": False,
			"can_reactivate": False,
			"can_create_contract": False,
			"reasons": {
				"edit": "الوحدة غير موجودة",
				"disable": "الوحدة غير موجودة",
				"delete": "الوحدة غير موجودة",
				"reactivate": "الوحدة غير موجودة",
				"create_contract": "الوحدة غير موجودة",
			},
		}

	# building?.isActive ?? false  →  default False when building is null
	building_active = False
	if unit.building:
		building_active = bool(frappe.db.get_value("Rental Building", unit.building, "is_active"))

	# Count related records
	contracts_count = 0
	evictions_count = 0
	dues_count = 0
	receipts_count = 0

	if frappe.db.exists("DocType", "Lease Contract"):
		contracts_count = frappe.db.count("Lease Contract", {"unit": unit_name})
	if frappe.db.exists("DocType", "Rental Eviction"):
		evictions_count = frappe.db.count("Rental Eviction", {"unit": unit_name})
	if frappe.db.exists("DocType", "Rental Due"):
		dues_count = frappe.db.count("Rental Due", {"unit": unit_name})
	if frappe.db.exists("DocType", "Rental Receipt"):
		receipts_count = frappe.db.count("Rental Receipt", {"unit": unit_name})

	has_any_history = (contracts_count + evictions_count + dues_count + receipts_count) > 0
	has_occupancy = _has_occupying_or_upcoming_contract(unit_name)

	# can_delete: true only if all counts are zero
	can_delete = not has_any_history

	# can_disable: unit active and no current/upcoming/expired-not-closed/cancelled-after-start contract
	can_disable = unit.is_active and not has_occupancy

	# can_reactivate: unit inactive and building active
	can_reactivate = (not unit.is_active) and building_active

	# can_create_contract: unit active and building active
	can_create_contract = unit.is_active and building_active

	# editable_fields
	editable_fields = _get_editable_fields(unit_name, contracts_count)

	# Build reasons (Arabic) — starts empty, keys added only when condition fails
	reasons: dict = {}

	if not can_delete:
		reasons["delete"] = "لا يمكن حذف وحدة تحتوي على سجلات استخدام (عقود، إخلاء، مستحقات، أو تحصيلات)"

	if not can_disable:
		if not unit.is_active:
			reasons["disable"] = "الوحدة معطلة مسبقاً"
		elif has_occupancy:
			reasons["disable"] = "لا يمكن تعطيل الوحدة لوجود عقد قائم، حجز مستقبلي، أو احتلال فعلي (عقد منتهي/ملغي لم يُخلاً)"

	if not can_reactivate:
		if unit.is_active:
			reasons["reactivate"] = "الوحدة نشطة مسبقاً"
		elif not building_active:
			reasons["reactivate"] = "لا يمكن تفعيل الوحدة لأن العقار التابع لها معطل"

	if not can_create_contract:
		if not unit.is_active:
			reasons["create_contract"] = "الوحدة معطلة ولا يمكن اعتماد عقود جديدة فيها"
		elif not building_active:
			reasons["create_contract"] = "العقار معطل ولا يمكن اعتماد عقود جديدة فيه"

	return {
		"can_edit": True,
		"editable_fields": editable_fields,
		"can_disable": can_disable,
		"can_reactivate": can_reactivate,
		"can_delete": can_delete,
		"can_create_contract": can_create_contract,
		"reasons": reasons,
	}


def _has_occupying_or_upcoming_contract(unit_name: str) -> bool:
	"""Check if unit has any occupying or upcoming contract."""
	if not frappe.db.exists("DocType", "Lease Contract"):
		return False

	today = to_calendar_day(frappe.utils.today())

	# Current active
	if frappe.db.exists("Lease Contract", {
		"unit": unit_name, "status": "active",
		"start_date": ["<=", today], "end_date": [">=", today],
	}):
		return True

	# Expired not closed
	if frappe.db.exists("Lease Contract", {
		"unit": unit_name, "status": "expired",
		"is_historical": 0, "closed_by_renewal_at": ["is", "not set"],
		"start_date": ["<=", today],
	}):
		return True

	# Cancelled after start — only the most recent cancelled contract (source: findFirst orderBy cancelledAt desc)
	cancelled = frappe.get_all(
		"Lease Contract",
		filters={"unit": unit_name, "status": "cancelled", "cancelled_at": ["is", "set"]},
		fields=["cancelled_at", "start_date"],
		order_by="cancelled_at desc",
		limit=1,
	)
	if cancelled:
		c = cancelled[0]
		if to_calendar_day(c.cancelled_at) >= to_calendar_day(c.start_date):
			return True

	# Upcoming active
	if frappe.db.exists("Lease Contract", {
		"unit": unit_name, "status": "active",
		"start_date": [">", today],
	}):
		return True

	return False


def get_editable_fields(unit_name: str) -> list[str]:
	"""Public wrapper for _get_editable_fields."""
	contracts_count = 0
	if frappe.db.exists("DocType", "Lease Contract"):
		contracts_count = frappe.db.count("Lease Contract", {"unit": unit_name})
	return _get_editable_fields(unit_name, contracts_count)


def _get_editable_fields(unit_name: str, contracts_count: int) -> list[str]:
	"""Return the list of editable fields based on contract history."""
	# Always editable descriptive fields
	fields = ["unit_type", "area", "rooms_count", "bathrooms_count", "notes"]

	# Identity fields only if no contracts
	if contracts_count == 0:
		fields.extend(["unit_number", "building", "floor"])

	# Meter reading fields only if no active metered contract
	if not has_active_metered_contract(unit_name, "electricity"):
		fields.append("current_electricity_meter_reading")
	if not has_active_metered_contract(unit_name, "water"):
		fields.append("current_water_meter_reading")

	return fields
