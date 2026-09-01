"""Cancel manual dues and rollback meter readings.

Ported from ``src/services/cancellation.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.services.contract_charge_service import get_meter_field
from rental.rental.services.archive_service import ensure_contract_not_archived


def cancel_due(due_name: str, reason: str, cancelled_by: str):
	"""Cancel a manual/metered due and roll back unit meter readings.

	Source: ``cancelDue`` (cancellation.service.ts:6-85).
	- Only manual source types can be cancelled.
	- For metered dues: block if a newer approved meter reading exists;
	  otherwise roll back to the previous approved reading, or to the
	  contract charge's opening_meter_reading if none.
	"""
	# Check due exists (legacy line 12, cancel/route.ts:32)
	if not frappe.db.exists("Rental Due", due_name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", due_name)

	# Check not already cancelled (legacy line 13, cancel/route.ts:33)
	if due.docstatus == 2:
		frappe.throw(frappe._("الالتزام ملغي مسبقاُ"))

	# Archive protection — blocks cancelling dues of archived contracts
	# (defense-in-depth for direct backend calls).
	ensure_contract_not_archived(due.contract, action="إلغاء التزام")

	# Only manual source types can be cancelled (legacy line 14)
	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("لا يمكن إلغاء الالتزامات الناتجة من العقود فرديًا"))

	# B1: metered rollback logic (legacy lines 19-71).
	is_meter_due = due.calculation_method == "metered"
	if is_meter_due and due.contract and due.unit and due.current_meter_reading:
		_rollback_meter(due, due_name)

	# Cancel the due
	due.cancel()

	# Set cancellation metadata (legacy lines 73-81)
	frappe.db.set_value("Rental Due", due_name, {
		"cancellation_reason": reason,
		"cancelled_by": cancelled_by,
		"cancelled_at": frappe.utils.now(),
	}, update_modified=False)

	return frappe.get_doc("Rental Due", due_name)


def _rollback_meter(due, due_name: str):
	"""Roll back the unit meter to the previous reading.

	Source: cancellation.service.ts:22-71.
	1. Find newer approved due with meter reading; block if exists.
	2. Find previous approved due with meter reading for rollback value.
	3. Fall back to contract charge opening_meter_reading.
	4. Update the unit meter field (only if field exists).
	"""
	dt_code = frappe.db.get_value("Rental Due Type", due.due_type, "due_type_code")
	field = get_meter_field(dt_code)

	# 1. Check for newer approved dues with meter readings (block if found).
	# Legacy orders by [transactionDate desc, createdAt desc].
	newer_dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": due.contract,
			"unit": due.unit,
			"due_type": due.due_type,
			"name": ["!=", due_name],
			"current_meter_reading": ["is", "set"],
			"docstatus": 1,
		},
		fields=["name", "transaction_date", "creation", "current_meter_reading"],
		order_by="transaction_date desc, creation desc",
		limit=1,
	)

	if newer_dues:
		newer = newer_dues[0]
		newer_date = frappe.utils.getdate(newer.transaction_date)
		due_date = frappe.utils.getdate(due.transaction_date)
		is_newer = newer_date > due_date or (
			newer_date == due_date and newer.creation > due.creation
		)
		if is_newer:
			frappe.throw(frappe._("لا يمكن إلغاء الالتزام لوجود حركة عداد أحدث"))

	# 2. Find previous approved due with meter reading for rollback value.
	previous_dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": due.contract,
			"unit": due.unit,
			"due_type": due.due_type,
			"name": ["!=", due_name],
			"current_meter_reading": ["is", "set"],
			"docstatus": 1,
		},
		fields=["name", "current_meter_reading"],
		order_by="transaction_date desc, creation desc",
		limit=1,
	)

	new_reading = None
	if previous_dues and previous_dues[0].current_meter_reading is not None:
		new_reading = previous_dues[0].current_meter_reading
	else:
		# 3. Fall back to contract charge opening_meter_reading.
		charge = frappe.db.get_value(
			"Contract Charge",
			{"parent": due.contract, "parenttype": "Lease Contract", "due_type": due.due_type},
			"opening_meter_reading",
		)
		if charge:
			new_reading = charge

	# 4. Update the unit meter field (legacy line 65: if (field && newReading !== null)).
	if field and new_reading is not None:
		frappe.db.set_value(
			"Rental Unit", due.unit, field,
			new_reading, update_modified=False,
		)
