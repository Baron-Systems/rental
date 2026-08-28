import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.utils.date_utils import to_calendar_day
from rental.rental.services.contract_validation import can_evict_contract


class RentalEviction(Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("حساب الإيجار مطلوب"))
		assert_account_access(self)

		# Contract must be evictable
		contract = frappe.get_doc("Lease Contract", self.contract)
		if not can_evict_contract(contract):
			frappe.throw(frappe._("لا يمكن إخلاء هذا العقد"))

		# A contract can be evicted only once
		existing = frappe.db.exists("Rental Eviction", {"contract": self.contract})
		if existing and existing != self.name:
			frappe.throw(frappe._("يوجد إخلاء مسجل لهذا العقد مسبقاً"))

		# Derive tenant and unit from contract
		self.tenant = contract.tenant
		self.unit = contract.unit

		# Eviction date defaults to today
		if not self.eviction_date:
			self.eviction_date = frappe.utils.today()

	def on_submit(self):
		"""On submit: set contract status to evicted, cancel future dues, recalculate unit."""
		# Set contract status to evicted
		frappe.db.set_value("Lease Contract", self.contract, "status", "evicted", update_modified=False)

		# Cancel future auto_contract dues
		from rental.rental.services.due_generation_service import cancel_future_dues
		cancel_future_dues(
			self.contract,
			self.eviction_date,
			frappe._("إخلاء الوحدة"),
			frappe.session.user,
		)

		# Recalculate unit status
		from rental.rental.services.contract_validation import recalculate_unit_status
		recalculate_unit_status(self.unit)
