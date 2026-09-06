import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.archive_service import ensure_contract_not_archived, get_archive_readiness


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

		# transaction_type defaults to 'receipt' for backward compatibility
		if not self.transaction_type:
			self.transaction_type = "receipt"

		# Amount must be positive for both receipt and refund
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
			frappe.throw(frappe._("لا يمكن إنشاء سند على عقد مسودة"))

		# Tenant must match contract (source: route.ts:174-176)
		if contract.tenant != self.tenant:
			frappe.throw(frappe._("العقد المختار لا ينتمي لهذا المستأجر"))

		# Derive building/unit from contract (source: route.ts:181-184)
		self.building = contract.building
		self.unit = contract.unit

		# Archive protection — blocks create/edit on receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="إنشاء أو تعديل سند")

		# Refund-specific validation at draft stage
		if self.transaction_type == "refund":
			self._validate_refund()

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

	def _validate_refund(self):
		"""Validate refund-specific business rules at draft stage.

		Checks:
		  1. Contract is operationally closed (reuses get_archive_readiness).
		  2. Contract balance < 0 (tenant has a credit balance).
		  3. amount <= abs(current_contract_balance).
		"""
		readiness = get_archive_readiness(self.contract)
		if not readiness["operationally_closed"]:
			frappe.throw(frappe._(
				"لا يمكن إنشاء سند رد على عقد غير مغلق تشغيليًا"
			))

		balance = readiness["balance"]
		if balance >= -0.005:
			frappe.throw(frappe._(
				"لا يمكن إنشاء سند رد بدون رصيد دائن (رصيد العقد يجب أن يكون سالبًا)"
			))

		amount = float(self.amount)
		abs_balance = abs(balance)
		if round(amount, 2) > round(abs_balance, 2):
			frappe.throw(frappe._(
				"مبلغ الرد ({0}) يتجاوز الرصيد الدائن للمستأجر ({1})"
			).format(amount, abs_balance))

	def on_submit(self):
		"""On approval: generate unique receipt_number (source: approve/route.ts:69-84)."""
		# Archive protection — blocks approving receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="اعتماد سند")

		# Refund revalidation at approval time — the balance may have changed
		# since the draft was created. By the time on_submit runs, docstatus=1
		# is already written to the DB by db_update(), so get_contract_balance
		# DOES include this refund in totalRefunds. Therefore bal["balance"]
		# is already the post-refund balance — we must NOT add self.amount again.
		# The balance after refund must still be <= 0
		# (refund must not convert credit to debit).
		if self.transaction_type == "refund":
			from rental.rental.services.balance_service import get_contract_balance
			bal = get_contract_balance(self.contract)
			if bal["balance"] > 0.005:
				frappe.throw(frappe._(
					"لا يمكن اعتماد سند الرد: الرصيد بعد الرد أصبح مدينًا ({0}). "
					"يجب ألا يحول الرد الرصيد من دائن إلى مدين."
				).format(round(bal["balance"], 2)))

		if not self.receipt_number:
			from rental.rental.doctype.rental_settings.rental_settings import generate_receipt_number
			self.receipt_number = generate_receipt_number(self.rental_account)
			self.db_set("receipt_number", self.receipt_number)

	def on_cancel(self):
		"""On cancellation: record metadata (source: cancel/route.ts:23-30)."""
		# Archive protection — blocks cancelling receipts of archived contracts.
		ensure_contract_not_archived(self.contract, action="إلغاء سند")

		if not self.cancellation_reason:
			frappe.throw(frappe._("سبب الإلغاء مطلوب"))
		self.cancelled_by = frappe.session.user
		self.cancelled_at = frappe.utils.now()
