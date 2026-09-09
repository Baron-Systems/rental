import frappe
from frappe.model.document import Document


class UserUnitPreference(Document):
	def validate(self):
		self._validate_composite_uniqueness()
		self._validate_attribute_belongs_to_unit_type()

	def _validate_composite_uniqueness(self):
		"""Ensure only one preference per (rental_account, user, unit_type, attribute)."""
		filters = {
			"rental_account": self.rental_account,
			"user": self.user,
			"unit_type": self.unit_type,
			"attribute": self.attribute,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]

		existing = frappe.db.exists("User Unit Preference", filters)
		if existing:
			frappe.throw(
				frappe._("Preference already exists for this Rental Account + User + Unit Type + Attribute combination."),
				frappe.ValidationError,
			)

	def _validate_attribute_belongs_to_unit_type(self):
		"""Block creating an override for an attribute not in the Unit Type."""
		type_doc = frappe.get_doc("Unit Type", self.unit_type)
		assigned = {row.attribute for row in type_doc.attributes}
		if self.attribute not in assigned:
			frappe.throw(
				frappe._("Attribute '{0}' is not assigned to Unit Type '{1}'. Cannot create a preference for an unassigned attribute.").format(
					self.attribute, self.unit_type
				),
				frappe.ValidationError,
			)
