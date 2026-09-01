"""Archive / unarchive contracts.

Archive = final operational + financial closure of a contract.

Required sequence:
  Operationally Closed → Financial Balance == 0 → Ready to Archive → Archive → Final Read Only

The Backend is the single source of truth for archive readiness.
``archive_contract`` always re-evaluates readiness, even when called
directly (bypassing the Vue/API layer), so the protection cannot be
circumvented.
"""

from __future__ import annotations

import frappe

from rental.rental.services.balance_service import get_contract_balance


# ---------------------------------------------------------------------------
# Archived-contract protection helper
# ---------------------------------------------------------------------------


def is_contract_archived(contract_name: str) -> bool:
	"""Return True if the contract is archived (is_archived = 1)."""
	if not contract_name:
		return False
	return bool(frappe.db.get_value("Lease Contract", contract_name, "is_archived"))


def get_archived_contract_names(account: str | None = None) -> list[str]:
	"""Return the names of all archived contracts (optionally for one account).

	Used by operational list queries (get_dues, get_receipts) to exclude
	historical movements of archived contracts from the daily operational
	lists. This does NOT affect the Tenant Statement (historical) which
	intentionally keeps the full financial history.
	"""
	filters = {"is_archived": 1}
	if account:
		filters["rental_account"] = account
	return frappe.get_all("Lease Contract", filters=filters, pluck="name")


def ensure_contract_not_archived(contract_name: str, *, action: str | None = None) -> None:
	"""Raise an Arabic ValidationError if the contract is archived.

	Central helper used by every financial/operational mutation path so the
	protection cannot be bypassed via ``frappe.get_doc().insert()`` / Server
	Script / internal calls. ``action`` is included in the message to make the
	rejection reason clear to the user.
	"""
	if not contract_name:
		return
	if is_contract_archived(contract_name):
		if action:
			frappe.throw(
				frappe._("لا يمكن {0} حركات عقد مؤرشف نهائيًا").format(action)
			)
		frappe.throw(frappe._("لا يمكن تعديل حركات عقد مؤرشف نهائيًا"))


# ---------------------------------------------------------------------------
# Archive readiness  (source of truth)
# ---------------------------------------------------------------------------


def _is_cancellation_settlement_complete(contract_name: str) -> bool:
	"""Return True if a cancellation settlement exists and is completed.

	A cancelled contract is only operationally closed when its settlement
	is completed. If no settlement exists (e.g. cancelled-before-start
	contracts that never created a settlement), the contract is considered
	operationally closed for cancellation cases.
	"""
	if not frappe.db.exists("DocType", "Contract Cancellation Settlement"):
		return True

	settlement_name = frappe.db.get_value(
		"Contract Cancellation Settlement", {"contract": contract_name}, "name"
	)
	if not settlement_name:
		# Cancelled-before-start contracts have no settlement; they are
		# operationally closed by definition.
		return True

	status = frappe.db.get_value(
		"Contract Cancellation Settlement", settlement_name, "status"
	)
	return status == "completed"


def get_archive_readiness(contract_name: str) -> dict:
	"""Return full archive readiness for a contract.

	Returns::
		{
			"contract": str,
			"eligible": bool,
			"reasons": list[str],          # Arabic reasons blocking archive
			"operationally_closed": bool,
			"financially_closed": bool,
			"balance": float,              # current contract balance
			"balance_breakdown": {totalDues, totalReceipts, balance},
		}

	The Backend is the source of truth — Vue must consume this result and
	must NOT re-implement the business logic.
	"""
	if not frappe.db.exists("Lease Contract", contract_name):
		frappe.throw(frappe._("العقد غير موجود"))

	contract = frappe.get_doc("Lease Contract", contract_name)

	reasons: list[str] = []

	# Already archived → not eligible (cannot re-archive)
	if contract.is_archived:
		reasons.append(frappe._("العقد مؤرشف مسبقاً"))
		balance_dict = get_contract_balance(contract_name)
		return {
			"contract": contract_name,
			"eligible": False,
			"reasons": reasons,
			"operationally_closed": True,
			"financially_closed": abs(balance_dict["balance"]) < 0.005,
			"balance": balance_dict["balance"],
			"balance_breakdown": balance_dict,
		}

	# --- (a) Operational closure -------------------------------------------
	operationally_closed = False

	if contract.status == "evicted":
		operationally_closed = True
	elif contract.status == "expired" and (contract.is_historical or contract.closed_by_renewal_at):
		# Expired + (historical OR closed by an approved started renewal)
		operationally_closed = True
	elif contract.status == "cancelled" and contract.cancelled_at:
		# Cancelled contracts: only operationally closed if the settlement
		# is completed (or no settlement exists, e.g. cancelled-before-start).
		from rental.rental.utils.date_utils import to_calendar_day
		cancelled_at = to_calendar_day(contract.cancelled_at)
		start_date = to_calendar_day(contract.start_date)
		if cancelled_at < start_date:
			# Cancelled before start — no settlement, operationally closed.
			operationally_closed = True
		elif _is_cancellation_settlement_complete(contract_name):
			operationally_closed = True

	if not operationally_closed:
		# Produce a precise, actionable reason.
		if contract.status == "expired" and not (contract.is_historical or contract.closed_by_renewal_at):
			reasons.append(frappe._("لا يمكن أرشفة العقد قبل إتمام الإخلاء"))
		elif contract.status == "cancelled":
			reasons.append(frappe._("لا يمكن أرشفة العقد قبل إكمال تسوية إلغاء العقد"))
		else:
			reasons.append(
				frappe._(
					"لا يمكن أرشفة هذا العقد؛ الأرشفة متاحة فقط للعقود المُخلاة، "
					"أو التاريخية المنتهية، أو المغلقة بتجديد معتمد، "
					"أو الملغاة بعد إكمال التسوية"
				)
			)

	# --- (b) Financial closure: Contract Balance == 0 exactly --------------
	balance_dict = get_contract_balance(contract_name)
	balance = balance_dict["balance"]
	financially_closed = abs(balance) < 0.005  # tolerance for float rounding

	if not financially_closed:
		# Format the remaining balance clearly in Arabic.
		abs_balance = abs(balance)
		if balance > 0:
			reasons.append(
				frappe._("لا يمكن أرشفة العقد لوجود رصيد مالي متبقٍ بقيمة {0}").format(
					frappe.utils.fmt_money(abs_balance, currency="")  # bare number
				)
			)
		else:
			reasons.append(
				frappe._("لا يمكن أرشفة العقد لوجود رصيد مالي دائن بقيمة {0}").format(
					frappe.utils.fmt_money(abs_balance, currency="")
				)
			)

	eligible = operationally_closed and financially_closed

	return {
		"contract": contract_name,
		"eligible": eligible,
		"reasons": reasons,
		"operationally_closed": operationally_closed,
		"financially_closed": financially_closed,
		"balance": balance,
		"balance_breakdown": balance_dict,
	}


