import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account


class UnitAttribute(Document):
	def validate(self):
		self._validate_system_attribute_protection()
		self._validate_custom_attribute_account()
		self._validate_capability_code_protection()
		self._validate_code_uniqueness()

	def _validate_system_attribute_protection(self):
		"""Protect only the identity fields of System Unit Attributes.

		System attributes can have their operational settings modified
		(is_active, display_order, Unit Type assignments) by Property Owners.
		Only the core identity — ``code``, ``is_system``, ``capability_code``,
		and ``attribute_name`` — is immutable.
		"""
		if self.is_new():
			return
		old = frappe.db.get_value(
			"Unit Attribute", self.name,
			["code", "is_system", "capability_code", "attribute_name", "data_type"],
			as_dict=True,
		)
		if not old:
			return
		was_system = int(old.is_system or 0) == 1
		if was_system:
			if self.code != old.code:
				frappe.throw(
					frappe._("لا يمكن تغيير رمز خاصية الوحدة النظامية"),
					frappe.PermissionError,
				)
			if int(self.is_system or 0) != int(old.is_system or 0):
				frappe.throw(
					frappe._("لا يمكن تغيير حالة النظام لخاصية الوحدة"),
					frappe.PermissionError,
				)
			if (self.capability_code or "") != (old.capability_code or ""):
				frappe.throw(
					frappe._("لا يمكن تغيير رمز القدرة لخاصية الوحدة النظامية"),
					frappe.PermissionError,
				)
			if self.attribute_name != old.attribute_name:
				frappe.throw(
					frappe._("لا يمكن تغيير اسم خاصية الوحدة النظامية"),
					frappe.PermissionError,
				)
			if self.data_type != old.data_type:
				frappe.throw(
					frappe._("لا يمكن تغيير نوع البيانات لخاصية الوحدة النظامية"),
					frappe.PermissionError,
				)

	def _validate_custom_attribute_account(self):
		if not self.is_system:
			account = get_current_rental_account()
			if account is None:
				if not self.rental_account:
					frappe.throw(
						frappe._("خصائص الوحدات المخصصة يجب أن تنتمي إلى حساب إيجار"),
						frappe.ValidationError,
					)
				if not frappe.db.exists("Rental Account", {"name": self.rental_account, "is_active": 1}):
					frappe.throw(
						frappe._("خصائص الوحدات المخصصة يجب أن تنتمي إلى حساب إيجار"),
						frappe.ValidationError,
					)
				return
			if not self.rental_account:
				self.rental_account = account
			if self.rental_account != account:
				frappe.throw(
					frappe._("يمكنك إنشاء خصائص الوحدات فقط لحساب الإيجار الخاص بك"),
					frappe.PermissionError,
				)

	def _validate_capability_code_protection(self):
		"""Custom (non-system) attributes cannot set capability_code."""
		if not self.is_system and self.capability_code:
			frappe.throw(
				frappe._("يمكن تعيين رموز القدرة فقط على الخصائص النظامية"),
				frappe.ValidationError,
			)

	def _validate_code_uniqueness(self):
		if not self.code:
			return
		filters = {"code": self.code}
		if not self.is_new():
			filters["name"] = ["!=", self.name]
		existing = frappe.db.exists("Unit Attribute", filters)
		if existing:
			frappe.throw(
				frappe._("رمز خاصية الوحدة '{0}' مستخدم مسبقًا").format(self.code),
				frappe.ValidationError,
			)

	def on_trash(self):
		if self.flags.get("cascade_delete_from_account"):
			return  # Skip protection for cascade delete
		if self.is_system and not self.flags.allow_system_delete:
			frappe.throw(
				frappe._("لا يمكن حذف خصائص الوحدات النظامية"),
				frappe.PermissionError,
			)
		# Check if any unit attribute values reference this attribute
		values = frappe.db.count("Unit Attribute Value", {"attribute": self.name})
		if values > 0:
			frappe.throw(
				frappe._("لا يمكن حذف خاصية الوحدة '{0}' لوجود {1} قيمة/قيم").format(
					self.attribute_name, values
				),
				frappe.ValidationError,
			)
		# Check if any unit type assignments reference this attribute
		assignments = frappe.db.count("Unit Type Attribute", {"attribute": self.name})
		if assignments > 0:
			frappe.throw(
				frappe._("لا يمكن حذف خاصية الوحدة '{0}' لوجود {1} تعيين/تعيينات نوع").format(
					self.attribute_name, assignments
				),
				frappe.ValidationError,
			)
