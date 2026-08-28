import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.balance_service import _db_sum


class RentalDueWaiver(Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account
		if not self.created_by:
			self.created_by = frappe.session.user

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Manual waivers can only be created against auto_contract approved dues
		if self.source_type == "manual" and self.due:
			due = frappe.db.get_value(
				"Rental Due", self.due,
				["source_type", "docstatus", "amount"],
				as_dict=True,
			)
			if not due:
				frappe.throw(frappe._("الالتزام غير موجود"))
			if due.source_type != "auto_contract":
				frappe.throw(frappe._("لا يمكن إعفاء إلا الالتزامات الناتجة من العقود"))
			if due.docstatus != 1:
				frappe.throw(frappe._("لا يمكن إعفاء إلا التزامات معتمدة"))

			# Sum of active waivers cannot exceed due amount
			if self.is_new() or self.status == "active":
				existing_waivers = _db_sum(
					"Rental Due Waiver",
					{
						"due": self.due,
						"status": "active",
						"name": ["!=", self.name or ""],
					},
					"amount",
				)
				total = float(existing_waivers) + float(self.amount or 0)
				if total > float(due.amount):
					frappe.throw(frappe._("إجمالي الإعفاءات لا يجوز أن يتجاوز مبلغ الالتزام"))

		# Amount must be positive
		if not self.amount or float(self.amount) <= 0:
			frappe.throw(frappe._("مبلغ الإعفاء يجب أن يكون أكبر من صفر"))
