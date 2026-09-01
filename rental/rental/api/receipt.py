"""Receipts API: CRUD, approve, cancel.

Ported from ``src/app/api/receipts/**``.
Source of truth: ``Rental_Management_olde/src/app/api/receipts/**``.
"""

from __future__ import annotations

import frappe
from frappe.utils import getdate

from rental.rental.utils.account import get_current_rental_account, is_system_manager
from rental.rental.services.archive_service import (
	ensure_contract_not_archived,
	get_archived_contract_names,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enrich_receipt(r):
	"""Add tenant_name, building_name, unit_number, contract_number, status to a receipt dict.

	Mirrors the original ``receiptSelect`` (route.ts:68-80) which returns nested
	``tenant: { fullName }``, ``building: { name }``, ``unit: { unitNumber }``,
	``contract: { contractNumber }``.
	"""
	if r.get("tenant"):
		r["tenant_name"] = frappe.db.get_value("Rental Tenant", r["tenant"], "full_name")
	if r.get("building"):
		r["building_name"] = frappe.db.get_value("Rental Building", r["building"], "building_name")
	if r.get("unit"):
		r["unit_number"] = frappe.db.get_value("Rental Unit", r["unit"], "unit_number")
	if r.get("contract"):
		r["contract_number"] = frappe.db.get_value("Lease Contract", r["contract"], "contract_number")
	r["status"] = "approved" if r.get("docstatus") == 1 else ("cancelled" if r.get("docstatus") == 2 else "draft")
	return r


def _receipt_as_dict(name):
	"""Return a receipt dict with resolved relation names (source: GET /api/receipts/[id])."""
	receipt = frappe.get_doc("Rental Receipt", name)
	receipt.check_permission("read")
	data = receipt.as_dict()
	_enrich_receipt(data)
	return data


# ---------------------------------------------------------------------------
# List receipts  (source: GET /api/receipts)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_receipts(
	tenant=None,
	contract=None,
	payment_method=None,
	from_date=None,
	to_date=None,
	status=None,
	search=None,
	print=0,
	page=1,
	limit=15,
):
	"""List receipts with filters, pagination, and stats."""
	account = get_current_rental_account()

	# Date range validation (source: route.ts:30-31)
	if from_date and to_date and getdate(from_date) > getdate(to_date):
		frappe.throw(frappe._("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية"))

	# Use list-style filters to support multiple conditions on the same field
	# (e.g. receipt_date >= X AND receipt_date <= Y). Dict-style would overwrite
	# the first condition when the second is set. Source: route.ts:34-53.
	filters = []
	if account:
		filters.append(["rental_account", "=", account])

	if tenant:
		filters.append(["tenant", "=", tenant])
	if contract:
		filters.append(["contract", "=", contract])
	if payment_method and payment_method != "all":
		filters.append(["payment_method", "=", payment_method])
	if search:
		filters.append(["receipt_number", "like", f"%{search}%"])

	# Date filters (source: route.ts:44-53)
	# receipt_date is a Date field, so end-of-day adjustment is not needed
	# (old project used setUTCHours(23,59,59,999) because Prisma stored DateTime).
	if from_date:
		filters.append(["receipt_date", ">=", getdate(from_date)])
	if to_date:
		filters.append(["receipt_date", "<=", getdate(to_date)])

	if status == "approved":
		filters.append(["docstatus", "=", 1])
	elif status == "cancelled":
		filters.append(["docstatus", "=", 2])
	elif status == "draft":
		filters.append(["docstatus", "=", 0])

	# Exclude receipts of archived contracts from the default operational list.
	# When a specific contract is requested (e.g. the archived-contract detail
	# page), we honor it so the historical file remains readable.
	if not contract:
		archived_contracts = get_archived_contract_names(account)
		if archived_contracts:
			filters.append(["contract", "not in", archived_contracts])

	fields = [
		"name", "receipt_number", "tenant", "contract", "building", "unit",
		"receipt_date", "amount", "payment_method", "reference_number",
		"cheque_date", "bank_name", "attachment", "docstatus", "notes",
		"cancellation_reason", "cancelled_by", "cancelled_at",
	]

	page_size = 0 if int(print) else int(limit)
	start = (int(page) - 1) * int(limit) if not int(print) else 0

	receipts = frappe.get_all(
		"Rental Receipt",
		filters=filters,
		fields=fields,
		order_by="creation desc",
		start=start,
		limit_page_length=page_size,
	)

	for r in receipts:
		_enrich_receipt(r)

	total = frappe.db.count("Rental Receipt", filters)
	stats = _get_receipt_stats(account)

	pagination = {
		"page": int(page),
		"pageSize": int(limit),
		"total": total,
		"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
	}

	result = {"receipts": receipts, "pagination": pagination, "stats": stats}

	# B10: print mode returns print.total + print.totalAmount (source: route.ts:95-115).
	if int(print):
		print_total = total
		print_total_amount = sum(
			float(r.get("amount") or 0)
			for r in receipts
			if r["docstatus"] == 1  # approved only
		)
		result["print"] = {"total": print_total, "totalAmount": round(print_total_amount, 2)}

	return result


