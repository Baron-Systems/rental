"""Migrate rooms_count and bathrooms_count from native fields to Unit Attribute Values.

Creates Unit Attribute Value records for each unit that has non-null
rooms_count or bathrooms_count. The native fields are NOT removed
(kept for backward compatibility).

Idempotent: checks if a value already exists before creating.

For units with orphaned rental_account references (account deleted but unit remains),
we bypass link validation via flags.ignore_links, preserving the unit's
rental_account value for referential consistency.
"""

import frappe


def execute():
	from rental.rental.services.unit_type_service import ensure_system_unit_attributes
	ensure_system_unit_attributes()

	# Get system attribute names
	rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
	bathrooms_attr = frappe.db.get_value("Unit Attribute", {"code": "bathrooms_count", "is_system": 1}, "name")

	if not rooms_attr or not bathrooms_attr:
		frappe.log_error(
			"v1_migrate_rooms_bathrooms: System attributes not found",
			"Unit Attribute Migration",
		)
		return

	units = frappe.get_all(
		"Rental Unit",
		fields=["name", "rental_account", "rooms_count", "bathrooms_count"],
	)

	migrated = 0
	orphaned = 0
	for unit in units:
		account = unit.rental_account
		if not account:
			frappe.log_error(
				f"v1_migrate_rooms_bathrooms: Unit {unit.name} has NULL rental_account, skipping",
				"Unit Attribute Migration",
			)
			continue

		account_exists = frappe.db.exists("Rental Account", account)

		# Migrate rooms_count (only if non-null)
		if unit.rooms_count is not None:
			existing = frappe.db.exists("Unit Attribute Value", {
				"unit": unit.name,
				"attribute": rooms_attr,
			})
			if not existing:
				_insert_value(account, unit.name, rooms_attr, "value_integer", unit.rooms_count, account_exists)
				if not account_exists:
					orphaned += 1
				migrated += 1

		# Migrate bathrooms_count (only if non-null)
		if unit.bathrooms_count is not None:
			existing = frappe.db.exists("Unit Attribute Value", {
				"unit": unit.name,
				"attribute": bathrooms_attr,
			})
			if not existing:
				_insert_value(account, unit.name, bathrooms_attr, "value_integer", unit.bathrooms_count, account_exists)
				if not account_exists:
					orphaned += 1
				migrated += 1

	frappe.db.commit()
	print(f"v1_migrate_rooms_bathrooms: migrated {migrated} values ({orphaned} via orphaned-account bypass)")


def _insert_value(rental_account, unit, attribute, value_field, value, account_exists):
	"""Insert a Unit Attribute Value, bypassing link validation for orphaned accounts."""
	doc = frappe.get_doc({
		"doctype": "Unit Attribute Value",
		"rental_account": rental_account,
		"unit": unit,
		"attribute": attribute,
		value_field: value,
	})
	if not account_exists:
		doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
