"""Tests for dues, receipts, waivers, and balance computation.

Ported test logic from the source-of-truth financial test suite.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestFinancials(FrappeTestCase):
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

		cls.owner = cls._create_test_user("fin_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Financial Test Account", cls.owner)
		cls._create_settings(cls.account)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		# Clean up in reverse dependency order
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
			"landlord_id": "ID-123456",
			"landlord_phone": "0555-123-456",
			"landlord_address": "Test Address, Test City",
			"currency": "JOD",
		})
		settings.insert(ignore_permissions=True)

	def _setup_contract(self, rent=500):
		"""Create a building, unit, tenant, and approved contract."""
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"Fin Building {frappe.utils.random_string(5)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)

		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building.name,
			"unit_number": f"U-{frappe.utils.random_string(4)}",
			"unit_type": "apartment",
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)

		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"Fin Tenant {frappe.utils.random_string(5)}",
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)

		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant.name,
			"building": building.name,
			"unit": unit.name,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
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

	# --- Balance computation ---

	def test_tenant_balance_with_dues_only(self):
		ctx = self._setup_contract(rent=500)

		from rental.rental.services.balance_service import get_tenant_balance
		balance = get_tenant_balance(ctx["tenant"])

		# Should have dues > 0 and receipts = 0
		self.assertTrue(balance["totalDues"] > 0, "Should have dues from contract approval")
		self.assertEqual(balance["totalReceipts"], 0)
		self.assertEqual(balance["balance"], balance["totalDues"])

	def test_tenant_balance_with_receipt(self):
		ctx = self._setup_contract(rent=500)

		# Create a receipt
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
		receipt.submit()
		self._created_receipts.append(receipt.name)

		from rental.rental.services.balance_service import get_tenant_balance
		balance = get_tenant_balance(ctx["tenant"])

		self.assertEqual(balance["totalReceipts"], 200)
		self.assertEqual(balance["balance"], balance["totalDues"] - 200)

	def test_contract_balance(self):
		ctx = self._setup_contract(rent=500)

		from rental.rental.services.balance_service import get_contract_balance
		balance = get_contract_balance(ctx["contract"])

		self.assertTrue(balance["totalDues"] > 0)
		self.assertEqual(balance["totalReceipts"], 0)

	def test_building_balance(self):
		ctx = self._setup_contract(rent=500)

		from rental.rental.services.balance_service import get_building_balance
		balance = get_building_balance(ctx["building"])

		self.assertTrue(balance["totalDues"] > 0)

	# --- Receipt lifecycle ---

	def test_receipt_draft_to_approved(self):
		ctx = self._setup_contract(rent=500)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 300,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		self._created_receipts.append(receipt.name)

		self.assertEqual(receipt.docstatus, 0)
		self.assertIsNone(receipt.receipt_number)

		receipt.submit()

		self.assertEqual(receipt.docstatus, 1)
		self.assertTrue(receipt.receipt_number, "Receipt number should be generated on submit")

	def test_receipt_cheque_validation(self):
		ctx = self._setup_contract(rent=500)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 300,
			"payment_method": "cheque",
			# Missing reference_number and cheque_date
		})

		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	def test_receipt_cancel(self):
		ctx = self._setup_contract(rent=500)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 300,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self._created_receipts.append(receipt.name)

		receipt.cancellation_reason = "Test cancel"
		receipt.cancel()

		self.assertEqual(receipt.docstatus, 2)
		self.assertTrue(receipt.cancelled_at)

	# --- Due creation (manual) ---

	def test_rent_due_cannot_be_created_manually(self):
		ctx = self._setup_contract(rent=500)

		rent_due_type = frappe.db.get_value("Rental Due Type", {"due_type_code": "rent"}, "name")

		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Rental Due",
				"rental_account": self.account,
				"tenant": ctx["tenant"],
				"contract": ctx["contract"],
				"due_type": rent_due_type,
				"due_date": frappe.utils.today(),
				"amount": 100,
				"source_type": "manual_contract",
			}).insert(ignore_permissions=True)

	# --- Waiver ---

	def test_waiver_reduces_balance(self):
		ctx = self._setup_contract(rent=500)

		# Get an auto_contract due
		due_name = frappe.db.get_value(
			"Rental Due",
			{"contract": ctx["contract"], "source_type": "auto_contract", "docstatus": 1},
			"name",
		)
		self.assertTrue(due_name)

		due_amount = frappe.db.get_value("Rental Due", due_name, "amount")

		from rental.rental.api.due import create_waiver
		waiver_amount = min(50, due_amount)
		create_waiver(due_name, amount=waiver_amount, reason="Test waiver")

		from rental.rental.services.balance_service import get_effective_due_total
		effective = get_effective_due_total({"tenant": ctx["tenant"]})

		# Effective total should be less than gross dues (dueDate <= today) by waiver_amount
		today = frappe.utils.today()
		gross = sum(float(a or 0) for a in frappe.get_all(
			"Rental Due",
			filters={"tenant": ctx["tenant"], "docstatus": 1, "due_date": ["<=", today]},
			pluck="amount",
		))
		self.assertEqual(effective, gross - waiver_amount)

	def test_waiver_cannot_exceed_due(self):
		ctx = self._setup_contract(rent=500)

		due_name = frappe.db.get_value(
			"Rental Due",
			{"contract": ctx["contract"], "source_type": "auto_contract", "docstatus": 1},
			"name",
		)
		due_amount = frappe.db.get_value("Rental Due", due_name, "amount")

		from rental.rental.api.due import create_waiver
		with self.assertRaises(frappe.ValidationError):
			create_waiver(due_name, amount=due_amount + 100, reason="Excessive waiver")

	# --- Statement ---

	def test_tenant_statement(self):
		ctx = self._setup_contract(rent=500)

		from rental.rental.services.statement_service import get_tenant_statement
		statement = get_tenant_statement(ctx["tenant"])

		self.assertTrue(len(statement["lines"]) > 0)
		self.assertTrue(statement["totalDues"] > 0)
		self.assertEqual(statement["totalReceipts"], 0)
		self.assertEqual(statement["closingBalance"], statement["totalDues"])
		self.assertEqual(statement["openingBalance"], 0)
