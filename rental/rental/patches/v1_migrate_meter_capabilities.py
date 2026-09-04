"""Migrate meter capabilities: set electricity_meter=1 and water_meter=1 for all existing units.

Per Phase 0 audit decision J.1: Set value_check=1 for ALL existing units.
This preserves current behavior (all units can use metered charges).
Users can disable per-unit later via the settings UI.

Idempotent: checks if a value already exists before creating.

For units with orphaned rental_account references (account deleted but unit remains),
we bypass link validation by inserting directly via db_insert, preserving the unit's
rental_account value for referential consistency. We do NOT delete or modify the units,
and we do NOT invent replacement accounts.
"""

import frappe


def execute():
	from rental.rental.services.unit_type_service import ensure_system_unit_attributes
	ensure_system_unit_attributes()

	# Get system capability attribute names
	elec_attr = frappe.db.get_value(
		"Unit Attribute",
		{"code": "electricity_meter", "is_system": 1},
		"name",
	)
	water_attr = frappe.db.get_value(
		"Unit Attribute",
		{"code": "water_meter", "is_system": 1},
		"name",
	)

	if not elec_attr or not water_attr:
		frappe.log_error(
			"v1_migrate_meter_capabilities: System capability attributes not found",
			"Meter Capability Migration",
		)
		return

	units = frappe.get_all("Rental Unit", fields=["name", "rental_account"])

	migrated = 0
	orphaned = 0
	for unit in units:
		account = unit.rental_account
		if not account:
			# Truly NULL rental_account — cannot assign capability
			frappe.log_error(
				f"v1_migrate_meter_capabilities: Unit {unit.name} has NULL rental_account, skipping",
				"Meter Capability Migration",
			)
			continue

		account_exists = frappe.db.exists("Rental Account", account)

		# Electricity meter capability
		existing = frappe.db.exists("Unit Attribute Value", {
			"unit": unit.name,
			"attribute": elec_attr,
		})
		if not existing:
			if account_exists:
				frappe.get_doc({
					"doctype": "Unit Attribute Value",
					"rental_account": account,
					"unit": unit.name,
					"attribute": elec_attr,
					"value_check": 1,
				}).insert(ignore_permissions=True)
			else:
				# Orphaned account — bypass link validation via direct DB insert
				_insert_uav_bypassing_links(account, unit.name, elec_attr, 1)
				orphaned += 1
			migrated += 1

		# Water meter capability
		existing = frappe.db.exists("Unit Attribute Value", {
			"unit": unit.name,
			"attribute": water_attr,
		})
		if not existing:
			if account_exists:
				frappe.get_doc({
					"doctype": "Unit Attribute Value",
					"rental_account": account,
					"unit": unit.name,
					"attribute": water_attr,
					"value_check": 1,
				}).insert(ignore_permissions=True)
			else:
				_insert_uav_bypassing_links(account, unit.name, water_attr, 1)
				orphaned += 1
			migrated += 1

	frappe.db.commit()
	print(f"v1_migrate_meter_capabilities: migrated {migrated} capability values ({orphaned} via orphaned-account bypass)")


def _insert_uav_bypassing_links(rental_account, unit, attribute, value_check):
	"""Insert a Unit Attribute Value row directly, bypassing Frappe link validation.

	Used for units with orphaned rental_account references (account was deleted
	but unit remains). The rental_account value is preserved from the unit's own
	field for referential consistency.
	"""
	import frappe.utils
	now = frappe.utils.now()

	doc = frappe.get_doc({
		"doctype": "Unit Attribute Value",
		"rental_account": rental_account,
		"unit": unit,
		"attribute": attribute,
		"value_check": value_check,
	})
	# Bypass link validation by using db_insert directly
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
