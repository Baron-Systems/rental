"""Settings API for Unit Types, Unit Attributes, and type-attribute mappings.

Follows the same pattern as ``rental.rental.api.settings`` (due-types CRUD).
All system protection rules are enforced by the DocType controllers
(``unit_type.py``, ``unit_attribute.py``) — this API layer only handles
data marshalling and account isolation.
"""

from __future__ import annotations

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
	"""Return the current user's rental account, or the first active account for System Manager.

	Uses a direct SQL query for the fallback to bypass any permission_query_conditions
	that might filter out Rental Account records for System Managers.
	"""
	account = get_current_rental_account()
	if account is not None:
		return account
	# Direct DB query — bypasses permission_query_conditions
	accounts = frappe.db.sql(
		"SELECT name FROM `tabRental Account` WHERE is_active = 1 LIMIT 1",
		as_dict=True,
	)
	if not accounts:
		return None
	return accounts[0]["name"]


def _merge_attribute_override(unit_type: str, attribute: str, defaults: dict) -> dict:
	"""Merge default Unit Type Attribute settings with a User Unit Preference override.

	If no override exists for (current_account, current_user, unit_type, attribute),
	returns defaults.  The rental_account and user are always derived from the
	session — never trusted from frontend input.
	"""
	user = frappe.session.user
	account = _get_account_or_fallback()
	filters = {
		"user": user,
		"unit_type": unit_type,
		"attribute": attribute,
	}
	if account:
		filters["rental_account"] = account
	override = frappe.db.get_value(
		"User Unit Preference",
		filters,
		["is_required", "is_active", "display_order"],
		as_dict=True,
	)
	if override:
		return {
			"is_required": int(override.is_required or 0),
			"is_active": int(override.is_active if override.is_active is not None else 1),
			"display_order": int(override.display_order or 0),
			"has_override": True,
		}
	return {
		"is_required": int(defaults.get("is_required", 0)),
		"is_active": int(defaults.get("is_active", 1)),
		"display_order": int(defaults.get("display_order", 0)),
		"has_override": False,
	}


# ---------------------------------------------------------------------------
# Unit Types
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_unit_types(include_inactive=1):
	"""List all unit types visible to the current account.

	System types (rental_account = NULL) and the account's custom types
	are returned. Ensures system types are seeded before listing.
	"""
	ensure_system_unit_types()

	account = _get_account_or_fallback()

	or_filters = {}
	if account:
		or_filters = {
			"rental_account": account,
			"is_system": 1,
		}

	filters = {}
	if not int(include_inactive):
		filters["is_active"] = 1

	types = frappe.get_all(
		"Unit Type",
		filters=filters if filters else None,
		or_filters=or_filters if or_filters else None,
		fields=[
			"name", "type_name", "code", "is_system",
			"is_active", "display_order", "rental_account",
		],
		order_by="is_system desc, display_order asc, type_name asc",
	)

	# Count units per type and attributes per type
	for t in types:
		t["unit_count"] = frappe.db.count("Rental Unit", {"unit_type": t["name"]})
		t["attribute_count"] = frappe.db.count("Unit Type Attribute", {"parent": t["name"]})

	return {"unitTypes": types}


