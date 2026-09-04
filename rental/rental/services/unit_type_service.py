"""Seed service for Unit Types, Unit Attributes, and default type-attribute mappings.

Follows the ``ensure_system_due_types`` pattern from ``due_generation_service.py``:
4-step lookup (by code+isSystem, by name+isSystem, by code any, by name any),
then claim or create.

All seed functions are idempotent — safe to run multiple times.
"""

from __future__ import annotations

import frappe


# ---------------------------------------------------------------------------
# System Unit Types
# ---------------------------------------------------------------------------

SYSTEM_UNIT_TYPES = [
	{"type_name": "شقة", "code": "apartment"},
	{"type_name": "محل", "code": "shop"},
	{"type_name": "مكتب", "code": "office"},
	{"type_name": "مستودع", "code": "warehouse"},
	{"type_name": "غرفة", "code": "room"},
	{"type_name": "كراج", "code": "garage"},
	{"type_name": "عقار مستقل", "code": "independent"},
	{"type_name": "أخرى", "code": "other"},
]


def ensure_system_unit_types() -> None:
	"""Seed the 8 system unit types. Idempotent."""
	for st in SYSTEM_UNIT_TYPES:
		existing = frappe.db.get_value(
			"Unit Type",
			{"code": st["code"], "is_system": 1},
			["name", "type_name", "code", "is_system", "is_active"],
			as_dict=True,
		)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Type",
				{"type_name": st["type_name"], "is_system": 1},
				["name", "type_name", "code", "is_system", "is_active"],
				as_dict=True,
			)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Type",
				{"code": st["code"]},
				["name", "type_name", "code", "is_system", "is_active"],
				as_dict=True,
			)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Type",
				{"type_name": st["type_name"]},
				["name", "type_name", "code", "is_system", "is_active"],
				as_dict=True,
			)

		if not existing:
			frappe.get_doc({
				"doctype": "Unit Type",
				"type_name": st["type_name"],
				"code": st["code"],
				"is_system": 1,
				"rental_account": None,
				"is_active": 1,
				"display_order": _system_type_order(st["code"]),
			}).insert(ignore_permissions=True)
		else:
			updates = {}
			if not existing.is_system:
				updates["is_system"] = 1
			# Do NOT re-enable disabled system types — respect user's operational changes
			if existing.code != st["code"]:
				updates["code"] = st["code"]
			if existing.type_name != st["type_name"]:
				updates["type_name"] = st["type_name"]
			# Do NOT override display_order — user may have changed it
			if updates:
				frappe.db.set_value("Unit Type", existing.name, updates, update_modified=False)


def _system_type_order(code: str) -> int:
	order_map = {
		"apartment": 1,
		"shop": 2,
		"office": 3,
		"warehouse": 4,
		"room": 5,
		"garage": 6,
		"independent": 7,
		"other": 8,
	}
	return order_map.get(code, 99)


# ---------------------------------------------------------------------------
# System Unit Attributes
# ---------------------------------------------------------------------------

SYSTEM_UNIT_ATTRIBUTES = [
	# Meter capabilities (critical)
	{"attribute_name": "عداد كهرباء", "code": "electricity_meter", "data_type": "Check", "capability_code": "electricity_meter"},
	{"attribute_name": "عداد مياه", "code": "water_meter", "data_type": "Check", "capability_code": "water_meter"},
	# Structural - internal
	{"attribute_name": "عدد الغرف", "code": "rooms_count", "data_type": "Integer", "category": "internal"},
	{"attribute_name": "عدد الحمامات", "code": "bathrooms_count", "data_type": "Integer", "category": "internal"},
	{"attribute_name": "مفروش", "code": "furnished", "data_type": "Check", "category": "internal"},
	{"attribute_name": "تكييف", "code": "air_conditioning", "data_type": "Check", "category": "internal"},
	# External
	{"attribute_name": "بلكونة", "code": "balcony", "data_type": "Check", "category": "external"},
	{"attribute_name": "حديقة", "code": "garden", "data_type": "Check", "category": "external"},
	{"attribute_name": "سطح خاص", "code": "private_roof", "data_type": "Check", "category": "external"},
	# Services
	{"attribute_name": "مصعد", "code": "elevator", "data_type": "Check", "category": "services"},
	{"attribute_name": "موقف سيارة", "code": "parking", "data_type": "Check", "category": "services"},
	{"attribute_name": "مدخل مستقل", "code": "independent_entrance", "data_type": "Check", "category": "services"},
	# Other
	{"attribute_name": "الاتجاه", "code": "orientation", "data_type": "Select", "category": "other", "options": "north\nsouth\neast\nwest\nnortheast\nnorthwest\nsoutheast\nsouthwest"},
	{"attribute_name": "حالة التشطيب", "code": "finishing_status", "data_type": "Select", "category": "other", "options": "unfinished\nstandard\nluxury\nfully_finished"},
	{"attribute_name": "سنة البناء/الترميم", "code": "construction_or_renovation_year", "data_type": "Integer", "category": "other"},
]


