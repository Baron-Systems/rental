import frappe
import json
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestTenantIsolation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []

		cls.admin_user = "Administrator"

		cls.owner_a = cls._create_test_user("owner_a@test.com", "Rental Property Owner")
		cls.owner_b = cls._create_test_user("owner_b@test.com", "Rental Property Owner")
		cls.no_account_user = cls._create_test_user("no_account@test.com", "Rental Property Owner")

		cls.account_a = cls._create_test_account("Account A", cls.owner_a)
		cls.account_b = cls._create_test_account("Account B", cls.owner_b)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

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

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"roles": [{"role": role}],
				"send_welcome_email": 0,
			}
		)
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

		account = frappe.get_doc(
			{
				"doctype": "Rental Account",
				"account_name": name,
				"owner_user": owner_user,
				"is_active": 1,
				"setup_completed": 1,
			}
		)
		account.insert(ignore_permissions=True)
		cls._created_accounts.append(account.name)
		return account.name

	def test_owner_a_resolves_only_account_a(self):
		frappe.set_user(self.owner_a)
		from rental.rental.utils.account import get_current_rental_account

		account = get_current_rental_account()
		self.assertEqual(account, self.account_a)

	def test_owner_b_resolves_only_account_b(self):
		frappe.set_user(self.owner_b)
		from rental.rental.utils.account import get_current_rental_account

		account = get_current_rental_account()
		self.assertEqual(account, self.account_b)

	def test_owner_can_read_own_account_but_not_others(self):
		frappe.set_user(self.owner_a)

		# Owner A CAN read their own account
		has_perm_own = frappe.has_permission("Rental Account", doc=self.account_a, user=self.owner_a)
		self.assertTrue(has_perm_own)

		# Owner A CANNOT read Account B
		has_perm_b = frappe.has_permission("Rental Account", doc=self.account_b, user=self.owner_a)
		self.assertFalse(has_perm_b)

		# Owner A has general read permission on Rental Account (filtered by permission_query_conditions)
		can_read = frappe.has_permission("Rental Account", "read", user=self.owner_a)
		self.assertTrue(can_read)

		# permission_query_conditions should filter by owner_user
		from rental.rental.utils.permissions import get_permission_query_conditions
		conditions = get_permission_query_conditions(self.owner_a, "Rental Account")
		self.assertIn(self.owner_a, conditions)

	def test_disabled_rental_account_blocks_app_access(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Rental Account", self.account_a, "is_active", 0)

		frappe.set_user(self.owner_a)
		from rental.rental.utils.account import get_current_rental_account

		with self.assertRaises(frappe.PermissionError):
			get_current_rental_account()

		frappe.set_user("Administrator")
		frappe.db.set_value("Rental Account", self.account_a, "is_active", 1)

	def test_user_with_no_rental_account_is_rejected(self):
		frappe.set_user(self.no_account_user)
		from rental.rental.utils.account import get_current_rental_account

		with self.assertRaises(frappe.PermissionError):
			get_current_rental_account()

	def test_setup_completion_only_affects_current_owner(self):
		frappe.set_user(self.owner_a)

		from rental.rental.api.setup import complete_setup

		result = complete_setup(
			lessor_type="person",
			landlord_name="Owner A Landlord",
			landlord_id="1234567890",
			currency="ILS",
		)

		self.assertEqual(result["success"], True)

		a_setup = frappe.db.get_value("Rental Account", self.account_a, "setup_completed")
		b_setup = frappe.db.get_value("Rental Account", self.account_b, "setup_completed")

		self.assertEqual(a_setup, 1)

		self.assertEqual(b_setup, 1)

		a_settings = frappe.db.get_value(
			"Rental Settings", {"rental_account": self.account_a}, "landlord_name"
		)
		b_settings_exists = frappe.db.exists(
			"Rental Settings", {"rental_account": self.account_b}
		)

		self.assertEqual(a_settings, "Owner A Landlord")
		self.assertFalse(b_settings_exists)

	def test_system_admin_bypass_remains_functional(self):
		frappe.set_user("Administrator")
		from rental.rental.utils.account import get_current_rental_account, is_system_manager

		self.assertTrue(is_system_manager())
		account = get_current_rental_account()
		self.assertIsNone(account)

	def test_permission_query_conditions_filter_by_account(self):
		frappe.set_user(self.owner_a)
		from rental.rental.utils.permissions import get_permission_query_conditions

		conditions = get_permission_query_conditions(self.owner_a, "Rental Settings")
		self.assertIn(self.account_a, conditions)
		self.assertNotIn(self.account_b, conditions)

	def test_permission_query_conditions_system_manager_no_filter(self):
		frappe.set_user("Administrator")
		from rental.rental.utils.permissions import get_permission_query_conditions

		conditions = get_permission_query_conditions("Administrator", "Rental Settings")
		self.assertIsNone(conditions)

	def test_unique_owner_user_constraint(self):
		frappe.set_user("Administrator")

		duplicate = frappe.get_doc(
			{
				"doctype": "Rental Account",
				"account_name": "Duplicate Account",
				"owner_user": self.owner_a,
				"is_active": 1,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			duplicate.insert(ignore_permissions=True)
