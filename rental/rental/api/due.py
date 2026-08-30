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
	"""List dues with filters, pagination, and stats.

	Source: ``GET /api/dues`` (route.ts:20-203).
	"""
	from datetime import timedelta
	from frappe.utils import getdate

	account = get_current_rental_account()
	today = to_calendar_day(frappe.utils.today())

	# --- Date validation (source: route.ts:40-54) ---
	parsed_from = None
	parsed_to = None
	if from_date:
		parsed_from = to_calendar_day(from_date)
		if parsed_from.year < 1900:
			frappe.throw(frappe._("تاريخ البداية غير صالح"))
	if to_date:
		parsed_to = to_calendar_day(to_date)
		if parsed_to.year < 1900:
			frappe.throw(frappe._("تاريخ النهاية غير صالح"))
	if parsed_from and parsed_to and parsed_from > parsed_to:
		frappe.throw(frappe._("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية"))

	# --- Build filters ---
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

	# Status filter (source: route.ts:106-114)
	if status and status != "all":
		if status == "draft":
			filters["docstatus"] = 0
		elif status == "cancelled":
			filters["docstatus"] = 2
		elif status in ("due", "future"):
			filters["docstatus"] = 1

	# Date filter targets due_date (source: route.ts:116-131)
	due_date_filter = {}
	if parsed_from:
		due_date_filter[">="] = parsed_from
	if parsed_to:
		due_date_filter["<="] = parsed_to

	if status == "due":
		# due = approved & dueDate <= min(toDate, today)
		due_upper = parsed_to if parsed_to and parsed_to < today else today
		due_date_filter["<="] = due_upper
	elif status == "future":
		# future = approved & dueDate >= max(fromDate, tomorrow)
		tomorrow = today + timedelta(days=1)
		future_lower = parsed_from if parsed_from and parsed_from > tomorrow else tomorrow
		due_date_filter[">="] = future_lower

	if due_date_filter:
		filters["due_date"] = due_date_filter

	if search:
		filters["due_number"] = ["like", f"%{search}%"]

	# --- Fields (source: route.ts:56-89) ---
	fields = [
		"name", "due_number", "tenant", "contract", "building", "unit",
		"due_type", "source_type", "calculation_method",
		"transaction_date", "due_date", "period_label",
		"amount", "description", "docstatus",
		"reference_number", "cancellation_reason", "cancelled_by", "cancelled_at",
		"notes",
		"previous_meter_reading", "current_meter_reading", "meter_consumption",
		"unit_price", "creation",
	]

	is_print = int(print)
	page_size = 0 if is_print else int(limit)
	start = (int(page) - 1) * int(limit) if not is_print else 0

	dues = frappe.get_all(
		"Rental Due",
		filters=filters,
		fields=fields,
		order_by="creation desc",
		start=start,
		limit_page_length=page_size,
	)

	# Enrich with nested names (source: route.ts:83-88)
	for d in dues:
		if d.get("tenant"):
			d["tenant_name"] = frappe.db.get_value("Rental Tenant", d["tenant"], "full_name")
		if d.get("building"):
			d["building_name"] = frappe.db.get_value("Rental Building", d["building"], "building_name")
		if d.get("unit"):
			d["unit_number"] = frappe.db.get_value("Rental Unit", d["unit"], "unit_number")
		if d.get("contract"):
			d["contract_number"] = frappe.db.get_value("Lease Contract", d["contract"], "contract_number")
		if d.get("due_type"):
			dt = frappe.db.get_value("Rental Due Type", d["due_type"], ["due_type_name", "due_type_code"], as_dict=True)
			d["due_type_name"] = dt.due_type_name if dt else None
			d["due_type_code"] = dt.due_type_code if dt else None
		# Add waivers summary
		d["waivers"] = frappe.get_all(
			"Rental Due Waiver",
			filters={"due": d["name"]},
			fields=["name", "amount", "status"],
		)
		d["status"] = "approved" if d["docstatus"] == 1 else ("cancelled" if d["docstatus"] == 2 else "draft")

	# Stats (source: route.ts:162-168)
	stats = _get_due_stats(account, today)

	# Pagination (source: route.ts:140-160, 189-191)
	total = frappe.db.count("Rental Due", filters)
	pagination = {
		"page": int(page),
		"pageSize": int(limit),
		"total": total,
		"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
	}

	result = {"dues": dues, "pagination": pagination, "stats": stats}

	# Print mode (source: route.ts:170-186)
	if is_print:
		from rental.rental.services.balance_service import _db_sum
		print_total_amount = 0
		for d in dues:
			if d["docstatus"] != 2:  # non-cancelled
				active_waivers = _db_sum(
					"Rental Due Waiver",
					{"due": d["name"], "status": "active"},
					"amount",
				)
				print_total_amount += max(float(d.get("amount") or 0) - float(active_waivers or 0), 0)
		result["print"] = {"total": total, "totalAmount": round_money(print_total_amount)}

	return result


