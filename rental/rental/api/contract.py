"""Contract API: CRUD, approve, cancel, renew, archive, unarchive, expire.

Ported from ``src/app/api/contracts/**``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager
from rental.rental.utils.date_utils import to_calendar_day, get_contract_period_status
from rental.rental.services.contract_validation import (
	validate_contract_basic_data,
	validate_contract_draft_unit,
	validate_contract_for_approval,
	validate_contract_date_for_approval,
	recalculate_unit_status,
	expire_contracts,
	can_renew_contract,
	can_evict_contract,
)
from rental.rental.services.contract_charge_service import (
	save_contract_charges,
	generate_fixed_periodic_dues,
	freeze_metered_opening_readings,
	copy_contract_charges_for_renewal,
	get_previous_meter_reading,
)
from rental.rental.services.due_generation_service import generate_contract_dues
from rental.rental.services.renewal_service import (
	can_create_renewal_for,
	close_previous_contract_by_renewal,
	get_renewal_first_due_date,
)
from rental.rental.services.archive_service import archive_contract, unarchive_contract
from rental.rental.doctype.rental_settings.rental_settings import (
	generate_contract_number,
	build_lessor_snapshot,
)


# ---------------------------------------------------------------------------
# List contracts  (source: GET /api/contracts)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_contracts(
	status=None,
	unit=None,
	tenant=None,
	building=None,
	archived=None,
	include_charges=0,
	search=None,
	eviction=0,
	from_date=None,
	to_date=None,
	contract_type=None,
	print=0,
	page=None,
	limit=15,
):
	"""List contracts with filters, pagination, and stats."""
	account = get_current_rental_account()

	# Source: route.ts:36-38 — date range validation
	if from_date and to_date:
		fd = to_calendar_day(from_date)
		td = to_calendar_day(to_date)
		if fd > td:
			frappe.throw(frappe._("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية"))

	filters = {}
	if account:
		filters["rental_account"] = account

	# Archive filter
	if archived == "true":
		filters["is_archived"] = 1
	elif archived == "false":
		filters["is_archived"] = 0
	else:
		filters["is_archived"] = 0  # default non-archived

	# Status filter — supports comma-separated list
	if status and status != "all":
		if status == "upcoming":
			today = frappe.utils.today()
			filters["status"] = "active"
			filters["start_date"] = [">", today]
		elif status == "active":
			today = frappe.utils.today()
			filters["status"] = "active"
			filters["start_date"] = ["<=", today]
			filters["end_date"] = [">=", today]
		elif status == "archived":
			filters["is_archived"] = 1
		elif "," in status:
			# Comma-separated list of statuses
			status_list = [s.strip() for s in status.split(",") if s.strip()]
			filters["status"] = ["in", status_list]
		else:
			filters["status"] = status

	if unit:
		filters["unit"] = unit
	if tenant:
		filters["tenant"] = tenant
	if building:
		filters["building"] = building
	# Date range filters (source: section 7.3)
	# fromDate → endDate >= fromDate (contracts that end on/after fromDate)
	# toDate → startDate <= toDate (contracts that start on/before toDate)
	if from_date:
		filters["end_date"] = [">=", from_date]
	if to_date:
		filters["start_date"] = ["<=", to_date]
	if contract_type == "original":
		filters["renewed_from_contract"] = ["is", "not set"]
	elif contract_type == "renewal":
		filters["renewed_from_contract"] = ["is", "set"]

	if search:
		filters["contract_number"] = ["like", f"%{search}%"]

	# Eviction candidates
	if int(eviction):
		all_contracts = frappe.get_all(
			"Lease Contract",
			filters={**filters, "is_archived": 0},
			fields=["name", "contract_number", "tenant", "building", "unit",
					"start_date", "end_date", "status", "is_historical",
					"cancelled_at", "renewed_from_contract"],
		)
		eviction_candidates = []
		for c in all_contracts:
			contract_doc = frappe.get_doc("Lease Contract", c.name)
			if can_evict_contract(contract_doc):
				eviction_candidates.append(c)
		return {"contracts": eviction_candidates, "stats": _get_contract_stats(account)}

	# Build query
	fields = [
		"name", "contract_number", "tenant", "building", "unit",
		"start_date", "end_date", "rent_amount", "payment_frequency",
		"status", "is_archived", "is_historical", "renewed_from_contract",
		"closed_by_renewal_at", "cancelled_at",
	]

	# Source: route.ts:30-32,131-156 — page is undefined when print=true or not provided
	# When page is None or print is true, return ALL contracts (no pagination)
	page_num = int(page) if page else 0
	if int(print) or not page_num:
		# No pagination — return all matching contracts
		contracts = frappe.get_all(
			"Lease Contract",
			filters=filters,
			fields=fields,
			order_by="creation desc",
		)
	else:
		# Paginated
		start = (page_num - 1) * int(limit)
		contracts = frappe.get_all(
			"Lease Contract",
			filters=filters,
			fields=fields,
			order_by="creation desc",
			start=start,
			limit_page_length=int(limit),
		)

	# Enrich with tenant names, building/unit names, renewals, dues count
	for c in contracts:
		if c.get("tenant"):
			c["tenant_name"] = frappe.db.get_value("Rental Tenant", c["tenant"], "full_name")
		if c.get("building"):
			c["building_name"] = frappe.db.get_value("Rental Building", c["building"], "building_name")
		if c.get("unit"):
			c["unit_number"] = frappe.db.get_value("Rental Unit", c["unit"], "unit_number")

		# A24: renewals filtered status not in [cancelled, evicted] (legacy route.ts:45-48).
		c["renewals"] = frappe.get_all(
			"Lease Contract",
			filters={"renewed_from_contract": c["name"], "status": ["not in", ["cancelled", "evicted"]]},
			fields=["name", "contract_number", "status"],
		)

		# Add _count.dues
		c["_count"] = {
			"dues": frappe.db.count("Rental Due", {"contract": c["name"]}),
		}

		# A24: honor include_charges (legacy route.ts:52-56).
		if int(include_charges):
			c["contract_charges"] = frappe.get_all(
				"Contract Charge",
				filters={"parent": c["name"], "parenttype": "Lease Contract"},
				fields=["name", "due_type"],
			)

		# Add previous_contract info for renewal meta labels (source: section 7.8)
		if c.get("renewed_from_contract"):
			prev_number = frappe.db.get_value(
				"Lease Contract", c["renewed_from_contract"], "contract_number"
			)
			c["previous_contract_number"] = prev_number

	# Pagination — only included when page is provided (source: route.ts:191-193)
	total = frappe.db.count("Lease Contract", filters)

	# A24: print mode returns print.total = count of contracts (legacy route.ts:197)
	result = {
		"contracts": contracts,
		"stats": _get_contract_stats(account),
	}

	if int(print):
		result["print"] = {"total": total}

	# Source: route.ts:191-193 — pagination only when page is provided (not print)
	if page_num and not int(print):
		result["pagination"] = {
			"page": int(page),
			"pageSize": int(limit),
			"total": total,
			"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
		}

	return result


def _get_contract_stats(account):
	"""Return contract stats: total, active, upcoming, eviction."""
	today = frappe.utils.today()
	base_filters = {"rental_account": account, "is_archived": 0} if account else {"is_archived": 0}

	total = frappe.db.count("Lease Contract", base_filters)
	active = frappe.db.count("Lease Contract", {**base_filters, "status": "active", "start_date": ["<=", today], "end_date": [">=", today]})
	upcoming = frappe.db.count("Lease Contract", {**base_filters, "status": "active", "start_date": [">", today]})

	# Eviction count (expensive — computed)
	all_terminal = frappe.get_all(
		"Lease Contract",
		filters={**base_filters, "status": ["in", ["expired", "cancelled"]]},
		fields=["name"],
	)
	eviction_count = 0
	for c in all_terminal:
		contract_doc = frappe.get_doc("Lease Contract", c.name)
		if can_evict_contract(contract_doc):
			eviction_count += 1

	return {"total": total, "active": active, "upcoming": upcoming, "eviction": eviction_count}


# ---------------------------------------------------------------------------
# Get single contract  (source: GET /api/contracts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_contract(name):
	"""Get a single contract with full details.

	Source: ``GET /api/contracts/{id}``.
	Returns the contract with enriched tenant, building, unit objects,
	dues, receipts, lessor data, and cancellation settlement.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	result = contract.as_dict()

	# Enrich contract charges with due_type_name and due_type_code.
	# Source: old program route.ts:33 — `contractCharges: { include: { dueType: true } }`
	# embeds the full DueType object in each charge. Frappe's as_dict() only
	# returns the link field (due_type = ID), so we add the display fields here.
	for charge in result.get("contract_charges", []):
		if charge.get("due_type"):
			dt = frappe.db.get_value(
				"Rental Due Type", charge["due_type"],
				["due_type_name", "due_type_code"], as_dict=True,
			)
			if dt:
				charge["due_type_name"] = dt.due_type_name
				charge["due_type_code"] = dt.due_type_code

	# Add lessor data — strip logo (source: route.ts:60-62)
	from rental.rental.doctype.rental_settings.rental_settings import get_lessor_data, parse_lessor_snapshot
	lessor = get_lessor_data(contract.rental_account)
	# Source: route.ts:62 — do not send heavy base64 logo in detail response
	if isinstance(lessor, dict) and "logo" in lessor:
		lessor = {k: v for k, v in lessor.items() if k != "logo"}
	result["lessor"] = lessor
	if contract.lessor_snapshot:
		snapshot = parse_lessor_snapshot(contract.lessor_snapshot)
		if isinstance(snapshot, dict) and "logo" in snapshot:
			snapshot = {k: v for k, v in snapshot.items() if k != "logo"}
		result["lessor_snapshot"] = snapshot

	# Enrich tenant object
	if contract.tenant:
		tenant = frappe.db.get_value(
			"Rental Tenant", contract.tenant,
			["name", "full_name", "national_id", "phone", "workplace",
			 "guarantor_name", "guarantor_phone", "is_active"],
			as_dict=True,
		)
		if tenant:
			result["tenant"] = tenant
			result["tenant_name"] = tenant.full_name

	# Enrich building object
	if contract.building:
		building = frappe.db.get_value(
			"Rental Building", contract.building,
			["name", "building_name", "owner_name", "address",
			 "latitude", "longitude", "is_active"],
			as_dict=True,
		)
		if building:
			result["building"] = building
			result["building_name"] = building.building_name

	# Enrich unit object
	if contract.unit:
		unit = frappe.db.get_value(
			"Rental Unit", contract.unit,
			["name", "unit_number", "building", "floor", "unit_type",
			 "area", "rooms_count", "bathrooms_count", "default_rent",
			 "electricity_meter_number", "water_meter_number",
			 "current_electricity_meter_reading", "current_water_meter_reading",
			 "status", "is_active"],
			as_dict=True,
		)
		if unit:
			result["unit"] = unit
			result["unit_number"] = unit.unit_number

	# Add dues — ordered by transactionDate asc (source: route.ts:39)
	dues = frappe.get_all(
		"Rental Due",
		filters={"contract": name},
		fields=["name", "due_number", "due_type", "source_type", "calculation_method",
				"transaction_date", "due_date", "period_label", "period_start", "period_end",
				"amount", "docstatus", "previous_meter_reading", "current_meter_reading",
				"meter_consumption", "unit_price", "cancelled_at", "is_system_cancelled"],
		order_by="transaction_date asc",
	)
	# Enrich due_type_name and waivers for each due
	for d in dues:
		if d.get("due_type"):
			dt = frappe.db.get_value("Rental Due Type", d["due_type"], ["due_type_name", "due_type_code"], as_dict=True)
			if dt:
				d["due_type_name"] = dt.due_type_name
				d["due_type_code"] = dt.due_type_code
		# Source: route.ts:37 — include waivers
		d["waivers"] = frappe.get_all(
			"Rental Due Waiver",
			filters={"due": d["name"]},
			fields=["name", "amount", "status"],
		)
	result["dues"] = dues

	# Add receipts — ordered by receiptDate asc (source: route.ts:43)
	receipts = frappe.get_all(
		"Rental Receipt",
		filters={"contract": name},
		fields=["name", "receipt_number", "receipt_date", "amount",
				"payment_method", "reference_number", "docstatus",
				"cancelled_at", "cancelled_by", "notes"],
		order_by="receipt_date asc",
	)
	result["receipts"] = receipts

	# Add attachments — ordered by createdAt desc (source: route.ts:45-48)
	attachments = frappe.get_all(
		"Contract Attachment",
		filters={"parent": name, "parenttype": "Lease Contract"},
		fields=["name", "file_name", "file_type", "creation"],
		order_by="creation desc",
	)
	result["attachments"] = attachments

	# Add evictions — ordered by createdAt desc (source: route.ts:49-52)
	evictions = frappe.get_all(
		"Rental Eviction",
		filters={"contract": name},
		fields=["name", "eviction_date", "notes"],
		order_by="creation desc",
	)
	result["evictions"] = evictions

	# Add renewals (contracts renewed from this one)
	renewals = frappe.get_all(
		"Lease Contract",
		filters={"renewed_from_contract": name},
		fields=["name", "contract_number", "status", "start_date", "end_date",
				"is_archived", "closed_by_renewal_at"],
		order_by="creation desc",
	)
	result["renewals"] = renewals

	# Add _count for dues
	result["_count"] = {"dues": len(dues)}

	# Add previous_contract for renewals (source: section 7.8, 13.2)
	if contract.renewed_from_contract:
		prev = frappe.db.get_value(
			"Lease Contract", contract.renewed_from_contract,
			["name", "contract_number", "status", "start_date", "end_date"],
			as_dict=True,
		)
		if prev:
			result["previous_contract"] = prev

	# Add cancellation settlement if exists
	if frappe.db.exists("DocType", "Contract Cancellation Settlement"):
		settlement_name = frappe.db.get_value(
			"Contract Cancellation Settlement", {"contract": name}, "name"
		)
		if settlement_name:
			settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name).as_dict()
			# Add summary fields expected by frontend
			settlement_items = settlement.get("settlement_items", [])
			result["cancellation_settlement"] = {
				"id": settlement_name,
				"name": settlement_name,
				"status": settlement.get("status"),
				"unresolved_count": sum(1 for it in settlement_items if it.get("status") != "decided"),
				**settlement,
			}

	return result


