"""Dues API: CRUD, approve, cancel, waivers.

Ported from ``src/app/api/dues/**``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager
from rental.rental.utils.date_utils import to_calendar_day, round_money
from rental.rental.services.contract_charge_service import (
	get_previous_meter_reading,
	can_create_meter_due,
)
from rental.rental.services.cancellation_service import cancel_due


# ---------------------------------------------------------------------------
# List due types  (source: GET /api/due-types)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_due_types(active_only=0):
	"""List all due types for the current account (plus system due types).

	Source: ``GET /api/due-types`` — used by statement filter dropdown.
	"""
	account = get_current_rental_account()
	filters = {}
	if account:
		filters["rental_account"] = ["in", [account, None, ""]]
	if int(active_only):
		filters["is_active"] = 1
	return frappe.get_all(
		"Rental Due Type",
		filters=filters,
		fields=["name", "due_type_name", "due_type_code", "is_system", "is_active"],
		order_by="due_type_name asc",
	)


# ---------------------------------------------------------------------------
# List dues  (source: GET /api/dues)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_dues(
	tenant=None,
	contract=None,
	due_type=None,
	status=None,
	source_type=None,
	search=None,
	from_date=None,
	to_date=None,
	print=0,
	page=1,
	limit=15,
):
	"""List dues with filters, pagination, and stats."""
	account = get_current_rental_account()

	filters = {}
	if account:
		filters["rental_account"] = account

	if tenant:
		filters["tenant"] = tenant
	if contract:
		filters["contract"] = contract
	if due_type:
		filters["due_type"] = due_type
	if source_type:
		# B8: legacy 'manual_contract' filter includes both manual_contract AND manual.
		if source_type == "manual_contract":
			filters["source_type"] = ["in", ["manual_contract", "manual"]]
		else:
			filters["source_type"] = source_type
	if from_date:
		filters["transaction_date"] = [">=", from_date]
	if to_date:
		filters["transaction_date"] = ["<=", to_date]
	if search:
		filters["due_number"] = ["like", f"%{search}%"]

	# Status filter: approved/cancelled/draft/due/future
	today = frappe.utils.today()
	if status == "approved":
		filters["docstatus"] = 1
	elif status == "cancelled":
		filters["docstatus"] = 2
	elif status == "draft":
		filters["docstatus"] = 0
	elif status == "due":
		# B7: approved dues with due_date <= today.
		filters["docstatus"] = 1
		filters["due_date"] = ["<=", today]
	elif status == "future":
		# B7: approved dues with due_date > tomorrow.
		from datetime import timedelta
		from frappe.utils import getdate
		tomorrow = getdate(today) + timedelta(days=1)
		filters["docstatus"] = 1
		filters["due_date"] = [">", tomorrow]

	fields = [
		"name", "due_number", "tenant", "contract", "building", "unit",
		"due_type", "source_type", "calculation_method",
		"transaction_date", "due_date", "period_label",
		"amount", "description", "docstatus",
		"previous_meter_reading", "current_meter_reading", "meter_consumption",
		"unit_price",
	]

	page_size = 0 if int(print) else int(limit)
	start = (int(page) - 1) * int(limit) if not int(print) else 0

	dues = frappe.get_all(
		"Rental Due",
		filters=filters,
		fields=fields,
		order_by="creation desc",
		start=start,
		limit_page_length=page_size,
	)

	# Enrich
	for d in dues:
		if d.get("tenant"):
			d["tenant_name"] = frappe.db.get_value("Rental Tenant", d["tenant"], "full_name")
		if d.get("due_type"):
			d["due_type_name"] = frappe.db.get_value("Rental Due Type", d["due_type"], "due_type_name")
		d["status"] = "approved" if d["docstatus"] == 1 else ("cancelled" if d["docstatus"] == 2 else "draft")

	# Stats
	total = frappe.db.count("Rental Due", filters)
	stats = _get_due_stats(account)

	pagination = {
		"page": int(page),
		"pageSize": int(limit),
		"total": total,
		"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
	}

	result = {"dues": dues, "pagination": pagination, "stats": stats}

	# B9: print mode returns print.totalAmount (legacy route.ts:170-180).
	if int(print):
		from rental.rental.services.balance_service import _db_sum
		print_total = 0
		for d in dues:
			if d["docstatus"] != 2:  # non-cancelled
				active_waivers = _db_sum(
					"Rental Due Waiver",
					{"due": d["name"], "status": "active"},
					"amount",
				)
				print_total += float(d.get("amount") or 0) - float(active_waivers or 0)
		result["print"] = {"totalAmount": round(print_total, 2)}

	return result


def _get_due_stats(account):
	"""Return due stats: total, approved, draft, cancelled."""
	base = {"rental_account": account} if account else {}
	return {
		"total": frappe.db.count("Rental Due", base),
		"approved": frappe.db.count("Rental Due", {**base, "docstatus": 1}),
		"draft": frappe.db.count("Rental Due", {**base, "docstatus": 0}),
		"cancelled": frappe.db.count("Rental Due", {**base, "docstatus": 2}),
	}


# ---------------------------------------------------------------------------
# Get single due  (source: GET /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_due(name):
	"""Get a single due with waivers and settlement info."""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("read")

	result = due.as_dict()

	# Add waivers
	waivers = frappe.get_all(
		"Rental Due Waiver",
		filters={"due": name},
		fields=["name", "amount", "reason", "source_type", "status", "creation"],
	)
	result["waivers"] = waivers

	# Add settlement item if linked
	if frappe.db.exists("DocType", "Cancellation Settlement Item"):
		settlement_item = frappe.db.get_value(
			"Cancellation Settlement Item", {"due": name},
			["name", "decision", "status", "gross_settled_amount"],
			as_dict=True,
		)
		result["settlement_item"] = settlement_item

	return result


# ---------------------------------------------------------------------------
# Create due  (source: POST /api/dues)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_due(**kwargs):
	"""Create a manual or additional due.

	Source: ``POST /api/dues``.
	"""
	account = get_current_rental_account()

	contract_name = kwargs.get("contract")
	due_type_name = kwargs.get("due_type")
	due_kind = kwargs.get("due_kind", "contractual")  # contractual or additional

	if not contract_name or not due_type_name:
		frappe.throw(frappe._("Contract and due type are required."))

	# Rent due type cannot be created manually
	dt_code = frappe.db.get_value("Rental Due Type", due_type_name, "due_type_code")
	if dt_code == "rent":
		frappe.throw(frappe._("Rent dues cannot be created manually."))

	# Contract must be active or expired
	contract = frappe.db.get_value(
		"Lease Contract", contract_name,
		["status", "tenant", "building", "unit", "rental_account"],
		as_dict=True,
	)
	if not contract:
		frappe.throw(frappe._("Contract does not exist."))
	if contract.status not in ("active", "expired"):
		frappe.throw(frappe._("Contract must be active or expired."))

	# Validate tenant/unit match
	if kwargs.get("tenant") and kwargs.get("tenant") != contract.tenant:
		frappe.throw(frappe._("Tenant does not match the contract."))
	if kwargs.get("unit") and kwargs.get("unit") != contract.unit:
		frappe.throw(frappe._("Unit does not match the contract."))

	due_data = {
		"doctype": "Rental Due",
		"rental_account": account,
		"tenant": contract.tenant,
		"contract": contract_name,
		"building": contract.building,
		"unit": contract.unit,
		"due_type": due_type_name,
		"transaction_date": kwargs.get("due_date"),
		"due_date": kwargs.get("due_date"),
		"description": kwargs.get("description"),
		"amount": kwargs.get("amount"),
		"notes": kwargs.get("notes"),
	}

	if due_kind == "additional":
		# Additional dues: cannot be system type, cannot have contract charge
		if frappe.db.get_value("Rental Due Type", due_type_name, "is_system"):
			frappe.throw(frappe._("Additional dues cannot be system due types."))
		charge_exists = frappe.db.exists(
			"Contract Charge",
			{"parent": contract_name, "parenttype": "Lease Contract", "due_type": due_type_name},
		)
		if charge_exists:
			frappe.throw(frappe._("Additional dues cannot have a contract charge."))
		if kwargs.get("current_meter_reading") or kwargs.get("previous_meter_reading"):
			frappe.throw(frappe._("Additional dues cannot have meter readings."))
		due_data["source_type"] = "additional"
		due_data["calculation_method"] = "on_demand"
		if not kwargs.get("description"):
			frappe.throw(frappe._("Description is required for additional dues."))
	else:
		# Contractual: must find matching ContractCharge
		charge = frappe.db.get_value(
			"Contract Charge",
			{"parent": contract_name, "parenttype": "Lease Contract", "due_type": due_type_name},
			["responsibility", "payment_by", "calculation_method"],
			as_dict=True,
		)
		if not charge:
			frappe.throw(frappe._("No contract charge found for this due type."))
		if charge.responsibility != "tenant":
			frappe.throw(frappe._("Due type responsibility must be tenant."))
		if charge.payment_by == "tenant":
			frappe.throw(frappe._("Cannot create due when tenant pays directly."))

		due_data["source_type"] = "manual_contract"
		due_data["calculation_method"] = charge.calculation_method

		if charge.calculation_method == "metered":
			# Metered due
			if not can_create_meter_due(contract_name, due_type_name):
				frappe.throw(frappe._("لا يمكن إنشاء التزام مترية قبل بدء العقد"))
			due_data["previous_meter_reading"] = get_previous_meter_reading(
				contract_name, contract.unit, due_type_name
			)
			due_data["current_meter_reading"] = kwargs.get("current_meter_reading")
			due_data["unit_price"] = kwargs.get("unit_price")
			if due_data["current_meter_reading"] is None:
				frappe.throw(frappe._("current_meter_reading is required for metered dues."))
			if not due_data["unit_price"]:
				frappe.throw(frappe._("unit_price is required for metered dues."))
			# B3: creation-time validation (legacy route.ts:305-310).
			prev_val = float(due_data["previous_meter_reading"] or 0)
			curr_val = float(due_data["current_meter_reading"])
			if curr_val < prev_val:
				frappe.throw(frappe._("القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"))
			unit_price_val = float(due_data["unit_price"])
			if unit_price_val <= 0:
				frappe.throw(frappe._("سعر الوحدة يجب أن يكون أكبر من صفر"))
		elif charge.calculation_method in ("actual_bill", "on_demand"):
			if not kwargs.get("amount"):
				frappe.throw(frappe._("Amount is required for {0} dues.").format(charge.calculation_method))
		elif charge.calculation_method == "fixed_periodic":
			frappe.throw(frappe._("Fixed periodic dues cannot be created manually."))

	due = frappe.get_doc(due_data)
	due.insert(ignore_permissions=is_system_manager())

	return due.name


# ---------------------------------------------------------------------------
# Update due  (source: PUT /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def update_due(name, **kwargs):
	"""Update a manual/additional draft due."""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("write")

	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("Only manual dues can be edited."))
	if due.docstatus != 0:
		frappe.throw(frappe._("Only draft dues can be edited."))

	# Forbidden identity keys
	forbidden = ["due_type", "contract", "tenant", "unit", "source_type", "calculation_method"]
	for f in forbidden:
		if f in kwargs:
			del kwargs[f]

	# Update allowed fields
	allowed = ["amount", "description", "due_date", "transaction_date",
			   "current_meter_reading", "unit_price", "notes"]
	for field in allowed:
		if field in kwargs and kwargs[field] is not None:
			due.set(field, kwargs[field])

	# B11: additional dues require non-empty description on update (legacy route.ts:62-66).
	if due.source_type == "additional":
		if not due.description or not due.description.strip():
			frappe.throw(frappe._("Description is required for additional dues."))

	due.save(ignore_permissions=is_system_manager())
	return due.name


# ---------------------------------------------------------------------------
# Delete due  (source: DELETE /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def delete_due(name):
	"""Delete a manual/additional draft due."""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("delete")

	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("Only manual dues can be deleted."))
	if due.docstatus != 0:
		frappe.throw(frappe._("Only draft dues can be deleted."))

	frappe.delete_doc("Rental Due", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Approve due  (source: POST /api/dues/[id]/approve)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def approve_due(name):
	"""Approve a manual/additional draft due.

	Source: ``POST /api/dues/[id]/approve``.
	"""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("submit")

	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("Only manual dues can be approved."))
	if due.docstatus != 0:
		frappe.throw(frappe._("Only draft dues can be approved."))

	# B5: revalidate contract status is active or expired (legacy route.ts:28-32).
	if due.contract:
		contract_status = frappe.db.get_value("Lease Contract", due.contract, "status")
		if contract_status not in ("active", "expired"):
			frappe.throw(frappe._("عقد الالتزام غير نشط أو منتهٍ ولا يمكن اعتماد الالتزام."))

	# For metered: recheck reading order
	if due.calculation_method == "metered":
		prev = float(due.previous_meter_reading or 0)
		curr = float(due.current_meter_reading or 0)
		if curr < prev:
			frappe.throw(frappe._("Current meter reading cannot be less than previous reading."))

		# B2: check no newer approved meter reading exists.
		# Legacy orders by [transactionDate desc, createdAt desc] and compares
		# both date AND createdAt (route.ts:93-112).
		newer_dues = frappe.get_all(
			"Rental Due",
			filters={
				"contract": due.contract,
				"due_type": due.due_type,
				"docstatus": 1,
				"current_meter_reading": ["is", "set"],
			},
			fields=["name", "transaction_date", "creation"],
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
				frappe.throw(frappe._("لا يمكن اعتماد الالتزام لوجود حركة عداد أحدث"))

	# Submit
	due.submit()
	return due.name


# ---------------------------------------------------------------------------
# Cancel due  (source: POST /api/dues/[id]/cancel)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def cancel_due_api(name, reason):
	"""Cancel a manual due."""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("cancel")

	cancel_due(name, reason)
	return {"success": True}


# ---------------------------------------------------------------------------
# Waivers  (source: GET/POST /api/dues/[id]/waivers)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_waivers(name):
	"""List waivers for a due."""
	due = frappe.get_doc("Rental Due", name)
	due.check_permission("read")

	waivers = frappe.get_all(
		"Rental Due Waiver",
		filters={"due": name},
		fields=["name", "amount", "reason", "source_type", "status",
				"cancellation_reason", "created_by", "creation"],
		order_by="creation desc",
	)
	return {"waivers": waivers}


@frappe.whitelist()
def create_waiver(name, amount, reason):
	"""Create a manual waiver for an auto_contract approved due."""
	account = get_current_rental_account()

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("read")

	if due.source_type != "auto_contract":
		frappe.throw(frappe._("Waivers can only be created for auto-contract dues."))
	if due.docstatus != 1:
		frappe.throw(frappe._("Waivers can only be created for approved dues."))

	# Check not linked to completed settlement
	if frappe.db.exists("DocType", "Cancellation Settlement Item"):
		settlement_item = frappe.db.get_value(
			"Cancellation Settlement Item",
			{"due": name, "status": "completed"},
			"name",
		)
		if settlement_item:
			frappe.throw(frappe._("Cannot create waiver for a due linked to a completed settlement."))

	waiver = frappe.get_doc({
		"doctype": "Rental Due Waiver",
		"rental_account": account,
		"due": name,
		"amount": amount,
		"reason": reason,
		"source_type": "manual",
		"status": "active",
		"created_by": frappe.session.user,
	})
	waiver.insert(ignore_permissions=is_system_manager())
	return waiver.name


@frappe.whitelist()
def cancel_waiver(due_name, waiver_name, reason):
	"""Cancel a manual waiver."""
	waiver = frappe.get_doc("Rental Due Waiver", waiver_name)
	waiver.check_permission("write")

	if waiver.source_type == "contract_cancellation":
		frappe.throw(frappe._("Contract cancellation waivers cannot be cancelled manually."))

	# Check not linked to completed settlement
	if waiver.settlement_item:
		item_status = frappe.db.get_value("Cancellation Settlement Item", waiver.settlement_item, "status")
		if item_status == "completed":
			frappe.throw(frappe._("Cannot cancel waiver linked to a completed settlement."))

	frappe.db.set_value("Rental Due Waiver", waiver_name, {
		"status": "cancelled",
		"cancellation_reason": reason,
		"cancelled_by": frappe.session.user,
		"cancelled_at": frappe.utils.now(),
	}, update_modified=False)

	return {"success": True}
