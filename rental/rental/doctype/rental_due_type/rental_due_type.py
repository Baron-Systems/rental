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
					frappe._("System Due Types are read-only and cannot be modified by Property Owners"),
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
						frappe._("Custom Due Types must belong to a Rental Account"),
						frappe.ValidationError,
					)
				# Validate the assigned account exists and is active
				if not frappe.db.exists("Rental Account", {"name": self.rental_account, "is_active": 1}):
					frappe.throw(
						frappe._("Custom Due Types must belong to a Rental Account"),
						frappe.ValidationError,
					)
				return
			if not self.rental_account:
				self.rental_account = account
			if self.rental_account != account:
				frappe.throw(
					frappe._("You can only create Due Types for your own Rental Account"),
					frappe.PermissionError,
				)

	def on_trash(self):
		if self.is_system:
			account = get_current_rental_account()
			if account is not None:
				frappe.throw(
					frappe._("System Due Types cannot be deleted by Property Owners"),
					frappe.PermissionError,
				)
