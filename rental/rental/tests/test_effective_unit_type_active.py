"""Verify Account-level effective is_active is used everywhere Unit Types are fetched."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestEffectiveUnitTypeActive(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_configs = []

		cls.owner_a = cls._create_test_user("effa@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Eff A", cls.owner_a)

		cls.owner_b = cls._create_test_user("effb@test.com", "Rental Property Owner")
		cls.account_b = cls._create_test_account("Eff B", cls.owner_b)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in cls._created_configs:
			if frappe.db.exists("Account Unit Type", name):
				frappe.delete_doc("Account Unit Type", name, force=True)
		for name in cls._created_accounts:
			if frappe.db.exists("Rental Account", name):
				frappe.delete_doc("Rental Account", name, force=True)
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

	def _get_all_system_types(self):
		return frappe.get_all("Unit Type", filters={"is_system": 1},
			fields=["name", "type_name", "code", "is_active"], order_by="display_order asc")

	def _enable_account_type(self, account, unit_type):
		existing = frappe.db.get_value("Account Unit Type",
			{"rental_account": account, "unit_type": unit_type}, "name")
		if existing:
			frappe.db.set_value("Account Unit Type", existing, "is_active", 1)
		else:
			doc = frappe.get_doc({
				"doctype": "Account Unit Type",
				"rental_account": account,
				"unit_type": unit_type,
				"is_active": 1,
			})
			doc.insert(ignore_permissions=True)
			self._created_configs.append(doc.name)

	def _clear_overrides(self, account):
		for name in frappe.get_all("Account Unit Type",
			filters={"rental_account": account}, pluck="name"):
			frappe.delete_doc("Account Unit Type", name, ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_overrides(self.account_a)
		self._clear_overrides(self.account_b)

	def test_enable_5_types_all_appear_in_creation_dropdown(self):
		"""Enable 5 system types for account A; all 5 must appear in get_active_unit_types."""
		from rental.rental.api.property import get_active_unit_types
		from rental.rental.api.unit_settings import get_unit_types

		all_types = self._get_all_system_types()
		self.assertGreaterEqual(len(all_types), 5,
			"Need at least 5 system unit types for this test")

		# Pick 5 types to enable (regardless of system is_active)
		types_to_enable = all_types[:5]
		frappe.set_user("Administrator")
		for t in types_to_enable:
			self._enable_account_type(self.account_a, t["name"])

		# Verify all 5 appear in Settings (get_unit_types with include_inactive=1)
		frappe.set_user(self.owner_a)
		result = get_unit_types(include_inactive=1)
		settings_names = {t["name"] for t in result["unitTypes"]}
		for t in types_to_enable:
			self.assertIn(t["name"], settings_names,
				f"{t['type_name']} should appear in Settings")

		# Verify all 5 appear in Unit creation dropdown (get_active_unit_types)
		result = get_active_unit_types()
		dropdown_names = {t["name"] for t in result["unitTypes"]}
		for t in types_to_enable:
			self.assertIn(t["name"], dropdown_names,
				f"{t['type_name']} should appear in creation dropdown after enabling")

	def test_disable_one_type_disappears_from_creation(self):
		"""Disable one type; it should disappear from creation dropdown."""
		from rental.rental.api.property import get_active_unit_types

		all_types = self._get_all_system_types()
		# Enable 5
		frappe.set_user("Administrator")
		types_to_enable = all_types[:5]
		for t in types_to_enable:
			self._enable_account_type(self.account_a, t["name"])

		# Disable the 3rd one
		disabled_type = types_to_enable[2]
		existing = frappe.db.get_value("Account Unit Type",
			{"rental_account": self.account_a, "unit_type": disabled_type["name"]}, "name")
		frappe.db.set_value("Account Unit Type", existing, "is_active", 0)

		frappe.set_user(self.owner_a)
		result = get_active_unit_types()
		dropdown_names = {t["name"] for t in result["unitTypes"]}
		self.assertNotIn(disabled_type["name"], dropdown_names,
			f"{disabled_type['type_name']} should NOT appear after disabling")

		# The other 4 should still be there
		for t in types_to_enable:
			if t["name"] == disabled_type["name"]:
				continue
			self.assertIn(t["name"], dropdown_names,
				f"{t['type_name']} should still appear")

	def test_account_isolation_in_creation_dropdown(self):
		"""Account A's enabled types don't affect Account B's dropdown."""
		from rental.rental.api.property import get_active_unit_types

		all_types = self._get_all_system_types()
		frappe.set_user("Administrator")
		# Enable 5 for A
		types_for_a = all_types[:5]
		for t in types_for_a:
			self._enable_account_type(self.account_a, t["name"])

		# Account B should NOT see A's enabled types (unless system is_active=1)
		frappe.set_user(self.owner_b)
		result_b = get_active_unit_types()
		b_names = {t["name"] for t in result_b["unitTypes"]}

		# Account B should only see types where system is_active=1 (no override for B)
		for t in all_types:
			system_active = int(t["is_active"] or 0)
			if system_active == 1:
				self.assertIn(t["name"], b_names,
					f"{t['type_name']} (system active) should appear for B")
			else:
				self.assertNotIn(t["name"], b_names,
					f"{t['type_name']} (system inactive) should NOT appear for B")

	def test_system_disabled_type_appears_when_account_enables(self):
		"""A system-disabled type enabled by account must appear in dropdown."""
		from rental.rental.api.property import get_active_unit_types

		# Find a system type with is_active=0
		disabled_types = frappe.get_all("Unit Type",
			filters={"is_system": 1, "is_active": 0},
			fields=["name", "type_name"], limit=1)
		if not disabled_types:
			self.skipTest("No system-disabled Unit Type found")

		disabled = disabled_types[0]
		frappe.set_user("Administrator")
		self._enable_account_type(self.account_a, disabled["name"])

		frappe.set_user(self.owner_a)
		result = get_active_unit_types()
		dropdown_names = {t["name"] for t in result["unitTypes"]}
		self.assertIn(disabled["name"], dropdown_names,
			f"{disabled['type_name']} (system-disabled but account-enabled) must appear")
