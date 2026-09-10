"""Settings API for Unit Types and Account-level Unit Type Attribute configuration.

System master data (Unit Types, Unit Attributes, and the Unit Type Attribute
child table) is read-only for accounts. Accounts configure which System
Attributes they use for each System Unit Type via ``Account Unit Type
Attribute`` rows.

Model summary:
- A row in ``Account Unit Type Attribute`` for (account, unit_type, attribute)
  means the attribute is in the account's list for that Unit Type.
- Absence of a row means the attribute is not used.
- When no rows exist for (account, unit_type), the System Default child table
  on the Unit Type is used.
- ``is_required`` and ``display_order`` are stored per account.
- There is no ``user`` and no ``is_active`` on the configuration row.
"""

from __future__ import annotations

import json

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager
from rental.rental.services.unit_type_service import (
	ensure_system_unit_types,
	ensure_system_unit_attributes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_account_or_fallback() -> str | None:
	"""Return the current user's rental account, or the first active account for System Manager."""
	account = get_current_rental_account()
	if account is not None:
		return account
	accounts = frappe.db.sql(
		"SELECT name FROM `tabRental Account` WHERE is_active = 1 LIMIT 1",
		as_dict=True,
	)
	if not accounts:
		return None
	return accounts[0]["name"]


def _resolve_account_config(account: str, unit_type: str):
	"""Return (rows, has_customization).

	``rows`` is a list of dicts: {attribute, is_required, display_order}.
	``has_customization`` is True when Account Unit Type Attribute rows exist
	for (account, unit_type); False when falling back to System Defaults.
	"""
	customizations = frappe.get_all(
		"Account Unit Type Attribute",
		filters={"rental_account": account, "unit_type": unit_type},
		fields=["attribute", "is_required", "display_order"],
		order_by="display_order asc",
	)
	if customizations:
		return customizations, True

	type_doc = frappe.get_doc("Unit Type", unit_type)
	rows = [
		{
			"attribute": row.attribute,
			"is_required": int(row.is_required or 0),
			"display_order": int(row.display_order or 0),
		}
		for row in type_doc.attributes
	]
	return rows, False


# ---------------------------------------------------------------------------
# Unit Types (read-only listing with Account-level active override)
# ---------------------------------------------------------------------------

def _resolve_account_unit_type_active(account: str, unit_type: str, system_is_active: int) -> tuple[int, bool]:
	"""Return (effective_is_active, has_account_override).

	When an Account Unit Type override exists, its is_active is authoritative.
	Otherwise the System Unit Type's is_active is used.
	"""
	override = frappe.db.get_value(
		"Account Unit Type",
		{"rental_account": account, "unit_type": unit_type},
		"is_active",
	)
	if override is None:
		return int(system_is_active or 0), False
	return int(override or 0), True


@frappe.whitelist()
def get_unit_types(include_inactive=1):
	"""List System Unit Types visible to the current account.

	System Unit Types are master data — their identity is read-only.
	The effective ``is_active`` for each type is resolved from:
	  1. Account Unit Type override (rental_account, unit_type) if present.
	  2. System Unit Type.is_active otherwise.

	When ``include_inactive=0``, types whose effective is_active is 0 are
	excluded from the result.
	"""
	ensure_system_unit_types()

	account = _get_account_or_fallback()

	types = frappe.get_all(
		"Unit Type",
		filters={"is_system": 1},
		fields=[
			"name", "type_name", "code", "is_system",
			"is_active", "display_order", "rental_account",
		],
		order_by="display_order asc, type_name asc",
	)

	# Pre-fetch all account overrides for this account (one query)
	account_overrides = {}
	if account:
		for row in frappe.get_all(
			"Account Unit Type",
			filters={"rental_account": account},
			fields=["unit_type", "is_active"],
		):
			account_overrides[row["unit_type"]] = int(row["is_active"] or 0)

	result = []
	for t in types:
		system_active = int(t.get("is_active") or 0)
		if account and t["name"] in account_overrides:
			effective_active = account_overrides[t["name"]]
			has_override = True
		else:
			effective_active = system_active
			has_override = False
		t["is_active"] = effective_active
		t["has_account_override"] = has_override
		t["system_is_active"] = system_active
		t["unit_count"] = frappe.db.count("Rental Unit", {"unit_type": t["name"]})
		t["attribute_count"] = frappe.db.count("Unit Type Attribute", {"parent": t["name"]})

		if not int(include_inactive) and not effective_active:
			continue
		result.append(t)

	return {"unitTypes": result}


@frappe.whitelist()
def toggle_account_unit_type(unit_type, is_active):
	"""Toggle the Account-level active state for a System Unit Type.

	Creates or updates an ``Account Unit Type`` override row for
	(rental_account, unit_type). Does NOT modify the System Unit Type.
	"""
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Account-level toggle is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	is_active = int(is_active or 0)

	existing = frappe.db.get_value(
		"Account Unit Type",
		{"rental_account": account, "unit_type": unit_type},
		"name",
	)
	if existing:
		doc = frappe.get_doc("Account Unit Type", existing)
		doc.is_active = is_active
		doc.flags.ignore_version = True
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({
			"doctype": "Account Unit Type",
			"rental_account": account,
			"unit_type": unit_type,
			"is_active": is_active,
		}).insert(ignore_permissions=True)

	return {"success": True, "is_active": is_active}


@frappe.whitelist()
def reset_account_unit_type(unit_type):
	"""Remove the Account-level override for a System Unit Type.

	Deletes the ``Account Unit Type`` row for (rental_account, unit_type).
	The next read falls back to the System Unit Type.is_active.
	"""
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Account-level reset is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	existing = frappe.get_all(
		"Account Unit Type",
		filters={"rental_account": account, "unit_type": unit_type},
		pluck="name",
	)
	for name in existing:
		frappe.delete_doc("Account Unit Type", name, ignore_permissions=True)

	return {"success": True, "removed": len(existing)}


# ---------------------------------------------------------------------------
# Account Unit Type Attribute configuration
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_unit_type_attributes(unit_type):
	"""Get the attribute list for a Unit Type as configured by the current account.

	If the account has customized this Unit Type, the account's full list is
	returned. Otherwise the System Default child table on the Unit Type is
	returned.
	"""
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Customization is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	rows, has_customization = _resolve_account_config(account, unit_type)

	result = []
	for row in rows:
		attr = frappe.db.get_value(
			"Unit Attribute", row["attribute"],
			[
				"name", "attribute_name", "code", "data_type", "options",
				"is_system", "is_active", "capability_code", "category",
			],
			as_dict=True,
		)
		if not attr:
			continue
		if not int(attr.is_active or 0):
			continue
		result.append({
			"attribute": row["attribute"],
			"attribute_name": attr.attribute_name,
			"attribute_code": attr.code,
			"data_type": attr.data_type,
			"options": attr.options or "",
			"is_system": attr.is_system,
			"capability_code": attr.capability_code or "",
			"category": attr.category or "",
			"is_required": int(row.get("is_required") or 0),
			"display_order": int(row.get("display_order") or 0),
			"has_customization": has_customization,
		})

	result.sort(key=lambda x: (x["display_order"], x["attribute_name"]))
	return {"attributes": result}


@frappe.whitelist()
def get_available_attributes(unit_type):
	"""Get System Attributes NOT currently in the account's list for this Unit Type.

	This allows re-adding an attribute that was previously removed.
	"""
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Customization is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	# Current list (customizations or defaults)
	rows, _ = _resolve_account_config(account, unit_type)
	used = {row["attribute"] for row in rows}

	all_attrs = frappe.get_all(
		"Unit Attribute",
		filters={"is_active": 1, "is_system": 1},
		fields=["name", "attribute_name", "code", "data_type", "is_system", "capability_code", "category"],
		order_by="attribute_name asc",
	)

	available = [a for a in all_attrs if a["name"] not in used]
	return {"attributes": available}


@frappe.whitelist()
def save_account_unit_type_attributes(unit_type, attributes):
	"""Replace the account's attribute list for a Unit Type (transactional).

	Validates the full payload first, then deletes existing rows and creates
	new ones inside a savepoint. Any error rolls back to preserve the prior
	configuration.
	"""
	if isinstance(attributes, str):
		attributes = json.loads(attributes)

	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	# 1. Validate Unit Type is System
	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Customization is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	# 2. Validate no duplicates and all attributes exist + are system
	seen = set()
	for item in attributes:
		attr_name = item.get("attribute") or item.get("name")
		if not attr_name:
			frappe.throw(
				frappe._("Invalid attribute in list."),
				frappe.ValidationError,
			)
		if attr_name in seen:
			frappe.throw(
				frappe._("Duplicate attribute in list."),
				frappe.ValidationError,
			)
		seen.add(attr_name)

		attr = frappe.db.get_value(
			"Unit Attribute", attr_name, ["name", "is_system"], as_dict=True,
		)
		if not attr:
			frappe.throw(
				frappe._("Attribute '{0}' does not exist.").format(attr_name),
				frappe.ValidationError,
			)
		if not int(attr.is_system or 0):
			frappe.throw(
				frappe._("Only System Attributes can be used in Account configuration."),
				frappe.ValidationError,
			)

	# 3. Transactional replace
	frappe.db.savepoint("before_account_attributes_save")
	try:
		existing = frappe.get_all(
			"Account Unit Type Attribute",
			filters={"rental_account": account, "unit_type": unit_type},
			pluck="name",
		)
		for name in existing:
			frappe.delete_doc(
				"Account Unit Type Attribute", name, ignore_permissions=True,
			)

		for idx, item in enumerate(attributes):
			attr_name = item.get("attribute") or item.get("name")
			frappe.get_doc({
				"doctype": "Account Unit Type Attribute",
				"rental_account": account,
				"unit_type": unit_type,
				"attribute": attr_name,
				"is_required": int(item.get("is_required", 0)),
				"display_order": idx,
			}).insert(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="before_account_attributes_save")
		raise

	return {"success": True, "count": len(attributes)}


@frappe.whitelist()
def reset_account_unit_type_attributes(unit_type):
	"""Restore System Defaults for (account, unit_type).

	Deletes all Account Unit Type Attribute rows for this account + unit_type.
	The next call to ``get_unit_type_attributes`` will fall back to the System
	Default child table.
	"""
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	type_doc = frappe.get_doc("Unit Type", unit_type)
	if not int(type_doc.is_system or 0):
		frappe.throw(
			frappe._("Customization is only supported on System Unit Types."),
			frappe.ValidationError,
		)

	existing = frappe.get_all(
		"Account Unit Type Attribute",
		filters={"rental_account": account, "unit_type": unit_type},
		pluck="name",
	)
	for name in existing:
		frappe.delete_doc(
			"Account Unit Type Attribute", name, ignore_permissions=True,
		)

	return {"success": True, "removed": len(existing)}
