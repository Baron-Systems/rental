"""Remove 27 deprecated system unit attributes and their Unit Type mappings.

Runs during ``bench migrate`` on existing sites. Idempotent — safe to run
multiple times. Only removes attributes that:
- Have ``is_system = 1``
- Have a code in ``DEPRECATED_SYSTEM_ATTRIBUTE_CODES``
- Have zero Unit Attribute Values (no stored data)

Does NOT touch:
- The 15 retained system attributes
- Custom (non-system) attributes
- Meter capability codes (electricity_meter, water_meter)
- Existing Unit Attribute Values
- Unit seed values

No commit is issued inside this patch — Frappe manages the migration
transaction.
"""

import frappe


def execute():
	from rental.rental.services.unit_type_service import (
		cleanup_deprecated_system_attributes,
	)

	result = cleanup_deprecated_system_attributes()

	if result["removed_attributes"] or result["removed_mappings"]:
		print(
			f"v1_cleanup_deprecated_system_attributes: "
			f"removed {result['removed_attributes']} deprecated attributes, "
			f"{result['removed_mappings']} mappings"
		)

	if result["skipped_with_values"]:
		for skipped in result["skipped_with_values"]:
			frappe.log_error(
				f"v1_cleanup_deprecated_system_attributes: Skipped '{skipped['code']}' "
				f"({skipped['name']}) — has {skipped['value_count']} Unit Attribute Values",
				"Deprecated Attribute Cleanup",
			)
