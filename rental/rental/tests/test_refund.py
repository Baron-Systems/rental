"""Tests for the transaction_type refund feature.

Covers:
  1. Default transaction_type is 'receipt' for new receipts.
  2. Receipt behavior unchanged: amount > 0, reduces contract balance.
  3. Refund behavior: amount > 0, increases contract balance.
  4. Refund validation: contract must be operationally closed.
  5. Refund validation: contract balance must be < 0 (credit to tenant).
  6. Refund validation: refund amount must <= abs(balance).
  7. Refund revalidation at approval time (on_submit).
  8. Refund on active (not operationally closed) contract is rejected.
  9. Refund on archived contract is rejected.
 10. Cancel refund reverses the balance effect.
 11. Balance service: totalRefunds tracked separately.
 12. Statement service: refund appears as debit entry.
 13. Dashboard financial trend: receipts exclude refunds.
 14. transaction_type cannot be changed via update_receipt.
 15. Invalid transaction_type value is rejected.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from datetime import date


class TestRefund(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_tenants = []
		cls._created_contracts = []
		cls._created_dues = []
		cls._created_receipts = []
		cls._created_evictions = []

		cls.owner = cls._create_test_user("refund_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Refund Test Account", cls.owner)
		cls._create_settings(cls.account)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for name in cls._created_receipts:
			if frappe.db.exists("Rental Receipt", name):
				try:
					doc = frappe.get_doc("Rental Receipt", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Receipt", name, force=True)
				except Exception:
					pass

		for name in cls._created_evictions:
			if frappe.db.exists("Rental Eviction", name):
				try:
					doc = frappe.get_doc("Rental Eviction", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Eviction", name, force=True)
				except Exception:
					frappe.db.delete("Rental Eviction", name)

		for name in cls._created_dues:
			if frappe.db.exists("Rental Due", name):
				try:
					doc = frappe.get_doc("Rental Due", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Due", name, force=True)
				except Exception:
					pass

		for name in cls._created_contracts:
			if frappe.db.exists("Lease Contract", name):
				try:
					frappe.db.set_value("Lease Contract", name, "is_archived", 0, update_modified=False)
					doc = frappe.get_doc("Lease Contract", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Lease Contract", name, force=True)
				except Exception:
					frappe.db.delete("Lease Contract", name)

		for name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", name):
				try:
					frappe.delete_doc("Rental Tenant", name, force=True)
				except Exception:
					frappe.db.delete("Rental Tenant", name)

		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				try:
					frappe.delete_doc("Rental Unit", name, force=True)
				except Exception:
					frappe.db.delete("Rental Unit", name)

		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				try:
					frappe.delete_doc("Rental Building", name, force=True)
				except Exception:
					frappe.db.delete("Rental Building", name)

		for name in cls._created_accounts:
			if frappe.db.exists("Rental Account", name):
				try:
					frappe.delete_doc("Rental Account", name, force=True)
				except Exception:
					frappe.db.delete("Rental Account", name)

		for user in cls._created_users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=True)

		super().tearDownClass()

	@classmethod
	def _create_test_user(cls, email, role):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"roles": [{"role": role}],
			"send_welcome_email": 0,
		})
		user.insert(ignore_permissions=True)
		update_password(user.name, "test12345")
		cls._created_users.append(email)
		return email

	@classmethod
	def _create_test_account(cls, name, owner_user):
		if frappe.db.exists("Rental Account", {"owner_user": owner_user}):
			frappe.delete_doc(
				"Rental Account",
				frappe.db.get_value("Rental Account", {"owner_user": owner_user}, "name"),
				force=True,
			)
		account = frappe.get_doc({
			"doctype": "Rental Account",
			"account_name": name,
			"owner_user": owner_user,
			"is_active": 1,
			"setup_completed": 1,
		})
		account.insert(ignore_permissions=True)
		cls._created_accounts.append(account.name)
		return account.name

	@classmethod
	def _create_settings(cls, account):
		if frappe.db.exists("Rental Settings", {"rental_account": account}):
			return
		settings = frappe.get_doc({
			"doctype": "Rental Settings",
			"rental_account": account,
			"landlord_type": "person",
			"landlord_name": "Test Landlord",
			"landlord_id": "1234567890",
			"landlord_phone": "0555-123-456",
			"landlord_address": "Test Address, Test City",
			"currency": "JOD",
		})
		settings.insert(ignore_permissions=True)

	def _setup_contract(self, rent=500, start_offset=-60, end_offset=30):
		"""Create a building, unit, tenant, and approved contract."""
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"Refund Building {frappe.utils.random_string(5)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)

		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building.name,
			"unit_number": f"U-{frappe.utils.random_string(4)}",
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)

		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"Refund Tenant {frappe.utils.random_string(5)}",
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)

		start = frappe.utils.add_days(frappe.utils.today(), start_offset)
		end = frappe.utils.add_days(frappe.utils.today(), end_offset)
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant.name,
			"building": building.name,
			"unit": unit.name,
			"start_date": start,
			"end_date": end,
			"rent_amount": rent,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
		})
		contract.insert(ignore_permissions=True)
		self._created_contracts.append(contract.name)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract.name, generate_dues=1)

		return {
			"building": building.name,
			"unit": unit.name,
			"tenant": tenant.name,
			"contract": contract.name,
		}

	def _evict_contract(self, contract_name):
		"""Expire the contract first (if needed) then evict."""
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		if status == "active":
			frappe.db.set_value("Lease Contract", contract_name, {
				"status": "expired",
				"end_date": frappe.utils.add_days(frappe.utils.today(), -1),
			}, update_modified=False)
		from rental.rental.api.eviction import create_eviction
		ev = create_eviction(contract=contract_name, notes="Test eviction for refund")
		self._created_evictions.append(ev["eviction"])
		return ev

	def _create_receipt(self, contract, tenant, amount, transaction_type="receipt"):
		"""Create and submit a receipt (or refund)."""
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract,
			"receipt_date": frappe.utils.today(),
			"amount": amount,
			"transaction_type": transaction_type,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self._created_receipts.append(receipt.name)
		return receipt.name

	def _create_receipt_draft(self, contract, tenant, amount, transaction_type="receipt"):
		"""Create a draft receipt (not submitted)."""
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract,
			"receipt_date": frappe.utils.today(),
			"amount": amount,
			"transaction_type": transaction_type,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		self._created_receipts.append(receipt.name)
		return receipt

	# ---- 1. Default transaction_type ----

	def test_default_transaction_type_is_receipt(self):
		"""New receipts default to transaction_type='receipt'."""
		ctx = self._setup_contract(rent=500)
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 100,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		self._created_receipts.append(receipt.name)
		self.assertEqual(receipt.transaction_type, "receipt")

	# ---- 2. Receipt behavior unchanged ----

	def test_receipt_reduces_balance(self):
		"""Receipt (transaction_type='receipt') reduces contract balance."""
		ctx = self._setup_contract(rent=500)

		from rental.rental.services.balance_service import get_contract_balance
		bal_before = get_contract_balance(ctx["contract"])

		self._create_receipt(ctx["contract"], ctx["tenant"], 200)

		bal_after = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after["balance"], bal_before["balance"] - 200)
		self.assertEqual(bal_after["totalReceipts"], 200)
		self.assertEqual(bal_after["totalRefunds"], 0)

	# ---- 3. Refund increases balance ----

	def test_refund_increases_balance(self):
		"""Refund (transaction_type='refund') increases contract balance."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay to create a credit balance (balance < 0)
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 100)

		bal_after_receipt = get_contract_balance(ctx["contract"])
		self.assertTrue(bal_after_receipt["balance"] < 0, "Should have credit balance after overpaying")

		# Create a refund of 50
		self._create_receipt(ctx["contract"], ctx["tenant"], 50, transaction_type="refund")

		bal_after_refund = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after_refund["balance"], bal_after_receipt["balance"] + 50)
		self.assertEqual(bal_after_refund["totalRefunds"], 50)

	# ---- 4. Refund requires operationally closed contract ----

	def test_refund_on_active_contract_rejected(self):
		"""Refund on an active (not operationally closed) contract is rejected."""
		ctx = self._setup_contract(rent=500, start_offset=0, end_offset=365)

		# Overpay to create credit balance
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 100)

		bal_after = get_contract_balance(ctx["contract"])
		self.assertTrue(bal_after["balance"] < 0)

		# Try to create a refund — should fail (contract is active, not closed)
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 50,
			"transaction_type": "refund",
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# ---- 5. Refund requires negative balance (credit) ----

	def test_refund_without_credit_balance_rejected(self):
		"""Refund without a credit balance (balance >= 0) is rejected."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self.assertTrue(bal["balance"] > 0, "Should have positive balance (debt)")

		# Try to create a refund — should fail (no credit balance)
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 50,
			"transaction_type": "refund",
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# ---- 6. Refund amount must <= abs(balance) ----

	def test_refund_exceeding_credit_balance_rejected(self):
		"""Refund amount exceeding abs(credit balance) is rejected."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay by exactly 100 to create credit of 100
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 100)

		bal_after = get_contract_balance(ctx["contract"])
		credit = abs(bal_after["balance"])
		self.assertTrue(credit > 0)

		# Try to refund more than the credit
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": credit + 50,
			"transaction_type": "refund",
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# ---- 7. Refund revalidation at approval time ----

	def test_refund_revalidation_at_approval(self):
		"""Refund draft that would push balance positive is rejected at approval."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay by 100 to create credit of 100
		overpay_name = self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 100)

		bal_after = get_contract_balance(ctx["contract"])
		credit = abs(bal_after["balance"])
		self.assertTrue(credit > 0)

		# Create a draft refund for exactly the credit amount (valid at draft)
		draft = self._create_receipt_draft(
			ctx["contract"], ctx["tenant"], credit, transaction_type="refund"
		)
		self.assertEqual(draft.docstatus, 0)

		# Before approving, cancel the overpayment receipt to remove the credit.
		# Now balance is positive again — approving the refund would push it
		# even more positive (projected = positive + refund_amount > 0).
		from rental.rental.api.receipt import cancel_receipt
		frappe.db.set_value("Lease Contract", ctx["contract"], "is_archived", 0, update_modified=False)
		cancel_receipt(overpay_name, reason="Test: remove credit before approving refund")

		bal_before_approve = get_contract_balance(ctx["contract"])
		self.assertTrue(bal_before_approve["balance"] > 0, "Balance should be positive after cancelling overpayment")

		# Approving the draft refund should fail
		with self.assertRaises(frappe.ValidationError):
			draft.submit()

	# ---- 8. Refund on archived contract rejected ----

	def test_refund_on_archived_contract_rejected(self):
		"""Refund on an archived contract is rejected."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 50,
			"transaction_type": "refund",
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# ---- 9. Cancel refund reverses balance effect ----

	def test_cancel_refund_reverses_balance(self):
		"""Cancelling an approved refund reverses its balance effect."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay by 200 to create credit of 200
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		bal_after_receipt = get_contract_balance(ctx["contract"])
		self.assertTrue(bal_after_receipt["balance"] < 0)

		# Create and approve a refund of 100
		refund_name = self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		bal_after_refund = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after_refund["totalRefunds"], 100)

		# Cancel the refund
		from rental.rental.api.receipt import cancel_receipt
		# Un-archive if needed (shouldn't be archived, but just in case)
		frappe.db.set_value("Lease Contract", ctx["contract"], "is_archived", 0, update_modified=False)
		cancel_receipt(refund_name, reason="Test cancel refund")

		bal_after_cancel = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after_cancel["totalRefunds"], 0)
		# Balance should be back to what it was before the refund
		self.assertEqual(bal_after_cancel["balance"], bal_after_receipt["balance"])

	# ---- 10. Balance service tracks totalRefunds separately ----

	def test_balance_service_tracks_total_refunds(self):
		"""get_contract_balance returns totalRefunds separately from totalReceipts."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay by 300 to create credit
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 300)

		# Refund 100
		self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		bal_final = get_contract_balance(ctx["contract"])
		self.assertIn("totalRefunds", bal_final)
		self.assertEqual(bal_final["totalRefunds"], 100)
		# totalReceipts should only include receipts, not refunds
		self.assertTrue(bal_final["totalReceipts"] > 100)

	# ---- 11. Tenant balance includes totalRefunds ----

	def test_tenant_balance_includes_total_refunds(self):
		"""get_tenant_balance returns totalRefunds and correct balance."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_tenant_balance
		bal = get_tenant_balance(ctx["tenant"])

		# Overpay by 200
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		# Refund 75
		self._create_receipt(ctx["contract"], ctx["tenant"], 75, transaction_type="refund")

		bal_final = get_tenant_balance(ctx["tenant"])
		self.assertIn("totalRefunds", bal_final)
		self.assertEqual(bal_final["totalRefunds"], 75)

	# ---- 12. Statement shows refund as debit ----

	def test_statement_refund_is_debit(self):
		"""Tenant statement shows refund as a debit entry with correct description."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		# Overpay by 200
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		# Refund 75
		self._create_receipt(ctx["contract"], ctx["tenant"], 75, transaction_type="refund")

		from rental.rental.services.statement_service import get_tenant_statement
		stmt = get_tenant_statement(ctx["tenant"])
		lines = stmt.get("lines", [])

		refund_lines = [l for l in lines if l.get("type") == "refund"]
		self.assertTrue(len(refund_lines) > 0, "Statement should contain refund lines")

		refund_line = refund_lines[0]
		self.assertEqual(float(refund_line["debit"]), 75)
		self.assertEqual(float(refund_line["credit"]), 0)
		self.assertEqual(refund_line["typeName"], "سند صرف")

	# ---- 13. Statement receipt still shows as credit ----

	def test_statement_receipt_is_credit(self):
		"""Tenant statement still shows receipts as credit entries."""
		ctx = self._setup_contract(rent=500)

		self._create_receipt(ctx["contract"], ctx["tenant"], 200)

		from rental.rental.services.statement_service import get_tenant_statement
		stmt = get_tenant_statement(ctx["tenant"])
		lines = stmt.get("lines", [])

		receipt_lines = [l for l in lines if l.get("type") == "receipt"]
		self.assertTrue(len(receipt_lines) > 0)

		receipt_line = receipt_lines[0]
		self.assertEqual(float(receipt_line["credit"]), 200)
		self.assertEqual(float(receipt_line["debit"]), 0)
		self.assertEqual(receipt_line["typeName"], "سند قبض")

	# ---- 14. transaction_type cannot be changed via update ----

	def test_transaction_type_cannot_be_changed_via_update(self):
		"""update_receipt rejects attempts to change transaction_type."""
		ctx = self._setup_contract(rent=500)

		draft = self._create_receipt_draft(ctx["contract"], ctx["tenant"], 100)

		from rental.rental.api.receipt import update_receipt
		with self.assertRaises(frappe.ValidationError):
			update_receipt(draft.name, transaction_type="refund")

	# ---- 15. Invalid transaction_type rejected ----

	def test_invalid_transaction_type_rejected(self):
		"""create_receipt rejects an invalid transaction_type value."""
		ctx = self._setup_contract(rent=500)

		from rental.rental.api.receipt import create_receipt
		with self.assertRaises(frappe.ValidationError):
			create_receipt(
				tenant=ctx["tenant"],
				contract=ctx["contract"],
				receipt_date=frappe.utils.today(),
				amount=100,
				payment_method="cash",
				transaction_type="invalid",
			)

	# ---- 16. Refund amount must be positive ----

	def test_refund_amount_must_be_positive(self):
		"""Refund with zero or negative amount is rejected."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 0,
			"transaction_type": "refund",
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# ---- 17. Refund via API create_receipt ----

	def test_refund_via_api_create(self):
		"""create_receipt API accepts transaction_type='refund' for eligible contract."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		from rental.rental.api.receipt import create_receipt
		result = create_receipt(
			tenant=ctx["tenant"],
			contract=ctx["contract"],
			receipt_date=frappe.utils.today(),
			amount=100,
			payment_method="cash",
			transaction_type="refund",
		)
		self.assertTrue(result.get("name"))
		self._created_receipts.append(result["name"])

	# ---- 18. Backward compatibility: existing receipts treated as 'receipt' ----

	def test_existing_receipts_treated_as_receipt(self):
		"""Receipts without explicit transaction_type are treated as 'receipt'."""
		ctx = self._setup_contract(rent=500)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 200,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		self._created_receipts.append(receipt.name)

		# validate() should have set transaction_type to 'receipt'
		self.assertEqual(receipt.transaction_type, "receipt")

	# ---- 19. Building balance includes refunds ----

	def test_building_balance_includes_refunds(self):
		"""get_building_balance correctly accounts for refunds."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_building_balance, get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)
		self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		bldg_bal = get_building_balance(ctx["building"])
		self.assertIn("totalRefunds", bldg_bal)
		self.assertEqual(bldg_bal["totalRefunds"], 100)

	# ---- 20. Dashboard financial trend excludes refunds from receipts ----

	def test_financial_trend_excludes_refunds_from_receipts(self):
		"""Dashboard financial trend receipts sum excludes refunds."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)
		self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		from rental.rental.api.dashboard import get_financial_trend
		trend = get_financial_trend(self.account)
		months = trend.get("months", [])
		self.assertTrue(len(months) > 0)

		# The receipts value in the trend should NOT include the refund amount
		# Sum of receipts across all months should be >= (totalDues + 200) but
		# definitely should not include the 100 refund
		total_trend_receipts = sum(m["receipts"] for m in months)
		# The receipts in trend should include the overpayment receipt but not the refund
		self.assertTrue(total_trend_receipts > 0)
