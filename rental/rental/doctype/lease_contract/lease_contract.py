import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.contract_validation import (
	validate_contract_basic_data,
	validate_contract_draft_unit,
)
from rental.rental.services.contract_charge_service import save_contract_charges


class LeaseContract(Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

		# Generate contract number on create
		if self.is_new() and not self.contract_number:
			from rental.rental.doctype.rental_settings.rental_settings import generate_contract_number
			self.contract_number = generate_contract_number(self.rental_account)

		# Default first_due_date to start_date
		if not self.first_due_date and self.start_date:
			self.first_due_date = self.start_date

		# Default commitment_timing
		if not self.commitment_timing:
			self.commitment_timing = "start"

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("حساب الإيجار مطلوب"))
		assert_account_access(self)

		# Archived contracts are immutable
		if self.is_archived and not self.flags.ignore_archive_check:
			frappe.throw(frappe._("لا يمكن تعديل عقد مؤرشف"))

		# Basic data validation
		validate_contract_basic_data(self)

		# Only draft contracts can be edited (except status changes via lifecycle)
		if not self.is_new() and self.status != "draft":
			original_status = frappe.db.get_value("Lease Contract", self.name, "status")
			if original_status != "draft":
				# Allow only lifecycle field updates (done via db_set, not save)
				frappe.throw(frappe._("لا يمكن تعديل العقد بعد الاعتماد"))

		# Draft unit validation
		if self.status == "draft":
			validate_contract_draft_unit(self)

		# Validate charges if present
		if self.contract_charges:
			account = self.rental_account
			charge_inputs = []
			for row in self.contract_charges:
				if row.due_type:
					charge_inputs.append({
						"due_type": row.due_type,
						"responsibility": row.responsibility,
						"calculation_method": row.calculation_method,
						"payment_by": row.payment_by,
						"amount": row.amount,
						"frequency": row.frequency,
						"first_due_date": row.first_due_date,
						"commitment_timing": row.commitment_timing,
						"last_period_handling": row.last_period_handling,
						"last_period_adjustment_amount": row.last_period_adjustment_amount,
						"opening_meter_reading": row.opening_meter_reading,
					})
			if charge_inputs:
				save_contract_charges(self, charge_inputs, account)

	# is_historical is set only during approval (in approve_contract), not on every validate.

	def on_trash(self):
		"""Only draft contracts can be deleted."""
		if self.status != "draft":
			frappe.throw(frappe._("لا يمكن حذف العقد بعد الاعتماد"))
		if self.is_archived:
			frappe.throw(frappe._("لا يمكن حذف عقد مؤرشف"))
