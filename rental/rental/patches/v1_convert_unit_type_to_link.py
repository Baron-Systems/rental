"""Convert Rental Unit.unit_type from Select string values to Unit Type Link names.

This patch runs post_model_sync (after the DocType schema has been updated
to make unit_type a Link field). Frappe preserves column data during
fieldtype changes, so the column still contains the old string values
(e.g., 'apartment'). This patch maps each string to the corresponding
Unit Type doc name (hash).

Mapping rules:
- Exact match on system type code (case-insensitive): use that system type
- Legacy capitalized variants (Office→office, Storage→warehouse, Other→other): map
- Unknown/empty: set to 'other' system type, log warning
"""

import frappe


# Legacy capitalized value → system type code mapping
LEGACY_MAPPING = {
	"Apartment": "apartment",
	"Shop": "shop",
	"Office": "office",
	"Warehouse": "warehouse",
	"Storage": "warehouse",
	"Room": "room",
	"Garage": "garage",
	"Other": "other",
	"Villa": "other",
	"Studio": "other",
	"Building": "other",
}


def execute():
	# Ensure system types exist first
	from rental.rental.services.unit_type_service import ensure_system_unit_types
	ensure_system_unit_types()

	# Get all system type codes → names mapping
	system_types = frappe.get_all(
		"Unit Type",
		filters={"is_system": 1},
		fields=["name", "code"],
	)
	code_to_name = {t.code: t.name for t in system_types}
	code_to_name_lower = {t.code.lower(): t.name for t in system_types}

	if not code_to_name:
		frappe.log_error(
			"v1_convert_unit_type_to_link: No system unit types found",
			"Unit Type Migration",
		)
		return

	other_name = code_to_name.get("other")

	# Read all units with their current unit_type value
	units = frappe.get_all(
		"Rental Unit",
		fields=["name", "unit_type"],
	)

	migrated = 0
	warnings = 0

	for unit in units:
		current_value = unit.unit_type
		if not current_value:
			# Empty/NULL → set to 'other'
			if other_name:
				frappe.db.set_value("Rental Unit", unit.name, "unit_type", other_name, update_modified=False)
				warnings += 1
			continue

		# Check if already a valid Link (hash name)
		if current_value in code_to_name.values():
			migrated += 1
			continue

		# Try exact code match (case-insensitive)
		target_name = code_to_name_lower.get(current_value.lower())

		# Try legacy mapping
		if not target_name:
			target_name = code_to_name.get(LEGACY_MAPPING.get(current_value, ""))

		# Fallback to 'other'
		if not target_name:
			target_name = other_name
			warnings += 1
			frappe.log_error(
				f"v1_convert_unit_type_to_link: Unknown unit_type '{current_value}' "
				f"on unit {unit.name} → mapped to 'other'",
				"Unit Type Migration",
			)

		if target_name:
			frappe.db.set_value("Rental Unit", unit.name, "unit_type", target_name, update_modified=False)
			migrated += 1

	frappe.db.commit()
	print(f"v1_convert_unit_type_to_link: migrated {migrated} units, {warnings} warnings")