def _get_receipt_stats(account):
	base = {"rental_account": account} if account else {}
	# Exclude archived contracts from operational stats.
	archived = get_archived_contract_names(account)
	if archived:
		base["contract"] = ["not in", archived]
	return {
		"total": frappe.db.count("Rental Receipt", base),
		"approved": frappe.db.count("Rental Receipt", {**base, "docstatus": 1}),
		"draft": frappe.db.count("Rental Receipt", {**base, "docstatus": 0}),
		"cancelled": frappe.db.count("Rental Receipt", {**base, "docstatus": 2}),
	}


# ---------------------------------------------------------------------------
# Get single receipt  (source: GET /api/receipts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_receipt(name):
	"""Get a single receipt with resolved relation names."""
	if not frappe.db.exists("Rental Receipt", name):
		frappe.throw(frappe._("سند القبض غير موجود"), frappe.DoesNotExistError)
	return _receipt_as_dict(name)


# ---------------------------------------------------------------------------
# Create receipt  (source: POST /api/receipts)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_receipt(**kwargs):
	"""Create a draft receipt linked to a contract."""
	account = get_current_rental_account()

	# Required-field validation (source: receiptSchema, validation.ts:245-259)
	if not kwargs.get("tenant"):
		frappe.throw(frappe._("المستأجر مطلوب"))
	if not kwargs.get("contract"):
		frappe.throw(frappe._("العقد مطلوب"))
	if not kwargs.get("receipt_date"):
		frappe.throw(frappe._("تاريخ السند مطلوب"))
	if not kwargs.get("amount"):
		frappe.throw(frappe._("المبلغ مطلوب"))
	payment_method = kwargs.get("payment_method")
	if payment_method not in ("cash", "cheque"):
		frappe.throw(frappe._("طريقة الدفع غير صالحة"))

	# Archive protection — blocks creating receipts for archived contracts.
	ensure_contract_not_archived(kwargs.get("contract"), action="إنشاء سند قبض")

	receipt_data = {
		"doctype": "Rental Receipt",
		"rental_account": account,
		"tenant": kwargs.get("tenant"),
		"contract": kwargs.get("contract"),
		"receipt_date": kwargs.get("receipt_date"),
		"amount": kwargs.get("amount"),
		"payment_method": payment_method,
		"reference_number": kwargs.get("reference_number"),
		"cheque_date": kwargs.get("cheque_date"),
		"bank_name": kwargs.get("bank_name"),
		"attachment": kwargs.get("attachment"),
		"notes": kwargs.get("notes"),
	}

	receipt = frappe.get_doc(receipt_data)
	receipt.insert(ignore_permissions=is_system_manager())
	return _receipt_as_dict(receipt.name)


# ---------------------------------------------------------------------------
# Update receipt  (source: PUT /api/receipts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def update_receipt(name, **kwargs):
	"""Update a draft receipt."""
	if not frappe.db.exists("Rental Receipt", name):
		frappe.throw(frappe._("سند القبض غير موجود"), frappe.DoesNotExistError)

	receipt = frappe.get_doc("Rental Receipt", name)
	receipt.check_permission("write")

	if receipt.docstatus != 0:
		frappe.throw(frappe._("لا يمكن تعديل إلا مسودات سند القبض"))

	# Forbidden identity keys — reject, do not silently drop (source: route.ts:34-37)
	forbidden = ["tenant", "contract", "building", "unit", "rental_account", "receipt_number"]
	for f in forbidden:
		if f in kwargs:
			frappe.throw(frappe._("لا يمكن تغيير بيانات هوية السند"))

	# Archive protection — blocks editing receipts of archived contracts.
	ensure_contract_not_archived(receipt.contract, action="تعديل سند قبض")

	# Determine effective payment method (source: route.ts:52)
	payment_method = kwargs.get("payment_method")
	if payment_method is None:
		payment_method = receipt.payment_method
	elif payment_method not in ("cash", "cheque"):
		frappe.throw(frappe._("طريقة الدفع غير صالحة"))

	# receipt_date — only update if provided and non-empty (source: route.ts:55-57)
	if "receipt_date" in kwargs and kwargs["receipt_date"] and str(kwargs["receipt_date"]).strip():
		receipt.receipt_date = kwargs["receipt_date"]

	# amount — only update if provided and non-empty (source: route.ts:58-60)
	if "amount" in kwargs and kwargs["amount"] and str(kwargs["amount"]).strip():
		receipt.amount = kwargs["amount"]

	# payment_method — always set (source: route.ts:62)
	receipt.payment_method = payment_method

	# attachment — set to provided (incl. None) or keep existing (source: route.ts:63)
	if "attachment" in kwargs:
		receipt.attachment = kwargs["attachment"]

	# notes — set to provided (incl. None) or keep existing (source: route.ts:64)
	if "notes" in kwargs:
		receipt.notes = kwargs["notes"]

	# Cheque fields (source: route.ts:66-80)
	if payment_method == "cheque":
		reference_number = kwargs.get("reference_number")
		if reference_number is None:
			reference_number = receipt.reference_number
		if not reference_number or not str(reference_number).strip():
			frappe.throw(frappe._("رقم الشيك مطلوب عند اختيار طريقة الدفع شيك"))
		receipt.reference_number = reference_number
		if "cheque_date" in kwargs:
			receipt.cheque_date = kwargs["cheque_date"]
		if "bank_name" in kwargs:
			receipt.bank_name = kwargs["bank_name"]
	else:
		receipt.reference_number = None
		receipt.cheque_date = None
		receipt.bank_name = None

	receipt.save(ignore_permissions=is_system_manager())
	return _receipt_as_dict(receipt.name)


