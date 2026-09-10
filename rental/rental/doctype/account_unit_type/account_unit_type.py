import frappe
from frappe.model.document import Document


class AccountUnitType(Document):
	def validate(self):
		self._validate_unique()

	def _validate_unique(self):
		"""Enforce uniqueness of (rental_account, unit_type)."""
		filters = {
			"rental_account": self.rental_account,
			"unit_type": self.unit_type,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		existing = frappe.db.exists("Account Unit Type", filters)
		if existing:
			frappe.throw(
				frappe._("An Account Unit Type override already exists for this account and unit type."),
				frappe.ValidationError,
			)
