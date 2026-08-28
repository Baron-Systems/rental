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
# Create settlement  (source: createContractCancellationSettlement)
# ---------------------------------------------------------------------------


def create_contract_cancellation_settlement(
	contract_name: str,
	cancellation_date,
	reason: str,
	account: str,
) -> str:
	"""Create a cancellation settlement for a contract.

	Source: ``createContractCancellationSettlement``.
	- Iterates auto-contract dues.
	- current (period overlaps cancel date) → creates settlement item.
	- future (period after cancel date) → auto-cancels due and waivers.
	- unresolved (no period) → user must resolve.
	"""
	cancel_date = to_calendar_day(cancellation_date)

	# Check for existing settlement
	existing = frappe.db.exists("Contract Cancellation Settlement", {"contract": contract_name})
	if existing:
		frappe.throw(frappe._("Settlement already exists for this contract"))

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

	# Process auto-contract dues
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
		if d.period_start and d.period_end:
			p_start = to_calendar_day(d.period_start)
			p_end = to_calendar_day(d.period_end)

			# Current: period overlaps cancel date
			if p_start <= cancel_date <= p_end:
				# Create settlement item
				# A5: exclude contract_cancellation waivers from manual waiver total
				# (legacy getActiveManualWaiverTotal filters sourceType !== 'contract_cancellation').
				active_waivers = _db_sum(
					"Rental Due Waiver",
					{"due": d.name, "status": "active", "source_type": ["!=", "contract_cancellation"]},
					"amount",
				)

				settlement.append("settlement_items", {
					"due": d.name,
					"original_amount": d.amount,
					"active_waiver_amount": active_waivers,
					"status": "pending",
				})

			# Future: period after cancel date → cancel
			elif p_start > cancel_date:
				_cancel_due_and_waivers(d.name, reason, account)

		# Unresolved: no period → user must resolve via /resolve-due

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

	Source: ``settleContractCancellationItem``.
	Decisions: keep_full, prorated, manual_settlement, full_waiver.
	"""
	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name)

	item = None
	for it in settlement.settlement_items:
		if it.name == item_name:
			item = it
			break

	if not item:
		raise CancellationError(frappe._("Settlement item not found"), 404)

	if item.status == "completed":
		raise CancellationError(frappe._("Settlement is already completed"), 409)

	due = frappe.db.get_value(
		"Rental Due", item.due,
		["amount", "period_start", "period_end"],
		as_dict=True,
	)
	if not due:
		raise CancellationError(frappe._("Due not found"), 404)

	# A5: recompute active manual waivers at settle time (excludes contract_cancellation).
	active_waiver_amount = _db_sum(
		"Rental Due Waiver",
		{"due": item.due, "status": "active", "source_type": ["!=", "contract_cancellation"]},
		"amount",
	)
	item.active_waiver_amount = active_waiver_amount
	current_net = float(due.amount) - float(active_waiver_amount or 0)

	if decision == "keep_full":
		gross = current_net
		adjustment = 0
	elif decision == "full_waiver":
		gross = 0
		adjustment = current_net
	elif decision == "prorated":
		if not due.period_start or not due.period_end:
			raise CancellationError(frappe._("Cannot prorate a due without period info"), 400)
		cancel_date = to_calendar_day(settlement.cancellation_date)
		p_start = to_calendar_day(due.period_start)
		p_end = to_calendar_day(due.period_end)
		occupied_days = calendar_day_diff(p_start, cancel_date) + 1
		total_days = calendar_day_diff(p_start, p_end) + 1
		if occupied_days < 0:
			occupied_days = 0
		if occupied_days > total_days:
			occupied_days = total_days
		# A4: prorate the ORIGINAL amount (D), not the net (C). Legacy line 102.
		original_amount = float(item.original_amount)
		gross = round_money(original_amount * occupied_days / total_days) if total_days > 0 else 0
		if gross > current_net:
			raise CancellationError(
				frappe._("المبلغ المحسوب حسب مدة الالتزام أعلى من المبلغ الحالي بعد الإعفاءات السابقة. يجب مراجعة الإعفاءات السابقة أولًا."),
				400,
			)
		adjustment = round_money(current_net - gross)
		item.prorated_occupied_days = occupied_days
		item.prorated_total_days = total_days
	elif decision == "manual_settlement":
		if gross_settled_amount is None:
			raise CancellationError(frappe._("Manual settlement requires final amount"), 400)
		gross = float(gross_settled_amount)
		if gross < 0 or gross > current_net:
			raise CancellationError(
				frappe._("المبلغ النهائي يجب أن يكون بين صفر والمبلغ الحالي"), 400
			)
		adjustment = round_money(current_net - gross)
	else:
		raise CancellationError(frappe._("Invalid decision: {0}").format(decision), 400)

	item.decision = decision
	item.gross_settled_amount = gross
	item.settled_amount = gross
	item.adjustment_amount = adjustment
	item.reason = reason
	item.status = "decided"
	item.settled_by = frappe.session.user
	item.settled_at = frappe.utils.now()

	settlement.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Complete settlement  (source: completeContractCancellationSettlement)
# ---------------------------------------------------------------------------


def complete_contract_cancellation_settlement(settlement_name: str, account: str) -> None:
	"""Complete a cancellation settlement.

	Source: ``completeContractCancellationSettlement``.
	- Requires no unresolved dues and no pending items.
	- Cancels all future auto-contract dues again.
	- Creates/updates a DueWaiver with sourceType='contract_cancellation' for each decided item.
	- Marks items and settlement as completed.
	"""
	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name)

	if settlement.status == "completed":
		raise CancellationError(frappe._("Settlement is already completed"), 409)

	# Check for pending items
	pending_items = [it for it in settlement.settlement_items if it.status == "pending"]
	if pending_items:
		raise CancellationError(frappe._("Cannot complete settlement: pending items exist"), 409)

	# Check for unresolved dues (auto-contract dues without period)
	unresolved = _get_unresolved_dues(settlement.contract, settlement_name)
	if unresolved:
		raise CancellationError(frappe._("Cannot complete settlement: unresolved dues exist"), 409)

	# Cancel all future auto-contract dues again
	from rental.rental.services.due_generation_service import cancel_future_dues
	cancel_future_dues(
		settlement.contract,
		settlement.cancellation_date,
		settlement.reason or "Contract cancelled",
		frappe.session.user,
	)

	# Create/update waivers for each decided item
	for item in settlement.settlement_items:
		if item.status == "decided" and item.adjustment_amount and float(item.adjustment_amount) > 0:
			# Check if waiver already exists
			existing_waiver = frappe.db.exists(
				"Rental Due Waiver",
				{"settlement_item": item.name},
			)
			if existing_waiver:
				frappe.db.set_value("Rental Due Waiver", existing_waiver, {
					"amount": item.adjustment_amount,
					"reason": item.reason or "تسوية إلغاء العقد",
				}, update_modified=False)
			else:
				waiver = frappe.get_doc({
					"doctype": "Rental Due Waiver",
					"rental_account": account,
					"due": item.due,
					"amount": item.adjustment_amount,
					"reason": item.reason or "تسوية إلغاء العقد",
					"source_type": "contract_cancellation",
					"settlement_item": item.name,
					"status": "active",
					"created_by": frappe.session.user,
				})
				waiver.insert(ignore_permissions=True)

		# Mark item as completed
		item.status = "completed"
		item.settled_at = frappe.utils.now()

	settlement.status = "completed"
	settlement.completed_by = frappe.session.user
	settlement.completed_at = frappe.utils.now()
	settlement.save(ignore_permissions=True)


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

	Source: ``/api/cancellation-settlements/[id]/resolve-due``.
	"""
	settlement = frappe.get_doc("Contract Cancellation Settlement", settlement_name)

	# Update the due's period
	frappe.db.set_value("Rental Due", due_id, {
		"period_start": period_start,
		"period_end": period_end,
	}, update_modified=False)

	# Now check if this due should become a settlement item
	cancel_date = to_calendar_day(settlement.cancellation_date)
	p_start = to_calendar_day(period_start)
	p_end = to_calendar_day(period_end)

	if p_start <= cancel_date <= p_end:
		# Current period → create settlement item if not exists
		existing = frappe.db.exists(
			"Cancellation Settlement Item",
			{"due": due_id, "parent": settlement_name},
		)
		if not existing:
			due = frappe.db.get_value("Rental Due", due_id, ["amount"], as_dict=True)
			# A5: exclude contract_cancellation waivers.
			active_waivers = _db_sum(
				"Rental Due Waiver",
				{"due": due_id, "status": "active", "source_type": ["!=", "contract_cancellation"]},
				"amount",
			)

			settlement.append("settlement_items", {
				"due": due_id,
				"original_amount": due.amount,
				"active_waiver_amount": active_waivers,
				"status": "pending",
			})
			settlement.save(ignore_permissions=True)
	elif p_start > cancel_date:
		# Future → cancel
		_cancel_due_and_waivers(due_id, settlement.reason or "Contract cancelled", account)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cancel_due_and_waivers(due_name: str, reason: str, account: str) -> None:
	"""Cancel a due and its active waivers."""
	due = frappe.get_doc("Rental Due", due_name)
	if due.docstatus == 1:
		due.cancel()
		frappe.db.set_value("Rental Due", due_name, {
			"cancellation_reason": reason,
			"cancelled_by": frappe.session.user,
			"cancelled_at": frappe.utils.now(),
			"is_system_cancelled": 1,
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
			"cancellation_reason": reason,
			"cancelled_by": frappe.session.user,
			"cancelled_at": frappe.utils.now(),
			"is_system_cancelled": 1,
		}, update_modified=False)


def _get_unresolved_dues(contract_name: str, settlement_name: str) -> list:
	"""Get auto-contract dues without period that are not in the settlement."""
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

	return frappe.get_all("Rental Due", filters=filters, fields=["name"])