def _get_due_stats(account, today=None):
	"""Return due stats: total, draft, due, future, cancelled.

	Source: route.ts:162-168.
	total excludes cancelled (status != cancelled).
	"""
	if today is None:
		today = to_calendar_day(frappe.utils.today())
	base = {"rental_account": account} if account else {}
	return {
		"total": frappe.db.count("Rental Due", {**base, "docstatus": ["!=", 2]}),
		"draft": frappe.db.count("Rental Due", {**base, "docstatus": 0}),
		"due": frappe.db.count("Rental Due", {**base, "docstatus": 1, "due_date": ["<=", today]}),
		"future": frappe.db.count("Rental Due", {**base, "docstatus": 1, "due_date": [">", today]}),
		"cancelled": frappe.db.count("Rental Due", {**base, "docstatus": 2}),
	}


# ---------------------------------------------------------------------------
# Get single due  (source: GET /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_due(name):
	"""Get a single due with waivers and settlement info.

	Source: ``GET /api/dues/[id]`` ([id]/route.ts:7-30).
	"""
	if not frappe.db.exists("Rental Due", name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("read")

	result = due.as_dict()

	# Add status field from docstatus (source: get_dues route.ts:83-88 does the same)
	result["status"] = "approved" if result.get("docstatus") == 1 else ("cancelled" if result.get("docstatus") == 2 else "draft")

	# Enrich nested objects (source: route.ts:12-19)
	if result.get("tenant"):
		result["tenant_name"] = frappe.db.get_value("Rental Tenant", result["tenant"], "full_name")
	if result.get("building"):
		result["building_name"] = frappe.db.get_value("Rental Building", result["building"], "building_name")
	if result.get("unit"):
		result["unit_number"] = frappe.db.get_value("Rental Unit", result["unit"], "unit_number")
	if result.get("contract"):
		result["contract_number"] = frappe.db.get_value("Lease Contract", result["contract"], "contract_number")
	if result.get("due_type"):
		dt = frappe.db.get_value("Rental Due Type", result["due_type"], ["due_type_name", "due_type_code"], as_dict=True)
		result["due_type_name"] = dt.due_type_name if dt else None
		result["due_type_code"] = dt.due_type_code if dt else None

	# Add waivers (source: route.ts:18 — waivers: true = all fields)
	waivers = frappe.get_all(
		"Rental Due Waiver",
		filters={"due": name},
		fields=["name", "amount", "reason", "source_type", "status",
				"cancellation_reason", "cancelled_by", "cancelled_at",
				"created_by", "creation"],
		order_by="creation desc",
	)
	result["waivers"] = waivers

	# Add settlement item if linked (source: route.ts:19 — settlementItem: { include: { settlement: true } })
	if frappe.db.exists("DocType", "Cancellation Settlement Item"):
		settlement_item = frappe.db.get_value(
			"Cancellation Settlement Item", {"due": name},
			["name", "decision", "status", "gross_settled_amount"],
			as_dict=True,
		)
		if settlement_item:
			# Include the parent settlement
			settlement_name = frappe.db.get_value("Cancellation Settlement Item", settlement_item.name, "parent")
			if settlement_name and frappe.db.exists("Contract Cancellation Settlement", settlement_name):
				settlement_item["settlement"] = frappe.db.get_value(
					"Contract Cancellation Settlement", settlement_name,
					["name", "status"], as_dict=True,
				)
		result["settlement_item"] = settlement_item

	return result


# ---------------------------------------------------------------------------
# Create due  (source: POST /api/dues)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_due(**kwargs):
	"""Create a manual or additional due.

	Source: ``POST /api/dues`` (route.ts:205-389).
	"""
	account = get_current_rental_account()

	contract_name = kwargs.get("contract")
	due_type_name = kwargs.get("due_type")
	due_kind = kwargs.get("due_kind", "contractual")  # contractual or additional

	# Required fields (source: dueSchema validation.ts:196-226)
	if not contract_name:
		frappe.throw(frappe._("العقد مطلوب"))
	if not due_type_name:
		frappe.throw(frappe._("نوع الالتزام مطلوب"))
	if not kwargs.get("due_date"):
		frappe.throw(frappe._("تاريخ الالتزام مطلوب"))

	# Additional dues require non-empty description (source: validation.ts:218-225)
	if due_kind == "additional":
		if not kwargs.get("description") or not str(kwargs.get("description")).strip():
			frappe.throw(frappe._("يرجى إدخال سبب الالتزام الإضافي"))

	# Amount validation if provided (source: validation.ts:209-217)
	if kwargs.get("amount") and str(kwargs.get("amount")).strip():
		try:
			amt = float(kwargs.get("amount"))
			if amt <= 0:
				frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))
		except (ValueError, TypeError):
			frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))

	# Due type existence check (source: route.ts:218-221)
	due_type = frappe.db.get_value(
		"Rental Due Type", due_type_name,
		["due_type_code", "is_system", "is_active"],
		as_dict=True,
	)
	if not due_type:
		frappe.throw(frappe._("نوع الالتزام غير موجود"))

	# Rent due type cannot be created manually (source: route.ts:222-224)
	if due_type.due_type_code == "rent":
		frappe.throw(frappe._("لا يمكن إنشاء التزام إيجار يدويًا"))

	# Due type must be active (source: route.ts:225-227)
	if not due_type.is_active:
		frappe.throw(frappe._("نوع الالتزام غير فعال"))

	# Contract must exist (source: route.ts:229-235)
	contract = frappe.db.get_value(
		"Lease Contract", contract_name,
		["status", "tenant", "building", "unit", "rental_account"],
		as_dict=True,
	)
	if not contract:
		frappe.throw(frappe._("العقد غير موجود"))
	if contract.status not in ("active", "expired"):
		frappe.throw(frappe._("لا يمكن إنشاء الالتزام لعقد غير نشط أو منتهٍ"))

	# Validate tenant/unit match (source: route.ts:240-245)
	if kwargs.get("unit") and kwargs.get("unit") != contract.unit:
		frappe.throw(frappe._("الوحدة المُرسلة لا تتطابق مع وحدة العقد"))
	if kwargs.get("tenant") and kwargs.get("tenant") != contract.tenant:
		frappe.throw(frappe._("المستأجر المُرسل لا يتطابق مع مستأجر العقد"))

	# Meter payload check (source: route.ts:253-257)
	has_meter_payload = bool(
		kwargs.get("previous_meter_reading")
		or kwargs.get("current_meter_reading")
		or kwargs.get("unit_price")
	)

	amount = 0
	meter_fields = None

	if due_kind == "additional":
		# Additional dues (source: route.ts:259-279)
		if due_type.is_system or due_type.due_type_code in ("rent", "electricity", "water"):
			frappe.throw(frappe._("لا يمكن إنشاء نوع نظامي كالتزام إضافي"))
		if not due_type.is_active:
			frappe.throw(frappe._("نوع الالتزام غير فعال"))
		charge_exists = frappe.db.exists(
			"Contract Charge",
			{"parent": contract_name, "parenttype": "Lease Contract", "due_type": due_type_name},
		)
		if charge_exists:
			frappe.throw(frappe._("هذا النوع مسجل في العقد؛ يجب إنشاؤه كالتزام تعاقدي"))
		if has_meter_payload:
			frappe.throw(frappe._("التزام إضافي لا يستخدم قراءات العداد"))
		# Amount required and > 0 (source: route.ts:272-278)
		if not kwargs.get("amount") or str(kwargs.get("amount")).strip() == "":
			frappe.throw(frappe._("المبلغ مطلوب"))
		manual_amount = float(kwargs.get("amount"))
		if manual_amount <= 0:
			frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))
		amount = manual_amount
	else:
		# Contractual (source: route.ts:280-351)
		charge = frappe.db.get_value(
			"Contract Charge",
			{"parent": contract_name, "parenttype": "Lease Contract", "due_type": due_type_name},
			["responsibility", "payment_by", "calculation_method"],
			as_dict=True,
		)
		if not charge:
			frappe.throw(frappe._("نوع الالتزام غير مسجل في العقد"))
		if charge.responsibility != "tenant":
			frappe.throw(frappe._("هذه الخدمة ليست مسؤولية المستأجر في العقد"))
		if charge.payment_by == "tenant":
			frappe.throw(frappe._("هذه الخدمة تُدفع مباشرة من المستأجر ولا يمكن إنشاؤها كالتزام"))

		calc_method = charge.calculation_method

		if calc_method == "metered":
			# Metered due (source: route.ts:292-319)
			if not kwargs.get("current_meter_reading") or str(kwargs.get("current_meter_reading")).strip() == "":
				frappe.throw(frappe._("القراءة الحالية مطلوبة للالتزامات المترية"))
			if not kwargs.get("unit_price") or str(kwargs.get("unit_price")).strip() == "":
				frappe.throw(frappe._("سعر الوحدة مطلوب للالتزامات المترية"))

			meter_check = can_create_meter_due(contract_name, due_type_name)
			if not meter_check.get("ok"):
				frappe.throw(meter_check.get("error") or frappe._("لا يمكن إنشاء التزام مترية قبل بدء العقد"))

			prev_reading_str = get_previous_meter_reading(
				contract_name, contract.unit, due_type_name
			)
			prev_reading = float(prev_reading_str or 0)
			curr_reading = float(kwargs.get("current_meter_reading"))
			unit_price = float(kwargs.get("unit_price"))

			if curr_reading < prev_reading:
				frappe.throw(frappe._("القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"))
			if unit_price <= 0:
				frappe.throw(frappe._("سعر الوحدة يجب أن يكون أكبر من صفر"))

			consumption = curr_reading - prev_reading
			amount = round_money(consumption * unit_price)
			meter_fields = {
				"prev": str(prev_reading),
				"curr": str(curr_reading),
				"consumption": str(consumption),
				"unit_price": unit_price,
			}

		elif calc_method == "actual_bill":
			# Actual bill (source: route.ts:322-331)
			if has_meter_payload:
				frappe.throw(frappe._("طريقة الاحتساب المختارة لا تستخدم قراءات العداد"))
			manual_amount = float(kwargs.get("amount") or 0)
			if manual_amount <= 0:
				frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))
			amount = manual_amount

		elif calc_method == "on_demand":
			# On demand (source: route.ts:334-343)
			if has_meter_payload:
				frappe.throw(frappe._("طريقة الاحتساب المختارة لا تستخدم قراءات العداد"))
			manual_amount = float(kwargs.get("amount") or 0)
			if manual_amount <= 0:
				frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))
			amount = manual_amount

		elif calc_method == "fixed_periodic":
			frappe.throw(frappe._("التزامات الخدمات الدورية الثابتة تُنشأ تلقائيًا من العقد"))

		else:
			frappe.throw(frappe._("طريقة الاحتساب غير صالحة للإنشاء اليدوي"))

	source_type = "additional" if due_kind == "additional" else "manual_contract"
	calculation_method = "on_demand" if due_kind == "additional" else (charge.calculation_method if due_kind != "additional" else "on_demand")

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
		"amount": amount,
		"source_type": source_type,
		"calculation_method": calculation_method,
		"notes": kwargs.get("notes"),
	}

	if meter_fields:
		due_data["previous_meter_reading"] = meter_fields["prev"]
		due_data["current_meter_reading"] = meter_fields["curr"]
		due_data["meter_consumption"] = meter_fields["consumption"]
		due_data["unit_price"] = meter_fields["unit_price"]

	due = frappe.get_doc(due_data)
	due.insert(ignore_permissions=is_system_manager())

	return due.name