@frappe.whitelist()
def create_unit_type(type_name, is_active=1, display_order=0):
	"""Create a custom unit type.

	System types cannot be created via this API.
	"""
	account = _get_account_or_fallback()
	if account is None:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	name = (type_name or "").strip()
	if not name:
		frappe.throw(frappe._("اسم نوع الوحدة مطلوب"), frappe.ValidationError)

	# Check unique name per account
	existing = frappe.db.exists(
		"Unit Type",
		{"type_name": name, "rental_account": account},
	)
	if existing:
		frappe.throw(
			frappe._("اسم نوع الوحدة مستخدم مسبقًا. يرجى إدخال اسم مختلف."),
			frappe.ValidationError,
		)

	# Auto-generate code from name
	code = name.replace(" ", "_").lower()[:50]
	# Ensure code uniqueness
	base_code = code
	counter = 1
	while frappe.db.exists("Unit Type", {"code": code}):
		code = f"{base_code}_{counter}"
		counter += 1

	doc = frappe.get_doc({
		"doctype": "Unit Type",
		"type_name": name,
		"code": code,
		"is_system": 0,
		"rental_account": account,
		"is_active": int(is_active),
		"display_order": int(display_order or 0),
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def update_unit_type(name, type_name=None, is_active=None, display_order=None):
	"""Update a unit type.

	System types are read-only for Rental Property Owners — any customization
	(is_active, display_order) must be done via User Unit Preference overrides.
	System Manager can still modify system types directly.
	type_name (identity) can only be changed on custom types.
	code and is_system are protected at the doctype level.
	"""
	doc = frappe.get_doc("Unit Type", name)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل أنواع الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	if type_name is not None and not doc.is_system:
		new_name = type_name.strip()
		if not new_name:
			frappe.throw(frappe._("اسم نوع الوحدة مطلوب"), frappe.ValidationError)
		doc.type_name = new_name

	if is_active is not None:
		doc.is_active = int(is_active)

	if display_order is not None:
		doc.display_order = int(display_order or 0)

	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def delete_unit_type(name):
	"""Delete a custom unit type. System types cannot be deleted.

	Backend on_trash checks for referenced units.
	"""
	doc = frappe.get_doc("Unit Type", name)
	if not is_system_manager():
		doc.check_permission("delete")

	if doc.is_system:
		frappe.throw(
			frappe._("لا يمكن حذف أنواع الوحدات النظامية"),
			frappe.PermissionError,
		)

	frappe.delete_doc("Unit Type", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Unit Type → Attributes mapping
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_unit_type_attributes(unit_type):
	"""Get the attribute assignments for a unit type.

	Returns a list of dicts with attribute details and mapping settings.
	Merged with User Unit Preference overrides if they exist.
	"""
	type_doc = frappe.get_doc("Unit Type", unit_type)
	result = []
	for row in type_doc.attributes:
		attr = frappe.db.get_value(
			"Unit Attribute", row.attribute,
			["name", "attribute_name", "code", "data_type", "is_system",
			 "is_active", "capability_code", "category"],
			as_dict=True,
		)
		if not attr:
			continue
		merged = _merge_attribute_override(unit_type, row.attribute, {
			"is_required": row.is_required,
			"is_active": row.is_active,
			"display_order": row.display_order,
		})
		result.append({
			"name": row.name,
			"attribute": row.attribute,
			"attribute_name": attr.attribute_name,
			"attribute_code": attr.code,
			"data_type": attr.data_type,
			"is_system": attr.is_system,
			"attribute_active": attr.is_active,
			"capability_code": attr.capability_code,
			"category": attr.category,
			"is_required": merged["is_required"],
			"is_active": merged["is_active"],
			"display_order": merged["display_order"],
			"has_override": merged["has_override"],
		})

	# Sort by display_order then attribute_name
	result.sort(key=lambda x: (x["display_order"] or 0, x["attribute_name"]))
	return {"attributes": result}


@frappe.whitelist()
def get_available_attributes(unit_type):
	"""Get all attributes NOT yet assigned to this unit type.

	Returns both system and account-specific attributes.
	"""
	account = _get_account_or_fallback()

	# Get currently assigned attribute names
	assigned = set()
	type_doc = frappe.get_doc("Unit Type", unit_type)
	for row in type_doc.attributes:
		assigned.add(row.attribute)

	# Get all visible attributes
	or_filters = {}
	if account:
		or_filters = {
			"rental_account": account,
			"is_system": 1,
		}

	all_attrs = frappe.get_all(
		"Unit Attribute",
		filters={"is_active": 1},
		or_filters=or_filters if or_filters else None,
		fields=[
			"name", "attribute_name", "code", "data_type",
			"is_system", "capability_code", "category",
		],
		order_by="is_system desc, attribute_name asc",
	)

	available = [a for a in all_attrs if a["name"] not in assigned]
	return {"attributes": available}


@frappe.whitelist()
def add_unit_type_attribute(unit_type, attribute, is_required=0, display_order=0):
	"""Add an attribute to a unit type.

	Works for custom unit types only.  System unit types are read-only for
	Rental Property Owners — use User Unit Preference overrides instead.
	System Manager can modify system types directly.
	Identity fields (code, is_system) are protected at the doctype level.
	"""
	doc = frappe.get_doc("Unit Type", unit_type)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل أنواع الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	# Check not already assigned
	for row in doc.attributes:
		if row.attribute == attribute:
			frappe.throw(
				frappe._("الخاصية مضافة بالفعل إلى هذا النوع"),
				frappe.ValidationError,
			)

	doc.append("attributes", {
		"attribute": attribute,
		"is_required": int(is_required),
		"is_active": 1,
		"display_order": int(display_order or 0),
	})
	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return {"success": True}


@frappe.whitelist()
def update_unit_type_attribute(unit_type, row_name, is_required=None, is_active=None, display_order=None):
	"""Update a unit type attribute mapping.

	Works for custom unit types only.  System unit types are read-only for
	Rental Property Owners — use User Unit Preference overrides instead.
	System Manager can modify system types directly.
	"""
	doc = frappe.get_doc("Unit Type", unit_type)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل أنواع الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	for row in doc.attributes:
		if row.name == row_name:
			if is_required is not None:
				row.is_required = int(is_required)
			if is_active is not None:
				row.is_active = int(is_active)
			if display_order is not None:
				row.display_order = int(display_order or 0)
			break
	else:
		frappe.throw(frappe._("الخاصية غير موجودة في هذا النوع"), frappe.ValidationError)

	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return {"success": True}


@frappe.whitelist()
def remove_unit_type_attribute(unit_type, row_name):
	"""Remove an attribute from a unit type.

	This does NOT delete stored values from existing rental units.
	Works for custom unit types only.  System unit types are read-only for
	Rental Property Owners — use User Unit Preference overrides instead.
	System Manager can modify system types directly.
	"""
	doc = frappe.get_doc("Unit Type", unit_type)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل أنواع الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	for i, row in enumerate(doc.attributes):
		if row.name == row_name:
			doc.attributes.pop(i)
			break
	else:
		frappe.throw(frappe._("الخاصية غير موجودة في هذا النوع"), frappe.ValidationError)

	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return {"success": True}


@frappe.whitelist()
def save_unit_type_attributes(unit_type, attributes):
	"""Save the full set of Unit Type → Attribute mappings in one transaction.

	Accepts a JSON list of dicts: ``[{attribute, is_required, display_order}, ...]``.
	New attributes are added, removed attributes are deleted, and existing ones
	are updated with the new ``is_required`` and ``display_order``.

	- Account scoped (checks write permission on the Unit Type).
	- Transactional — all changes succeed or none do.
	- Only accepts attributes that are valid (exist in Unit Attribute doctype).
	- Prevents duplicate attribute assignments.
	- ``display_order`` is rebuilt sequentially (0, 1, 2, ...) based on list order.
	"""
	import json

	if isinstance(attributes, str):
		attributes = json.loads(attributes)

	doc = frappe.get_doc("Unit Type", unit_type)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل أنواع الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	# Validate input — no duplicates, all attributes exist
	seen = set()
	for item in attributes:
		attr_name = item.get("attribute") or item.get("name")
		if not attr_name:
			frappe.throw(frappe._("خاصية غير صالحة في القائمة"), frappe.ValidationError)
		if attr_name in seen:
			frappe.throw(
				frappe._("الخاصية مكررة في القائمة"),
				frappe.ValidationError,
			)
		seen.add(attr_name)
		if not frappe.db.exists("Unit Attribute", attr_name):
			frappe.throw(
				frappe._("الخاصية '{0}' غير موجودة").format(attr_name),
				frappe.ValidationError,
			)

	# Build the new child table from scratch
	# Preserve is_active for existing rows; default to 1 for new rows
	existing_map = {}
	for row in doc.attributes:
		existing_map[row.attribute] = row

	new_rows = []
	for idx, item in enumerate(attributes):
		attr_name = item.get("attribute") or item.get("name")
		is_required = int(item.get("is_required", 0))
		display_order = idx  # sequential 0, 1, 2, ...
		is_active = int(existing_map.get(attr_name, {}).get("is_active", 1)) if attr_name in existing_map else 1
		new_rows.append({
			"attribute": attr_name,
			"is_required": is_required,
			"is_active": is_active,
			"display_order": display_order,
		})

	# Clear existing and rebuild
	doc.attributes = []
	for row in new_rows:
		doc.append("attributes", row)

	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return {"success": True, "count": len(new_rows)}


@frappe.whitelist()
def save_user_unit_type_preferences(unit_type, attributes):
	"""Save User Unit Preference overrides for a unit type's attributes.

	Accepts a JSON list of dicts: ``[{attribute, is_required, is_active, display_order}, ...]``.
	Only attributes already assigned to the Unit Type can have overrides.
	Missing attributes in the payload keep their existing overrides (if any).
	"""
	import json

	if isinstance(attributes, str):
		attributes = json.loads(attributes)

	user = frappe.session.user
	account = _get_account_or_fallback()
	if not account:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	# Ensure the unit type exists and the user can read it
	type_doc = frappe.get_doc("Unit Type", unit_type)
	assigned = {row.attribute for row in type_doc.attributes}

	for item in attributes:
		attr_name = item.get("attribute") or item.get("name")
		if not attr_name:
			continue
		if attr_name not in assigned:
			frappe.throw(
				frappe._("الخاصية '{0}' غير مضافة إلى نوع الوحدة. لا يمكن إنشاء تفضيل لخاصية غير موجودة.").format(attr_name),
				frappe.ValidationError,
			)

		existing_filters = {
			"user": user,
			"unit_type": unit_type,
			"attribute": attr_name,
		}
		if account:
			existing_filters["rental_account"] = account
		existing = frappe.db.get_value(
			"User Unit Preference",
			existing_filters,
			"name",
		)
		if existing:
			doc = frappe.get_doc("User Unit Preference", existing)
			doc.is_required = int(item.get("is_required", 0))
			doc.is_active = int(item.get("is_active", 1))
			doc.display_order = int(item.get("display_order", 0))
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc({
				"doctype": "User Unit Preference",
				"rental_account": account,
				"user": user,
				"unit_type": unit_type,
				"attribute": attr_name,
				"is_required": int(item.get("is_required", 0)),
				"is_active": int(item.get("is_active", 1)),
				"display_order": int(item.get("display_order", 0)),
			}).insert(ignore_permissions=True)

	return {"success": True}


@frappe.whitelist()
def reset_user_unit_preferences(unit_type=None):
	"""Delete all User Unit Preference overrides for the current user.

	If ``unit_type`` is provided, only preferences for that unit type are removed.
	If omitted, ALL user unit preferences are removed.
	"""
	user = frappe.session.user
	account = _get_account_or_fallback()
	filters = {"user": user}
	if account:
		filters["rental_account"] = account
	if unit_type:
		filters["unit_type"] = unit_type

	prefs = frappe.get_all("User Unit Preference", filters=filters, pluck="name")
	for name in prefs:
		frappe.delete_doc("User Unit Preference", name, ignore_permissions=True)

	return {"success": True, "removed": len(prefs)}


# ---------------------------------------------------------------------------
# Unit Attributes
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_unit_attributes(include_inactive=1):
	"""List all unit attributes visible to the current account.

	System attributes (rental_account = NULL) and the account's custom
	attributes are returned. Ensures system attributes are seeded before listing.
	"""
	ensure_system_unit_attributes()

	account = _get_account_or_fallback()

	or_filters = {}
	if account:
		or_filters = {
			"rental_account": account,
			"is_system": 1,
		}

	filters = {}
	if not int(include_inactive):
		filters["is_active"] = 1

	attrs = frappe.get_all(
		"Unit Attribute",
		filters=filters if filters else None,
		or_filters=or_filters if or_filters else None,
		fields=[
			"name", "attribute_name", "code", "data_type",
			"options", "category", "is_system", "is_active",
			"display_order", "rental_account", "capability_code",
		],
		order_by="is_system desc, display_order asc, attribute_name asc",
	)

	# Count values per attribute
	for a in attrs:
		a["value_count"] = frappe.db.count("Unit Attribute Value", {"attribute": a["name"]})
		a["type_assignment_count"] = frappe.db.count("Unit Type Attribute", {"attribute": a["name"]})

	return {"unitAttributes": attrs}


@frappe.whitelist()
def create_unit_attribute(
	attribute_name, data_type, options=None, category=None,
	is_active=1, display_order=0,
):
	"""Create a custom unit attribute.

	System attributes cannot be created via this API.
	Capability_code is never settable via this API.
	"""
	account = _get_account_or_fallback()
	if account is None:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	name = (attribute_name or "").strip()
	if not name:
		frappe.throw(frappe._("اسم الخاصية مطلوب"), frappe.ValidationError)

	# Validate data_type
	valid_types = {"Text", "Integer", "Decimal", "Check", "Select", "Date"}
	if data_type not in valid_types:
		frappe.throw(frappe._("نوع البيانات غير صالح"), frappe.ValidationError)

	# Options required for Select type
	if data_type == "Select":
		if not options or not options.strip():
			frappe.throw(
				frappe._("الخيارات مطلوبة عند اختيار نوع البيانات 'قائمة منسدلة'"),
				frappe.ValidationError,
			)
	else:
		options = None

	# Validate category if provided
	valid_categories = {"internal", "external", "services", "commercial", "warehouse", "office", "other"}
	if category and category not in valid_categories:
		frappe.throw(frappe._("التصنيف غير صالح"), frappe.ValidationError)

	# Check unique name per account
	existing = frappe.db.exists(
		"Unit Attribute",
		{"attribute_name": name, "rental_account": account},
	)
	if existing:
		frappe.throw(
			frappe._("اسم الخاصية مستخدم مسبقًا. يرجى إدخال اسم مختلف."),
			frappe.ValidationError,
		)

	# Auto-generate code from name
	code = name.replace(" ", "_").lower()[:50]
	base_code = code
	counter = 1
	while frappe.db.exists("Unit Attribute", {"code": code}):
		code = f"{base_code}_{counter}"
		counter += 1

	doc = frappe.get_doc({
		"doctype": "Unit Attribute",
		"attribute_name": name,
		"code": code,
		"data_type": data_type,
		"options": options,
		"category": category,
		"is_system": 0,
		"rental_account": account,
		"is_active": int(is_active),
		"display_order": int(display_order or 0),
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def update_unit_attribute(
	name, attribute_name=None, data_type=None, options=None,
	category=None, is_active=None, display_order=None,
):
	"""Update a unit attribute.

	System attributes are read-only for Rental Property Owners — any
	customization (is_active, display_order) must be done via User Unit
	Preference overrides.  System Manager can still modify system attributes
	directly.
	Identity fields (attribute_name, data_type, code, is_system, capability_code)
	are protected at the doctype level.
	Custom attributes: all fields can be changed.
	Capability_code is NEVER user-editable via this API.
	"""
	doc = frappe.get_doc("Unit Attribute", name)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system and not is_system_manager():
		frappe.throw(
			frappe._("لا يمكن تعديل خصائص الوحدات النظامية. استخدم تفضيلات المستخدم للتخصيص."),
			frappe.PermissionError,
		)

	# Custom attributes: allow identity field updates
	if not doc.is_system:
		if attribute_name is not None:
			new_name = attribute_name.strip()
			if not new_name:
				frappe.throw(frappe._("اسم الخاصية مطلوب"), frappe.ValidationError)
			doc.attribute_name = new_name

		if data_type is not None:
			valid_types = {"Text", "Integer", "Decimal", "Check", "Select", "Date"}
			if data_type not in valid_types:
				frappe.throw(frappe._("نوع البيانات غير صالح"), frappe.ValidationError)
			doc.data_type = data_type

		if options is not None:
			if doc.data_type == "Select":
				if not options or not options.strip():
					frappe.throw(
						frappe._("الخيارات مطلوبة عند اختيار نوع البيانات 'قائمة منسدلة'"),
						frappe.ValidationError,
					)
				doc.options = options
			else:
				doc.options = None

		if category is not None:
			valid_categories = {"internal", "external", "services", "commercial", "warehouse", "office", "other"}
			if category and category not in valid_categories:
				frappe.throw(frappe._("التصنيف غير صالح"), frappe.ValidationError)
			doc.category = category

		if display_order is not None:
			doc.display_order = int(display_order or 0)

	# Both system and custom: allow operational settings
	if is_active is not None:
		doc.is_active = int(is_active)

	if display_order is not None and doc.is_system:
		doc.display_order = int(display_order or 0)

	doc.flags.ignore_version = True
	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def delete_unit_attribute(name):
	"""Delete a custom unit attribute. System attributes cannot be deleted.

	Backend on_trash checks for stored values and type assignments.
	"""
	doc = frappe.get_doc("Unit Attribute", name)
	if not is_system_manager():
		doc.check_permission("delete")

	if doc.is_system:
		frappe.throw(
			frappe._("لا يمكن حذف خصائص الوحدات النظامية"),
			frappe.PermissionError,
		)

	frappe.delete_doc("Unit Attribute", name, ignore_permissions=is_system_manager())
	return {"success": True}
