import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account


class RentalDueType(Document):
	def validate(self):
		self._validate_system_type_protection()
		self._validate_custom_type_account()

	def _validate_system_type_protection(self):
		if self.is_system:
			account = get_current_rental_account()
			if account is not None:
				frappe.throw(
					frappe._("أنواع الالتزامات النظامية للقراءة فقط ولا يمكن تعديلها من قبل ملاك العقارات"),
					frappe.PermissionError,
				)

	def _validate_custom_type_account(self):
		if not self.is_system:
			account = get_current_rental_account()
			if account is None:
				# System Manager: allow if rental_account is already set
				# (the API layer resolves the target account for System Manager)
				if not self.rental_account:
					frappe.throw(
						frappe._("أنواع الالتزامات المخصصة يجب أن تنتمي إلى حساب إيجار"),
						frappe.ValidationError,
					)
				# Validate the assigned account exists and is active
				if not frappe.db.exists("Rental Account", {"name": self.rental_account, "is_active": 1}):
					frappe.throw(
						frappe._("أنواع الالتزامات المخصصة يجب أن تنتمي إلى حساب إيجار"),
						frappe.ValidationError,
					)
				return
			if not self.rental_account:
				self.rental_account = account
			if self.rental_account != account:
				frappe.throw(
					frappe._("يمكنك إنشاء أنواع الالتزامات فقط لحساب الإيجار الخاص بك"),
					frappe.PermissionError,
				)

	def on_trash(self):
		if self.flags.get("cascade_delete_from_account"):
			return  # Skip protection for cascade delete
		if self.is_system:
			account = get_current_rental_account()
			if account is not None:
				frappe.throw(
					frappe._("لا يمكن حذف أنواع الالتزامات النظامية من قبل ملاك العقارات"),
					frappe.PermissionError,
				)
