"""Set transaction_type='receipt' on all existing Rental Receipt records.

Runs during ``bench migrate`` on existing sites. Idempotent — safe to run
multiple times. Only updates records where transaction_type is NULL or
empty string, setting them to 'receipt' (the default for normal receipts).

This ensures backward compatibility: all existing receipts are treated as
transaction_type='receipt' after the schema change that introduced the
transaction_type field.

No commit is issued inside this patch — Frappe manages the migration
transaction.
"""

import frappe


def execute():
	count = frappe.db.count("Rental Receipt", {
		"transaction_type": ["in", [None, ""]],
	})
	if count:
		frappe.db.set_value(
			"Rental Receipt",
			{"transaction_type": ["in", [None, ""]]},
			"transaction_type",
			"receipt",
			update_modified=False,
		)
		print(f"v1_set_transaction_type_on_receipts: updated {count} records to 'receipt'")