def ensure_system_unit_attributes() -> None:
	"""Seed all system unit attributes. Idempotent."""
	for sa in SYSTEM_UNIT_ATTRIBUTES:
		existing = frappe.db.get_value(
			"Unit Attribute",
			{"code": sa["code"], "is_system": 1},
			["name", "attribute_name", "code", "is_system", "is_active", "data_type", "capability_code"],
			as_dict=True,
		)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Attribute",
				{"attribute_name": sa["attribute_name"], "is_system": 1},
				["name", "attribute_name", "code", "is_system", "is_active", "data_type", "capability_code"],
				as_dict=True,
			)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Attribute",
				{"code": sa["code"]},
				["name", "attribute_name", "code", "is_system", "is_active", "data_type", "capability_code"],
				as_dict=True,
			)

		if not existing:
			existing = frappe.db.get_value(
				"Unit Attribute",
				{"attribute_name": sa["attribute_name"]},
				["name", "attribute_name", "code", "is_system", "is_active", "data_type", "capability_code"],
				as_dict=True,
			)

		if not existing:
			frappe.get_doc({
				"doctype": "Unit Attribute",
				"attribute_name": sa["attribute_name"],
				"code": sa["code"],
				"data_type": sa["data_type"],
				"options": sa.get("options"),
				"category": sa.get("category"),
				"is_system": 1,
				"rental_account": None,
				"is_active": 1,
				"display_order": _system_attr_order(sa["code"]),
				"capability_code": sa.get("capability_code"),
			}).insert(ignore_permissions=True)
		else:
			updates = {}
			if not existing.is_system:
				updates["is_system"] = 1
			# Do NOT re-enable disabled system attributes — respect user's operational changes
			# (is_active and display_order are operational settings the user can control)
			if existing.code != sa["code"]:
				updates["code"] = sa["code"]
			if existing.attribute_name != sa["attribute_name"]:
				updates["attribute_name"] = sa["attribute_name"]
			if existing.data_type != sa["data_type"]:
				updates["data_type"] = sa["data_type"]
			if sa.get("capability_code") and existing.capability_code != sa.get("capability_code"):
				updates["capability_code"] = sa["capability_code"]
			# Do NOT override display_order — user may have changed it
			if updates:
				frappe.db.set_value("Unit Attribute", existing.name, updates, update_modified=False)


def _system_attr_order(code: str) -> int:
	for i, sa in enumerate(SYSTEM_UNIT_ATTRIBUTES):
		if sa["code"] == code:
			return i + 1
	return 99


# ---------------------------------------------------------------------------
# Cleanup deprecated system attributes (idempotent, safe)
# ---------------------------------------------------------------------------

DEPRECATED_SYSTEM_ATTRIBUTE_CODES = [
	"bedrooms_count", "living_rooms_count", "kitchens_count",
	"equipped_kitchen", "heating", "flooring_type",
	"balconies_count", "terrace", "view", "parking_count",
	"storage_room", "frontage_width", "doors_count", "ceiling_height",
	"main_street_frontage", "corner_unit", "display_area",
	"truck_entrance", "loading_area", "storage_height",
	"industrial_floor", "large_gate",
	"meeting_room", "offices_count", "reception", "internal_network",
	"internal_unit_number",
]