def _contract_response_object(name: str) -> dict:
	"""Build a contract response object with key fields for API responses.

	Used by create/approve/cancel/renew/update to return ``{ contract: {...} }``
	instead of a bare string.
	"""
	contract = frappe.db.get_value(
		"Lease Contract", name,
		["name", "contract_number", "tenant", "building", "unit",
		 "start_date", "end_date", "rent_amount", "payment_frequency",
		 "commitment_timing", "first_due_date", "payment_method",
		 "contract_date", "terms", "witnesses", "status",
		 "is_archived", "is_historical", "renewed_from_contract",
		 "closed_by_renewal_at", "cancelled_at", "cancellation_reason",
		 "lessor_snapshot"],
		as_dict=True,
	)
	if not contract:
		return {"id": name}

	# Add tenant/building/unit names
	if contract.get("tenant"):
		contract["tenant_name"] = frappe.db.get_value("Rental Tenant", contract["tenant"], "full_name")
	if contract.get("building"):
		contract["building_name"] = frappe.db.get_value("Rental Building", contract["building"], "building_name")
	if contract.get("unit"):
		contract["unit_number"] = frappe.db.get_value("Rental Unit", contract["unit"], "unit_number")

	# Add id alias
	contract["id"] = contract["name"]
	return contract


# ---------------------------------------------------------------------------
# Create contract  (source: POST /api/contracts)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_contract(**kwargs):
	"""Create a draft contract."""
	account = get_current_rental_account()

	# System Manager may not be linked to a Rental Account — resolve from kwargs or building
	if not account:
		account = kwargs.get("rental_account")
	if not account:
		# Infer from the selected building (each building belongs to one account)
		building = kwargs.get("building") or kwargs.get("building_id")
		if building:
			account = frappe.db.get_value("Rental Building", building, "rental_account")
	if not account:
		# Fall back to the first active account (System Manager only)
		if is_system_manager():
			account = frappe.db.get_value("Rental Account", {"is_active": 1}, "name")
	if not account:
		frappe.throw(frappe._("Could not determine Rental Account. Please complete setup first."))

	# Map frontend field names to doctype fields.
	# The old program's API accepts tenantId/buildingId/unitId; after the
	# frontend's camelCase→snake_case conversion these arrive as tenant_id/
	# building_id/unit_id. The Frappe doctype fields are tenant/building/unit.
	tenant = kwargs.get("tenant") or kwargs.get("tenant_id")
	building = kwargs.get("building") or kwargs.get("building_id")
	unit = kwargs.get("unit") or kwargs.get("unit_id")

	# Build contract doc
	contract_data = {
		"doctype": "Lease Contract",
		"rental_account": account,
		"tenant": tenant,
		"building": building,
		"unit": unit,
		"start_date": kwargs.get("start_date"),
		"end_date": kwargs.get("end_date"),
		"rent_amount": kwargs.get("rent_amount"),
		"payment_frequency": kwargs.get("payment_frequency"),
		"commitment_timing": kwargs.get("commitment_timing", "start"),
		"payment_method": kwargs.get("payment_method"),
		"contract_date": kwargs.get("contract_date"),
		"first_due_date": kwargs.get("first_due_date"),
		"terms": kwargs.get("terms"),
		"witnesses": kwargs.get("witnesses"),
		"status": "draft",
	}

	# Add charges if provided — map frontend field names to doctype fields.
	# Frontend sends due_type_id (snake_case of dueTypeId); doctype field is due_type.
	# Strip non-doctype keys (due_type_name, due_type_code) that the frontend
	# includes for display purposes. Source: old program saveContractCharges
	# maps dueTypeId → Prisma's dueTypeId field; here we map to Frappe's due_type.
	charges = kwargs.get("contract_charges")
	if charges:
		if isinstance(charges, str):
			import json
			charges = json.loads(charges)
		mapped_charges = []
		for c in charges:
			mapped = {}
			for k, v in c.items():
				if k == "due_type_id":
					mapped["due_type"] = v
				elif k in ("due_type_name", "due_type_code"):
					continue  # display-only fields, not on doctype
				else:
					mapped[k] = v
			mapped_charges.append(mapped)
		contract_data["contract_charges"] = mapped_charges

	contract = frappe.get_doc(contract_data)
	contract.insert(ignore_permissions=is_system_manager())

	# Determine if dues choice is needed (past contract)
	period_status = get_contract_period_status(contract.start_date, contract.end_date)
	requires_dues_choice = period_status == "past"

	return {
		"contract": _contract_response_object(contract.name),
		"requiresDuesChoice": requires_dues_choice,
	}


