"""Renewal eligibility, closure of previous contracts, meter capture.

Ported from ``src/services/renewal.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import to_calendar_day, add_days
from rental.rental.services.contract_charge_service import capture_metered_openings_from_unit
from rental.rental.services.contract_validation import can_renew_contract


# ---------------------------------------------------------------------------
# Renewal eligibility  (source: canCreateRenewalFor)
# ---------------------------------------------------------------------------


def can_create_renewal_for(previous_contract_name: str, exclude: str | None = None) -> dict:
	"""Check if a renewal can be created for *previous_contract_name*.

	Source: ``canCreateRenewalFor`` (renewal.service.ts:49-66).
	Returns ``{"ok": bool, "reason": str | None}`` with Arabic reasons.
	"""
	previous = frappe.db.get_value(
		"Lease Contract", previous_contract_name,
		["name", "status", "is_archived", "is_historical", "closed_by_renewal_at",
		 "start_date", "end_date"],
		as_dict=True,
	)
	if not previous:
		return {"ok": False, "reason": frappe._("العقد السابق غير موجود")}

	# Check for existing non-cancelled/non-evicted renewal
	renewal_filters = {
		"renewed_from_contract": previous_contract_name,
		"status": ["not in", ["cancelled", "evicted"]],
	}
	if exclude:
		renewal_filters["name"] = ["!=", exclude]

	if frappe.db.exists("Lease Contract", renewal_filters):
		return {"ok": False, "reason": frappe._("يوجد تجديد مرتبط غير ملغى لهذا العقد")}

	if not can_renew_contract(previous):
		return {"ok": False, "reason": frappe._("العقد السابق غير صالح للتجديد")}

	return {"ok": True, "reason": None}


# ---------------------------------------------------------------------------
# Close previous contract by renewal  (source: closePreviousContractByRenewal)
# ---------------------------------------------------------------------------


def close_previous_contract_by_renewal(
	previous_contract_name: str,
	renewal_contract: dict,
	account: str,
) -> None:
	"""Close the previous contract when the renewal starts.

	Source: ``closePreviousContractByRenewal``.
	- Only closes if previous endDate < today and renewal.startDate <= today
	and not already closed.
	- Sets closedByRenewalAt to now.
	- Captures metered openings from unit.
	"""
	today = to_calendar_day(frappe.utils.today())

	previous = frappe.db.get_value(
		"Lease Contract", previous_contract_name,
		["name", "end_date", "closed_by_renewal_at", "status"],
		as_dict=True,
	)
	if not previous:
		return

	prev_end = to_calendar_day(previous.end_date)
	renewal_start = to_calendar_day(renewal_contract.get("start_date"))

	# Only close if previous has ended and renewal has started
	if prev_end >= today:
		return
	if renewal_start > today:
		return
	if previous.closed_by_renewal_at:
		return  # Already closed

	# Set closedByRenewalAt
	frappe.db.set_value(
		"Lease Contract", previous_contract_name,
		"closed_by_renewal_at", frappe.utils.now(),
		update_modified=False,
	)

	# Capture metered openings from unit for the new renewal contract
	if renewal_contract.get("name"):
		new_contract_doc = frappe.get_doc("Lease Contract", renewal_contract["name"])
		capture_metered_openings_from_unit(new_contract_doc, account)
		new_contract_doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Close expired contracts by renewal  (source: closeExpiredContractsByRenewal)
# ---------------------------------------------------------------------------


def close_expired_contracts_by_renewal() -> int:
	"""Close expired contracts whose approved renewal has now started.

	Source: ``closeExpiredContractsByRenewal``.
	"""
	today = to_calendar_day(frappe.utils.today())

	# Find expired contracts with no closedByRenewalAt that have a started renewal
	expired_contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"status": "expired",
			"closed_by_renewal_at": ["is", "not set"],
		},
		fields=["name", "end_date"],
	)

	count = 0
	for c in expired_contracts:
		renewal = frappe.get_all(
			"Lease Contract",
			filters={
				"renewed_from_contract": c.name,
				"status": ["not in", ["draft", "cancelled", "evicted"]],
				"start_date": ["<=", today],
			},
			fields=["name", "start_date", "rental_account"],
			limit=1,
		)
		if renewal:
			r = renewal[0]
			prev_end = to_calendar_day(c.end_date)
			if prev_end < today:
				close_previous_contract_by_renewal(c.name, r, r.get("rental_account"))
				count += 1

	return count


# ---------------------------------------------------------------------------
# Renewal helpers  (source: isApprovedRenewal, isStartedRenewal, etc.)
# ---------------------------------------------------------------------------


def is_approved_renewal(contract_name: str) -> bool:
	"""Check if contract is an approved renewal (not draft/cancelled/evicted)."""
	status = frappe.db.get_value("Lease Contract", contract_name, "status")
	return status not in ("draft", "cancelled", "evicted")


def is_started_renewal(contract_name: str) -> bool:
	"""Check if renewal has started (start_date <= today)."""
	today = to_calendar_day(frappe.utils.today())
	start_date = frappe.db.get_value("Lease Contract", contract_name, "start_date")
	if not start_date:
		return False
	return to_calendar_day(start_date) <= today


def has_non_cancelled_renewal(previous_contract_name: str) -> bool:
	"""Check if a non-cancelled/non-evicted renewal exists."""
	return bool(frappe.db.exists(
		"Lease Contract",
		{
			"renewed_from_contract": previous_contract_name,
			"status": ["not in", ["cancelled", "evicted"]],
		},
	))


def get_started_renewal(previous, as_of=None) -> dict | None:
	"""Return the started approved renewal for a previous contract, if any.

	Source: ``getStartedRenewal`` (renewal.service.ts:37-39).
	Accepts either a contract name (str) or a previous contract dict (with
	optional ``renewals`` list). When a dict with ``renewals`` is passed,
	filtering is done in-memory to match the original semantics.
	"""
	if as_of is None:
		as_of = to_calendar_day(frappe.utils.today())
	else:
		as_of = to_calendar_day(as_of)

	# If given a dict with renewals already attached, filter in-memory
	if isinstance(previous, dict) and "renewals" in previous and previous["renewals"]:
		for r in previous["renewals"]:
			if is_approved_renewal_status(r.get("status")):
				r_start = to_calendar_day(r.get("start_date"))
				if r_start <= as_of:
					return r
		return None

	# Otherwise resolve by name (str or dict with "name")
	previous_name = previous if isinstance(previous, str) else previous.get("name")
	if not previous_name:
		return None

	renewals = frappe.get_all(
		"Lease Contract",
		filters={
			"renewed_from_contract": previous_name,
			"status": ["not in", ["draft", "cancelled", "evicted"]],
			"start_date": ["<=", as_of],
		},
		fields=["name", "start_date", "rental_account"],
		limit=1,
	)
	return renewals[0] if renewals else None


def is_approved_renewal_status(status: str | None) -> bool:
	"""Source: ``isApprovedRenewal`` (renewal.service.ts:12-14)."""
	return status not in ("draft", "cancelled", "evicted")


def get_approved_renewals(previous_contract_name: str) -> list[dict]:
	"""Return all approved renewals for a previous contract.

	Source: ``getApprovedRenewals`` (renewal.service.ts:33-35).
	"""
	return frappe.get_all(
		"Lease Contract",
		filters={
			"renewed_from_contract": previous_contract_name,
			"status": ["not in", ["draft", "cancelled", "evicted"]],
		},
		fields=["name", "contract_number", "status", "start_date", "end_date"],
	)


# ---------------------------------------------------------------------------
# Renewal first due date  (source: getRenewalFirstDueDate)
# ---------------------------------------------------------------------------


def get_renewal_first_due_date(previous_contract_name: str):
	"""Return the renewal start date (= previous end_date + 1 day)."""
	end_date = frappe.db.get_value("Lease Contract", previous_contract_name, "end_date")
	if not end_date:
		return None
	return add_days(end_date, 1)
