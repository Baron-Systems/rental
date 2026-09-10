"""Tests for Account Unit Type (Account-level enable/disable of System Unit Types)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestAccountUnitType(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_configs = []

		cls.owner_a = cls._create_test_user("auta2_owner@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Account A2", cls.owner_a)

		cls.owner_b = cls._create_test_user("autb2_owner@test.com", "Rental Property Owner")
		cls.account_b = cls._create_test_account("Account B2", cls.owner_b)

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

	def _get_apartment(self):
		return frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

	def _get_shop(self):
		return frappe.db.get_value("Unit Type", {"code": "shop", "is_system": 1}, "name")

	def _clear_overrides(self, account, unit_type=None):
		filters = {"rental_account": account}
		if unit_type:
			filters["unit_type"] = unit_type
		overrides = frappe.get_all("Account Unit Type", filters=filters, pluck="name")
		for name in overrides:
			frappe.delete_doc("Account Unit Type", name, ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_overrides(self.account_a)
		self._clear_overrides(self.account_b)

	# ======================================================================
	# T1: No override → effective is_active = System is_active
	# ======================================================================

	def test_t1_no_override_returns_system_active(self):
		from rental.rental.api.unit_settings import get_unit_types
		frappe.set_user(self.owner_a)
		apartment = self._get_apartment()
		system_active = int(frappe.db.get_value("Unit Type", apartment, "is_active") or 0)

		result = get_unit_types(include_inactive=1)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		self.assertIsNotNone(apt)
		self.assertEqual(int(apt["is_active"]), system_active)
		self.assertFalse(apt["has_account_override"])

	# ======================================================================
	# T2: Toggle disable creates override
	# ======================================================================

	def test_t2_toggle_disable_creates_override(self):
		from rental.rental.api.unit_settings import toggle_account_unit_type
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		result = toggle_account_unit_type(apartment, 0)
		self.assertTrue(result["success"])
		self.assertEqual(result["is_active"], 0)

		override = frappe.db.get_value(
			"Account Unit Type",
			{"rental_account": self.account_a, "unit_type": apartment},
			["name", "is_active"],
			as_dict=True,
		)
		self.assertIsNotNone(override)
		self.assertEqual(int(override.is_active), 0)

	# ======================================================================
	# T3: Toggle enable updates existing override
	# ======================================================================

	def test_t3_toggle_enable_updates_override(self):
		from rental.rental.api.unit_settings import toggle_account_unit_type
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		# Disable first
		toggle_account_unit_type(apartment, 0)
		# Enable again
		toggle_account_unit_type(apartment, 1)

		override = frappe.db.get_value(
			"Account Unit Type",
			{"rental_account": self.account_a, "unit_type": apartment},
			["is_active"],
			as_dict=True,
		)
		self.assertEqual(int(override.is_active), 1)

		# Should be only one override row
		count = frappe.db.count("Account Unit Type",
			{"rental_account": self.account_a, "unit_type": apartment})
		self.assertEqual(count, 1)

	# ======================================================================
	# T4: get_unit_types reflects account override
	# ======================================================================

	def test_t4_get_unit_types_reflects_override(self):
		from rental.rental.api.unit_settings import get_unit_types, toggle_account_unit_type
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		# Disable apartment for account A
		toggle_account_unit_type(apartment, 0)

		result = get_unit_types(include_inactive=1)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		self.assertIsNotNone(apt)
		self.assertEqual(int(apt["is_active"]), 0)
		self.assertTrue(apt["has_account_override"])

	# ======================================================================
	# T5: include_inactive=0 excludes disabled types
	# ======================================================================

	def test_t5_include_inactive_excludes_disabled(self):
		from rental.rental.api.unit_settings import get_unit_types, toggle_account_unit_type
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		# Disable apartment
		toggle_account_unit_type(apartment, 0)

		result = get_unit_types(include_inactive=0)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		self.assertIsNone(apt, "Disabled type should not appear when include_inactive=0")

	# ======================================================================
	# T6: Reset removes override → falls back to system default
	# ======================================================================

	def test_t6_reset_restores_default(self):
		from rental.rental.api.unit_settings import (
			get_unit_types, toggle_account_unit_type, reset_account_unit_type,
		)
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		system_active = int(frappe.db.get_value("Unit Type", apartment, "is_active") or 0)

		# Disable
		toggle_account_unit_type(apartment, 0)
		# Reset
		result = reset_account_unit_type(apartment)
		self.assertTrue(result["success"])
		self.assertEqual(result["removed"], 1)

		# Verify override gone
		override = frappe.db.exists("Account Unit Type",
			{"rental_account": self.account_a, "unit_type": apartment})
		self.assertIsNone(override)

		# Verify get_unit_types reflects system default
		result = get_unit_types(include_inactive=1)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		self.assertEqual(int(apt["is_active"]), system_active)
		self.assertFalse(apt["has_account_override"])

	# ======================================================================
	# T7: Account A override does not affect Account B
	# ======================================================================

	def test_t7_account_isolation(self):
		from rental.rental.api.unit_settings import get_unit_types, toggle_account_unit_type
		apartment = self._get_apartment()
		system_active = int(frappe.db.get_value("Unit Type", apartment, "is_active") or 0)

		# Account A disables apartment
		frappe.set_user(self.owner_a)
		toggle_account_unit_type(apartment, 0)

		# Account B sees system default
		frappe.set_user(self.owner_b)
		result = get_unit_types(include_inactive=1)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		self.assertEqual(int(apt["is_active"]), system_active)
		self.assertFalse(apt["has_account_override"])

	# ======================================================================
	# T8: Permission isolation — Account A cannot see Account B overrides
	# ======================================================================

	def test_t8_permission_isolation(self):
		apartment = self._get_apartment()
		frappe.set_user(self.owner_b)
		frappe.get_doc({
			"doctype": "Account Unit Type",
			"rental_account": self.account_b,
			"unit_type": apartment,
			"is_active": 0,
		}).insert(ignore_permissions=True)

		frappe.set_user(self.owner_a)
		visible = frappe.get_list(
			"Account Unit Type",
			filters={"unit_type": apartment},
			fields=["rental_account"],
		)
		for v in visible:
			self.assertNotEqual(v["rental_account"], self.account_b)

	# ======================================================================
	# T9: get_active_unit_types excludes account-disabled types
	# ======================================================================

	def test_t9_get_active_unit_types_respects_override(self):
		from rental.rental.api.property import get_active_unit_types
		from rental.rental.api.unit_settings import toggle_account_unit_type
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		# First verify apartment is in active list
		result = get_active_unit_types()
		names = [t["name"] for t in result["unitTypes"]]
		self.assertIn(apartment, names)

		# Disable apartment for this account
		toggle_account_unit_type(apartment, 0)

		# Now apartment should be excluded
		result = get_active_unit_types()
		names = [t["name"] for t in result["unitTypes"]]
		self.assertNotIn(apartment, names)

	# ======================================================================
	# T10: Toggle on non-system type fails
	# ======================================================================

	def test_t10_toggle_non_system_fails(self):
		from rental.rental.api.unit_settings import toggle_account_unit_type
		# Find a custom (non-system) unit type
		custom = frappe.db.get_value("Unit Type", {"is_system": 0}, "name")
		if not custom:
			self.skipTest("No custom Unit Type found in DB")
		frappe.set_user(self.owner_a)
		with self.assertRaises(frappe.ValidationError):
			toggle_account_unit_type(custom, 0)

	# ======================================================================
	# T11: Uniqueness — duplicate (rental_account, unit_type) rejected
	# ======================================================================

	def test_t11_uniqueness_enforced(self):
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)
		frappe.get_doc({
			"doctype": "Account Unit Type",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"is_active": 0,
		}).insert(ignore_permissions=True)

		# Second insert should fail
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Account Unit Type",
				"rental_account": self.account_a,
				"unit_type": apartment,
				"is_active": 1,
			}).insert(ignore_permissions=True)

	# ======================================================================
	# T12: System Unit Type.is_active is NOT modified by toggle
	# ======================================================================

	def test_t12_system_is_active_unchanged(self):
		from rental.rental.api.unit_settings import toggle_account_unit_type
		apartment = self._get_apartment()
		system_active_before = int(frappe.db.get_value("Unit Type", apartment, "is_active") or 0)

		frappe.set_user(self.owner_a)
		toggle_account_unit_type(apartment, 0)

		system_active_after = int(frappe.db.get_value("Unit Type", apartment, "is_active") or 0)
		self.assertEqual(system_active_after, system_active_before,
			"System Unit Type.is_active must not be modified by account toggle")

	# ======================================================================
	# T13: Multiple types can be toggled independently
	# ======================================================================

	def test_t13_multiple_types_independent(self):
		from rental.rental.api.unit_settings import get_unit_types, toggle_account_unit_type
		apartment = self._get_apartment()
		shop = self._get_shop()
		frappe.set_user(self.owner_a)

		# Disable apartment, keep shop active
		toggle_account_unit_type(apartment, 0)

		result = get_unit_types(include_inactive=1)
		apt = next((t for t in result["unitTypes"] if t["name"] == apartment), None)
		shp = next((t for t in result["unitTypes"] if t["name"] == shop), None)

		self.assertEqual(int(apt["is_active"]), 0)
		self.assertTrue(apt["has_account_override"])
		# Shop should not have an override
		if shp:
			self.assertFalse(shp["has_account_override"])