# ---------------------------------------------------------------------------
# Update contract  (source: PUT /api/contracts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def update_contract(name, **kwargs):
	"""Update a draft contract."""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("write")

	if contract.is_archived:
		frappe.throw(frappe._("لا يمكن تعديل عقد مؤرشف"))
	if contract.status != "draft":
		frappe.throw(frappe._("لا يمكن تعديل العقد بعد الاعتماد"))

	# Map frontend field names to doctype fields (same as create_contract).
	# Frontend sends tenant_id/building_id/unit_id; doctype fields are tenant/building/unit.
	for old_key, new_key in [("tenant_id", "tenant"), ("building_id", "building"), ("unit_id", "unit")]:
		if old_key in kwargs and new_key not in kwargs:
			kwargs[new_key] = kwargs[old_key]

	# Renewal drafts cannot change fixed fields (tenant/building/unit/dates)
	# Source: route.ts:128-137 — reject with 409, do NOT silently delete
	if contract.renewed_from_contract:
		forbidden = ["tenant", "building", "unit", "first_due_date", "start_date", "renewed_from_contract"]
		for f in forbidden:
			if f in kwargs and kwargs[f] is not None:
				frappe.throw(frappe._("لا يمكن تعديل البيانات الثابتة لتجديد العقد"))

	# Update allowed fields
	# Non-renewal drafts may change tenant/building/unit; renewal drafts forbid it above.
	allowed = ["tenant", "building", "unit", "start_date", "end_date", "rent_amount",
			   "payment_frequency", "commitment_timing", "payment_method",
			   "contract_date", "first_due_date", "terms", "witnesses"]

	# Track if unit/building changed to re-run draft unit validation
	unit_or_building_changed = False
	for field in allowed:
		if field in kwargs and kwargs[field] is not None:
			old_val = contract.get(field)
			new_val = kwargs[field]
			if field in ("building", "unit") and str(old_val) != str(new_val):
				unit_or_building_changed = True
			contract.set(field, kwargs[field])

	# Re-run draft unit validation if unit/building changed (source: section 9.4)
	if unit_or_building_changed:
		validate_contract_draft_unit(contract)

	# Update charges if provided — map frontend field names to doctype fields.
	# Frontend sends due_type_id; doctype field is due_type.
	charges = kwargs.get("contract_charges")
	if charges:
		if isinstance(charges, str):
			import json
			charges = json.loads(charges)
		mapped_charges = []
		for c in charges:
			mapped = {}
			for k, v in c.items():
				if k == "due_type_id":
					mapped["due_type"] = v
				elif k in ("due_type_name", "due_type_code"):
					continue
				else:
					mapped[k] = v
			mapped_charges.append(mapped)
		save_contract_charges(contract, mapped_charges, contract.rental_account)

	contract.save(ignore_permissions=is_system_manager())
	# Source: route.ts:196 returns { contract: updated }
	return {"contract": _contract_response_object(contract.name)}


