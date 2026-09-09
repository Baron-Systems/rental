"""Tests for User Unit Preference (User-specific overrides for Unit Type Attributes)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestUserUnitPreference(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_pref_names = []
		cls._created_unit_types = []
		cls._created_unit_attrs = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_attr_values = []

		cls.owner_a = cls._create_test_user("pref_owner_a@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Preference Test Account A", cls.owner_a)

		cls.owner_b = cls._create_test_user("pref_owner_b@test.com", "Rental Property Owner")
		cls.account_b = cls._create_test_account("Preference Test Account B", cls.owner_b)

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

		for name in cls._created_unit_types:
			if frappe.db.exists("Unit Type", name):
				frappe.delete_doc("Unit Type", name, force=True)

		for name in cls._created_unit_attrs:
			if frappe.db.exists("Unit Attribute", name):
				frappe.delete_doc("Unit Attribute", name, force=True)

		for name in cls._created_pref_names:
			if frappe.db.exists("User Unit Preference", name):
				frappe.delete_doc("User Unit Preference", name, force=True)

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

	def _create_custom_attribute(self, name, account):
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": name,
			"code": f"custom_attr_{frappe.utils.random_string(4).lower()}",
			"data_type": "Text",
			"is_system": 0,
			"rental_account": account,
		})
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)
		return attr.name

	def _create_building(self, account):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": account,
			"building_name": f"Pref Test Bldg {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit(self, building, account, unit_type_name=None):
		frappe.set_user("Administrator")
		if not unit_type_name:
			unit_type_name = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building,
			"unit_number": f"PREF-{frappe.utils.random_string(5)}",
			"unit_type": unit_type_name,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	def _get_system_apartment_type(self):
		return frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

	def tearDown(self):
		"""Clean up User Unit Preference records between tests."""
		frappe.set_user("Administrator")
		for user in [self.owner_a, self.owner_b]:
			prefs = frappe.get_all("User Unit Preference", filters={"user": user}, pluck="name")
			for name in prefs:
				if frappe.db.exists("User Unit Preference", name):
					frappe.delete_doc("User Unit Preference", name, force=True)

	# ======================================================================
	# 1. No override → returns defaults
	# ======================================================================

	def test_no_override_returns_default(self):
		"""Without any User Unit Preference, get_unit_type_attributes returns defaults."""
		from rental.rental.api.unit_settings import get_unit_type_attributes

		frappe.set_user(self.owner_a)
		apartment = self._get_system_apartment_type()
		result = get_unit_type_attributes(apartment)
		attrs = result["attributes"]

		# All should have has_override=False
		for attr in attrs:
			self.assertFalse(attr.get("has_override"), f"Attribute {attr['attribute']} should not have override")

	# ======================================================================
	# 2. User A override does NOT affect User B
	# ======================================================================

	def test_user_a_override_does_not_affect_user_b(self):
		"""User A changes display_order; User B still sees defaults."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)

		apartment = self._get_system_apartment_type()

		# Step 1: User A saves a preference (reorder + make first attribute required)
		frappe.set_user(self.owner_a)
		result_before = get_unit_type_attributes(apartment)
		first_attr = result_before["attributes"][0]["attribute"]

		payload = [
			{
				"attribute": first_attr,
				"is_required": 1,
				"is_active": 1,
				"display_order": 99,
			},
		]
		save_user_unit_type_preferences(apartment, payload)

		# Step 2: User A sees the override
		result_a = get_unit_type_attributes(apartment)
		attr_a = [r for r in result_a["attributes"] if r["attribute"] == first_attr][0]
		self.assertTrue(attr_a["has_override"])
		self.assertEqual(attr_a["is_required"], 1)
		self.assertEqual(attr_a["display_order"], 99)

		# Step 3: User B sees defaults (no override)
		frappe.set_user(self.owner_b)
		result_b = get_unit_type_attributes(apartment)
		attr_b = [r for r in result_b["attributes"] if r["attribute"] == first_attr][0]
		self.assertFalse(attr_b["has_override"])
		self.assertEqual(attr_b["is_required"], 0)

		# Cleanup User A preference
		frappe.set_user("Administrator")
		pref_name = frappe.db.get_value(
			"User Unit Preference",
			{"user": self.owner_a, "unit_type": apartment, "attribute": first_attr},
			"name",
		)
		if pref_name:
			frappe.delete_doc("User Unit Preference", pref_name, force=True)

	# ======================================================================
	# 3. Reset preferences → return to defaults
	# ======================================================================

	def test_reset_preferences_returns_to_defaults(self):
		"""After creating an override and resetting, defaults are restored."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
			reset_user_unit_preferences,
		)
		from rental.rental.api.property import get_unit_type_attributes_for_unit

		apartment = self._get_system_apartment_type()

		frappe.set_user(self.owner_a)
		result_before = get_unit_type_attributes(apartment)
		first_attr = result_before["attributes"][0]["attribute"]

		# Create override: hide the attribute
		payload = [{"attribute": first_attr, "is_required": 0, "is_active": 0, "display_order": 0}]
		save_user_unit_type_preferences(apartment, payload)

		# Verify override exists (attribute hidden in unit form)
		result_for_unit = get_unit_type_attributes_for_unit(apartment)
		self.assertEqual(len([a for a in result_for_unit["attributes"] if a["attribute"] == first_attr]), 0)

		# Reset
		reset_user_unit_preferences(apartment)

		# Verify default restored (attribute visible again in unit form)
		result_reset = get_unit_type_attributes_for_unit(apartment)
		attr_reset = [a for a in result_reset["attributes"] if a["attribute"] == first_attr]
		self.assertEqual(len(attr_reset), 1)
		self.assertFalse(attr_reset[0]["has_override"])

	# ======================================================================
	# 4. is_required, is_active, display_order all work as overrides
	# ======================================================================

	def test_all_override_fields_work(self):
		"""is_required, is_active, and display_order are all overridden correctly."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)
		from rental.rental.api.property import get_unit_type_attributes_for_unit

		apartment = self._get_system_apartment_type()

		frappe.set_user(self.owner_a)
		result = get_unit_type_attributes(apartment)
		self.assertTrue(len(result["attributes"]) >= 2, "Need at least 2 attributes for this test")

		attr_1 = result["attributes"][0]["attribute"]
		attr_2 = result["attributes"][1]["attribute"]

		payload = [
			{"attribute": attr_1, "is_required": 1, "is_active": 1, "display_order": 5},
			{"attribute": attr_2, "is_required": 0, "is_active": 0, "display_order": 1},
		]
		save_user_unit_type_preferences(apartment, payload)

		# Check settings API (returns all, including inactive)
		result_after = get_unit_type_attributes(apartment)
		a1 = [a for a in result_after["attributes"] if a["attribute"] == attr_1][0]
		a2 = [a for a in result_after["attributes"] if a["attribute"] == attr_2][0]

		self.assertTrue(a1["has_override"])
		self.assertEqual(a1["is_required"], 1)
		self.assertEqual(a1["display_order"], 5)

		self.assertTrue(a2["has_override"])
		self.assertEqual(a2["is_active"], 0)

		# Check property API (filters out inactive)
		result_for_unit = get_unit_type_attributes_for_unit(apartment)
		a2_for_unit = [a for a in result_for_unit["attributes"] if a["attribute"] == attr_2]
		self.assertEqual(len(a2_for_unit), 0, "Inactive attribute should be hidden in unit form")

	# ======================================================================
	# 5. Unit creation uses user-specific required attribute validation
	# ======================================================================

	def test_validate_required_attributes_uses_user_override(self):
		"""If User A makes an attribute non-required via override, unit creation succeeds without it."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)
		from rental.rental.api.property import _validate_required_attributes

		apartment = self._get_system_apartment_type()

		frappe.set_user(self.owner_a)
		result = get_unit_type_attributes(apartment)
		# Find an attribute that is required by default
		required_attr = None
		for a in result["attributes"]:
			if a["is_required"]:
				required_attr = a["attribute"]
				break

		if not required_attr:
			self.skipTest("No required attribute found in default apartment type")

		# Override: make it non-required
		payload = [{"attribute": required_attr, "is_required": 0, "is_active": 1, "display_order": 0}]
		save_user_unit_type_preferences(apartment, payload)

		# Validation should NOT throw even without the attribute value
		try:
			_validate_required_attributes(apartment, {})
		except frappe.ValidationError:
			self.fail("Validation should not raise when required attribute is overridden to non-required")

	# ======================================================================
	# 6. Cannot create preference for unassigned attribute
	# ======================================================================

	def test_cannot_override_unassigned_attribute(self):
		"""Creating a User Unit Preference for an attribute not in the Unit Type is blocked."""
		from rental.rental.api.unit_settings import save_user_unit_type_preferences

		apartment = self._get_system_apartment_type()
		# Create a custom attribute but do NOT add it to the apartment type
		custom_attr = self._create_custom_attribute("UnassignedAttr", self.account_a)

		frappe.set_user(self.owner_a)
		payload = [{"attribute": custom_attr, "is_required": 0, "is_active": 1, "display_order": 0}]

		with self.assertRaises(frappe.ValidationError):
			save_user_unit_type_preferences(apartment, payload)

	# ======================================================================
	# 7. Custom Unit Type supports overrides
	# ======================================================================

	def test_custom_unit_type_override(self):
		"""Overrides work on custom unit types too."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)

		frappe.set_user("Administrator")
		# Create a custom unit type with one custom attribute
		custom_attr = self._create_custom_attribute("CustomForType", self.account_a)
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Custom Override Type {frappe.utils.random_string(4)}",
			"code": f"custom_ov_{frappe.utils.random_string(4).lower()}",
			"rental_account": self.account_a,
			"is_active": 1,
			"attributes": [
				{"attribute": custom_attr, "is_required": 0, "is_active": 1, "display_order": 0},
			],
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		frappe.set_user(self.owner_a)
		# Verify default
		result_default = get_unit_type_attributes(custom_type.name)
		self.assertEqual(len(result_default["attributes"]), 1)
		self.assertEqual(result_default["attributes"][0]["is_required"], 0)
		self.assertFalse(result_default["attributes"][0]["has_override"])

		# Override: make required
		payload = [{"attribute": custom_attr, "is_required": 1, "is_active": 1, "display_order": 0}]
		save_user_unit_type_preferences(custom_type.name, payload)

		result_override = get_unit_type_attributes(custom_type.name)
		self.assertEqual(result_override["attributes"][0]["is_required"], 1)
		self.assertTrue(result_override["attributes"][0]["has_override"])

	# ======================================================================
	# 8. get_unit_type_attributes_for_unit respects user override
	# ======================================================================

	def test_get_unit_type_attributes_for_unit_respects_override(self):
		"""The property API also merges user preferences."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)
		from rental.rental.api.property import get_unit_type_attributes_for_unit

		apartment = self._get_system_apartment_type()

		frappe.set_user(self.owner_a)
		result = get_unit_type_attributes(apartment)
		first_attr = result["attributes"][0]["attribute"]

		# Override: hide it
		payload = [{"attribute": first_attr, "is_required": 0, "is_active": 0, "display_order": 0}]
		save_user_unit_type_preferences(apartment, payload)

		result_for_unit = get_unit_type_attributes_for_unit(apartment)
		found = [a for a in result_for_unit["attributes"] if a["attribute"] == first_attr]
		self.assertEqual(len(found), 0, "Hidden attribute should not appear in get_unit_type_attributes_for_unit")

	# ======================================================================
	# 9. System Unit Type cannot be modified by Rental Property Owner
	# ======================================================================

	def test_system_unit_type_cannot_be_modified_by_owner(self):
		"""Rental Property Owner cannot change is_active or display_order on system Unit Types."""
		from rental.rental.api.unit_settings import update_unit_type

		apartment = self._get_system_apartment_type()

		frappe.set_user(self.owner_a)
		with self.assertRaises(frappe.PermissionError):
			update_unit_type(apartment, is_active=0)
		with self.assertRaises(frappe.PermissionError):
			update_unit_type(apartment, display_order=99)

	# ======================================================================
	# 10. System Unit Attribute cannot be modified by Rental Property Owner
	# ======================================================================

	def test_system_unit_attribute_cannot_be_modified_by_owner(self):
		"""Rental Property Owner cannot change is_active or display_order on system Unit Attributes."""
		from rental.rental.api.unit_settings import update_unit_attribute

		elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		self.assertTrue(elec_attr, "System electricity_meter attribute should exist")

		frappe.set_user(self.owner_a)
		with self.assertRaises(frappe.PermissionError):
			update_unit_attribute(elec_attr, is_active=0)
		with self.assertRaises(frappe.PermissionError):
			update_unit_attribute(elec_attr, display_order=99)

	# ======================================================================
	# 11. System Unit Type child table cannot be modified by Rental Property Owner
	# ======================================================================

	def test_system_unit_type_attribute_endpoints_blocked(self):
		"""add/update/remove/save_unit_type_attributes are blocked on system types for owners."""
		from rental.rental.api.unit_settings import (
			add_unit_type_attribute,
			update_unit_type_attribute,
			remove_unit_type_attribute,
			save_unit_type_attributes,
		)

		apartment = self._get_system_apartment_type()
		elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)

		frappe.set_user(self.owner_a)
		# add
		with self.assertRaises(frappe.PermissionError):
			add_unit_type_attribute(apartment, elec_attr)
		# save (batch)
		with self.assertRaises(frappe.PermissionError):
			save_unit_type_attributes(apartment, [{"attribute": elec_attr, "is_required": 0}])

		# update/remove need a valid row_name — just verify they throw PermissionError
		# before reaching the row lookup
		with self.assertRaises(frappe.PermissionError):
			update_unit_type_attribute(apartment, "fake_row", is_active=0)
		with self.assertRaises(frappe.PermissionError):
			remove_unit_type_attribute(apartment, "fake_row")

	# ======================================================================
	# 12. User Unit Preference is scoped by rental_account + user
	# ======================================================================

	def test_preference_isolated_by_account(self):
		"""User A's preference in Account A is not visible to User B in Account B."""
		from rental.rental.api.unit_settings import (
			get_unit_type_attributes,
			save_user_unit_type_preferences,
		)

		apartment = self._get_system_apartment_type()

		# User A saves a preference
		frappe.set_user(self.owner_a)
		result_before = get_unit_type_attributes(apartment)
		first_attr = result_before["attributes"][0]["attribute"]
		payload = [{"attribute": first_attr, "is_required": 1, "is_active": 1, "display_order": 50}]
		save_user_unit_type_preferences(apartment, payload)

		# Verify the preference record has rental_account set
		pref = frappe.db.get_value(
			"User Unit Preference",
			{"user": self.owner_a, "unit_type": apartment, "attribute": first_attr},
			["rental_account", "is_required", "display_order"],
			as_dict=True,
		)
		self.assertIsNotNone(pref, "Preference should exist")
		self.assertEqual(pref.rental_account, self.account_a, "Preference should be scoped to account_a")
		self.assertEqual(pref.is_required, 1)
		self.assertEqual(pref.display_order, 50)

		# User B does NOT see User A's override
		frappe.set_user(self.owner_b)
		result_b = get_unit_type_attributes(apartment)
		attr_b = [r for r in result_b["attributes"] if r["attribute"] == first_attr][0]
		self.assertFalse(attr_b["has_override"], "User B should not see User A's override")

		# User B cannot query User A's preference via DB (permission_query_conditions)
		# frappe.get_list applies permission_query_conditions (unlike frappe.get_all)
		frappe.set_user(self.owner_b)
		prefs_visible = frappe.get_list(
			"User Unit Preference",
			filters={"unit_type": apartment, "attribute": first_attr},
			fields=["user", "rental_account"],
		)
		for p in prefs_visible:
			self.assertNotEqual(p["user"], self.owner_a, "User B should not see User A's preference records")
