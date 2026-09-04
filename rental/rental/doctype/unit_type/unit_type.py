import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account


class UnitType(Document):
	def validate(self):
		self._validate_system_type_protection()
		self._validate_custom_type_account()
		self._validate_code_uniqueness()
		self._validate_attribute_uniqueness()

	def _validate_attribute_uniqueness(self):
		"""Check that no duplicate attributes exist in the child table."""
		seen = set()
		for row in self.attributes:
			if not row.attribute:
				continue
			if row.attribute in seen:
				frappe.throw(
					frappe._("Attribute is already assigned to this Unit Type"),
					frappe.ValidationError,
				)
			seen.add(row.attribute)

	def _validate_system_type_protection(self):
		"""Protect only the identity fields of System Unit Types.

		System types can have their operational settings modified (attributes,
		is_required, display_order, is_active) by Property Owners.  Only the
		core identity — ``code``, ``is_system``, and ``type_name`` — is immutable.
		"""
		if self.is_new():
			return
		old = frappe.db.get_value("Unit Type", self.name, ["code", "is_system", "type_name"], as_dict=True)
		if not old:
			return
		was_system = int(old.is_system or 0) == 1
		if was_system:
			if self.code != old.code:
				frappe.throw(
					frappe._("لا يمكن تغيير رمز نوع الوحدة النظامي"),
					frappe.PermissionError,
				)
			if int(self.is_system or 0) != int(old.is_system or 0):
				frappe.throw(
					frappe._("لا يمكن تغيير حالة النظام لنوع الوحدة"),
					frappe.PermissionError,
				)
			if self.type_name != old.type_name:
				frappe.throw(
					frappe._("لا يمكن تغيير اسم نوع الوحدة النظامي"),
					frappe.PermissionError,
				)

	def _validate_custom_type_account(self):
		if not self.is_system:
			account = get_current_rental_account()
			if account is None:
				if not self.rental_account:
					frappe.throw(
						frappe._("Custom Unit Types must belong to a Rental Account"),
						frappe.ValidationError,
					)
				if not frappe.db.exists("Rental Account", {"name": self.rental_account, "is_active": 1}):
					frappe.throw(
						frappe._("Custom Unit Types must belong to a Rental Account"),
						frappe.ValidationError,
					)
				return
			if not self.rental_account:
				self.rental_account = account
			if self.rental_account != account:
				frappe.throw(
					frappe._("You can only create Unit Types for your own Rental Account"),
					frappe.PermissionError,
				)

	def _validate_code_uniqueness(self):
		if not self.code:
			return
		filters = {"code": self.code}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		existing = frappe.db.exists("Unit Type", filters)
		if existing:
			frappe.throw(
				frappe._("Unit Type code '{0}' is already in use").format(self.code),
				frappe.ValidationError,
			)

	def on_trash(self):
		if self.is_system:
			account = get_current_rental_account()
			if account is not None:
				frappe.throw(
					frappe._("System Unit Types cannot be deleted by Property Owners"),
					frappe.PermissionError,
				)
		# Check if any units reference this type
		units = frappe.db.count("Rental Unit", {"unit_type": self.name})
		if units > 0:
			frappe.throw(
				frappe._("Cannot delete Unit Type '{0}' because {1} unit(s) are using it").format(
					self.type_name, units
				),
				frappe.ValidationError,
			)