def cleanup_deprecated_system_attributes() -> dict:
	"""Remove deprecated system attributes and their Unit Type mappings.

	Safe and idempotent — can be run multiple times.
	Only removes attributes that:
	- Have ``is_system = 1``
	- Have a code in ``DEPRECATED_SYSTEM_ATTRIBUTE_CODES``
	- Have zero Unit Attribute Values (no stored data)

	Returns a summary dict with counts of what was removed.
	"""
	removed_mappings = 0
	removed_attributes = 0
	skipped_with_values = []

	for code in DEPRECATED_SYSTEM_ATTRIBUTE_CODES:
		attr_name = frappe.db.get_value(
			"Unit Attribute",
			{"code": code, "is_system": 1},
			"name",
		)
		if not attr_name:
			continue  # already removed or never existed

		# Safety: skip if there are stored values
		value_count = frappe.db.count("Unit Attribute Value", {"attribute": attr_name})
		if value_count > 0:
			skipped_with_values.append({
				"code": code, "name": attr_name, "value_count": value_count,
			})
			continue

		# 1. Delete Unit Type Attribute mappings first
		mappings = frappe.db.get_all(
			"Unit Type Attribute",
			filters={"attribute": attr_name},
			pluck="name",
		)
		for row_name in mappings:
			frappe.delete_doc(
				"Unit Type Attribute", row_name,
				ignore_permissions=True,
			)
			removed_mappings += 1

		# 2. Delete the System Attribute itself
		#    Set flag to bypass the on_trash system-attribute protection
		attr_doc = frappe.get_doc("Unit Attribute", attr_name)
		attr_doc.flags.allow_system_delete = True
		attr_doc.delete(ignore_permissions=True)
		removed_attributes += 1

	return {
		"removed_mappings": removed_mappings,
		"removed_attributes": removed_attributes,
		"skipped_with_values": skipped_with_values,
	}


# ---------------------------------------------------------------------------
# Default Unit Type ↔ Attribute mappings
# ---------------------------------------------------------------------------

DEFAULT_TYPE_ATTRIBUTES: dict[str, list[str]] = {
	"apartment": [
		"electricity_meter", "water_meter",
		"rooms_count", "bathrooms_count",
		"furnished", "air_conditioning",
		"balcony", "elevator", "parking",
		"orientation", "finishing_status",
	],
	"shop": [
		"electricity_meter", "water_meter",
		"bathrooms_count", "air_conditioning",
		"parking", "independent_entrance",
		"finishing_status",
	],
	"office": [
		"electricity_meter", "water_meter",
		"rooms_count", "bathrooms_count",
		"air_conditioning", "elevator", "parking",
		"orientation", "finishing_status",
	],
	"warehouse": [
		"electricity_meter", "water_meter",
		"bathrooms_count", "parking",
		"independent_entrance", "finishing_status",
	],
	"room": [
		"electricity_meter", "water_meter",
		"bathrooms_count", "furnished", "air_conditioning",
	],
	"garage": [
		"electricity_meter",
		"parking", "independent_entrance",
	],
	"independent": [
		"electricity_meter", "water_meter",
		"rooms_count", "bathrooms_count",
		"furnished", "air_conditioning",
		"balcony", "garden", "private_roof",
		"elevator", "parking", "independent_entrance",
		"orientation", "finishing_status",
		"construction_or_renovation_year",
	],
	"other": [
		"electricity_meter", "water_meter",
	],
}


def seed_default_type_attributes() -> None:
	"""Seed default attribute assignments for each system unit type. Idempotent."""
	for type_code, attr_codes in DEFAULT_TYPE_ATTRIBUTES.items():
		type_name = frappe.db.get_value("Unit Type", {"code": type_code, "is_system": 1}, "name")
		if not type_name:
			continue

		type_doc = frappe.get_doc("Unit Type", type_name)
		existing_attrs = {row.attribute for row in type_doc.attributes}

		for order, attr_code in enumerate(attr_codes):
			attr_name = frappe.db.get_value(
				"Unit Attribute",
				{"code": attr_code, "is_system": 1},
				"name",
			)
			if not attr_name or attr_name in existing_attrs:
				continue

			type_doc.append("attributes", {
				"attribute": attr_name,
				"is_required": 0,
				"is_active": 1,
				"display_order": order,
			})

		if len(type_doc.attributes) > len(existing_attrs):
			type_doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Convenience: seed everything
# ---------------------------------------------------------------------------

def ensure_system_unit_setup() -> None:
	"""Run all seed functions in order. Idempotent."""
	ensure_system_unit_types()
	ensure_system_unit_attributes()
	seed_default_type_attributes()
