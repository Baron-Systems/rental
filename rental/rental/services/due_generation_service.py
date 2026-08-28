"""Due generation: rent dues, fixed-periodic dues, regenerate/cancel future.

Ported from ``src/services/due-generation.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import (
	to_calendar_day,
	build_periodic_schedule,
	round_money,
)


# ---------------------------------------------------------------------------
# Ensure system due types exist  (source: ensureSystemDueTypes)
# ---------------------------------------------------------------------------


def ensure_system_due_types() -> None:
	"""Ensure rent, electricity, water system due types exist.

	Source: ``ensureSystemDueTypes`` (system-due-types.ts:39-91).
	C7: 4-step lookup (by code+isSystem, by name+isSystem, by code any, by name any)
	then claim/update existing or create new.
	C8: Arabic names (إيجار, كهرباء, مياه).
	"""
	system_types = [
		{"due_type_name": "إيجار", "due_type_code": "rent"},
		{"due_type_name": "كهرباء", "due_type_code": "electricity"},
		{"due_type_name": "مياه", "due_type_code": "water"},
	]

	for st in system_types:
		# 1. Find by code + isSystem
		existing = frappe.db.get_value(
			"Rental Due Type",
			{"due_type_code": st["due_type_code"], "is_system": 1},
			["name", "due_type_name", "due_type_code", "is_system", "is_active"],
			as_dict=True,
		)

		# 2. Find by name + isSystem
		if not existing:
			existing = frappe.db.get_value(
				"Rental Due Type",
				{"due_type_name": st["due_type_name"], "is_system": 1},
				["name", "due_type_name", "due_type_code", "is_system", "is_active"],
				as_dict=True,
			)

		# 3. Find by code (any isSystem)
		if not existing:
			existing = frappe.db.get_value(
				"Rental Due Type",
				{"due_type_code": st["due_type_code"]},
				["name", "due_type_name", "due_type_code", "is_system", "is_active"],
				as_dict=True,
			)

		# 4. Find by name (any isSystem)
		if not existing:
			existing = frappe.db.get_value(
				"Rental Due Type",
				{"due_type_name": st["due_type_name"]},
				["name", "due_type_name", "due_type_code", "is_system", "is_active"],
				as_dict=True,
			)

		if not existing:
			frappe.get_doc({
				"doctype": "Rental Due Type",
				"due_type_name": st["due_type_name"],
				"due_type_code": st["due_type_code"],
				"is_system": 1,
				"rental_account": None,
				"is_active": 1,
			}).insert(ignore_permissions=True)
		else:
			# Claim/update existing record to be the system type
			updates = {}
			if not existing.is_system:
				updates["is_system"] = 1
			if not existing.is_active:
				updates["is_active"] = 1
			if existing.due_type_code != st["due_type_code"]:
				updates["due_type_code"] = st["due_type_code"]
			if existing.due_type_name != st["due_type_name"]:
				updates["due_type_name"] = st["due_type_name"]
			if updates:
				frappe.db.set_value("Rental Due Type", existing.name, updates, update_modified=False)


# ---------------------------------------------------------------------------
# Get rent due type  (source: system due type lookup)
# ---------------------------------------------------------------------------


def get_rent_due_type() -> str:
	"""Return the name of the rent DueType."""
	ensure_system_due_types()
	name = frappe.db.get_value("Rental Due Type", {"due_type_code": "rent"}, "name")
	if not name:
		frappe.throw(frappe._("System 'rent' due type not found."))
	return name


# ---------------------------------------------------------------------------
# Generate rent dues  (source: generateContractDues)
# ---------------------------------------------------------------------------


def generate_contract_dues(contract_doc, account: str, generate: bool = True) -> int:
	"""Create rent Due rows for the contract.

	Uses firstDueDate or startDate, paymentFrequency, commitmentTiming.
	Status approved (docstatus=1), sourceType='auto_contract', calculationMethod='fixed_periodic'.
	Throws if any auto_contract dues already exist.

	Returns the number of dues created.
	"""
	if not generate:
		return 0

	# Check for existing auto_contract dues
	existing = frappe.db.exists(
		"Rental Due",
		{
			"contract": contract_doc.name,
			"source_type": "auto_contract",
		},
	)
	if existing:
		frappe.throw(frappe._("Auto-contract dues already exist for this contract."))

	rent_due_type = get_rent_due_type()

	schedule = build_periodic_schedule(
		start_date=contract_doc.start_date,
		end_date=contract_doc.end_date,
		frequency=contract_doc.payment_frequency,
		amount=contract_doc.rent_amount,
		commitment_timing=contract_doc.commitment_timing or "start",
		first_due_date=contract_doc.first_due_date,
	)

	created = 0
	for item in schedule:
		_create_auto_due(
			contract_doc=contract_doc,
			due_type=rent_due_type,
			account=account,
			due_date=item["due_date"],
			period_start=item["period_start"],
			period_end=item["period_end"],
			period_label=item["period_label"],
			amount=item["amount"],
			calculation_method="fixed_periodic",
			description=f"إيجار - {item['period_label']}",
		)
		created += 1

	return created


# ---------------------------------------------------------------------------
# Create due from schedule  (used by fixed-periodic generation)
# ---------------------------------------------------------------------------


def create_due_from_schedule(contract_doc, charge, schedule_item, account, calculation_method="fixed_periodic"):
	"""Create an auto_contract due from a schedule item (for fixed-periodic charges)."""
	_create_auto_due(
		contract_doc=contract_doc,
		due_type=charge.due_type,
		account=account,
		due_date=schedule_item["due_date"],
		period_start=schedule_item["period_start"],
		period_end=schedule_item["period_end"],
		period_label=schedule_item["period_label"],
		amount=schedule_item["amount"],
		calculation_method=calculation_method,
		description=f"{frappe.db.get_value('Rental Due Type', charge.due_type, 'due_type_name')} - {schedule_item['period_label']}",
	)


def _create_auto_due(
	contract_doc,
	due_type,
	account,
	due_date,
	period_start,
	period_end,
	period_label,
	amount,
	calculation_method,
	description,
):
	"""Create a single auto_contract due (submitted/approved)."""
	from rental.rental.doctype.rental_settings.rental_settings import generate_due_number

	due_number = generate_due_number(account)

	due = frappe.get_doc({
		"doctype": "Rental Due",
		"rental_account": account,
		"due_number": due_number,
		"tenant": contract_doc.tenant,
		"contract": contract_doc.name,
		"building": contract_doc.building,
		"unit": contract_doc.unit,
		"due_type": due_type,
		"transaction_date": due_date,
		"due_date": due_date,
		"period_label": period_label,
		"period_start": period_start,
		"period_end": period_end,
		"description": description,
		"amount": round_money(amount),
		"calculation_method": calculation_method,
		"source_type": "auto_contract",
		"reference_number": contract_doc.contract_number,
		"docstatus": 1,  # Auto-approved
	})
	due.insert(ignore_permissions=True)
	# Submit immediately
	due.submit()


# ---------------------------------------------------------------------------
# Regenerate future dues  (source: regenerateFutureDues)
# ---------------------------------------------------------------------------


def regenerate_future_dues(contract_name: str, new_rent: float, from_date=None) -> int:
	"""Update amount and description of future auto_contract dues from from_date.

	Source: ``regenerateFutureDues`` (due-generation.service.ts:104-139).
	Updates ALL auto_contract dues (not just rent) with transactionDate >= fromDate.
	Appends " (تعديل قيمة الإيجار)" to the existing description.
	Returns the number of dues updated.
	"""
	filters = {
		"contract": contract_name,
		"source_type": "auto_contract",
		"docstatus": 1,
	}

	if from_date:
		# A21: legacy uses transaction_date (not due_date).
		filters["transaction_date"] = [">=", to_calendar_day(from_date)]

	future_dues = frappe.get_all("Rental Due", filters=filters, fields=["name", "description"])

	count = 0
	for d in future_dues:
		# A21: append to existing description (legacy line 137).
		existing_desc = d.description or ""
		new_desc = f"{existing_desc} (تعديل قيمة الإيجار)"
		frappe.db.set_value("Rental Due", d.name, {
			"amount": round_money(new_rent),
			"description": new_desc,
		}, update_modified=False)
		count += 1

	return count


# ---------------------------------------------------------------------------
# Cancel future dues  (source: cancelFutureDues)
# ---------------------------------------------------------------------------


def cancel_future_dues(contract_name: str, from_date, reason: str, cancelled_by: str = None) -> int:
	"""Set future auto_contract dues to cancelled.

	Returns the number of dues cancelled.
	"""
	from_date = to_calendar_day(from_date)

	future_dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": contract_name,
			"source_type": "auto_contract",
			"docstatus": 1,
			# A22: legacy uses >= (inclusive), not > (strict).
			"transaction_date": [">=", from_date],
		},
		fields=["name"],
	)

	count = 0
	for d in future_dues:
		due = frappe.get_doc("Rental Due", d.name)
		if due.docstatus == 1:
			due.cancel()
			frappe.db.set_value("Rental Due", d.name, {
				"cancellation_reason": reason,
				"cancelled_by": cancelled_by,
			}, update_modified=False)
			count += 1

	return count