# ---------------------------------------------------------------------------
# Update due  (source: PUT /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def update_due(name, **kwargs):
	"""Update a manual/additional draft due.

	Source: ``PUT /api/dues/[id]`` ([id]/route.ts:34-123).
	"""
	if not frappe.db.exists("Rental Due", name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("write")

	# Source type check (source: route.ts:52)
	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("لا يمكن تعديل الالتزامات الناتجة من العقود"))
	# Draft check (source: route.ts:53)
	if due.docstatus != 0:
		frappe.throw(frappe._("لا يمكن تعديل إلا المسودات"))

	# Forbidden identity keys — must throw, not silently delete (source: route.ts:55-60)
	forbidden_keys = ["due_type", "contract", "tenant", "unit", "source_type", "calculation_method"]
	for k in forbidden_keys:
		if k in kwargs and kwargs[k] is not None:
			frappe.throw(frappe._("لا يمكن تغيير بيانات هوية الالتزام"))

	# Additional dues require non-empty description (source: route.ts:62-66)
	if due.source_type == "additional":
		if "description" in kwargs and (not kwargs["description"] or not str(kwargs["description"]).strip()):
			frappe.throw(frappe._("يرجى إدخال سبب الالتزام الإضافي"))

	is_meter_due = due.calculation_method == "metered"

	# Update allowed fields
	if kwargs.get("due_date"):
		due.due_date = kwargs.get("due_date")
		due.transaction_date = kwargs.get("due_date")  # source: route.ts:71
	if "description" in kwargs and kwargs["description"] is not None:
		due.description = kwargs["description"]

	if is_meter_due:
		# Metered revalidation and recomputation (source: route.ts:74-92)
		prev_reading = float(due.previous_meter_reading or 0)
		curr_reading_str = kwargs.get("current_meter_reading", due.current_meter_reading)
		unit_price_str = kwargs.get("unit_price", str(due.unit_price or 0))
		curr_reading = float(curr_reading_str or 0)
		unit_price = float(unit_price_str or 0)

		if curr_reading < prev_reading:
			frappe.throw(frappe._("القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"))
		if unit_price <= 0:
			frappe.throw(frappe._("سعر الوحدة يجب أن يكون أكبر من صفر"))

		consumption = curr_reading - prev_reading
		due.amount = round_money(consumption * unit_price)
		due.current_meter_reading = str(curr_reading)
		due.meter_consumption = str(consumption)
		due.unit_price = unit_price
	else:
		# Non-metered amount validation (source: route.ts:94-100)
		if kwargs.get("amount") is not None:
			amount = float(kwargs.get("amount") or 0)
			if amount <= 0:
				frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))
			due.amount = amount

	if kwargs.get("notes") is not None:
		due.notes = kwargs.get("notes")

	due.save(ignore_permissions=is_system_manager())
	return due.name


