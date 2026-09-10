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
		"""Validate the attribute is a valid override OR an account-scoped addition.

		- Attribute already in the Unit Type child table → override (always allowed).
		- Attribute NOT in the child table → account-scoped addition. Allowed only
		  for System Unit Types (``is_system = 1``). Custom Unit Types must add
		  attributes via the child table (global mutation of the account-owned type).
		The attribute must exist and be visible to the account.
		"""
		if not frappe.db.exists("Unit Attribute", self.attribute):
			frappe.throw(
				frappe._("Attribute '{0}' does not exist.").format(self.attribute),
				frappe.ValidationError,
			)

		type_doc = frappe.get_doc("Unit Type", self.unit_type)
		assigned = {row.attribute for row in type_doc.attributes}
		if self.attribute in assigned:
			return  # override of an existing (global) attribute — always allowed

		# Account-scoped addition — only permitted for System Unit Types
		if not int(type_doc.is_system or 0):
			frappe.throw(
				frappe._("Attribute '{0}' is not assigned to Unit Type '{1}'. Add it to the custom Unit Type first.").format(
					self.attribute, self.unit_type
				),
				frappe.ValidationError,
			)