# ---------------------------------------------------------------------------
# Delete contract  (source: DELETE /api/contracts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def delete_contract(name):
	"""Delete a draft contract."""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("delete")

	if contract.is_archived:
		frappe.throw(frappe._("لا يمكن حذف عقد مؤرشف"))
	if contract.status != "draft":
		frappe.throw(frappe._("لا يمكن حذف العقد بعد الاعتماد"))

	frappe.delete_doc("Lease Contract", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Approve contract  (source: POST /api/contracts/[id]/approve)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def approve_contract(name, generate_dues=0):
	"""Approve a draft contract.

	Source: ``POST /api/contracts/[id]/approve``.
	All validation runs first; then writes are applied sequentially.
	If any write step fails, the contract is reverted to draft status and
	any dues created during this call are cleaned up (A23 atomicity).
	"""
	from rental.rental.doctype.rental_settings.rental_settings import validate_lessor_data_for_contract

	account = get_current_rental_account() or frappe.db.get_value("Lease Contract", name, "rental_account")
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("write")

	if contract.is_archived:
		frappe.throw(frappe._("لا يمكن اعتماد عقد مؤرشف"))
	if contract.status != "draft":
		frappe.throw(frappe._("العقد ليس مسودة"))

	# Full validation (all checks before any writes)
	# Source: approve/route.ts:44-47 — date validation runs BEFORE full validation
	from rental.rental.services.contract_validation import validate_contract_date_for_approval
	validate_contract_date_for_approval(contract)

	validate_contract_for_approval(contract)

	# Validate lessor data is complete
	validate_lessor_data_for_contract(account)

	# Determine new status
	period_status = get_contract_period_status(contract.start_date, contract.end_date)
	is_past = period_status == "past"
	new_status = "expired" if is_past else "active"

	is_future_renewal = bool(contract.renewed_from_contract) and to_calendar_day(contract.start_date) > to_calendar_day(frappe.utils.today())

	# Freeze lessor snapshot
	snapshot = build_lessor_snapshot(account)

	# Source: approve/route.ts:29 — generateDues === true (strict boolean)
	# Handle both boolean and string/integer representations from frontend
	if isinstance(generate_dues, bool):
		generate_dues_flag = generate_dues
	elif isinstance(generate_dues, (int, float)):
		generate_dues_flag = bool(int(generate_dues))
	elif isinstance(generate_dues, str):
		generate_dues_flag = generate_dues.lower() == "true"
	else:
		generate_dues_flag = False

	# A1: Both rent and fixed-periodic dues run only when
	# `generateDues || periodStatus !== 'past'` (legacy approve route.ts:97).
	should_generate_dues = generate_dues_flag or not is_past

	# Track dues created during this call for atomicity cleanup (A23).
	created_due_names: list[str] = []

	# Apply writes — if any step fails, revert contract to draft + delete dues
	try:
		# Update contract status + snapshot + is_historical
		frappe.db.set_value("Lease Contract", name, {
			"status": new_status,
			"is_historical": 1 if is_past else 0,
			"lessor_snapshot": snapshot,
		}, update_modified=False)

		# Sync the in-memory contract object so downstream calls
		# (generate_fixed_periodic_dues, freeze_metered_opening_readings, etc.)
		# see the updated status. The old program fetches the contract fresh
		# from DB inside each service function; the Frappe port passes the
		# in-memory doc, so we must keep it in sync with the DB write above.
		contract.status = new_status
		contract.is_historical = 1 if is_past else 0
		contract.lessor_snapshot = snapshot

		# If renewal, close previous contract
		if contract.renewed_from_contract:
			close_previous_contract_by_renewal(
				contract.renewed_from_contract,
				{"name": name, "start_date": contract.start_date},
				account,
			)

		# Generate rent dues + fixed periodic dues (both gated by should_generate_dues)
		if should_generate_dues:
			# Record existing auto-contract dues before generation so we can
			# identify newly created ones for cleanup on failure.
			from rental.rental.services.due_generation_service import generate_contract_dues
			created_count = generate_contract_dues(contract, account, generate=True)
			# generate_contract_dues creates dues via _create_auto_due; track them
			new_dues = frappe.get_all(
				"Rental Due",
				filters={"contract": name, "source_type": "auto_contract"},
				pluck="name",
			)
			created_due_names.extend(new_dues)

			# Fixed periodic dues
			from rental.rental.services.contract_charge_service import generate_fixed_periodic_dues
			generate_fixed_periodic_dues(contract, account)
			# Track any additional fixed-periodic dues
			all_dues = frappe.get_all(
				"Rental Due",
				filters={"contract": name, "source_type": "auto_contract"},
				pluck="name",
			)
			for dn in all_dues:
				if dn not in created_due_names:
					created_due_names.append(dn)

		# Freeze metered opening readings (unless future renewal)
		if not is_future_renewal:
			freeze_metered_opening_readings(contract, account)

		# Recalculate unit status
		recalculate_unit_status(contract.unit)
	except Exception:
		# A23: Clean up any dues created during this approval attempt.
		for due_name in created_due_names:
			try:
				if frappe.db.exists("Rental Due", due_name):
					frappe.delete_doc("Rental Due", due_name, force=True, ignore_permissions=True)
			except Exception:
				pass  # best-effort cleanup

		# Revert contract to draft on failure
		frappe.db.set_value("Lease Contract", name, {
			"status": "draft",
			"is_historical": 0,
			"lessor_snapshot": None,
		}, update_modified=False)
		# Sync in-memory object to match the revert
		contract.status = "draft"
		contract.is_historical = 0
		contract.lessor_snapshot = None
		raise

	# Source: route.ts:111 returns { contract: updated } (no status field)
	return {"contract": _contract_response_object(name)}


# ---------------------------------------------------------------------------
# Cancel contract  (source: POST /api/contracts/[id]/cancel)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def cancel_contract(name, cancellation_date, reason=None):
	"""Cancel an active contract and create cancellation settlement."""
	account = get_current_rental_account() or frappe.db.get_value("Lease Contract", name, "rental_account")
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("write")

	# Default reason to 'إلغاء العقد' (source: cancel/route.ts:69)
	if not reason:
		reason = "إلغاء العقد"

	if contract.is_archived:
		frappe.throw(frappe._("لا يمكن إلغاء عقد مؤرشف"))
	if contract.status == "cancelled":
		frappe.throw(frappe._("العقد ملغي مسبقاً"))
	if contract.status in ("expired", "evicted"):
		frappe.throw(frappe._("لا يمكن إلغاء عقد منتهٍ أو تم إخلاؤه"))

	# Source: cancel/route.ts:34-40 — only APPROVED renewals block cancellation
	# (not drafts). Uses isApprovedRenewal which excludes draft/cancelled/evicted.
	from rental.rental.services.renewal_service import is_approved_renewal
	renewals = frappe.get_all(
		"Lease Contract",
		filters={"renewed_from_contract": name},
		pluck="name",
	)
	if any(is_approved_renewal(r) for r in renewals):
		frappe.throw(frappe._("لا يمكن إلغاء العقد لوجود تجديد معتمد؛ يجب إلغاء التجديد أولاّ"))

	# Source: cancel/route.ts:42-44 — status !== 'active' check comes AFTER renewal check
	if contract.status != "active":
		frappe.throw(frappe._("لا يمكن إلغاء عقد غير نشط"))

	# Source: cancel/route.ts:46-49 — cancellationDate presence check
	if not cancellation_date:
		frappe.throw(frappe._("تاريخ الإلغاء مطلوب"))

	# Cancellation date must be within [startDate, endDate]
	cancel_date = to_calendar_day(cancellation_date)
	start = to_calendar_day(contract.start_date)
	end = to_calendar_day(contract.end_date)
	if cancel_date < start or cancel_date > end:
		frappe.throw(frappe._("تاريخ الإلغاء خارج فترة العقد"))

	# Update contract status — use the normalized cancel_date as cancelled_at
	# Source: cancel/route.ts:64-71 — cancelledAt: cancellationDate (normalized)
	frappe.db.set_value("Lease Contract", name, {
		"status": "cancelled",
		"cancelled_at": cancel_date,
		"cancellation_reason": reason,
	}, update_modified=False)

	# Create cancellation settlement — pass normalized cancel_date
	# Source: cancel/route.ts:73-81 — cancellationDate is the normalized date
	from rental.rental.services.contract_cancellation_settlement_service import (
		create_contract_cancellation_settlement,
	)
	settlement_name = create_contract_cancellation_settlement(name, cancel_date, reason or "", account)

	# Recalculate unit status
	recalculate_unit_status(contract.unit)

	# Build settlement response object (source: route.ts:83 returns full settlement)
	settlement_doc = frappe.get_doc("Contract Cancellation Settlement", settlement_name).as_dict()
	settlement_items = settlement_doc.get("settlement_items", []) or settlement_doc.get("items", [])
	settlement_response = {
		"id": settlement_name,
		"name": settlement_name,
		"status": settlement_doc.get("status") or "pending",
		"unresolved_count": sum(1 for it in settlement_items if it.get("status") != "decided"),
		**settlement_doc,
	}

	return {
		"contract": _contract_response_object(name),
		"settlement": settlement_response,
	}


# ---------------------------------------------------------------------------
# Renew contract  (source: POST /api/contracts/[id]/renew)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def renew_contract(name, **kwargs):
	"""Create a renewal draft for a contract.

	Source: ``POST /api/contracts/[id]/renew``.
	"""
	account = get_current_rental_account() or frappe.db.get_value("Lease Contract", name, "rental_account")
	previous = frappe.get_doc("Lease Contract", name)
	previous.check_permission("read")

	renewal_check = can_create_renewal_for(name)
	if not renewal_check["ok"]:
		frappe.throw(renewal_check["reason"] or frappe._("لا يمكن إنشاء تجديد لهذا العقد"))

	# Renewal start = previous end + 1 day (source: route.ts:42-43)
	from rental.rental.utils.date_utils import add_days
	start_date = add_days(previous.end_date, 1)

	# Source: route.ts:44 — endDate defaults to startDate if not provided
	end_date_input = kwargs.get("end_date")
	end_date = end_date_input if end_date_input else start_date

	# Validate end > start (source: route.ts:48-50)
	from rental.rental.utils.date_utils import validate_dates
	if not validate_dates(start_date, end_date):
		frappe.throw(frappe._("تاريخ النهاية يجب أن يكون بعد تاريخ البداية"))

	# Source: route.ts:45-46 — rentAmount defaults to previous, paymentFrequency defaults to previous
	rent_amount_input = kwargs.get("rent_amount")
	rent_amount = float(rent_amount_input) if rent_amount_input else float(previous.rent_amount)
	payment_frequency = kwargs.get("payment_frequency") or previous.payment_frequency

	# Create renewal draft
	# Source: route.ts:72-89 — optional fields default to null, NOT previous values
	renewal_data = {
		"doctype": "Lease Contract",
		"rental_account": account,
		"tenant": previous.tenant,
		"building": previous.building,
		"unit": previous.unit,
		"start_date": start_date,
		"end_date": end_date,
		"rent_amount": rent_amount,
		"payment_frequency": payment_frequency,
		# Source: route.ts:83 — commitmentTiming || 'start'
		"commitment_timing": kwargs.get("commitment_timing") or "start",
		# Source: route.ts:82 — paymentMethod ?? null
		"payment_method": kwargs.get("payment_method"),
		# Source: route.ts:86 — contractDate ? new Date(contractDate) : null
		"contract_date": kwargs.get("contract_date"),
		"first_due_date": start_date,
		# Source: route.ts:84-85 — terms || null, witnesses || null
		"terms": kwargs.get("terms") or None,
		"witnesses": kwargs.get("witnesses") or None,
		"status": "draft",
		"renewed_from_contract": name,
	}

	renewal = frappe.get_doc(renewal_data)

	# Copy charges
	copy_contract_charges_for_renewal(previous, renewal, account)

	renewal.insert(ignore_permissions=is_system_manager())

	return {"contract": _contract_response_object(renewal.name)}


# ---------------------------------------------------------------------------
# Archive / unarchive  (source: POST /api/contracts/[id]/archive, unarchive)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def archive_contract_api(name):
	"""Archive a contract.

	Source: ``POST /api/contracts/[id]/archive``.
	Returns the full contract object (source: route.ts:10).
	"""
	archive_contract(name)
	return {"contract": _contract_response_object(name)}


@frappe.whitelist()
def unarchive_contract_api(name):
	"""Unarchive a contract.

	Source: ``POST /api/contracts/[id]/unarchive``.
	Returns the full contract object.
	"""
	unarchive_contract(name)
	return {"contract": _contract_response_object(name)}


# ---------------------------------------------------------------------------
# Contract balance  (source: GET /api/contracts/[id]/balance)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_contract_balance(name):
	"""Get contract balance.

	Source: ``GET /api/contracts/[id]/balance``.
	Returns 404 if contract does not exist (source: route.ts:14-21).
	"""
	# Source: route.ts:14-21 — contract existence check
	if not frappe.db.exists("Lease Contract", name):
		frappe.throw(frappe._("العقد غير موجود"))
	from rental.rental.services.balance_service import get_contract_balance as _get_contract_balance
	return _get_contract_balance(name)


# ---------------------------------------------------------------------------
# Contract due types  (source: GET /api/contracts/[id]/due-types)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_contract_due_types(name):
	"""List contract charges eligible for manual due creation.

	Source: ``GET /api/contracts/[id]/due-types``.
	Returns tenant charges paid by landlord (excluding rent and inactive due types).
	Fixed-periodic charges are included but marked with disabledReason.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	def _get_disabled_reason(calculation_method):
		if calculation_method == "fixed_periodic":
			return "هذه الخدمة دورية ثابتة، ويتم إنشاء التزاماتها تلقائيًا من العقد"
		return None

	charges = []
	for charge in contract.contract_charges:
		# Source filter: responsibility === 'tenant' && paymentBy !== 'tenant' && code !== 'rent' && isActive !== false
		if charge.responsibility != "tenant":
			continue
		if charge.payment_by == "tenant":
			continue
		dt = frappe.db.get_value(
			"Rental Due Type", charge.due_type,
			["name", "due_type_name", "due_type_code", "is_active"],
			as_dict=True,
		)
		if not dt:
			continue
		if dt.due_type_code == "rent":
			continue
		if dt.is_active == 0:
			continue
		charges.append({
			"contract_charge_id": charge.name,
			"due_type_id": dt.name,
			"due_type_name": dt.due_type_name,
			"due_type_code": dt.due_type_code,
			"calculation_method": charge.calculation_method,
			"disabled_reason": _get_disabled_reason(charge.calculation_method),
		})

	return {"charges": charges}


# ---------------------------------------------------------------------------
# Previous meter reading  (source: GET /api/contracts/[id]/previous-reading)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_previous_reading(name, due_type=None):
	"""Get previous meter reading for a contract/due_type.

	Source: ``GET /api/contracts/[id]/previous-reading``.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	if not due_type:
		frappe.throw(frappe._("نوع الالتزام مطلوب"))

	# Source: previous-reading/route.ts:26-28 — unit presence check
	if not contract.unit:
		frappe.throw(frappe._("العقد لا يحتوي على وحدة"))

	reading = get_previous_meter_reading(name, contract.unit, due_type)
	return {"previous_meter_reading": reading}


# ---------------------------------------------------------------------------
# Contract cancellation settlement summary (for detail page alerts)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_cancellation_settlement(contract=None, name=None):
	"""Get cancellation settlement summary for a contract.

	Used by the contract detail page to show pending/completed settlement alerts.
	Returns ``{ id, name, status, unresolved_count }`` or ``None``.
	"""
	contract_name = contract or name
	if not contract_name:
		frappe.throw(frappe._("معرف العقد مطلوب"))

	if not frappe.db.exists("DocType", "Contract Cancellation Settlement"):
		return None

	settlement_name = frappe.db.get_value(
		"Contract Cancellation Settlement", {"contract": contract_name}, "name"
	)
	if not settlement_name:
		return None

	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name).as_dict()
	# Source: contracts/[id]/route.ts:64-77 — unresolvedCount = approved auto-contract dues
	# with periodStart or periodEnd null
	unresolved_count = frappe.db.count(
		"Rental Due",
		filters={
			"contract": contract_name,
			"source_type": "auto_contract",
			"docstatus": 1,
			"period_start": ["is", "not set"],
		},
	) + frappe.db.count(
		"Rental Due",
		filters={
			"contract": contract_name,
			"source_type": "auto_contract",
			"docstatus": 1,
			"period_end": ["is", "not set"],
		},
	)
	return {
		"id": settlement_name,
		"name": settlement_name,
		"status": settlement.get("status") or "pending",
		"unresolved_count": unresolved_count,
	}


