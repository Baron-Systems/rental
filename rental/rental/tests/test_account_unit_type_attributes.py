"""Tests for Account Unit Type Attribute (Account-level configuration).

Covers:
- System Default fallback when no customization exists
- Account customizations override defaults
- Replace-all save (transactional)
- Reset to defaults
- Account isolation
- Required attribute validation
- get_unit_type_attributes_for_unit respects account config
- get_available_attributes excludes used attributes
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestAccountUnitTypeAttributes(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_configs = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_attr_values = []

		cls.owner_a = cls._create_test_user("auta_owner@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Account A", cls.owner_a)

		cls.owner_b = cls._create_test_user("autb_owner@test.com", "Rental Property Owner")
		cls.account_b = cls._create_test_account("Account B", cls.owner_b)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in cls._created_attr_values:
			if frappe.db.exists("Unit Attribute Value", name):
				frappe.delete_doc("Unit Attribute Value", name, force=True)
		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				frappe.delete_doc("Rental Unit", name, force=True)
		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				frappe.delete_doc("Rental Building", name, force=True)
		for name in cls._created_configs:
			if frappe.db.exists("Account Unit Type Attribute", name):
				frappe.delete_doc("Account Unit Type Attribute", name, force=True)
		for name in cls._created_accounts:
			if frappe.db.exists("Rental Account", name):
				frappe.delete_doc("Rental Account", name, force=True)
		for user in cls._created_users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=True)
		super().tearDownClass()

	# --- Helpers ---

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

	def _get_attr(self, code):
		return frappe.db.get_value("Unit Attribute", {"code": code, "is_system": 1}, "name")

	def _clear_configs(self, account, unit_type=None):
		filters = {"rental_account": account}
		if unit_type:
			filters["unit_type"] = unit_type
		configs = frappe.get_all("Account Unit Type Attribute", filters=filters, pluck="name")
		for name in configs:
			frappe.delete_doc("Account Unit Type Attribute", name, ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_configs(self.account_a)
		self._clear_configs(self.account_b)

	# ======================================================================
	# T1: No customization → returns System Default
	# ======================================================================

	def test_t1_no_customization_returns_default(self):
		from rental.rental.api.unit_settings import get_unit_type_attributes
		frappe.set_user(self.owner_a)
		apartment = self._get_apartment()
		result = get_unit_type_attributes(apartment)
		attrs = result["attributes"]
		self.assertTrue(len(attrs) > 0)
		for attr in attrs:
			self.assertFalse(attr["has_customization"], "Should not have customization")
		# Apartment defaults include rooms_count and electricity_meter
		codes = [a["attribute_code"] for a in attrs]
		self.assertIn("rooms_count", codes)
		self.assertIn("electricity_meter", codes)

	# ======================================================================
	# T2: Customization exists → returns account list
	# ======================================================================

	def test_t2_customization_returns_account_list(self):
		from rental.rental.api.unit_settings import get_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		elec = self._get_attr("electricity_meter")

		frappe.set_user(self.owner_a)
		# Create a customization with only 2 attributes
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 1,
			"display_order": 0,
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": elec,
			"is_required": 0,
			"display_order": 1,
		}).insert(ignore_permissions=True)

		result = get_unit_type_attributes(apartment)
		attrs = result["attributes"]
		self.assertEqual(len(attrs), 2)
		for attr in attrs:
			self.assertTrue(attr["has_customization"], "Should have customization")
		codes = [a["attribute_code"] for a in attrs]
		self.assertEqual(set(codes), {"rooms_count", "electricity_meter"})

	# ======================================================================
	# T3: Save creates new records
	# ======================================================================

	def test_t3_save_creates_records(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		elec = self._get_attr("electricity_meter")

		frappe.set_user(self.owner_a)
		payload = json.dumps([
			{"attribute": rooms, "is_required": 1, "display_order": 0},
			{"attribute": elec, "is_required": 0, "display_order": 1},
		])
		result = save_account_unit_type_attributes(apartment, payload)
		self.assertTrue(result["success"])
		self.assertEqual(result["count"], 2)

		configs = frappe.get_all("Account Unit Type Attribute",
			filters={"rental_account": self.account_a, "unit_type": apartment},
			fields=["attribute", "is_required", "display_order"],
			order_by="display_order")
		self.assertEqual(len(configs), 2)
		self.assertEqual(configs[0]["attribute"], rooms)
		self.assertEqual(int(configs[0]["is_required"]), 1)
		self.assertEqual(configs[1]["attribute"], elec)

	# ======================================================================
	# T4: Save replaces existing records (replace-all)
	# ======================================================================

	def test_t4_save_replaces_existing(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		elec = self._get_attr("electricity_meter")
		water = self._get_attr("water_meter")

		frappe.set_user(self.owner_a)
		# Initial save with 2 attrs
		payload1 = json.dumps([
			{"attribute": rooms, "is_required": 1, "display_order": 0},
			{"attribute": elec, "is_required": 0, "display_order": 1},
		])
		save_account_unit_type_attributes(apartment, payload1)

		# Replace with 1 attr (different)
		payload2 = json.dumps([
			{"attribute": water, "is_required": 1, "display_order": 0},
		])
		save_account_unit_type_attributes(apartment, payload2)

		configs = frappe.get_all("Account Unit Type Attribute",
			filters={"rental_account": self.account_a, "unit_type": apartment},
			fields=["attribute"], pluck="attribute")
		self.assertEqual(len(configs), 1)
		self.assertEqual(configs[0], water)

	# ======================================================================
	# T5: Save rejects nonexistent attribute
	# ======================================================================

	def test_t5_save_rejects_nonexistent(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)
		payload = json.dumps([
			{"attribute": "NONEXISTENT-12345", "is_required": 0, "display_order": 0},
		])
		with self.assertRaises(frappe.ValidationError):
			save_account_unit_type_attributes(apartment, payload)

	# ======================================================================
	# T6: Save rejects duplicates
	# ======================================================================

	def test_t6_save_rejects_duplicates(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		frappe.set_user(self.owner_a)
		payload = json.dumps([
			{"attribute": rooms, "is_required": 0, "display_order": 0},
			{"attribute": rooms, "is_required": 1, "display_order": 1},
		])
		with self.assertRaises(frappe.ValidationError):
			save_account_unit_type_attributes(apartment, payload)

	# ======================================================================
	# T7: Save rejects non-system attribute (custom attr)
	# ======================================================================

	def test_t7_save_rejects_non_system_attribute(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)
		# Create a custom attribute
		custom = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"CustomReject {frappe.utils.random_string(4)}",
			"code": f"custom_rej_{frappe.utils.random_string(4).lower()}",
			"data_type": "Text",
			"is_system": 0,
			"rental_account": self.account_a,
		})
		custom.insert(ignore_permissions=True)
		try:
			payload = json.dumps([
				{"attribute": custom.name, "is_required": 0, "display_order": 0},
			])
			with self.assertRaises(frappe.ValidationError):
				save_account_unit_type_attributes(apartment, payload)
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Unit Attribute", custom.name, force=True)

	# ======================================================================
	# T8: Save is transactional — rollback on error
	# ======================================================================

	def test_t8_save_transactional_rollback(self):
		from rental.rental.api.unit_settings import save_account_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		elec = self._get_attr("electricity_meter")

		frappe.set_user(self.owner_a)
		# First save succeeds
		payload1 = json.dumps([
			{"attribute": rooms, "is_required": 1, "display_order": 0},
		])
		save_account_unit_type_attributes(apartment, payload1)
		count_before = frappe.db.count("Account Unit Type Attribute",
			{"rental_account": self.account_a, "unit_type": apartment})
		self.assertEqual(count_before, 1)

		# Second save with invalid attribute — should fail and NOT delete the first
		payload2 = json.dumps([
			{"attribute": rooms, "is_required": 0, "display_order": 0},
			{"attribute": "INVALID-ATTR", "is_required": 0, "display_order": 1},
		])
		with self.assertRaises(frappe.ValidationError):
			save_account_unit_type_attributes(apartment, payload2)

		# The original record should still exist (validation happens before delete)
		count_after = frappe.db.count("Account Unit Type Attribute",
			{"rental_account": self.account_a, "unit_type": apartment})
		self.assertEqual(count_after, 1, "Original config should be preserved on validation error")

	# ======================================================================
	# T9: Reset restores defaults
	# ======================================================================

	def test_t9_reset_restores_defaults(self):
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes, save_account_unit_type_attributes,
			reset_account_unit_type_attributes,
		)
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		frappe.set_user(self.owner_a)
		# Save a customization with only 1 attr
		payload = json.dumps([
			{"attribute": rooms, "is_required": 1, "display_order": 0},
		])
		save_account_unit_type_attributes(apartment, payload)

		# Verify customization
		result = get_unit_type_attributes(apartment)
		self.assertEqual(len(result["attributes"]), 1)

		# Reset
		reset_account_unit_type_attributes(apartment)

		# Verify defaults restored
		result_after = get_unit_type_attributes(apartment)
		self.assertGreater(len(result_after["attributes"]), 1)
		for attr in result_after["attributes"]:
			self.assertFalse(attr["has_customization"])

	# ======================================================================
	# T10: Account A customizations do not affect Account B
	# ======================================================================

	def test_t10_account_isolation(self):
		from rental.rental.api.unit_settings import get_unit_type_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		# Account A creates a customization with only 1 attr
		frappe.set_user(self.owner_a)
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 1,
			"display_order": 0,
		}).insert(ignore_permissions=True)

		# Account B sees defaults (not Account A's customization)
		frappe.set_user(self.owner_b)
		result_b = get_unit_type_attributes(apartment)
		attrs_b = result_b["attributes"]
		self.assertGreater(len(attrs_b), 1, "Account B should see defaults, not Account A's config")
		for attr in attrs_b:
			self.assertFalse(attr["has_customization"], "Account B should not see Account A's customization")

	# ======================================================================
	# T11: Account A cannot query Account B's configs (permission_query_conditions)
	# ======================================================================

	def test_t11_permission_isolation(self):
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		# Account B creates a config
		frappe.set_user(self.owner_b)
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_b,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 1,
			"display_order": 0,
		}).insert(ignore_permissions=True)

		# Account A uses get_list (applies permission_query_conditions)
		frappe.set_user(self.owner_a)
		visible = frappe.get_list(
			"Account Unit Type Attribute",
			filters={"unit_type": apartment},
			fields=["rental_account"],
		)
		for v in visible:
			self.assertNotEqual(v["rental_account"], self.account_b,
				"Account A should not see Account B's configs")

	# ======================================================================
	# T12: get_unit_type_attributes_for_unit respects account config
	# ======================================================================

	def test_t12_get_for_unit_respects_config(self):
		from rental.rental.api.property import get_unit_type_attributes_for_unit
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		frappe.set_user(self.owner_a)
		# Create config with only 1 attr
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 1,
			"display_order": 0,
		}).insert(ignore_permissions=True)

		result = get_unit_type_attributes_for_unit(apartment)
		attrs = result["attributes"]
		self.assertEqual(len(attrs), 1)
		self.assertEqual(attrs[0]["attribute"], rooms)

	# ======================================================================
	# T13: get_unit_type_attributes_for_unit returns defaults when no config
	# ======================================================================

	def test_t13_get_for_unit_returns_defaults(self):
		from rental.rental.api.property import get_unit_type_attributes_for_unit
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)
		result = get_unit_type_attributes_for_unit(apartment)
		attrs = result["attributes"]
		self.assertGreater(len(attrs), 1)
		codes = [a["attribute_code"] for a in attrs]
		self.assertIn("rooms_count", codes)

	# ======================================================================
	# T14: _validate_required_attributes respects account config
	# ======================================================================

	def test_t14_validate_required_respects_config(self):
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		frappe.set_user(self.owner_a)
		# Create config making rooms required
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 1,
			"display_order": 0,
		}).insert(ignore_permissions=True)

		# Validation should throw without rooms value
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {})

		# Validation should pass with rooms value
		_validate_required_attributes(apartment, {rooms: 3})

	# ======================================================================
	# T15: _validate_required_attributes respects defaults
	# ======================================================================

	def test_t15_validate_required_respects_defaults(self):
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)

		# Find a required default attribute
		type_doc = frappe.get_doc("Unit Type", apartment)
		required_attr = None
		for row in type_doc.attributes:
			if row.is_required:
				required_attr = row.attribute
				break
		if not required_attr:
			self.skipTest("No required default attribute found")

		# Validation should throw without the required default
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {})

		# Validation should pass with the required default
		_validate_required_attributes(apartment, {required_attr: "value"})

	# ======================================================================
	# T16: get_available_attributes excludes used
	# ======================================================================

	def test_t16_available_excludes_used(self):
		from rental.rental.api.unit_settings import get_available_attributes
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")

		frappe.set_user(self.owner_a)
		# Create config with rooms
		frappe.get_doc({
			"doctype": "Account Unit Type Attribute",
			"rental_account": self.account_a,
			"unit_type": apartment,
			"attribute": rooms,
			"is_required": 0,
			"display_order": 0,
		}).insert(ignore_permissions=True)

		result = get_available_attributes(apartment)
		available = result["attributes"]
		available_names = [a["name"] for a in available]
		self.assertNotIn(rooms, available_names, "Used attribute should not be available")

	# ======================================================================
	# T17: get_available_attributes returns system only
	# ======================================================================

	def test_t17_available_returns_system_only(self):
		from rental.rental.api.unit_settings import get_available_attributes
		apartment = self._get_apartment()
		frappe.set_user(self.owner_a)
		result = get_available_attributes(apartment)
		for a in result["attributes"]:
			self.assertTrue(int(a.get("is_system") or 0), "Available should be system only")

	# ======================================================================
	# T18: Re-add a removed attribute
	# ======================================================================

	def test_t18_readd_removed_attribute(self):
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes, get_available_attributes,
			save_account_unit_type_attributes,
		)
		apartment = self._get_apartment()
		rooms = self._get_attr("rooms_count")
		elec = self._get_attr("electricity_meter")

		frappe.set_user(self.owner_a)
		# Save with both
		payload = json.dumps([
			{"attribute": rooms, "is_required": 0, "display_order": 0},
			{"attribute": elec, "is_required": 0, "display_order": 1},
		])
		save_account_unit_type_attributes(apartment, payload)

		# Remove rooms (save without it)
		payload2 = json.dumps([
			{"attribute": elec, "is_required": 0, "display_order": 0},
		])
		save_account_unit_type_attributes(apartment, payload2)

		# rooms should now be available
		result = get_available_attributes(apartment)
		available_names = [a["name"] for a in result["attributes"]]
		self.assertIn(rooms, available_names, "Removed attribute should be available for re-add")

		# Re-add rooms
		payload3 = json.dumps([
			{"attribute": elec, "is_required": 0, "display_order": 0},
			{"attribute": rooms, "is_required": 1, "display_order": 1},
		])
		save_account_unit_type_attributes(apartment, payload3)

		result_final = get_unit_type_attributes(apartment)
		codes = [a["attribute_code"] for a in result_final["attributes"]]
		self.assertIn("rooms_count", codes)
		self.assertIn("electricity_meter", codes)
