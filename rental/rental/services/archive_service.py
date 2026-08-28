"""Archive / unarchive contracts.

Ported from ``src/services/archive.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.services.contract_validation import can_archive_contract_eligible


# ---------------------------------------------------------------------------
# Can archive  (source: canArchiveContract)
# ---------------------------------------------------------------------------


def can_archive_contract(contract_name: str) -> dict:
	"""Check if a contract is eligible for archiving.

	Source: ``canArchiveContract`` (archive.service.ts:4-23).
	Returns ``{"eligible": bool, "reason": str | None}``.
	"""
	contract = frappe.get_doc("Lease Contract", contract_name)
	if contract.is_archived:
		return {"eligible": False, "reason": frappe._("العقد مؤرشف مسبقاً")}

	if can_archive_contract_eligible(contract):
		return {"eligible": True, "reason": None}

	return {
		"eligible": False,
		"reason": frappe._(
			"لا يمكن أرشفة هذا العقد؛ الأرشفة متاحة فقط للعقود المُخلاة، "
			"أو التاريخية المنتهية، أو المغلقة بتجديد معتمد، أو المستقبلية الملغاة قبل تاريخ البدء"
		),
	}


# ---------------------------------------------------------------------------
# Archive  (source: archiveContract)
# ---------------------------------------------------------------------------


def archive_contract(contract_name: str):
	"""Archive a contract.

	Source: ``archiveContract`` (archive.service.ts:25-38).
	Order of checks (must match original):
	  1. Contract exists → 'العقد غير موجود'
	  2. Archive eligibility (canArchiveContract)
	  3. Update is_archived + archived_at
	Returns the updated contract document.
	"""
	if not frappe.db.exists("Lease Contract", contract_name):
		frappe.throw(frappe._("العقد غير موجود"))

	result = can_archive_contract(contract_name)
	if not result["eligible"]:
		frappe.throw(result["reason"] or frappe._("لا يمكن أرشفة العقد"))

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

	Source: ``unarchiveContract`` (archive.service.ts:40-51).
	Order of checks (must match original):
	  1. Contract exists → 'العقد غير موجود'
	  2. is_archived → 'العقد غير مؤرشف'
	  3. Update is_archived + archived_at
	Returns the updated contract document.
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
