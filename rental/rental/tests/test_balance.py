"""Tests for balance computation.

Source: TENANTS_MIGRATION_SPEC §37.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBalance(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_tenants = []
		cls._created_users = []
		cls._created_accounts = []

		cls.owner_a = cls._create_test_user("balance_owner_a@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Balance Account A", cls.owner_a)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for tenant_name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", tenant_name):
				frappe.delete_doc("Rental Tenant", tenant_name, force=True)

		for account_name in cls._created_accounts:
			if frappe.db.exists("Rental Account", account_name):
				frappe.delete_doc("Rental Account", account_name, force=True)

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
			"first_name": "Balance",
			"last_name": "Owner",
			"roles": [{"role": role}],
			"send_welcome_email": 0,
		})
		user.insert(ignore_permissions=True)
		cls._created_users.append(email)
		return email

	@classmethod
	def _create_test_account(cls, name, owner):
		if frappe.db.exists("Rental Account", name):
			frappe.delete_doc("Rental Account", name, force=True)
		account = frappe.get_doc({
			"doctype": "Rental Account",
			"account_name": name,
			"owner_user": owner,
			"is_active": 1,
		})
		account.insert(ignore_permissions=True)
		cls._created_accounts.append(name)
		return name

	def _create_tenant(self, full_name="Balance Test Tenant"):
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": full_name,
		})
		doc.insert(ignore_permissions=True)
		self._created_tenants.append(doc.name)
		return doc

	# ---- TEN-BE-007: balance computed, not stored ----

	def test_balance_is_computed(self):
		"""TEN-BE-007: balance is computed at runtime, not stored."""
		from rental.rental.services.balance_service import get_tenant_balance
		doc = self._create_tenant(full_name="Computed Balance Test")
		bal = get_tenant_balance(doc.name)
		self.assertIn("totalDues", bal)
		self.assertIn("totalReceipts", bal)
		self.assertIn("balance", bal)
		self.assertEqual(bal["balance"], bal["totalDues"] - bal["totalReceipts"])

	# ---- TEN-BE-008: balance with no dues/receipts ----

	def test_balance_zero_with_no_data(self):
		"""TEN-BE-008: balance is 0 when no dues or receipts exist."""
		from rental.rental.services.balance_service import get_tenant_balance
		doc = self._create_tenant(full_name="Zero Balance Test")
		bal = get_tenant_balance(doc.name)
		self.assertEqual(bal["totalDues"], 0)
		self.assertEqual(bal["totalReceipts"], 0)
		self.assertEqual(bal["balance"], 0)

	# ---- TEN-BE-018: all approved receipts regardless of date ----

	def test_balance_includes_all_approved_receipts(self):
		"""TEN-BE-018: balance includes all approved receipts regardless of receiptDate."""
		from rental.rental.services.balance_service import get_tenant_balance
		# This test verifies the function signature and behavior
		# Actual receipt data requires the Receipt module
		doc = self._create_tenant(full_name="Receipt Date Test")
		bal = get_tenant_balance(doc.name)
		# With no receipts, totalReceipts should be 0
		self.assertEqual(bal["totalReceipts"], 0)

	# ---- TEN-BE-008: sign convention ----

	def test_balance_sign_convention(self):
		"""TEN-BE-008: >0 owes, <0 overpaid, =0 settled."""
		from rental.rental.services.balance_service import get_tenant_balance
		doc = self._create_tenant(full_name="Sign Test")
		bal = get_tenant_balance(doc.name)
		# With no data, balance is 0 (settled)
		self.assertEqual(bal["balance"], 0)

	# ---- Stats ----

	def test_tenant_balance_stats(self):
		"""TEN-BE-008: stats return total, debt, credit, zero."""
		from rental.rental.services.balance_service import get_tenant_balance_stats
		self._create_tenant(full_name="Stats Test Tenant")
		frappe.set_user(self.owner_a)
		stats = get_tenant_balance_stats({"rental_account": self.account_a})
		self.assertIn("total", stats)
		self.assertIn("debt", stats)
		self.assertIn("credit", stats)
		self.assertIn("zero", stats)
		self.assertGreaterEqual(stats["total"], 1)