# ---------------------------------------------------------------------------
# Can archive  (legacy thin wrapper — kept for compatibility)
# ---------------------------------------------------------------------------


def can_archive_contract(contract_name: str) -> dict:
	"""Legacy compatibility wrapper around ``get_archive_readiness``.

	Returns ``{"eligible": bool, "reason": str | None}`` where ``reason`` is
	the first blocking reason (if any). New code should call
	``get_archive_readiness`` directly to get the full picture.
	"""
	result = get_archive_readiness(contract_name)
	reason = result["reasons"][0] if result["reasons"] else None
	return {"eligible": result["eligible"], "reason": reason}


# ---------------------------------------------------------------------------
# Archive  (source: archiveContract)
# ---------------------------------------------------------------------------


def archive_contract(contract_name: str):
	"""Archive a contract — final operational + financial closure.

	Order of checks (must always run, even on direct backend calls):
	  1. Contract exists → 'العقد غير موجود'
	  2. Archive readiness (operational + financial balance == 0)
	  3. Update is_archived + archived_at

	The contract status is NOT changed by archiving. The contract becomes
	Read Only after archiving (enforced by ``ensure_contract_not_archived``
	and the LeaseContract.validate hook).
	"""
	if not frappe.db.exists("Lease Contract", contract_name):
		frappe.throw(frappe._("العقد غير موجود"))

	result = get_archive_readiness(contract_name)
	if not result["eligible"]:
		# Surface every blocking reason so the user can act on all of them.
		reasons = result["reasons"] or [frappe._("لا يمكن أرشفة العقد")]
		frappe.throw(" — ".join(str(r) for r in reasons))

	frappe.db.set_value("Lease Contract", contract_name, {
		"is_archived": 1,
		"archived_at": frappe.utils.now(),
	})

	return frappe.get_doc("Lease Contract", contract_name)


# ---------------------------------------------------------------------------
# Unarchive  (source: unarchiveContract)
# ---------------------------------------------------------------------------


def unarchive_contract(contract_name: str):
	"""Reverse the archive flag.

	NOTE: After the archive-as-final-closure change, unarchive is no longer
	exposed to end users (the UI button is removed). This function is kept
	for internal/technical use only and is intentionally NOT wired to a
	normal user workflow. It does NOT re-validate closure conditions.
	"""
	if not frappe.db.exists("Lease Contract", contract_name):
		frappe.throw(frappe._("العقد غير موجود"))

	contract = frappe.get_doc("Lease Contract", contract_name)
	if not contract.is_archived:
		frappe.throw(frappe._("العقد غير مؤرشف"))

	frappe.db.set_value("Lease Contract", contract_name, {
		"is_archived": 0,
		"archived_at": None,
	})

	return frappe.get_doc("Lease Contract", contract_name)


# ---------------------------------------------------------------------------
# Inspection of legacy archived contracts (section 14)
# ---------------------------------------------------------------------------


def inspect_archived_contracts() -> list[dict]:
	"""Audit existing ``is_archived = 1`` contracts against the new rules.

	Returns one record per archived contract with:
	  - contract name/number/status
	  - whether it satisfies the new operational + financial closure
	  - the blocking reasons (if any)
	  - current balance

	This is a READ-ONLY inspection. No data is modified. The caller should
	review the report before any migration.
	"""
	archived = frappe.get_all(
		"Lease Contract",
		filters={"is_archived": 1},
		fields=["name", "contract_number", "status", "is_historical",
				"closed_by_renewal_at", "cancelled_at", "start_date", "end_date"],
	)

	report = []
	for c in archived:
		# Temporarily flip is_archived off so get_archive_readiness evaluates
		# the real closure conditions (it short-circuits when already archived).
		frappe.db.set_value("Lease Contract", c.name, "is_archived", 0, update_modified=False)
		try:
			readiness = get_archive_readiness(c.name)
		finally:
			# Always restore the archived flag.
			frappe.db.set_value("Lease Contract", c.name, "is_archived", 1, update_modified=False)

		report.append({
			"name": c.name,
			"contract_number": c.contract_number,
			"status": c.status,
			"start_date": str(c.start_date) if c.start_date else None,
			"end_date": str(c.end_date) if c.end_date else None,
			"meets_new_rules": readiness["eligible"],
			"operationally_closed": readiness["operationally_closed"],
			"financially_closed": readiness["financially_closed"],
			"balance": readiness["balance"],
			"blocking_reasons": readiness["reasons"],
		})

	return report