# ---------------------------------------------------------------------------
# Delete receipt  (source: DELETE /api/receipts/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def delete_receipt(name):
	"""Delete a draft receipt."""
	if not frappe.db.exists("Rental Receipt", name):
		frappe.throw(frappe._("سند القبض غير موجود"), frappe.DoesNotExistError)

	receipt = frappe.get_doc("Rental Receipt", name)
	receipt.check_permission("delete")

	if receipt.docstatus != 0:
		frappe.throw(frappe._("لا يمكن حذف إلا مسودات سند القبض"))

	# Archive protection — blocks deleting receipts of archived contracts.
	ensure_contract_not_archived(receipt.contract, action="حذف سند قبض")

	frappe.delete_doc("Rental Receipt", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Approve receipt  (source: POST /api/receipts/[id]/approve)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def approve_receipt(name):
	"""Approve a draft receipt and generate receipt_number."""
	if not frappe.db.exists("Rental Receipt", name):
		frappe.throw(frappe._("سند القبض غير موجود"), frappe.DoesNotExistError)

	receipt = frappe.get_doc("Rental Receipt", name)
	receipt.check_permission("submit")

	if receipt.docstatus != 0:
		frappe.throw(frappe._("يمكن اعتماد المسودات فقط"))

	# Archive protection — blocks approving receipts of archived contracts.
	ensure_contract_not_archived(receipt.contract, action="اعتماد سند قبض")

	# Validate amount (source: route.ts:53-55)
	if not receipt.amount or float(receipt.amount) <= 0:
		frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))

	# Validate receiptDate (source: route.ts:57-59)
	if not receipt.receipt_date:
		frappe.throw(frappe._("تاريخ السند غير صالح"))

	# Validate paymentMethod (source: route.ts:61-63)
	if receipt.payment_method not in ("cash", "cheque"):
		frappe.throw(frappe._("طريقة الدفع غير صالحة"))

	# Validate cheque reference_number (source: route.ts:65-67)
	if receipt.payment_method == "cheque":
		if not receipt.reference_number or not receipt.reference_number.strip():
			frappe.throw(frappe._("رقم الشيك مطلوب عند اختيار طريقة الدفع شيك"))

	receipt.submit()
	return _receipt_as_dict(receipt.name)


# ---------------------------------------------------------------------------
# Cancel receipt  (source: POST /api/receipts/[id]/cancel)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def cancel_receipt(name, reason):
	"""Cancel an approved receipt."""
	if not frappe.db.exists("Rental Receipt", name):
		frappe.throw(frappe._("سند القبض غير موجود"), frappe.DoesNotExistError)

	receipt = frappe.get_doc("Rental Receipt", name)
	receipt.check_permission("cancel")

	if receipt.docstatus != 1:
		frappe.throw(frappe._("يمكن إلغاء السندات المعتمدة فقط"))

	# Archive protection — blocks cancelling receipts of archived contracts.
	ensure_contract_not_archived(receipt.contract, action="إلغاء سند قبض")

	# Validate reason (source: cancellationSchema, validation.ts:322-324)
	# z.string().min(1) rejects empty/None but accepts non-empty strings incl. whitespace
	if not reason:
		frappe.throw(frappe._("سبب الإلغاء مطلوب"))

	receipt.cancellation_reason = reason
	receipt.cancel()
	return _receipt_as_dict(receipt.name)