# ---------------------------------------------------------------------------
# Delete due  (source: DELETE /api/dues/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def delete_due(name):
	"""Delete a manual/additional draft due.

	Source: ``DELETE /api/dues/[id]`` ([id]/route.ts:125-142).
	"""
	if not frappe.db.exists("Rental Due", name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("delete")

	# Check order: status first, then source type (source: route.ts:130-131)
	if due.docstatus != 0:
		frappe.throw(frappe._("لا يمكن حذف إلا مسودات الالتزامات"))
	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("لا يمكن حذف الالتزامات الناتجة من العقود"))

	frappe.delete_doc("Rental Due", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Approve due  (source: POST /api/dues/[id]/approve)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def approve_due(name):
	"""Approve a manual/additional draft due.

	Source: ``POST /api/dues/[id]/approve`` (approve/route.ts:11-183).
	"""
	if not frappe.db.exists("Rental Due", name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("submit")

	# Source type check (source: route.ts:25)
	if due.source_type not in ("manual", "manual_contract", "additional"):
		frappe.throw(frappe._("لا يمكن اعتماد هذا النوع من الالتزامات"))
	# Draft check (source: route.ts:26)
	if due.docstatus != 0:
		frappe.throw(frappe._("يمكن اعتماد المسودات فقط"))

	# Contract must exist and be active/expired (source: route.ts:28-32)
	if not due.contract or not frappe.db.exists("Lease Contract", due.contract):
		frappe.throw(frappe._("العقد غير موجود"), frappe.DoesNotExistError)
	contract_status = frappe.db.get_value("Lease Contract", due.contract, "status")
	if contract_status not in ("active", "expired"):
		frappe.throw(frappe._("لا يمكن اعتماد الالتزام لعقد غير نشط أو منتهٍ"))

	is_additional = due.source_type == "additional"
	due_type = frappe.db.get_value(
		"Rental Due Type", due.due_type,
		["due_type_code", "is_system", "is_active"],
		as_dict=True,
	)

	# Find matching contract charge
	charge = frappe.db.get_value(
		"Contract Charge",
		{"parent": due.contract, "parenttype": "Lease Contract", "due_type": due.due_type},
		["responsibility", "payment_by", "calculation_method"],
		as_dict=True,
	) if not is_additional else None

	# Additional validations (source: route.ts:38-50)
	if is_additional:
		if not due_type or due_type.is_system or due_type.due_type_code in ("rent", "electricity", "water"):
			frappe.throw(frappe._("لا يمكن اعتماد نوع نظامي كالتزام إضافي"))
		if not due_type.is_active:
			frappe.throw(frappe._("نوع الالتزام غير فعال"))
		if charge:
			frappe.throw(frappe._("هذا النوع مسجل في العقد؛ يجب إنشاؤه كالتزام تعاقدي"))
		if not (due.description and due.description.strip()):
			frappe.throw(frappe._("يرجى إدخال سبب الالتزام الإضافي"))
	else:
		# Contractual validations (source: route.ts:52-63)
		if not charge:
			frappe.throw(frappe._("نوع الالتزام غير مسجل في العقد"))
		if charge.responsibility != "tenant":
			frappe.throw(frappe._("هذه الخدمة ليست مسؤولية المستأجر في العقد"))
		if charge.payment_by == "tenant":
			frappe.throw(frappe._("هذه الخدمة تُدفع مباشرة من المستأجر ولا يمكن اعتمادها كالتزام"))
		if charge.calculation_method == "fixed_periodic":
			frappe.throw(frappe._("التزامات الخدمات الدورية الثابتة تُنشأ تلقائيًا من العقد"))

	calculation_method = "on_demand" if is_additional else charge.calculation_method
	is_meter_due = calculation_method == "metered"

	# Metered validations (source: route.ts:76-118)
	if is_meter_due:
		# Complete meter data check (source: route.ts:77-78)
		if not due.current_meter_reading or due.unit_price is None:
			frappe.throw(frappe._("بيانات العداد غير مكتملة"))

		prev_reading_str = get_previous_meter_reading(due.contract, due.unit, due.due_type)
		prev_reading = float(prev_reading_str or 0)
		curr_reading = float(due.current_meter_reading or 0)
		unit_price = float(due.unit_price or 0)

		if curr_reading < prev_reading:
			frappe.throw(frappe._("القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"))
		if unit_price <= 0:
			frappe.throw(frappe._("سعر الوحدة يجب أن يكون أكبر من صفر"))

		# Check no newer approved meter reading exists (source: route.ts:93-112)
		newer_dues = frappe.get_all(
			"Rental Due",
			filters={
				"contract": due.contract,
				"unit": due.unit,
				"due_type": due.due_type,
				"name": ["!=", name],
				"current_meter_reading": ["is", "set"],
				"docstatus": 1,
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

		# Recompute amount and meter fields (source: route.ts:114-118)
		consumption = curr_reading - prev_reading
		due.amount = round_money(consumption * unit_price)
		due.previous_meter_reading = str(prev_reading)
		due.current_meter_reading = str(curr_reading)
		due.meter_consumption = str(consumption)
		due.unit_price = unit_price
	else:
		# Non-metered: amount must be > 0 for additional/actual_bill/on_demand (source: route.ts:120-125)
		if is_additional or calculation_method in ("actual_bill", "on_demand"):
			if not due.amount or float(due.amount) <= 0:
				frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))

	# Submit (on_submit hook generates due_number and updates unit meter)
	due.submit()
	return due.name


# ---------------------------------------------------------------------------
# Cancel due  (source: POST /api/dues/[id]/cancel)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def cancel_due_api(name, reason):
	"""Cancel a manual due.

	Source: ``POST /api/dues/[id]/cancel`` (cancel/route.ts:8-41).
	"""
	# Reason required (source: cancellationSchema validation.ts:322-324)
	if not reason or not str(reason).strip():
		frappe.throw(frappe._("سبب الإلغاء مطلوب"))

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("cancel")

	cancelled = cancel_due(name, reason, frappe.session.user)
	return {"due": cancelled}


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
	"""Create a manual waiver for an auto_contract approved due.

	Source: ``POST /api/dues/[id]/waivers`` (waivers/route.ts:32-99).
	"""
	account = get_current_rental_account()

	# Validation: amount required and > 0 (source: dueWaiverSchema validation.ts:326-335)
	if not amount or str(amount).strip() == "":
		frappe.throw(frappe._("مبلغ الإعفاء مطلوب"))
	waiver_amount = float(amount)
	if waiver_amount <= 0:
		frappe.throw(frappe._("مبلغ الإعفاء يجب أن يكون أكبر من صفر"))

	# Validation: reason required (source: dueWaiverSchema validation.ts:328)
	if not reason or str(reason).strip() == "":
		frappe.throw(frappe._("سبب الإعفاء مطلوب"))

	if not frappe.db.exists("Rental Due", name):
		frappe.throw(frappe._("الالتزام غير موجود"), frappe.DoesNotExistError)

	due = frappe.get_doc("Rental Due", name)
	due.check_permission("read")

	# Source type check (source: route.ts:53-55)
	if due.source_type != "auto_contract":
		frappe.throw(frappe._("لا يمكن إعفاء إلا الالتزامات الناتجة من العقود"))
	# Status check (source: route.ts:57-59)
	if due.docstatus != 1:
		frappe.throw(frappe._("لا يمكن إعفاء إلا التزامات معتمدة"))

	# Check not linked to completed settlement (source: route.ts:61-71)
	if frappe.db.exists("DocType", "Cancellation Settlement Item"):
		settlement_item = frappe.db.get_value(
			"Cancellation Settlement Item",
			{"due": name},
			["name", "parent"],
			as_dict=True,
		)
		if settlement_item and settlement_item.parent:
			settlement_status = frappe.db.get_value(
				"Contract Cancellation Settlement", settlement_item.parent, "status"
			)
			if settlement_status == "completed":
				frappe.throw(frappe._("لا يمكن تعديل إعفاءات هذا الالتزام بعد اكتمال تسوية إلغاء العقد"))

	# Waiver amount cap: activeWaivers + amount <= due.amount (source: route.ts:73-79)
	from rental.rental.services.balance_service import _db_sum
	active_waivers = _db_sum(
		"Rental Due Waiver",
		{"due": name, "status": "active"},
		"amount",
	)
	if active_waivers + waiver_amount > float(due.amount):
		frappe.throw(frappe._("إجمالي الإعفاءات لا يجوز أن يتجاوز مبلغ الالتزام"))

	waiver = frappe.get_doc({
		"doctype": "Rental Due Waiver",
		"rental_account": account,
		"due": name,
		"amount": waiver_amount,
		"reason": reason,
		"source_type": "manual",
		"status": "active",
		"created_by": frappe.session.user,
	})
	waiver.insert(ignore_permissions=is_system_manager())
	return waiver.name


@frappe.whitelist()
def cancel_waiver(due_name, waiver_name, reason):
	"""Cancel a manual waiver.

	Source: ``POST /api/dues/[id]/waivers/[waiverId]/cancel``
	([waiverId]/cancel/route.ts:7-63).
	"""
	# Reason required (source: dueWaiverCancelSchema validation.ts:337-339)
	if not reason or str(reason).strip() == "":
		frappe.throw(frappe._("سبب إلغاء الإعفاء مطلوب"))

	waiver = frappe.get_doc("Rental Due Waiver", waiver_name)
	waiver.check_permission("write")

	# Waiver/due match check (source: route.ts:24-26)
	if not waiver or waiver.due != due_name:
		frappe.throw(frappe._("الإعفاء غير موجود"), frappe.DoesNotExistError)

	# Source type check (source: route.ts:28-33)
	if waiver.source_type == "contract_cancellation":
		frappe.throw(frappe._("لا يمكن إلغاء إعفاء تسوية إلغاء العقد"))

	# Status check — only active waivers can be cancelled (source: route.ts:35-37)
	if waiver.status != "active":
		frappe.throw(frappe._("يمكن إلغاء الإعفاءات الفعالة فقط"))

	# Check not linked to completed settlement (source: route.ts:39-44)
	if waiver.settlement_item:
		settlement_name = frappe.db.get_value("Cancellation Settlement Item", waiver.settlement_item, "parent")
		if settlement_name:
			settlement_status = frappe.db.get_value(
				"Contract Cancellation Settlement", settlement_name, "status"
			)
			if settlement_status == "completed":
				frappe.throw(frappe._("لا يمكن تعديل إعفاءات هذا الالتزام بعد اكتمال تسوية إلغاء العقد"))

	frappe.db.set_value("Rental Due Waiver", waiver_name, {
		"status": "cancelled",
		"cancellation_reason": reason,
		"cancelled_by": frappe.session.user,
		"cancelled_at": frappe.utils.now(),
	}, update_modified=False)

	# Return the cancelled waiver (source: route.ts:56)
	cancelled = frappe.get_doc("Rental Due Waiver", waiver_name)
	return {"waiver": cancelled.as_dict()}