# ---------------------------------------------------------------------------
# Contract settlement  (source: GET /api/contracts/[id]/settlement)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_contract_settlement(name):
	"""Get cancellation settlement for a contract.

	Source: ``GET /api/contracts/[id]/settlement``.
	- totals is null when no settlement (source: route.ts:55)
	- unresolvedDues checks OR periodStart null OR periodEnd null (source: route.ts:36)
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	settlement_name = frappe.db.get_value(
		"Contract Cancellation Settlement", {"contract": name}, "name"
	)
	if not settlement_name:
		# Source: route.ts:55 — totals is null when no settlement
		return {"settlement": None, "unresolved_dues": [], "totals": None}

	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name).as_dict()

	# Source: route.ts:31-45 — unresolved dues: auto_contract, approved, periodStart OR periodEnd null
	unresolved_dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": name,
			"source_type": "auto_contract",
			"docstatus": 1,
			"period_start": ["is", "not set"],
		},
		fields=["name", "due_number", "due_date", "due_type"],
		order_by="due_date asc",
	)
	# Also check period_end null (OR condition)
	unresolved_dues_end = frappe.get_all(
		"Rental Due",
		filters={
			"contract": name,
			"source_type": "auto_contract",
			"docstatus": 1,
			"period_end": ["is", "not set"],
		},
		fields=["name", "due_number", "due_date", "due_type"],
		order_by="due_date asc",
	)
	# Merge and deduplicate
	seen = set()
	unresolved = []
	for d in unresolved_dues + unresolved_dues_end:
		if d.name not in seen:
			seen.add(d.name)
			dt_name = frappe.db.get_value("Rental Due Type", d.due_type, "due_type_name") if d.due_type else None
			unresolved.append({
				"dueId": d.name,
				"dueNumber": d.due_number,
				"dueType": dt_name,
				"dueDate": d.due_date,
				"blockingReason": "Missing periodStart or periodEnd",
			})

	# Totals (source: route.ts:55-65) — match original camelCase field names
	items = settlement.get("settlement_items", []) or settlement.get("items", [])
	totals = {
		"originalTotal": sum(float(it.get("original_amount") or 0) for it in items),
		"grossSettledTotal": sum(float(it.get("gross_settled_amount") or 0) for it in items),
		"settledTotal": sum(float(it.get("settled_amount") or 0) for it in items),
		"adjustmentTotal": sum(float(it.get("adjustment_amount") or 0) for it in items),
		"waiverSnapshotTotal": sum(float(it.get("active_waiver_amount") or 0) for it in items),
	}

	return {"settlement": settlement, "unresolved_dues": unresolved, "totals": totals}


# ---------------------------------------------------------------------------
# Contract attachments  (source: GET/POST/DELETE /api/contracts/[id]/attachments)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_attachments(name):
	"""List contract attachments.

	Source: ``GET /api/contracts/[id]/attachments``.
	Returns id, fileName, fileType, createdAt ordered by createdAt desc.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	# Order by creation desc (source: route.ts:14)
	attachments = []
	rows = frappe.db.get_all(
		"Contract Attachment",
		filters={"parent": name, "parenttype": "Lease Contract"},
		fields=["name", "file_name", "file_type", "creation"],
		order_by="creation desc",
	)
	for att in rows:
		attachments.append({
			"id": att.name,
			"name": att.name,
			"file_name": att.file_name,
			"file_type": att.file_type,
			"created_at": att.creation,
			"createdAt": att.creation,
		})

	return {"attachments": attachments}


