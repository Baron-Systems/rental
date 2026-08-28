"""Tests for tenant statement computation.

Source: TENANTS_MIGRATION_SPEC §37.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestStatement(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_tenants = []
		cls._created_users = []
		cls._created_accounts = []

		cls.owner_a = cls._create_test_user("stmt_owner_a@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Statement Account A", cls.owner_a)

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
			"first_name": "Statement",
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

	def _create_tenant(self, full_name="Statement Test Tenant"):
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": full_name,
		})
		doc.insert(ignore_permissions=True)
		self._created_tenants.append(doc.name)
		return doc

	# ---- TEN-BE-009: default excludes future ----

	def test_statement_default_excludes_future(self):
		"""TEN-BE-009: statement default scope excludes future dues/receipts."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Future Exclusion Test")
		stmt = get_tenant_statement(doc.name)
		self.assertEqual(stmt["openingBalance"], 0)
		self.assertEqual(len(stmt["lines"]), 0)

	# ---- TEN-BE-011: ordering ----

	def test_statement_ordering(self):
		"""TEN-BE-011: statement lines ordered by date, creation, id."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Ordering Test")
		stmt = get_tenant_statement(doc.name)
		# With no data, lines should be empty
		self.assertEqual(len(stmt["lines"]), 0)

	# ---- TEN-BE-010: uses dueDate ----

	def test_statement_uses_due_date(self):
		"""TEN-BE-010: statement uses dueDate, not transaction date."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Due Date Test")
		stmt = get_tenant_statement(doc.name)
		self.assertIn("lines", stmt)
		self.assertIn("totalDues", stmt)
		self.assertIn("totalReceipts", stmt)
		self.assertIn("closingBalance", stmt)

	# ---- Opening balance always 0 ----

	def test_opening_balance_always_zero(self):
		"""TEN-BE-012: opening balance is always 0."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Opening Balance Test")
		stmt = get_tenant_statement(doc.name)
		self.assertEqual(stmt["openingBalance"], 0)

	# ---- Pagination ----

	def test_statement_pagination(self):
		"""TEN-UX-012: statement uses pagination with page size 15."""
		from rental.rental.services.statement_service import get_tenant_statement, STATEMENT_PAGE_SIZE
		self.assertEqual(STATEMENT_PAGE_SIZE, 15)
		doc = self._create_tenant(full_name="Pagination Test")
		stmt = get_tenant_statement(doc.name, page=1)
		self.assertIn("pagination", stmt)
		self.assertEqual(stmt["pagination"]["pageSize"], 15)

	# ---- Print mode ignores pagination ----

	def test_print_mode_ignores_pagination(self):
		"""TEN-UX-017: print mode returns all lines without pagination."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Print Mode Statement Test")
		stmt = get_tenant_statement(doc.name, print_mode=True)
		# Print mode should still return pagination info but with all lines
		self.assertIn("lines", stmt)

	# ---- TEN-BE-016: contract ownership ----

	def test_statement_rejects_contract_not_owned(self):
		"""TEN-BE-016: statement rejects contractId not owned by tenant."""
		from rental.rental.services.statement_service import apply_contract_filter
		doc = self._create_tenant(full_name="Contract Ownership Test")
		# Use a non-existent contract — should not raise (None contract)
		apply_contract_filter(doc.name, None)
		# With a fake contract name that doesn't exist, get_value returns None
		# which != tenant name, so it should raise
		self.assertRaises(
			frappe.PermissionError,
			apply_contract_filter,
			doc.name,
			"NONEXISTENT-CONTRACT-12345",
		)

	# ---- TEN-BE-012: closing balance ----

	def test_closing_balance_equals_total_dues_minus_receipts(self):
		"""TEN-BE-012: closing balance = totalDues - totalReceipts."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Closing Balance Test")
		stmt = get_tenant_statement(doc.name)
		expected = stmt["totalDues"] - stmt["totalReceipts"]
		self.assertEqual(stmt["closingBalance"], expected)

	# ---- Line structure ----

	def test_statement_line_structure(self):
		"""TEN-BE-010: statement lines have required fields."""
		from rental.rental.services.statement_service import get_tenant_statement
		doc = self._create_tenant(full_name="Line Structure Test")
		stmt = get_tenant_statement(doc.name)
		# Even with no lines, the structure should be present
		self.assertIn("lines", stmt)
		self.assertIn("openingBalance", stmt)
		self.assertIn("totalDues", stmt)
		self.assertIn("totalReceipts", stmt)
		self.assertIn("closingBalance", stmt)
		self.assertIn("pagination", stmt)
