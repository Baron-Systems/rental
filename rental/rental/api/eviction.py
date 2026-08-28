"""Evictions API.

Ported from ``src/app/api/evictions/route.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager


@frappe.whitelist()
def create_eviction(contract, notes=None):
	"""Create and submit an eviction record.

	Source: ``POST /api/evictions``.
	Only accepts ``contract`` and ``notes`` — matching the original API.
	Eviction date is auto-set to today by the doctype validate method.
	"""
	# Source: evictions/route.ts:13-15 — contractId is required
	if not contract:
		frappe.throw(frappe._("العقد مطلوب"))

	account = get_current_rental_account()

	# Check contract exists
	if not frappe.db.exists("Lease Contract", contract):
		frappe.throw(frappe._("العقد غير موجود"))

	# Check contract is not archived
	is_archived = frappe.db.get_value("Lease Contract", contract, "is_archived")
	if is_archived:
		frappe.throw(frappe._("لا يمكن إخلاء عقد مؤرشف"))

	# Check for pending cancellation settlement
	if frappe.db.exists("DocType", "Contract Cancellation Settlement"):
		settlement_name = frappe.db.get_value(
			"Contract Cancellation Settlement", {"contract": contract}, "status"
		)
		if settlement_name == "pending":
			frappe.throw(frappe._("لا يمكن إخلاء الوحدة قبل إكمال تسوية الالتزامات الناتجة عن إلغاء العقد."))

	# Check contract is evictable
	from rental.rental.services.contract_validation import can_evict_contract
	contract_doc = frappe.get_doc("Lease Contract", contract)
	if not can_evict_contract(contract_doc):
		if contract_doc.is_historical:
			frappe.throw(frappe._("لا يمكن إخلاء عقد تاريخي"))
		if contract_doc.status not in ("expired", "cancelled"):
			frappe.throw(frappe._("لا يمكن إخلاء الوحدة إلا للعقد المنتهي أو الملغي"))
		if contract_doc.status == "cancelled" and contract_doc.cancelled_at:
			from rental.rental.utils.date_utils import to_calendar_day
			cancelled_at = to_calendar_day(contract_doc.cancelled_at)
			start_date = to_calendar_day(contract_doc.start_date)
			if cancelled_at < start_date:
				frappe.throw(frappe._("لا يمكن إخلاء الوحدة للعقد القادم الملغي"))
		frappe.throw(frappe._("لا يمكن إخلاء العقد لوجود تجديد معتمد مرتبط به"))

	eviction = frappe.get_doc({
		"doctype": "Rental Eviction",
		"rental_account": account,
		"contract": contract,
		"notes": notes,
	})
	eviction.insert(ignore_permissions=is_system_manager())
	eviction.submit()
	eviction.reload()

	# Source: route.ts:92 returns { eviction } with the created record
	return {
		"eviction": {
			"id": eviction.name,
			"contract_id": eviction.contract,
			"tenant_id": eviction.tenant,
			"unit_id": eviction.unit,
			"eviction_date": eviction.eviction_date,
			"electricity_meter_reading": eviction.electricity_meter_reading,
			"water_meter_reading": eviction.water_meter_reading,
			"notes": eviction.notes,
			"created_at": eviction.creation,
		}
	}