@frappe.whitelist()
def get_attachment(name, attachment_id):
	"""Get a single contract attachment with file data.

	Source: ``GET /api/contracts/[id]/attachments/[attachmentId]``.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("read")

	for att in contract.contract_attachments:
		if att.name == attachment_id:
			return {
				"attachment": {
					"id": att.name,
					"contract": name,
					"file_name": att.file_name,
					"file_type": att.file_type,
					"file_data": att.file_data,
				}
			}

	frappe.throw(frappe._("المرفق غير موجود"))


@frappe.whitelist()
def add_attachment(name, attachments=None):
	"""Add attachments to a contract.

	Source: ``POST /api/contracts/[id]/attachments``.
	"""
	contract = frappe.get_doc("Lease Contract", name)
	contract.check_permission("write")

	if contract.is_archived:
		frappe.throw(frappe._("لا يمكن إضافة صور لعقد مؤرشف"))
	if contract.status in ("cancelled", "expired", "evicted"):
		frappe.throw(frappe._("لا يمكن إضافة صور لعقد في هذه الحالة"))

	if isinstance(attachments, str):
		import json
		attachments = json.loads(attachments)

	# Source: route.ts:31-33 — attachments must be an array
	if not isinstance(attachments, list):
		frappe.throw(frappe._("المرفقات يجب أن تكون مصفوفة"))

	created = []
	for att in attachments:
		# Source: route.ts:48-49 — defaults: fileName='صورة', fileType='image'
		contract.append("contract_attachments", {
			"file_name": att.get("file_name") or "صورة",
			"file_type": att.get("file_type") or "image",
			"file_data": att.get("file_data"),
		})

	contract.save(ignore_permissions=is_system_manager())

	# Return the created attachments (source: route.ts:56 returns created attachments)
	for a in contract.contract_attachments:
		created.append({
			"id": a.name,
			"file_name": a.file_name,
			"file_type": a.file_type,
		})
	return {"attachments": created}


# Alias for frontend compatibility
upload_attachments = add_attachment


@frappe.whitelist()
def delete_attachment(name=None, attachment_id=None, contract=None, attachment=None):
	"""Delete an attachment from a contract.

	Source: ``DELETE /api/contracts/[id]/attachments/[attachmentId]``.
	Accepts both (name, attachment_id) and (contract, attachment) parameter names
	for frontend compatibility.
	"""
	contract_name = name or contract
	attachment_name = attachment_id or attachment

	if not contract_name or not attachment_name:
		frappe.throw(frappe._("معرف العقد ومعرف المرفق مطلوبان"))

	contract_doc = frappe.get_doc("Lease Contract", contract_name)
	contract_doc.check_permission("write")

	if contract_doc.is_archived:
		frappe.throw(frappe._("لا يمكن حذف مرفقات عقد مؤرشف"))

	# Remove the attachment row
	found = False
	for i, att in enumerate(contract_doc.contract_attachments):
		if att.name == attachment_name:
			contract_doc.contract_attachments.pop(i)
			found = True
			break

	# Source: attachments/[attachmentId]/route.ts:28-47 — throw if not found
	if not found:
		frappe.throw(frappe._("المرفق غير موجود"))

	contract_doc.save(ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Expire contracts  (source: GET /api/contracts/expire)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def expire_contracts_api():
	"""Manual trigger to expire past contracts."""
	count = expire_contracts()
	return {"expired": count}
