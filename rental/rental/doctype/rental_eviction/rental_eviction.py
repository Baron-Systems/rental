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
		"""On submit: set contract status to evicted, cancel future dues, recalculate unit.

		Source: evictions/route.ts:57-90 — the eviction route cancels future
		dues with transactionDate > evictionDate (strict greater than), NOT >=.
		This is different from cancelFutureDues which uses >=.
		"""
		from rental.rental.utils.date_utils import to_calendar_day

		# Set contract status to evicted
		frappe.db.set_value("Lease Contract", self.contract, "status", "evicted", update_modified=False)

		# Cancel future auto_contract dues with transactionDate > evictionDate
		# Source: evictions/route.ts:73-85 — uses gt (strict), not gte
		eviction_date = to_calendar_day(self.eviction_date)
		future_dues = frappe.get_all(
			"Rental Due",
			filters={
				"contract": self.contract,
				"source_type": "auto_contract",
				"docstatus": 1,
				"transaction_date": [">", eviction_date],
			},
			fields=["name"],
		)
		for d in future_dues:
			due = frappe.get_doc("Rental Due", d.name)
			due.cancellation_reason = frappe._("إخلاء الوحدة")
			due.cancel()

		# Recalculate unit status
		from rental.rental.services.contract_validation import recalculate_unit_status
		recalculate_unit_status(self.unit)
