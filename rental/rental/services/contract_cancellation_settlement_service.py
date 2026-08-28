"""Contract cancellation settlement workflow.

Ported from ``src/services/contract-cancellation-settlement.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import to_calendar_day, calendar_day_diff, round_money
from rental.rental.services.balance_service import _db_sum


class CancellationError(frappe.ValidationError):
	"""Custom error for settlement-specific issues with status code."""

	def __init__(self, message: str, status_code: int = 400):
		super().__init__(message)
		self.status_code = status_code


# ---------------------------------------------------------------------------
# Constants  (source: lines 28-29)
# ---------------------------------------------------------------------------

SYSTEM_CANCELLATION_REASON = "System cancellation due to contract cancellation settlement"
SETTLEMENT_WAIVER_REASON = "تسوية إلغاء العقد"


# ---------------------------------------------------------------------------
# Helpers  (source: getActiveManualWaiverTotal, classifyDue, assertValidPeriod,
#            computeItemValues, systemCancelDueAndWaivers)
# ---------------------------------------------------------------------------


def _get_active_manual_waiver_total(due_name: str) -> float:
	"""Sum of active waivers excluding contract_cancellation source.

	Source: ``getActiveManualWaiverTotal`` (lines 31-36).
	"""
	return _db_sum(
		"Rental Due Waiver",
		{"due": due_name, "status": "active", "source_type": ["!=", "contract_cancellation"]},
		"amount",
	)


def _classify_due(due, cancellation_date) -> str:
	"""Classify a due relative to the cancellation date.

	Source: ``classifyDue`` (lines 38-48).
	Returns 'past', 'current', 'future', or 'unresolved'.
	"""
	period_start = due.get("period_start") if isinstance(due, dict) else due.period_start
	period_end = due.get("period_end") if isinstance(due, dict) else due.period_end

	if not period_start or not period_end:
		return "unresolved"

	start = to_calendar_day(period_start)
	end = to_calendar_day(period_end)
	cancel = to_calendar_day(cancellation_date)

	if end < cancel:
		return "past"
	if start > cancel:
		return "future"
	return "current"


def _assert_valid_period(due, cancellation_date, label: str) -> None:
	"""Validate that a due has a resolvable period containing the cancel date.

	Source: ``assertValidPeriod`` (lines 50-66).
	"""
	period_start = due.get("period_start") if isinstance(due, dict) else due.period_start
	period_end = due.get("period_end") if isinstance(due, dict) else due.period_end

	if not period_start or not period_end:
		raise CancellationError(frappe._("{0}: due period is unresolved").format(label), 400)

	start = to_calendar_day(period_start)
	end = to_calendar_day(period_end)
	cancel = to_calendar_day(cancellation_date)

	if end < start:
		raise CancellationError(
			frappe._("{0}: invalid period (periodEnd before periodStart)").format(label), 400
		)

	if cancel < start or cancel > end:
		raise CancellationError(
			frappe._("{0}: cancellation date is outside due period").format(label), 400
		)


def _compute_item_values(
	decision: str,
	original_amount: float,
	active_manual_waiver_amount: float,
	period_start,
	period_end,
	cancellation_date,
	stored_final_amount=None,
	reason: str | None = None,
) -> dict:
	"""Compute settlement values for a single item.

	Source: ``computeItemValues`` (lines 68-136).
	"""
	D = float(original_amount)
	W = float(active_manual_waiver_amount or 0)
	C = max(0, round_money(D - W))
	T = 0
	occupied_days = None
	total_days = None

	_assert_valid_period(
		{"period_start": period_start, "period_end": period_end},
		cancellation_date,
		"computeItemValues",
	)

	if decision == "keep_full":
		T = C
	elif decision == "prorated":
		total_days = calendar_day_diff(period_start, period_end) + 1
		occupied_days = calendar_day_diff(period_start, cancellation_date) + 1
		T = round_money((D * occupied_days) / total_days)
		if T > C:
			raise CancellationError(
				frappe._(
					"المبلغ المحسوب حسب مدة الالتزام أعلى من المبلغ الحالي بعد الإعفاءات السابقة. يجب مراجعة الإعفاءات السابقة أولًا."
				),
				400,
			)
	elif decision == "manual_settlement":
		if stored_final_amount is None:
			raise CancellationError(frappe._("Manual settlement requires final amount"), 400)
		T = round_money(float(stored_final_amount))
		if T < 0 or T > C:
			raise CancellationError(
				frappe._("المبلغ النهائي يجب أن يكون بين صفر والمبلغ الحالي"), 400
			)
	elif decision == "full_waiver":
		T = 0
	else:
		raise CancellationError(frappe._("Invalid decision: {0}").format(decision), 400)

	settlement_waiver_amount = round_money(C - T)

	return {
		"gross_settled_amount": T,
		"settled_amount": T,
		"settlement_waiver_amount": settlement_waiver_amount,
		"prorated_occupied_days": occupied_days,
		"prorated_total_days": total_days,
		"reason": reason or SETTLEMENT_WAIVER_REASON,
	}


def _system_cancel_due_and_waivers(due_name: str, reason: str) -> None:
	"""Cancel a due and its active waivers (system cancellation).

	Source: ``systemCancelDueAndWaivers`` (lines 138-169).
	- Skips if due not found or already cancelled.
	- Sets cancelledBy = null (legacy line 150, 163).
	"""
	due_doc = frappe.get_doc("Rental Due", due_name)
	# Original: if (!due || due.status === 'cancelled') return;
	if not due_doc or due_doc.docstatus == 2:
		return

	# Set cancellation_reason BEFORE cancel() so on_cancel hook passes.
	# The original directly updates the due without hooks; we must satisfy
	# the on_cancel validation that requires cancellation_reason.
	due_doc.cancellation_reason = reason
	due_doc.cancel()
	frappe.db.set_value("Rental Due", due_name, {
		"is_system_cancelled": 1,
		"cancelled_by": None,
		"cancelled_at": frappe.utils.now(),
		"cancellation_reason": reason,
	}, update_modified=False)

	# Cancel active waivers
	waivers = frappe.get_all(
		"Rental Due Waiver",
		filters={"due": due_name, "status": "active"},
		pluck="name",
	)
	for w in waivers:
		frappe.db.set_value("Rental Due Waiver", w, {
			"status": "cancelled",
			"is_system_cancelled": 1,
			"cancelled_by": None,
			"cancelled_at": frappe.utils.now(),
			"cancellation_reason": reason,
		}, update_modified=False)


# ---------------------------------------------------------------------------
# Create settlement  (source: createContractCancellationSettlement)
# ---------------------------------------------------------------------------


def create_contract_cancellation_settlement(
	contract_name: str,
	cancellation_date,
	reason: str,
	account: str,
) -> str:
	"""Create a cancellation settlement for a contract.

	Source: ``createContractCancellationSettlement`` (lines 171-237).
	- Iterates auto-contract dues.
	- current (period overlaps cancel date) → creates settlement item.
	- future (period after cancel date) → auto-cancels due and waivers.
	- unresolved (no period) → user must resolve.
	"""
	cancel_date = to_calendar_day(cancellation_date)

	# Check contract exists (legacy line 180)
	if not frappe.db.exists("Lease Contract", contract_name):
		raise CancellationError(frappe._("Contract not found"), 404)

	# Check for existing settlement (legacy line 181)
	existing = frappe.db.exists("Contract Cancellation Settlement", {"contract": contract_name})
	if existing:
		raise CancellationError(frappe._("Settlement already exists for this contract"), 409)

	settlement = frappe.get_doc({
		"doctype": "Contract Cancellation Settlement",
		"rental_account": account,
		"contract": contract_name,
		"cancellation_date": cancellation_date,
		"reason": reason,
		"status": "pending",
		"created_by": frappe.session.user,
	})
	settlement.insert(ignore_permissions=True)

	# Process auto-contract dues (legacy lines 193-200)
	dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": contract_name,
			"source_type": "auto_contract",
			"docstatus": 1,
		},
		fields=["name", "amount", "period_start", "period_end", "due_date"],
	)

	for d in dues:
		classification = _classify_due(d, cancel_date)

		if classification == "current":
			# Assert valid period (legacy line 208)
			_assert_valid_period(d, cancel_date, f"Due {d.name}")

			active_waivers = _get_active_manual_waiver_total(d.name)

			settlement.append("settlement_items", {
				"due": d.name,
				"original_amount": d.amount,
				"active_waiver_amount": active_waivers,
				"decision": "pending",
				"status": "pending",
			})

		elif classification == "future":
			# Legacy line 223: if (due.periodStart && due.periodEnd)
			if d.period_start and d.period_end:
				_system_cancel_due_and_waivers(d.name, SYSTEM_CANCELLATION_REASON)

		# 'past' and 'unresolved' → no action

	settlement.save(ignore_permissions=True)
	return settlement.name


# ---------------------------------------------------------------------------
# Settle item  (source: settleContractCancellationItem)
# ---------------------------------------------------------------------------


def settle_contract_cancellation_item(
	settlement_name: str,
	item_name: str,
	decision: str,
	gross_settled_amount: float | None = None,
	reason: str | None = None,
) -> None:
	"""Apply a decision to a settlement item.

	Source: ``settleContractCancellationItem`` (lines 239-289).
	Decisions: keep_full, prorated, manual_settlement, full_waiver.
	"""
	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name)

	# Legacy line 243-247: fetch item first, check existence before settlement status
	item = None
	for it in settlement.settlement_items:
		if it.name == item_name:
			item = it
			break

	if not item:
		raise CancellationError(frappe._("Settlement item not found"), 404)

	# Check settlement is not completed (legacy line 248: item.settlement.status === 'completed')
	if settlement.status == "completed":
		raise CancellationError(frappe._("Settlement is already completed"), 409)

	due = frappe.db.get_value(
		"Rental Due", item.due,
		["amount", "period_start", "period_end"],
		as_dict=True,
	)
	if not due:
		raise CancellationError(frappe._("Due not found"), 404)

	original_amount = float(item.original_amount)
	cancellation_date = settlement.cancellation_date

	# Assert valid period (legacy line 254)
	_assert_valid_period(due, cancellation_date, f"Due {item.due}")

	active_waiver_amount = _get_active_manual_waiver_total(item.due)

	values = _compute_item_values(
		decision=decision,
		original_amount=original_amount,
		active_manual_waiver_amount=active_waiver_amount,
		period_start=due.period_start,
		period_end=due.period_end,
		cancellation_date=cancellation_date,
		stored_final_amount=gross_settled_amount if decision == "manual_settlement" else None,
		reason=reason,
	)

	item.decision = decision
	item.active_waiver_amount = active_waiver_amount
	item.gross_settled_amount = values["gross_settled_amount"]
	item.settled_amount = values["settled_amount"]
	item.adjustment_amount = values["settlement_waiver_amount"]
	item.prorated_occupied_days = values["prorated_occupied_days"]
	item.prorated_total_days = values["prorated_total_days"]
	item.reason = values["reason"]
	item.status = "decided"
	item.settled_by = frappe.session.user
	item.settled_at = frappe.utils.now()

	settlement.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Complete settlement  (source: completeContractCancellationSettlement)
# ---------------------------------------------------------------------------


def complete_contract_cancellation_settlement(settlement_name: str, account: str) -> dict:
	"""Complete a cancellation settlement.

	Source: ``completeContractCancellationSettlement`` (lines 343-472).
	- Idempotent: if already completed, returns settlement.
	- Requires no unresolved dues and no pending items.
	- Cancels all future auto-contract dues again.
	- Re-reads current dues, validates, and recomputes values.
	- Creates/updates/cancels a DueWaiver with sourceType='contract_cancellation'.
	- Marks items and settlement as completed.
	"""
	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name)

	# Legacy line 353: if (!settlement) throw 'Settlement not found', 404
	if not settlement:
		raise CancellationError(frappe._("Settlement not found"), 404)

	# Legacy line 354: if (settlement.status === 'completed') return settlement
	if settlement.status == "completed":
		return settlement.as_dict()

	cancel_date = to_calendar_day(settlement.cancellation_date)

	# Get all auto-contract approved dues (legacy lines 358-365)
	all_dues = frappe.get_all(
		"Rental Due",
		filters={
			"contract": settlement.contract,
			"source_type": "auto_contract",
			"docstatus": 1,
		},
		fields=["name", "amount", "period_start", "period_end"],
	)

	# Check for unresolved dues (legacy lines 367-373)
	unresolved_dues = [d for d in all_dues if not d.period_start or not d.period_end]
	if unresolved_dues:
		raise CancellationError(
			frappe._("Cannot complete settlement: unresolved dues exist ({0})").format(
				", ".join(d.name for d in unresolved_dues)
			),
			409,
		)

	# Check for pending items (legacy line 375: status === 'pending' OR decision === 'pending')
	pending_items = [
		it for it in settlement.settlement_items
		if it.status == "pending" or it.decision == "pending"
	]
	if pending_items:
		raise CancellationError(frappe._("Cannot complete settlement: pending items exist"), 409)

	# Cancel all future auto-contract dues (legacy lines 380-385)
	for due in all_dues:
		start = to_calendar_day(due.period_start)
		if start > cancel_date:
			_system_cancel_due_and_waivers(due.name, SYSTEM_CANCELLATION_REASON)

	# Process each item (legacy lines 387-458)
	for item in settlement.settlement_items:
		# Re-read current due (legacy lines 388-391)
		current_due = frappe.db.get_value(
			"Rental Due", item.due,
			["name", "amount", "period_start", "period_end", "docstatus"],
			as_dict=True,
		)
		# Legacy line 392: if (!currentDue || currentDue.status !== 'approved')
		if not current_due or current_due.docstatus != 1:
			raise CancellationError(
				frappe._("Due {0} is not approved").format(item.due), 409
			)

		# Assert valid period (legacy line 396)
		_assert_valid_period(current_due, cancel_date, f"Due {item.due}")

		active_manual_waiver_amount = _get_active_manual_waiver_total(item.due)
		original_amount = float(item.original_amount)

		# Recompute values (legacy lines 402-411)
		values = _compute_item_values(
			decision=item.decision,
			original_amount=original_amount,
			active_manual_waiver_amount=active_manual_waiver_amount,
			period_start=current_due.period_start,
			period_end=current_due.period_end,
			cancellation_date=cancel_date,
			stored_final_amount=item.gross_settled_amount if item.decision == "manual_settlement" else None,
			reason=item.reason,
		)

		settlement_waiver_amount = values["settlement_waiver_amount"]

		if settlement_waiver_amount > 0:
			# Upsert waiver (legacy lines 416-431)
			existing_waiver = frappe.db.exists(
				"Rental Due Waiver",
				{"settlement_item": item.name},
			)
			if existing_waiver:
				frappe.db.set_value("Rental Due Waiver", existing_waiver, {
					"amount": settlement_waiver_amount,
					"status": "active",
				}, update_modified=False)
			else:
				waiver = frappe.get_doc({
					"doctype": "Rental Due Waiver",
					"rental_account": account,
					"due": current_due.name,
					"amount": settlement_waiver_amount,
					"reason": values["reason"],
					"source_type": "contract_cancellation",
					"settlement_item": item.name,
					"status": "active",
					"created_by": frappe.session.user,
				})
				waiver.insert(ignore_permissions=True)
		else:
			# Cancel existing settlement waiver (legacy lines 432-442)
			existing_settlement_waiver = frappe.db.get_value(
				"Rental Due Waiver",
				{"settlement_item": item.name},
				"name",
			)
			if existing_settlement_waiver:
				frappe.db.set_value("Rental Due Waiver", existing_settlement_waiver, {
					"status": "cancelled",
					"cancellation_reason": "إلغاء بسبب تغيير قرار التسوية",
				}, update_modified=False)

		# Update item with recomputed values (legacy lines 444-457)
		item.active_waiver_amount = active_manual_waiver_amount
		item.gross_settled_amount = values["gross_settled_amount"]
		item.settled_amount = values["settled_amount"]
		item.adjustment_amount = values["settlement_waiver_amount"]
		item.prorated_occupied_days = values["prorated_occupied_days"]
		item.prorated_total_days = values["prorated_total_days"]
		item.status = "completed"
		item.settled_by = frappe.session.user
		item.settled_at = frappe.utils.now()

	# Mark settlement as completed (legacy lines 460-468)
	settlement.status = "completed"
	settlement.completed_by = frappe.session.user
	settlement.completed_at = frappe.utils.now()
	settlement.save(ignore_permissions=True)

	return settlement.as_dict()


# ---------------------------------------------------------------------------
# Resolve due  (source: reconcileSettlementAfterResolveDue)
# ---------------------------------------------------------------------------


def resolve_due(
	settlement_name: str,
	due_id: str,
	period_start,
	period_end,
	account: str,
) -> None:
	"""Set periodStart/periodEnd for an unresolved auto due, then reconcile.

	Source: ``reconcileSettlementAfterResolveDue`` (lines 291-341).
	"""
	# Get settlement (legacy lines 292-295)
	settlement = frappe.db.get_value(
		"Contract Cancellation Settlement", settlement_name,
		["contract", "cancellation_date", "status"],
		as_dict=True,
	)
	# Legacy line 296
	if not settlement:
		raise CancellationError(frappe._("Settlement not found"), 404)
	# Legacy line 297
	if settlement.status == "completed":
		raise CancellationError(frappe._("Settlement is already completed"), 409)

	# Get due (legacy lines 299-302)
	due = frappe.db.get_value(
		"Rental Due", due_id,
		["name", "contract", "source_type", "docstatus", "amount", "period_start", "period_end"],
		as_dict=True,
	)
	# Legacy line 303
	if not due:
		raise CancellationError(frappe._("Due not found"), 404)

	# Legacy lines 304-306
	if due.contract != settlement.contract:
		raise CancellationError(frappe._("الالتزام لا ينتمي لهذا العقد"), 403)

	# Legacy lines 307-309
	if due.source_type != "auto_contract" or due.docstatus != 1:
		raise CancellationError(
			frappe._("يمكن تعيين الفترة فقط لالتزامات العقد التلقائية المعتمدة"), 403
		)

	# Update the due's period
	frappe.db.set_value("Rental Due", due_id, {
		"period_start": period_start,
		"period_end": period_end,
	}, update_modified=False)

	# Re-read due with updated period for classification
	due_updated = frappe.db.get_value(
		"Rental Due", due_id,
		["name", "amount", "period_start", "period_end", "docstatus"],
		as_dict=True,
	)

	classification = _classify_due(due_updated, settlement.cancellation_date)

	# Check for existing item (legacy lines 312-314)
	existing_item = frappe.db.exists(
		"Cancellation Settlement Item",
		{"due": due_id, "parent": settlement_name},
	)

	if classification == "current":
		# Legacy lines 316-328: create item if not exists
		if not existing_item:
			active_waivers = _get_active_manual_waiver_total(due_id)
			settlement_doc = frappe.get_doc("Contract Cancellation Settlement", settlement_name)
			settlement_doc.append("settlement_items", {
				"due": due_id,
				"original_amount": due_updated.amount,
				"active_waiver_amount": active_waivers,
				"decision": "pending",
				"status": "pending",
			})
			settlement_doc.save(ignore_permissions=True)

	elif classification == "future":
		# Legacy lines 329-335: delete existing item, then cancel due
		if existing_item:
			_delete_settlement_item(settlement_name, due_id)
		if due_updated.docstatus == 1:
			_system_cancel_due_and_waivers(due_id, SYSTEM_CANCELLATION_REASON)

	elif classification == "past":
		# Legacy lines 336-339: delete existing item
		if existing_item:
			_delete_settlement_item(settlement_name, due_id)


def _delete_settlement_item(settlement_name: str, due_id: str) -> None:
	"""Delete a settlement item by due_id from a settlement."""
	settlement_doc = frappe.get_doc("Contract Cancellation Settlement", settlement_name)
	# Remove items matching due_id
	remaining = [it for it in settlement_doc.settlement_items if it.due != due_id]
	if len(remaining) != len(settlement_doc.settlement_items):
		settlement_doc.settlement_items = remaining
		settlement_doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Helpers for unresolved dues
# ---------------------------------------------------------------------------


def _get_unresolved_dues(contract_name: str, settlement_name: str) -> list:
	"""Get auto-contract dues without period that are not in the settlement.

	Source: route.ts:31-53 — returns ``{ dueId, dueNumber, dueType, dueDate,
	blockingReason }`` for each unresolved due.
	"""
	# Get due names already in settlement
	settled_due_names = frappe.get_all(
		"Cancellation Settlement Item",
		filters={"parent": settlement_name},
		pluck="due",
	)

	filters = {
		"contract": contract_name,
		"source_type": "auto_contract",
		"docstatus": 1,
		"period_start": ["is", "not set"],
	}
	if settled_due_names:
		filters["name"] = ["not in", settled_due_names]

	dues = frappe.get_all(
		"Rental Due", filters=filters,
		fields=["name", "due_number", "due_date", "due_type"],
		order_by="due_date asc",
	)

	result = []
	for d in dues:
		due_type_name = None
		if d.get("due_type"):
			due_type_name = frappe.db.get_value("Rental Due Type", d["due_type"], "due_type_name")
		result.append({
			"dueId": d.name,
			"due_id": d.name,
			"dueNumber": d.due_number,
			"due_number": d.due_number,
			"dueType": due_type_name,
			"due_type_name": due_type_name,
			"dueDate": d.due_date,
			"due_date": d.due_date,
			"blockingReason": "Missing periodStart or periodEnd",
		})
	return result
