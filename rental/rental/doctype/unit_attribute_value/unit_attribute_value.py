import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account


class UnitAttributeValue(Document):
	def validate(self):
		self._validate_uniqueness()
		self._validate_data_type_consistency()
		self._validate_custom_value_account()
		self._validate_capability_removal_protection()

	def _validate_uniqueness(self):
		if not self.unit or not self.attribute:
			return
		filters = {"unit": self.unit, "attribute": self.attribute}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		existing = frappe.db.exists("Unit Attribute Value", filters)
		if existing:
			frappe.throw(
				frappe._("A value for this attribute already exists for this unit"),
				frappe.ValidationError,
			)

	def _validate_data_type_consistency(self):
		attr = frappe.db.get_value(
			"Unit Attribute", self.attribute,
			["data_type", "capability_code"], as_dict=True,
		)
		if not attr:
			frappe.throw(
				frappe._("Attribute does not exist"),
				frappe.ValidationError,
			)

		# Ensure only the correct value field is populated
		data_type = attr.data_type
		value_fields = {
			"Text": "value_text",
			"Integer": "value_integer",
			"Decimal": "value_decimal",
			"Check": "value_check",
			"Select": "value_text",
			"Date": "value_date",
		}
		correct_field = value_fields.get(data_type)
		if not correct_field:
			return

		# Clear non-matching value fields
		# Note: Text and Select both use value_text, so we must check
		# against the correct_field, not just the data_type
		for dt, field in value_fields.items():
			if field == correct_field:
				continue  # don't clear the field that belongs to this data_type
			if field == "value_check":
				continue  # check field handled separately
			if self.get(field):
				self.set(field, None)

	def _validate_custom_value_account(self):
		account = get_current_rental_account()
		if account is None:
			if not self.rental_account:
				frappe.throw(
					frappe._("Unit Attribute Values must belong to a Rental Account"),
					frappe.ValidationError,
				)
			return
		if not self.rental_account:
			self.rental_account = account
		if self.rental_account != account:
			frappe.throw(
				frappe._("You can only create Unit Attribute Values for your own Rental Account"),
				frappe.PermissionError,
			)

	def _validate_capability_removal_protection(self):
		"""Block removing a meter capability if a blocking metered contract exists."""
		attr = frappe.db.get_value(
			"Unit Attribute", self.attribute,
			["data_type", "capability_code", "code"], as_dict=True,
		)
		if not attr or not attr.capability_code or attr.data_type != "Check":
			return

		# Only block when setting value_check from 1 to 0
		if self.value_check:
			return  # enabling is always allowed

		# Check if this is a transition from 1 to 0
		if self.is_new():
			return  # new record with 0 is fine

		old_value = frappe.db.get_value("Unit Attribute Value", self.name, "value_check")
		if not old_value:
			return  # was already 0

		# Capability is being removed — check for blocking contracts
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract

		capability_to_due_type = {
			"electricity_meter": "electricity",
			"water_meter": "water",
		}
		due_type_code = capability_to_due_type.get(attr.capability_code)
		if not due_type_code:
			return

		if has_blocking_metered_contract(self.unit, due_type_code):
			if due_type_code == "electricity":
				frappe.throw(
					frappe._("لا يمكن إزالة عداد الكهرباء لوجود عقد فعّال أو مستقبلي يستخدم الاحتساب حسب القراءة."),
					frappe.ValidationError,
				)
			elif due_type_code == "water":
				frappe.throw(
					frappe._("لا يمكن إزالة عداد المياه لوجود عقد فعّال أو مستقبلي يستخدم الاحتساب حسب القراءة."),
					frappe.ValidationError,
				)
