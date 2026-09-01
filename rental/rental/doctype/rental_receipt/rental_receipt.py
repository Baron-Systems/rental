import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.archive_service import ensure_contract_not_archived


class RentalReceipt(Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Amount must be positive (source: route.ts:156-158)
		if not self.amount or float(self.amount) <= 0:
			frappe.throw(frappe._("المبلغ يجب أن يكون أكبر من صفر"))

		# Contract is mandatory (section 5: Rental Receipt.contract required
		# at DocType + Backend level). The DB has no receipts without a contract.
		if not self.contract:
			frappe.throw(frappe._("العقد مطلوب"))

		# Contract must exist and not be draft (source: route.ts:161-172)
		contract = frappe.db.get_value(
			"Lease Contract", self.contract,
			["status", "tenant", "building", "unit", "rental_account"],
			as_dict=True,
		)
		if not contract:
			frappe.throw(frappe._("العقد غير موجود"))
		if contract.status == "draft":
			frappe.throw(frappe._("لا يمكن إنشاء سند قبض على عقد مسودة"))

		# Tenant must match contract (source: route.ts:174-176)
		if contract.tenant != self.tenant:
			frappe.throw(frappe._("العقد المختار لا ينتمي لهذا المستأجر"))

		# Derive building/unit from contract (source: route.ts:181-184)
		self.building = contract.building
		self.unit = contract.unit

		# Archive protection — blocks create/edit on receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="إنشاء أو تعديل سند قبض")

		# Cheque validation — only reference_number required (source: route.ts:65-67, validation.ts:266-273)
		if self.payment_method == "cheque":
			if not self.reference_number or not self.reference_number.strip():
				frappe.throw(frappe._("رقم الشيك مطلوب عند اختيار طريقة الدفع شيك"))
		else:
			# Reject cheque fields for non-cheque method (source: validation.ts:274-282).
			if self.reference_number or self.cheque_date or self.bank_name:
				frappe.throw(frappe._("لا يجب إدخال بيانات شيك عند طريقة الدفع نقدًا"))
			# B12: clear cheque fields for ANY non-cheque method (source: route.ts:76-79).
			self.reference_number = None
			self.cheque_date = None
			self.bank_name = None

	def on_submit(self):
		"""On approval: generate unique receipt_number (source: approve/route.ts:69-84)."""
		# Archive protection — blocks approving receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="اعتماد سند قبض")

		if not self.receipt_number:
			from rental.rental.doctype.rental_settings.rental_settings import generate_receipt_number
			self.receipt_number = generate_receipt_number(self.rental_account)
			self.db_set("receipt_number", self.receipt_number)

	def on_cancel(self):
		"""On cancellation: record metadata (source: cancel/route.ts:23-30)."""
		# Archive protection — blocks cancelling receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="إلغاء سند قبض")

		if not self.cancellation_reason:
			frappe.throw(frappe._("سبب الإلغاء مطلوب"))
		self.cancelled_by = frappe.session.user
		self.cancelled_at = frappe.utils.now()
