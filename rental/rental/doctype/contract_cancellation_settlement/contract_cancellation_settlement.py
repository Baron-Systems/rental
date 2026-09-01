import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.archive_service import ensure_contract_not_archived


class ContractCancellationSettlement(Document):
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

		# Archive protection — blocks creating/editing settlements for
		# archived contracts. (A settlement is created at cancellation time,
		# before archiving; once archived it must be immutable.)
		ensure_contract_not_archived(self.contract, action="تعديل تسوية إلغاء العقد")
