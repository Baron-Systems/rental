"""Cancellation Settlements API.

Ported from ``src/app/api/cancellation-settlements/**``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager
from rental.rental.services.contract_cancellation_settlement_service import (
	settle_contract_cancellation_item,
	complete_contract_cancellation_settlement,
	resolve_due,
	_get_unresolved_dues,
)
from rental.rental.services.archive_service import ensure_contract_not_archived


@frappe.whitelist()
def get_settlement(contract=None, name=None, settlement_id=None):
	"""Get cancellation settlement for a contract.

	Source: ``GET /api/contracts/[id]/settlement``.
	Returns ``{ settlement, unresolved_dues, totals }``.
	"""
	contract_name = contract or name
	if not contract_name and settlement_id:
		contract_name = frappe.db.get_value("Contract Cancellation Settlement", settlement_id, "contract")

	if not contract_name:
		frappe.throw(frappe._("معرف العقد مطلوب"))

	if not frappe.db.exists("DocType", "Contract Cancellation Settlement"):
		return {"settlement": None, "unresolved_dues": [], "totals": {}}

	settlement_name = frappe.db.get_value(
		"Contract Cancellation Settlement", {"contract": contract_name}, "name"
	)
	if not settlement_name:
		return {"settlement": None, "unresolved_dues": [], "totals": {}}

	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name).as_dict()

	# Get unresolved dues
	unresolved = _get_unresolved_dues(contract_name, settlement_name)

	# Enrich each settlement item with the full `due` object (source: route.ts:22
	# — Prisma include: { due: { include: { dueType: true, waivers: true } } }).
	# Frappe only stores the due Link (string); we fetch the related fields so the
	# frontend (ported from Prisma) can access item.due.due_type_name, etc.
	items = settlement.get("settlement_items", []) or settlement.get("items", [])
	for it in items:
		due_name = it.get("due")
		if due_name and isinstance(due_name, str):
			due = frappe.db.get_value(
				"Rental Due", due_name,
				["name", "due_number", "amount", "period_start", "period_end",
				 "due_date", "due_type", "source_type", "docstatus"],
				as_dict=True,
			) or {}
			due_type_name = None
			if due.get("due_type"):
				due_type_name = frappe.db.get_value("Rental Due Type", due["due_type"], "due_type_name")
			due["due_type_name"] = due_type_name
			# Fetch active waivers for this due (source: Prisma include waivers)
			waivers = frappe.get_all(
				"Rental Due Waiver",
				filters={"due": due_name, "status": "active"},
				fields=["name", "amount", "reason", "status", "source_type"],
			)
			due["waivers"] = waivers
			it["due"] = due
	# Expose `items` as an alias for `settlement_items` so the frontend (ported
	# from Prisma where the relation is named `items`) can use `settlement.items`.
	settlement["items"] = items
	totals = {
		"originalTotal": sum(float(it.get("original_amount") or 0) for it in items),
		"grossSettledTotal": sum(float(it.get("gross_settled_amount") or 0) for it in items),
		"settledTotal": sum(float(it.get("settled_amount") or 0) for it in items),
		"adjustmentTotal": sum(float(it.get("adjustment_amount") or 0) for it in items),
		"waiverSnapshotTotal": sum(float(it.get("active_waiver_amount") or 0) for it in items),
	}

	return {"settlement": settlement, "unresolved_dues": unresolved, "totals": totals}


@frappe.whitelist()
def complete_settlement(settlement_id=None, name=None):
	"""Complete a cancellation settlement.

	Source: ``GET /api/cancellation-settlements/[id]/complete``.
	"""
	sid = settlement_id or name
	if not sid:
		frappe.throw(frappe._("معرف التسوية مطلوب"))

	# Archive protection — blocks completing settlements for archived contracts.
	settlement_contract = frappe.db.get_value("Contract Cancellation Settlement", sid, "contract")
	ensure_contract_not_archived(settlement_contract, action="إكمال تسوية إلغاء العقد")

	account = get_current_rental_account()
	complete_contract_cancellation_settlement(sid, account)
	return {"settlement": sid, "status": "completed"}


@frappe.whitelist()
def settle_item(settlement_id=None, item_id=None, decision=None, gross_settled_amount=None, reason=None, item=None):
	"""Apply a decision to a settlement item.

	Source: ``PATCH /api/cancellation-settlements/[id]/items/[itemId]``.
	Accepts both ``item_id`` and ``item`` parameter names for frontend compatibility.
	If ``settlement_id`` is not provided, it is inferred from the item.
	"""
	# Source: items/[itemId]/route.ts:6 — VALID_DECISIONS
	VALID_DECISIONS = ["keep_full", "prorated", "manual_settlement", "full_waiver"]
	if decision not in VALID_DECISIONS:
		frappe.throw(frappe._("قرار التسوية غير صالح"))

	# Source: items/[itemId]/route.ts:19-22 — grossSettledAmount validation
	if gross_settled_amount is not None:
		try:
			gross_settled_amount = float(gross_settled_amount)
		except (TypeError, ValueError):
			frappe.throw(frappe._("المبلغ الإجمالي يجب أن يكون أكبر من أو يساوي صفر"))
		if gross_settled_amount < 0:
			frappe.throw(frappe._("المبلغ الإجمالي يجب أن يكون أكبر من أو يساوي صفر"))

	item_name = item_id or item
	if not item_name:
		frappe.throw(frappe._("معرف عنصر التسوية مطلوب"))

	# Infer settlement_id from the item if not provided
	if not settlement_id:
		settlement_id = frappe.db.get_value("Cancellation Settlement Item", item_name, "parent")
	if not settlement_id:
		frappe.throw(frappe._("تعذر تحديد التسوية لعنصر التسوية"))

	# Archive protection — blocks settling items for archived contracts.
	settlement_contract = frappe.db.get_value("Contract Cancellation Settlement", settlement_id, "contract")
	ensure_contract_not_archived(settlement_contract, action="تسوية عنصر إلغاء العقد")

	settle_contract_cancellation_item(
		settlement_id, item_name, decision, gross_settled_amount, reason
	)
	return {"item": item_name, "decision": decision}


# Alias for frontend compatibility
update_item_decision = settle_item


@frappe.whitelist()
def resolve_settlement_due(settlement_id=None, due_id=None, period_start=None, period_end=None, settlement=None):
	"""Reconcile a due by setting its period.

	Source: ``PATCH /api/cancellation-settlements/[id]/resolve-due``.
	Accepts both ``settlement_id`` and ``settlement`` parameter names for frontend compatibility.
	"""
	settlement_name = settlement_id or settlement
	# Validate required fields (source: route.ts:14-16)
	if not due_id or not period_start or not period_end:
		frappe.throw(frappe._("معرف الالتزام وتاريخا البداية والنهاية مطلوبان"))

	if not settlement_name:
		frappe.throw(frappe._("معرف التسوية مطلوب"))

	# Check settlement exists
	if not frappe.db.exists("Contract Cancellation Settlement", settlement_name):
		frappe.throw(frappe._("التسوية غير موجودة"))

	# Check settlement not completed
	settlement_status = frappe.db.get_value("Contract Cancellation Settlement", settlement_name, "status")
	if settlement_status == "completed":
		frappe.throw(frappe._("التسوية مكتملة ولا يمكن تعديلها"))

	# Validate period order
	from rental.rental.utils.date_utils import to_calendar_day
	ps = to_calendar_day(period_start)
	pe = to_calendar_day(period_end)
	if pe < ps:
		frappe.throw(frappe._("نهاية الفترة يجب أن تكون بعد بدايتها"))

	# Check due exists
	if not frappe.db.exists("Rental Due", due_id):
		frappe.throw(frappe._("الالتزام غير موجود"))

	# Check due belongs to the same contract as the settlement
	settlement_contract = frappe.db.get_value("Contract Cancellation Settlement", settlement_name, "contract")
	due_contract = frappe.db.get_value("Rental Due", due_id, "contract")
	if due_contract != settlement_contract:
		frappe.throw(frappe._("الالتزام لا ينتمي لهذا العقد"))

	# Check due is auto_contract
	due_source_type = frappe.db.get_value("Rental Due", due_id, "source_type")
	if due_source_type != "auto_contract":
		frappe.throw(frappe._("يمكن تعيين الفترة فقط لالتزامات العقد التلقائية"))

	# Check due is approved (docstatus=1)
	due_docstatus = frappe.db.get_value("Rental Due", due_id, "docstatus")
	if due_docstatus != 1:
		frappe.throw(frappe._("لا يمكن تعيين الفترة لالتزام غير معتمد"))

	# Check due doesn't already have a period
	existing_ps = frappe.db.get_value("Rental Due", due_id, "period_start")
	existing_pe = frappe.db.get_value("Rental Due", due_id, "period_end")
	if existing_ps and existing_pe:
		frappe.throw(frappe._("الالتزام ليس مفتوح الفترة"))

	# Archive protection — blocks resolving dues for archived contracts.
	ensure_contract_not_archived(settlement_contract, action="استكمال تسوية إلغاء العقد")

	account = get_current_rental_account()
	resolve_due(settlement_name, due_id, period_start, period_end, account)
	return {"due": due_id, "period_start": period_start, "period_end": period_end}


# Alias for frontend compatibility
resolve_due_period = resolve_settlement_due
