"""Tenant service layer.

Source: TENANTS_MIGRATION_SPEC §21.
"""

from __future__ import annotations

import frappe


def can_delete_tenant(tenant_name: str) -> tuple[bool, str | None]:
	"""Check if a tenant can be deleted.

	Source: TEN-BE-004, TEN-BE-005.
	Returns (True, None) if deletable, (False, error_message) otherwise.
	"""
	if frappe.db.exists("DocType", "Lease Contract"):
		contract_count = frappe.db.count("Lease Contract", {"tenant": tenant_name})
		if contract_count:
			return False, "لا يمكن حذف مستأجر لديه عقود"

	if frappe.db.exists("DocType", "Rental Due"):
		due_count = frappe.db.count("Rental Due", {"tenant": tenant_name})
		if due_count:
			return False, "لا يمكن حذف مستأجر لديه حركات مالية"

	if frappe.db.exists("DocType", "Rental Receipt"):
		receipt_count = frappe.db.count("Rental Receipt", {"tenant": tenant_name})
		if receipt_count:
			return False, "لا يمكن حذف مستأجر لديه حركات مالية"

	return True, None


def assert_tenant_exists(tenant_name: str) -> None:
	"""Raise DoesNotExistError if tenant does not exist."""
	if not frappe.db.exists("Rental Tenant", tenant_name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)
