import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.tenant_service import can_delete_tenant


class RentalTenant(Document):
	def before_insert(self):
		"""Set rental_account and is_active defaults before insert.

		Source: TEN-ARCH-001, TEN-BE-006.
		"""
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account
		if not self.is_active:
			self.is_active = 1

	def validate(self):
		"""Validate field constraints and immutability.

		Source: TEN-BE-001, TEN-BE-002, TEN-BE-003.
		"""
		# Require rental_account unless System Manager
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Enforce full_name length 1-100 (TEN-BE-001)
		if self.full_name:
			if len(self.full_name) > 100:
				frappe.throw(frappe._("الاسم الكامل لا يمكن أن يتجاوز 100 حرف."))
		else:
			frappe.throw(frappe._("الاسم الكامل مطلوب."))

		# Enforce national_id max 50 (TEN-BE-002)
		if self.national_id and len(self.national_id) > 50:
			frappe.throw(frappe._("رقم الهوية لا يمكن أن يتجاوز 50 حرف."))

		# Enforce phone max 20
		if self.phone and len(self.phone) > 20:
			frappe.throw(frappe._("رقم الهاتف لا يمكن أن يتجاوز 20 حرف."))

		# Enforce guarantor_phone max 20
		if self.guarantor_phone and len(self.guarantor_phone) > 20:
			frappe.throw(frappe._("هاتف الكفيل لا يمكن أن يتجاوز 20 حرف."))

		# Enforce workplace max 100
		if self.workplace and len(self.workplace) > 100:
			frappe.throw(frappe._("جهة العمل لا يمكن أن تتجاوز 100 حرف."))

		# Enforce guarantor_name max 100
		if self.guarantor_name and len(self.guarantor_name) > 100:
			frappe.throw(frappe._("اسم الكفيل لا يمكن أن يتجاوز 100 حرف."))

		# Enforce address max 255
		if self.address and len(self.address) > 255:
			frappe.throw(frappe._("العنوان لا يمكن أن يتجاوز 255 حرف."))

		# Enforce email format
		if self.email:
			import re
			if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', self.email):
				frappe.throw(frappe._("يرجى إدخال بريد إلكتروني صحيح."))

		# Immutability after creation (TEN-BE-003)
		if not self.is_new():
			original = frappe.db.get_value(
				"Rental Tenant", self.name,
				["full_name", "national_id", "rental_account", "is_active"],
				as_dict=True,
			)
			if original:
				if self.full_name != original.full_name:
					frappe.throw(frappe._("لا يمكن تغيير الاسم الكامل بعد الإنشاء."))
				if self.national_id != original.national_id:
					frappe.throw(frappe._("لا يمكن تغيير رقم الهوية بعد الإنشاء."))
				if self.rental_account != original.rental_account:
					frappe.throw(frappe._("لا يمكن تغيير الحساب بعد الإنشاء."))
				if self.is_active != original.is_active:
					frappe.throw(frappe._("لا يمكن تغيير حالة النشاط."))

	def on_trash(self):
		"""Block deletion if tenant has any contracts, dues, receipts, or evictions.

		Source: TEN-BE-004, TEN-BE-005.
		"""
		can_delete, error_message = can_delete_tenant(self.name)
		if not can_delete:
			frappe.throw(frappe._(error_message), title=frappe._("تعذر الحذف"))
