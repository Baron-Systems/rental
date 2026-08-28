import frappe
from frappe.model.document import Document


class RentalAccount(Document):
	def validate(self):
		self._validate_unique_owner_user()

	def _validate_unique_owner_user(self):
		existing = frappe.db.get_value(
			"Rental Account",
			{"owner_user": self.owner_user, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				frappe._("User {0} is already linked to Rental Account {1}").format(
					self.owner_user, existing
				),
				frappe.ValidationError,
			)
