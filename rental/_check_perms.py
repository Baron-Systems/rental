import frappe
import json


def check():
	perms = frappe.get_all(
		"DocPerm",
		filters={"parent": "Rental Receipt"},
		fields=["role", "read", "write", "create", "submit", "cancel", "delete"],
		order_by="role",
	)
	print(json.dumps(perms, indent=2, default=str))
