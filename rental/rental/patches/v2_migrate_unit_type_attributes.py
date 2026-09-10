"""Migrate User Unit Preference rows to Account Unit Type Attribute.

This patch is idempotent and safe to re-run. It:

1. Reads all User Unit Preference rows ordered by ``modified DESC`` so that
   when multiple users in the same Rental Account configured the same
   (unit_type, attribute), the most recently modified row wins.
2. Skips rows where ``is_active = 0`` (those represented "hidden" attributes
   in the old override model and have no equivalent in the new presence/
   absence model).
3. Creates an Account Unit Type Attribute row for each surviving
   (rental_account, unit_type, attribute) combination, unless one already
   exists.
4. Does NOT delete the User Unit Preference DocType or rows — that is a
   separate manual step performed after verifying the migration and tests.
5. Does NOT delete Custom Unit Types or Custom Unit Attributes — those are
   left for manual review.

Run:
    bench --site <site> execute rental.rental.patches.v2_migrate_unit_type_attributes.execute
"""

from __future__ import annotations

import frappe


def execute():
	"""Migrate User Unit Preference → Account Unit Type Attribute."""
	if not frappe.db.table_exists("User Unit Preference"):
		print("User Unit Preference table no longer exists — nothing to migrate.")
		return {"migrated": 0, "skipped_inactive": 0, "skipped_duplicate": 0,
				"skipped_missing_attr": 0, "custom_types_remaining": 0,
				"custom_attrs_remaining": 0}

	if not frappe.db.table_exists("Account Unit Type Attribute"):
		print("Account Unit Type Attribute table does not exist yet — run migrate first.")
		return {"migrated": 0, "skipped_inactive": 0, "skipped_duplicate": 0,
				"skipped_missing_attr": 0, "custom_types_remaining": 0,
				"custom_attrs_remaining": 0}

	# Order by modified DESC so the most recent preference wins on conflict.
	prefs = frappe.db.sql(
		"""
		SELECT name, rental_account, user, unit_type, attribute,
			   is_required, is_active, display_order, modified
		FROM `tabUser Unit Preference`
		ORDER BY modified DESC
		""",
		as_dict=True,
	)

	migrated = 0
	skipped_inactive = 0
	skipped_duplicate = 0
	skipped_missing_attr = 0
	seen = set()  # (rental_account, unit_type, attribute)

	for p in prefs:
		# Skip inactive preferences — they represented "hidden" attributes.
		if not int(p.get("is_active") or 0):
			skipped_inactive += 1
			continue

		key = (p["rental_account"], p["unit_type"], p["attribute"])

		# First occurrence wins (most recent due to ORDER BY modified DESC).
		if key in seen:
			skipped_duplicate += 1
			continue

		# Skip if the referenced attribute no longer exists.
		if not frappe.db.exists("Unit Attribute", p["attribute"]):
			skipped_missing_attr += 1
			seen.add(key)
			continue

		# Skip if the referenced unit type no longer exists.
		if not frappe.db.exists("Unit Type", p["unit_type"]):
			skipped_missing_attr += 1
			seen.add(key)
			continue

		# Skip if an Account Unit Type Attribute row already exists.
		if frappe.db.exists("Account Unit Type Attribute", {
			"rental_account": p["rental_account"],
			"unit_type": p["unit_type"],
			"attribute": p["attribute"],
		}):
			skipped_duplicate += 1
			seen.add(key)
			continue

		# Create the new Account Unit Type Attribute row.
		frappe.flags.in_migrate = True
		try:
			frappe.get_doc({
				"doctype": "Account Unit Type Attribute",
				"rental_account": p["rental_account"],
				"unit_type": p["unit_type"],
				"attribute": p["attribute"],
				"is_required": int(p.get("is_required") or 0),
				"display_order": int(p.get("display_order") or 0),
			}).insert(ignore_permissions=True)
			migrated += 1
		finally:
			frappe.flags.in_migrate = False

		seen.add(key)

	frappe.db.commit()

	# Report Custom Unit Types / Attributes (DO NOT delete).
	custom_types = frappe.get_all("Unit Type", filters={"is_system": 0},
		fields=["name", "type_name", "code", "rental_account"])
	custom_attrs = frappe.get_all("Unit Attribute", filters={"is_system": 0},
		fields=["name", "attribute_name", "code", "rental_account"])

	print("=" * 60)
	print("Migration: User Unit Preference → Account Unit Type Attribute")
	print("=" * 60)
	print(f"  Migrated:               {migrated}")
	print(f"  Skipped (inactive):      {skipped_inactive}")
	print(f"  Skipped (duplicate):    {skipped_duplicate}")
	print(f"  Skipped (missing ref):   {skipped_missing_attr}")
	print(f"  Custom Unit Types left:  {len(custom_types)} (NOT deleted)")
	print(f"  Custom Unit Attrs left:  {len(custom_attrs)} (NOT deleted)")

	if custom_types:
		print("  Custom Unit Types to review:")
		for t in custom_types:
			unit_count = frappe.db.count("Rental Unit", {"unit_type": t["name"]})
			print(f"    - {t['type_name']} ({t['name']}) — {unit_count} units")

	if custom_attrs:
		print("  Custom Unit Attributes to review:")
		for a in custom_attrs:
			value_count = frappe.db.count("Unit Attribute Value", {"attribute": a["name"]})
			print(f"    - {a['attribute_name']} ({a['name']}) — {value_count} values")

	return {
		"migrated": migrated,
		"skipped_inactive": skipped_inactive,
		"skipped_duplicate": skipped_duplicate,
		"skipped_missing_attr": skipped_missing_attr,
		"custom_types_remaining": len(custom_types),
		"custom_attrs_remaining": len(custom_attrs),
	}
