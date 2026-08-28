import frappe

from rental.rental.utils.date_utils import to_calendar_day


def derive_unit_status(unit_doc) -> str:
	"""Pure calculation of unit status. No DB saves or db_set.

	Ported from ``recalculateUnitStatus`` in ``src/services/contract-validation.ts``.

	Algorithm:
	0. Manually marked unavailable → unavailable (overrides everything)
	1. Current active contract (start <= today <= end) → rented
	2. Expired contract (not historical, not closed by renewal, latest end_date) → rented
	3. Cancelled contract with cancelledAt >= startDate → rented (matches source: contract-validation.ts)
	4. Upcoming active contract (start > today) → reserved
	5. Default → empty
	"""
	# 0. Manual override
	if unit_doc.get("is_manually_unavailable"):
		return "unavailable"

	if not frappe.db.exists("DocType", "Lease Contract"):
		return "empty"

	today = to_calendar_day(frappe.utils.today())
	unit_name = unit_doc.get("name")

	if unit_name:
		# 1. Current active contract
		current = frappe.db.exists(
			"Lease Contract",
			{
				"unit": unit_name,
				"status": "active",
				"start_date": ["<=", today],
				"end_date": [">=", today],
			},
		)
		if current:
			return "rented"

		# 2. Expired contract that is NOT historical and NOT closed by renewal
		expired = frappe.get_all(
			"Lease Contract",
			filters={
				"unit": unit_name,
				"status": "expired",
				"start_date": ["<=", today],
				"is_historical": 0,
				"closed_by_renewal_at": ["is", "not set"],
			},
			fields=["name"],
			order_by="end_date desc",
			limit=1,
		)
		if expired:
			return "rented"

		# 3. Cancelled contract that already started (cancelledAt >= startDate) → rented
		cancelled = frappe.get_all(
			"Lease Contract",
			filters={
				"unit": unit_name,
				"status": "cancelled",
				"cancelled_at": ["is", "set"],
			},
			fields=["name", "cancelled_at", "start_date"],
			order_by="cancelled_at desc",
			limit=1,
		)
		if cancelled:
			c = cancelled[0]
			cancelled_at = to_calendar_day(c.cancelled_at)
			start_date = to_calendar_day(c.start_date)
			if cancelled_at >= start_date:
				return "rented"

		# 4. Upcoming active contract
		upcoming = frappe.db.exists(
			"Lease Contract",
			{
				"unit": unit_name,
				"status": "active",
				"start_date": [">", today],
			},
		)
		if upcoming:
			return "reserved"

	return "empty"


def recalculate_unit_status(unit_name: str) -> str:
	"""External function for use after contract lifecycle operations.

	Loads unit doc, derives status, and updates DB directly (no save cycle).
	"""
	unit_doc = frappe.get_doc("Rental Unit", unit_name)
	derived = derive_unit_status(unit_doc)
	frappe.db.set_value("Rental Unit", unit_name, "status", derived, update_modified=False)
	return derived


def update_building_counts(building_name: str) -> None:
	"""Update floors_count and units_count on the building record.

	Called after Floor/Unit lifecycle events (insert, delete).
	"""
	floor_count = frappe.db.count("Rental Floor", {"building": building_name})
	unit_count = frappe.db.count("Rental Unit", {"building": building_name})
	frappe.db.set_value("Rental Building", building_name, "floors_count", floor_count, update_modified=False)
	frappe.db.set_value("Rental Building", building_name, "units_count", unit_count, update_modified=False)
