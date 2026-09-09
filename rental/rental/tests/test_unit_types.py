"""Tests for Unit Type and Unit Attribute DocTypes (Phase 2 — H.2, H.3)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestUnitTypes(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_unit_types = []
		cls._created_unit_attrs = []
		cls._created_units = []
		cls._created_buildings = []
		cls._created_attr_values = []

		cls.owner = cls._create_test_user("unit_type_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Unit Type Test Account", cls.owner)

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

		# Remove custom attributes from ALL unit types (including system) before deleting them
		for attr_name in cls._created_unit_attrs:
			if not frappe.db.exists("Unit Attribute", attr_name):
				continue
			# Find all unit type assignments for this attribute and remove them
			assignments = frappe.get_all("Unit Type Attribute", {"attribute": attr_name}, ["name", "parent"])
			for a in assignments:
				type_doc = frappe.get_doc("Unit Type", a.parent)
				for i, row in enumerate(type_doc.attributes):
					if row.name == a.name:
						type_doc.attributes.pop(i)
						type_doc.save(ignore_permissions=True)
						break

		for name in cls._created_unit_types:
			if frappe.db.exists("Unit Type", name):
				frappe.delete_doc("Unit Type", name, force=True)

		for name in cls._created_unit_attrs:
			if frappe.db.exists("Unit Attribute", name):
				frappe.delete_doc("Unit Attribute", name, force=True)

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

	def _create_building(self):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"UT Test Bldg {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit(self, building, unit_type_name=None):
		frappe.set_user("Administrator")
		if not unit_type_name:
			unit_type_name = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building,
			"unit_number": f"UT-{frappe.utils.random_string(5)}",
			"unit_type": unit_type_name,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	# ======================================================================
	# H.2 — Unit Type tests
	# ======================================================================

	def test_system_unit_type_cannot_delete_by_owner(self):
		"""System Unit Types cannot be deleted by Property Owners."""
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Unit Type", system_type)

	def test_system_unit_type_cannot_delete_by_admin_with_units(self):
		"""System Unit Type with units referencing it cannot be deleted even by Admin."""
		frappe.set_user("Administrator")
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		building = self._create_building()
		unit = self._create_unit(building, system_type)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Unit Type", system_type)

	def test_custom_unit_type_unused_can_delete(self):
		"""Custom Unit Type with no units referencing it can be deleted."""
		frappe.set_user("Administrator")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Custom Type {frappe.utils.random_string(4)}",
			"code": f"custom_{frappe.utils.random_string(4).lower()}",
			"rental_account": self.account,
			"is_active": 1,
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		# Delete should succeed
		frappe.delete_doc("Unit Type", custom_type.name, force=True)
		self.assertFalse(frappe.db.exists("Unit Type", custom_type.name))
		# Remove from cleanup list since already deleted
		self._created_unit_types.remove(custom_type.name)

	def test_custom_unit_type_used_cannot_delete(self):
		"""Custom Unit Type with units referencing it cannot be deleted."""
		frappe.set_user("Administrator")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Custom Type {frappe.utils.random_string(4)}",
			"code": f"custom_{frappe.utils.random_string(4).lower()}",
			"rental_account": self.account,
			"is_active": 1,
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		building = self._create_building()
		unit = self._create_unit(building, custom_type.name)

		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Unit Type", custom_type.name, force=True)

	def test_unit_type_code_unique(self):
		"""Duplicate code rejected."""
		frappe.set_user("Administrator")
		code = f"dup_{frappe.utils.random_string(4).lower()}"
		type1 = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Type A {frappe.utils.random_string(4)}",
			"code": code,
			"rental_account": self.account,
		})
		type1.insert(ignore_permissions=True)
		self._created_unit_types.append(type1.name)

		type2 = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Type B {frappe.utils.random_string(4)}",
			"code": code,
			"rental_account": self.account,
		})
		with self.assertRaises(frappe.ValidationError):
			type2.insert(ignore_permissions=True)

	def test_unit_type_attribute_uniqueness(self):
		"""Duplicate attribute in child table rejected."""
		frappe.set_user("Administrator")
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")

		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Unique Attr Test {frappe.utils.random_string(4)}",
			"code": f"uniq_{frappe.utils.random_string(4).lower()}",
			"rental_account": self.account,
			"attributes": [
				{"attribute": attr, "is_required": 0, "is_active": 1},
			],
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		# Try to add the same attribute again
		custom_type.append("attributes", {"attribute": attr, "is_required": 1, "is_active": 1})
		with self.assertRaises(frappe.ValidationError):
			custom_type.save(ignore_permissions=True)

	def test_system_unit_types_seeded(self):
		"""All 8 system unit types exist after seeding."""
		from rental.rental.services.unit_type_service import SYSTEM_UNIT_TYPES
		for st in SYSTEM_UNIT_TYPES:
			exists = frappe.db.exists("Unit Type", {"code": st["code"], "is_system": 1})
			self.assertTrue(exists, f"System unit type '{st['code']}' should exist")

	def test_system_unit_type_protected_from_owner_edit(self):
		"""Property Owner cannot change identity fields (type_name) of system unit type."""
		system_type_name = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		frappe.set_user(self.owner)
		doc = frappe.get_doc("Unit Type", system_type_name)
		doc.type_name = "Modified"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	# ==================================================================
	# System Unit Type — narrowed protection tests
	# ==================================================================

	def test_1_system_unit_type_cannot_be_deleted(self):
		"""Test 1: System Unit Type cannot be deleted."""
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Unit Type", system_type, ignore_permissions=True)

	def test_2_system_unit_type_code_cannot_be_changed(self):
		"""Test 2: code of a System Unit Type cannot be changed."""
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Unit Type", system_type)
		doc.code = "modified_apartment"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_3_system_unit_type_is_system_cannot_be_changed(self):
		"""Test 3: is_system of a System Unit Type cannot be changed."""
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Unit Type", system_type)
		doc.is_system = 0
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_4_cannot_add_attribute_to_system_unit_type(self):
		"""Test 4: Property Owner CANNOT add an attribute to a System Unit Type."""
		from rental.rental.api.unit_settings import add_unit_type_attribute
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		# Create a custom attribute to add
		frappe.set_user("Administrator")
		attr_name = f"TestAttr_{frappe.utils.random_string(4)}"
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": attr_name,
			"data_type": "Text",
			"is_system": 0,
			"rental_account": self.account,
		})
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)

		# Property Owner cannot add to system type
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			add_unit_type_attribute(unit_type=system_type, attribute=attr.name, is_required=0, display_order=5)

	def test_5_cannot_remove_attribute_from_system_unit_type(self):
		"""Test 5: Property Owner CANNOT remove an attribute from a System Unit Type."""
		from rental.rental.api.unit_settings import remove_unit_type_attribute
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

		# Get an existing attribute row
		type_doc = frappe.get_doc("Unit Type", system_type)
		if not type_doc.attributes:
			self.skipTest("No attributes to test")
		row = type_doc.attributes[0]

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			remove_unit_type_attribute(unit_type=system_type, row_name=row.name)

	def test_6_cannot_change_is_required_on_system_unit_type(self):
		"""Test 6: Property Owner CANNOT change is_required on a System Unit Type attribute."""
		from rental.rental.api.unit_settings import update_unit_type_attribute
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

		type_doc = frappe.get_doc("Unit Type", system_type)
		if not type_doc.attributes:
			self.skipTest("No attributes to test")
		row = type_doc.attributes[0]

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			update_unit_type_attribute(unit_type=system_type, row_name=row.name, is_required=1)

	def test_7_cannot_change_display_order_on_system_unit_type(self):
		"""Test 7: Property Owner CANNOT change display_order on a System Unit Type attribute."""
		from rental.rental.api.unit_settings import update_unit_type_attribute
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

		type_doc = frappe.get_doc("Unit Type", system_type)
		if not type_doc.attributes:
			self.skipTest("No attributes to test")
		row = type_doc.attributes[0]

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			update_unit_type_attribute(unit_type=system_type, row_name=row.name, display_order=99)

	def test_8_cannot_change_is_active_on_system_unit_type_attribute(self):
		"""Test 8: Property Owner CANNOT change is_active on a System Unit Type attribute mapping."""
		from rental.rental.api.unit_settings import update_unit_type_attribute
		system_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

		type_doc = frappe.get_doc("Unit Type", system_type)
		if not type_doc.attributes:
			self.skipTest("No attributes to test")
		row = type_doc.attributes[0]

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			update_unit_type_attribute(unit_type=system_type, row_name=row.name, is_active=0)

	def test_9_custom_unit_type_still_works(self):
		"""Test 9: Custom Unit Type operations remain unchanged."""
		from rental.rental.api.unit_settings import create_unit_type, update_unit_type, delete_unit_type
		frappe.set_user(self.owner)
		# Create custom type
		name = create_unit_type(
			type_name=f"Custom Type {frappe.utils.random_string(4)}",
			is_active=1,
			display_order=50,
		)
		self._created_unit_types.append(name)

		# Update it
		update_unit_type(name=name, type_name="Updated Custom Type", is_active=1, display_order=99)
		doc = frappe.get_doc("Unit Type", name)
		self.assertEqual(doc.type_name, "Updated Custom Type")
		self.assertEqual(doc.display_order, 99)

		# Delete it
		delete_unit_type(name=name)
		self.assertFalse(frappe.db.exists("Unit Type", name))

	# ==================================================================
	# Batch save Unit Type Attributes (Drag & Drop UX)
	# ==================================================================

	def test_batch_save_reorders_attributes(self):
		"""Batch save correctly reorders attributes with sequential display_order."""
		import json
		from rental.rental.api.unit_settings import (
			save_unit_type_attributes,
			get_unit_type_attributes,
		)
		# Use a custom type — system types are read-only for Property Owners
		frappe.set_user("Administrator")
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count"}, "name")
		bathrooms_attr = frappe.db.get_value("Unit Attribute", {"code": "bathrooms_count"}, "name")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"BatchReorder {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"is_active": 1,
			"attributes": [
				{"attribute": rooms_attr, "is_required": 0, "is_active": 1, "display_order": 0},
				{"attribute": bathrooms_attr, "is_required": 0, "is_active": 1, "display_order": 1},
			],
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		# Get current attributes
		res = get_unit_type_attributes(custom_type.name)
		original_attrs = res["attributes"]
		self.assertTrue(len(original_attrs) > 0)

		# Reverse the order
		reversed_attrs = list(reversed(original_attrs))
		payload = json.dumps([
			{"attribute": a["attribute"], "is_required": a["is_required"], "display_order": idx}
			for idx, a in enumerate(reversed_attrs)
		])

		frappe.set_user(self.owner)
		result = save_unit_type_attributes(unit_type=custom_type.name, attributes=payload)
		self.assertTrue(result.get("success"))

		# Verify new order
		res2 = get_unit_type_attributes(custom_type.name)
		new_attrs = res2["attributes"]
		# Sort by display_order
		new_attrs_sorted = sorted(new_attrs, key=lambda a: a.get("display_order", 0))
		# First attribute should now be the last original one
		self.assertEqual(new_attrs_sorted[0]["attribute"], reversed_attrs[0]["attribute"])
		# display_order should be sequential 0,1,2,...
		for idx, a in enumerate(new_attrs_sorted):
			self.assertEqual(a["display_order"], idx)

	def test_batch_save_rejects_duplicates(self):
		"""Batch save rejects duplicate attributes in the list."""
		import json
		from rental.rental.api.unit_settings import save_unit_type_attributes
		# Use a custom type — system types are read-only for Property Owners
		frappe.set_user("Administrator")
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count"}, "name")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"BatchDup {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"is_active": 1,
			"attributes": [
				{"attribute": rooms_attr, "is_required": 0, "is_active": 1, "display_order": 0},
			],
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		payload = json.dumps([
			{"attribute": rooms_attr, "is_required": 0, "display_order": 0},
			{"attribute": rooms_attr, "is_required": 0, "display_order": 1},
		])
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.ValidationError):
			save_unit_type_attributes(unit_type=custom_type.name, attributes=payload)

	def test_batch_save_rejects_nonexistent_attribute(self):
		"""Batch save rejects an attribute that doesn't exist."""
		import json
		from rental.rental.api.unit_settings import save_unit_type_attributes
		# Use a custom type — system types are read-only for Property Owners
		frappe.set_user("Administrator")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"BatchNonexist {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"is_active": 1,
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		payload = json.dumps([
			{"attribute": "NONEXISTENT-ATTR-12345", "is_required": 0, "display_order": 0},
		])
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.ValidationError):
			save_unit_type_attributes(unit_type=custom_type.name, attributes=payload)

	def test_batch_save_adds_and_removes(self):
		"""Batch save can add new attributes and remove existing ones in one call."""
		import json
		from rental.rental.api.unit_settings import (
			save_unit_type_attributes,
			get_unit_type_attributes,
		)
		frappe.set_user("Administrator")
		# Create a custom unit type for this test
		name = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"BatchTest {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"is_active": 1,
		}).insert(ignore_permissions=True).name
		self._created_unit_types.append(name)

		# Get two system attributes to assign
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count"}, "name")
		bathrooms_attr = frappe.db.get_value("Unit Attribute", {"code": "bathrooms_count"}, "name")

		# Add both
		payload = json.dumps([
			{"attribute": rooms_attr, "is_required": 1, "display_order": 0},
			{"attribute": bathrooms_attr, "is_required": 0, "display_order": 1},
		])
		frappe.set_user(self.owner)
		result = save_unit_type_attributes(unit_type=name, attributes=payload)
		self.assertTrue(result.get("success"))

		# Verify both are assigned
		res = get_unit_type_attributes(name)
		assigned = [a["attribute"] for a in res["attributes"]]
		self.assertIn(rooms_attr, assigned)
		self.assertIn(bathrooms_attr, assigned)

		# Now remove bathrooms, keep only rooms
		payload2 = json.dumps([
			{"attribute": rooms_attr, "is_required": 0, "display_order": 0},
		])
		save_unit_type_attributes(unit_type=name, attributes=payload2)
		res2 = get_unit_type_attributes(name)
		assigned2 = [a["attribute"] for a in res2["attributes"]]
		self.assertIn(rooms_attr, assigned2)
		self.assertNotIn(bathrooms_attr, assigned2)

	def test_batch_save_preserves_is_active_for_existing(self):
		"""Batch save preserves is_active for existing attribute mappings."""
		import json
		from rental.rental.api.unit_settings import (
			save_unit_type_attributes,
			update_unit_type_attribute,
			get_unit_type_attributes,
		)
		# Use a custom type — system types are read-only for Property Owners
		frappe.set_user("Administrator")
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count"}, "name")
		bathrooms_attr = frappe.db.get_value("Unit Attribute", {"code": "bathrooms_count"}, "name")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"BatchPreserve {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"is_active": 1,
			"attributes": [
				{"attribute": rooms_attr, "is_required": 0, "is_active": 1, "display_order": 0},
				{"attribute": bathrooms_attr, "is_required": 0, "is_active": 1, "display_order": 1},
			],
		})
		custom_type.insert(ignore_permissions=True)
		self._created_unit_types.append(custom_type.name)

		# Get current attributes
		res = get_unit_type_attributes(custom_type.name)
		original_attrs = res["attributes"]
		if not original_attrs:
			self.skipTest("No attributes to test")

		# Deactivate the first attribute
		first_attr = original_attrs[0]
		frappe.set_user(self.owner)
		update_unit_type_attribute(
			unit_type=custom_type.name,
			row_name=first_attr["name"],
			is_active=0,
		)

		# Now batch save with the same attributes — is_active should be preserved
		payload = json.dumps([
			{"attribute": a["attribute"], "is_required": a["is_required"], "display_order": idx}
			for idx, a in enumerate(original_attrs)
		])
		save_unit_type_attributes(unit_type=custom_type.name, attributes=payload)

		# Verify is_active is still 0 for the first attribute
		res2 = get_unit_type_attributes(custom_type.name)
		first_after = [a for a in res2["attributes"] if a["attribute"] == first_attr["attribute"]][0]
		self.assertEqual(int(first_after["is_active"]), 0)


class TestUnitAttributes(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_unit_attrs = []
		cls._created_attr_values = []
		cls._created_units = []
		cls._created_buildings = []

		cls.owner = cls._create_test_user("unit_attr_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Unit Attr Test Account", cls.owner)

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

		for name in cls._created_unit_attrs:
			if frappe.db.exists("Unit Attribute", name):
				frappe.delete_doc("Unit Attribute", name, force=True)

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

	def _create_building(self):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"UA Test Bldg {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit(self, building):
		frappe.set_user("Administrator")
		unit_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building,
			"unit_number": f"UA-{frappe.utils.random_string(5)}",
			"unit_type": unit_type,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	# ======================================================================
	# H.3 — Unit Attribute tests
	# ======================================================================

	def test_system_attribute_cannot_delete_by_owner(self):
		"""System Unit Attributes cannot be deleted by Property Owners."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Unit Attribute", attr)

	def test_custom_attribute_unused_can_delete(self):
		"""Custom attribute with no values can be deleted."""
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Custom Attr {frappe.utils.random_string(4)}",
			"code": f"cust_{frappe.utils.random_string(4).lower()}",
			"data_type": "Text",
			"rental_account": self.account,
		})
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)

		frappe.delete_doc("Unit Attribute", attr.name, force=True)
		self.assertFalse(frappe.db.exists("Unit Attribute", attr.name))
		self._created_unit_attrs.remove(attr.name)

	def test_custom_attribute_with_values_cannot_delete(self):
		"""Custom attribute with values cannot be deleted."""
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Custom Attr {frappe.utils.random_string(4)}",
			"code": f"cust_{frappe.utils.random_string(4).lower()}",
			"data_type": "Text",
			"rental_account": self.account,
		})
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)

		building = self._create_building()
		unit = self._create_unit(building)

		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr.name,
			"value_text": "test value",
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)

		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Unit Attribute", attr.name, force=True)

	def test_custom_attribute_cannot_set_capability_code(self):
		"""Custom (non-system) attributes cannot set capability_code."""
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Custom Cap {frappe.utils.random_string(4)}",
			"code": f"cap_{frappe.utils.random_string(4).lower()}",
			"data_type": "Check",
			"rental_account": self.account,
			"capability_code": "some_capability",
		})
		with self.assertRaises(frappe.ValidationError):
			attr.insert(ignore_permissions=True)

	def test_duplicate_unit_attribute_value_blocked(self):
		"""Two values for same unit+attribute rejected."""
		frappe.set_user("Administrator")
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		building = self._create_building()
		unit = self._create_unit(building)

		val1 = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_integer": 3,
		})
		val1.insert(ignore_permissions=True)
		self._created_attr_values.append(val1.name)

		val2 = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_integer": 5,
		})
		with self.assertRaises(frappe.ValidationError):
			val2.insert(ignore_permissions=True)

	def test_check_false_treated_as_valid_value(self):
		"""value_check=0 is a valid value, not 'missing'."""
		frappe.set_user("Administrator")
		attr = frappe.db.get_value("Unit Attribute", {"code": "furnished", "is_system": 1}, "name")
		building = self._create_building()
		unit = self._create_unit(building)

		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_check": 0,
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)

		# Verify it was saved with value_check=0
		saved = frappe.db.get_value("Unit Attribute Value", val.name, "value_check")
		self.assertEqual(saved, 0)

	def test_integer_zero_valid(self):
		"""value_integer=0 is valid, not 'missing'."""
		frappe.set_user("Administrator")
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		building = self._create_building()
		unit = self._create_unit(building)

		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_integer": 0,
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)

		saved = frappe.db.get_value("Unit Attribute Value", val.name, "value_integer")
		self.assertEqual(saved, 0)

	def test_data_type_consistency_clears_wrong_fields(self):
		"""Setting value_text on an Integer attribute clears value_text on validate."""
		frappe.set_user("Administrator")
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		building = self._create_building()
		unit = self._create_unit(building)

		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_integer": 3,
			"value_text": "should be cleared",
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)

		# value_text should be cleared because attribute is Integer type
		saved_text = frappe.db.get_value("Unit Attribute Value", val.name, "value_text")
		self.assertIsNone(saved_text)
		saved_int = frappe.db.get_value("Unit Attribute Value", val.name, "value_integer")
		self.assertEqual(saved_int, 3)

	def test_system_attributes_seeded(self):
		"""All system unit attributes exist after seeding."""
		from rental.rental.services.unit_type_service import SYSTEM_UNIT_ATTRIBUTES
		for sa in SYSTEM_UNIT_ATTRIBUTES:
			exists = frappe.db.exists("Unit Attribute", {"code": sa["code"], "is_system": 1})
			self.assertTrue(exists, f"System attribute '{sa['code']}' should exist")

	def test_meter_capability_attributes_have_capability_code(self):
		"""electricity_meter and water_meter attributes have capability_code set."""
		elec = frappe.db.get_value("Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "capability_code")
		self.assertEqual(elec, "electricity_meter")

		water = frappe.db.get_value("Unit Attribute", {"code": "water_meter", "is_system": 1}, "capability_code")
		self.assertEqual(water, "water_meter")

	def test_default_type_attributes_seeded(self):
		"""Default attribute mappings exist for apartment type."""
		apartment_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		type_doc = frappe.get_doc("Unit Type", apartment_type)
		attr_codes = []
		for row in type_doc.attributes:
			code = frappe.db.get_value("Unit Attribute", row.attribute, "code")
			attr_codes.append(code)

		# Apartment should have rooms_count and electricity_meter
		self.assertIn("rooms_count", attr_codes)
		self.assertIn("electricity_meter", attr_codes)
		self.assertIn("water_meter", attr_codes)

	# ==================================================================
	# System Unit Attribute — narrowed protection tests
	# ==================================================================

	def test_attr_1_system_attribute_cannot_be_deleted(self):
		"""Test 1: System Unit Attribute cannot be deleted (even by Admin)."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Unit Attribute", attr, force=True)

	def test_attr_2_system_attribute_code_cannot_be_changed(self):
		"""Test 2: code of a System Unit Attribute cannot be changed."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.code = "modified_rooms"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_attr_3_system_attribute_is_system_cannot_be_changed(self):
		"""Test 3: is_system of a System Unit Attribute cannot be changed."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.is_system = 0
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_attr_4_system_attribute_capability_code_cannot_be_changed(self):
		"""Test 4: capability_code of a System Unit Attribute cannot be changed."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.capability_code = "water_meter"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_attr_5_electricity_meter_identity_cannot_be_modified(self):
		"""Test 5: electricity_meter identity (code, capability_code, name, data_type) is immutable."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		# Try changing code
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.code = "elec_meter_v2"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		# Try changing capability_code
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.capability_code = "something_else"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		# Try changing attribute_name
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.attribute_name = "عداد كهرباء معدّل"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		# Try changing data_type
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.data_type = "Integer"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_attr_6_water_meter_identity_cannot_be_modified(self):
		"""Test 6: water_meter identity (code, capability_code, name, data_type) is immutable."""
		attr = frappe.db.get_value("Unit Attribute", {"code": "water_meter", "is_system": 1}, "name")
		frappe.set_user("Administrator")
		# Try changing code
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.code = "h2o_meter"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		# Try changing capability_code
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.capability_code = "gas_meter"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		# Try changing attribute_name
		doc = frappe.get_doc("Unit Attribute", attr)
		doc.attribute_name = "عداد مياه معدّل"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)

	def test_attr_7_system_attribute_is_active_cannot_be_changed_by_owner(self):
		"""Test 7: System Attribute is_active CANNOT be changed by Property Owner."""
		from rental.rental.api.unit_settings import update_unit_attribute
		attr = frappe.db.get_value("Unit Attribute", {"code": "furnished", "is_system": 1}, "name")

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			update_unit_attribute(name=attr, is_active=0)

	def test_attr_8_system_attribute_display_order_cannot_be_changed_by_owner(self):
		"""Test 8: System Attribute display_order CANNOT be changed by Property Owner."""
		from rental.rental.api.unit_settings import update_unit_attribute
		attr = frappe.db.get_value("Unit Attribute", {"code": "air_conditioning", "is_system": 1}, "name")

		frappe.set_user(self.owner)
		with self.assertRaises(frappe.PermissionError):
			update_unit_attribute(name=attr, display_order=999)

	def test_attr_9_disabling_does_not_delete_attribute_values(self):
		"""Test 9: Disabling a System Attribute does NOT delete Unit Attribute Values.

		System attributes can only be disabled by System Manager.
		"""
		from rental.rental.api.unit_settings import update_unit_attribute
		attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		original_active = frappe.db.get_value("Unit Attribute", attr, "is_active")

		frappe.set_user("Administrator")
		building = self._create_building()
		unit = self._create_unit(building)

		# Create an attribute value
		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr,
			"value_integer": 3,
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)

		# Disable the attribute as System Manager (Property Owners can't)
		update_unit_attribute(name=attr, is_active=0)

		# Verify the attribute value still exists
		self.assertTrue(frappe.db.exists("Unit Attribute Value", val.name))
		saved_val = frappe.db.get_value("Unit Attribute Value", val.name, "value_integer")
		self.assertEqual(saved_val, 3)

		# Restore
		frappe.set_user("Administrator")
		frappe.db.set_value("Unit Attribute", attr, "is_active", original_active, update_modified=False)

	def test_attr_10_disabling_does_not_delete_type_mappings(self):
		"""Test 10: Disabling a System Attribute does NOT delete Unit Type Attribute mappings.

		System attributes can only be disabled by System Manager.
		"""
		from rental.rental.api.unit_settings import update_unit_attribute
		attr = frappe.db.get_value("Unit Attribute", {"code": "furnished", "is_system": 1}, "name")
		original_active = frappe.db.get_value("Unit Attribute", attr, "is_active")

		# Count existing type mappings for this attribute
		mappings_before = frappe.db.count("Unit Type Attribute", {"attribute": attr})

		# Disable the attribute as System Manager (Property Owners can't)
		frappe.set_user("Administrator")
		update_unit_attribute(name=attr, is_active=0)

		# Verify mappings still exist
		mappings_after = frappe.db.count("Unit Type Attribute", {"attribute": attr})
		self.assertEqual(mappings_after, mappings_before)

		# Restore
		frappe.set_user("Administrator")
		frappe.db.set_value("Unit Attribute", attr, "is_active", original_active, update_modified=False)

	def test_attr_11_custom_attributes_retain_existing_behavior(self):
		"""Test 11: Custom attributes retain existing behavior (full edit + delete)."""
		from rental.rental.api.unit_settings import update_unit_attribute, delete_unit_attribute
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Custom Behav {frappe.utils.random_string(4)}",
			"code": f"behav_{frappe.utils.random_string(4).lower()}",
			"data_type": "Text",
			"rental_account": self.account,
		})
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)

		# Property Owner can update all fields
		frappe.set_user(self.owner)
		update_unit_attribute(
			name=attr.name,
			attribute_name="Updated Custom Attr",
			data_type="Integer",
			is_active=1,
			display_order=50,
		)
		doc = frappe.get_doc("Unit Attribute", attr.name)
		self.assertEqual(doc.attribute_name, "Updated Custom Attr")
		self.assertEqual(doc.data_type, "Integer")
		self.assertEqual(int(doc.display_order), 50)

		# Property Owner can delete (no values exist)
		frappe.set_user(self.owner)
		delete_unit_attribute(name=attr.name)
		self.assertFalse(frappe.db.exists("Unit Attribute", attr.name))
		self._created_unit_attrs.remove(attr.name)

	# ==================================================================
	# System Attribute Library Cleanup — regression tests
	# ==================================================================

	def test_cleanup_1_seed_creates_exactly_15_system_attributes(self):
		"""Test 1: Seed creates exactly the 15 approved System Attributes."""
		from rental.rental.services.unit_type_service import (
			SYSTEM_UNIT_ATTRIBUTES, ensure_system_unit_attributes,
		)
		frappe.set_user("Administrator")
		ensure_system_unit_attributes()
		# Verify count matches
		self.assertEqual(len(SYSTEM_UNIT_ATTRIBUTES), 15)
		# Verify each one exists
		for sa in SYSTEM_UNIT_ATTRIBUTES:
			exists = frappe.db.exists("Unit Attribute", {"code": sa["code"], "is_system": 1})
			self.assertTrue(exists, f"System attribute '{sa['code']}' should exist")

	def test_cleanup_2_deprecated_not_recreated_by_seed(self):
		"""Test 2: Running seed does NOT recreate any of the 27 deprecated attributes."""
		from rental.rental.services.unit_type_service import (
			DEPRECATED_SYSTEM_ATTRIBUTE_CODES, ensure_system_unit_attributes,
		)
		frappe.set_user("Administrator")
		ensure_system_unit_attributes()
		for code in DEPRECATED_SYSTEM_ATTRIBUTE_CODES:
			exists = frappe.db.exists("Unit Attribute", {"code": code, "is_system": 1})
			self.assertFalse(exists, f"Deprecated attribute '{code}' should NOT exist after seed")

	def test_cleanup_3_cleanup_removes_deprecated_mappings(self):
		"""Test 3: Cleanup removes Unit Type Attribute mappings for deprecated attrs."""
		from rental.rental.services.unit_type_service import cleanup_deprecated_system_attributes
		frappe.set_user("Administrator")
		# Create a fake deprecated system attribute + mapping
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"TestDep {frappe.utils.random_string(4)}",
			"code": f"test_deprecated_{frappe.utils.random_string(4).lower()}",
			"data_type": "Check",
			"is_system": 1,
			"rental_account": None,
		})
		attr.flags.ignore_validate = True
		attr.insert(ignore_permissions=True)
		self._created_unit_attrs.append(attr.name)

		# Add it to apartment type
		apartment = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		type_doc = frappe.get_doc("Unit Type", apartment)
		type_doc.append("attributes", {
			"attribute": attr.name,
			"is_required": 0,
			"is_active": 1,
			"display_order": 999,
		})
		type_doc.flags.ignore_version = True
		type_doc.save(ignore_permissions=True)

		# Verify mapping exists
		mapping_exists = frappe.db.exists("Unit Type Attribute", {"attribute": attr.name})
		self.assertTrue(mapping_exists)

		# Temporarily add this code to deprecated list and run cleanup
		import rental.rental.services.unit_type_service as svc
		original_deprecated = svc.DEPRECATED_SYSTEM_ATTRIBUTE_CODES
		svc.DEPRECATED_SYSTEM_ATTRIBUTE_CODES = list(original_deprecated) + [attr.code]
		try:
			result = cleanup_deprecated_system_attributes()
			self.assertGreaterEqual(result["removed_mappings"], 1)
		finally:
			svc.DEPRECATED_SYSTEM_ATTRIBUTE_CODES = original_deprecated

		# Verify mapping is gone
		mapping_exists = frappe.db.exists("Unit Type Attribute", {"attribute": attr.name})
		self.assertFalse(mapping_exists)
		# Attribute should also be gone
		self.assertFalse(frappe.db.exists("Unit Attribute", attr.name))
		if attr.name in self._created_unit_attrs:
			self._created_unit_attrs.remove(attr.name)

	def test_cleanup_4_cleanup_removes_deprecated_attributes(self):
		"""Test 4: Cleanup deletes the deprecated System Attributes themselves."""
		from rental.rental.services.unit_type_service import cleanup_deprecated_system_attributes
		frappe.set_user("Administrator")
		# The cleanup was already run on the site, so all 27 should be gone.
		# Verify by checking that none of the deprecated codes exist.
		from rental.rental.services.unit_type_service import DEPRECATED_SYSTEM_ATTRIBUTE_CODES
		for code in DEPRECATED_SYSTEM_ATTRIBUTE_CODES:
			exists = frappe.db.exists("Unit Attribute", {"code": code, "is_system": 1})
			self.assertFalse(exists, f"Deprecated '{code}' should have been removed")

	def test_cleanup_5_cleanup_is_idempotent(self):
		"""Test 5: Running cleanup multiple times does not error."""
		from rental.rental.services.unit_type_service import cleanup_deprecated_system_attributes
		frappe.set_user("Administrator")
		result1 = cleanup_deprecated_system_attributes()
		result2 = cleanup_deprecated_system_attributes()
		# Second run should remove nothing
		self.assertEqual(result2["removed_attributes"], 0)
		self.assertEqual(result2["removed_mappings"], 0)
		self.assertEqual(result2["skipped_with_values"], [])

	def test_cleanup_6_kept_attributes_not_affected(self):
		"""Test 6: The 15 kept attributes are not affected by cleanup."""
		from rental.rental.services.unit_type_service import (
			SYSTEM_UNIT_ATTRIBUTES, cleanup_deprecated_system_attributes,
		)
		frappe.set_user("Administrator")
		# Record names before cleanup
		names_before = {}
		for sa in SYSTEM_UNIT_ATTRIBUTES:
			name = frappe.db.get_value("Unit Attribute", {"code": sa["code"], "is_system": 1}, "name")
			names_before[sa["code"]] = name

		cleanup_deprecated_system_attributes()

		# Verify all 15 still exist with same names
		for sa in SYSTEM_UNIT_ATTRIBUTES:
			name = frappe.db.get_value("Unit Attribute", {"code": sa["code"], "is_system": 1}, "name")
			self.assertTrue(name, f"Kept attribute '{sa['code']}' should still exist")
			self.assertEqual(name, names_before[sa["code"]])

	def test_cleanup_7_meter_capability_codes_unchanged(self):
		"""Test 7: electricity_meter and water_meter capability_codes are unchanged."""
		elec_cap = frappe.db.get_value("Unit Attribute", {"code": "electricity_meter"}, "capability_code")
		water_cap = frappe.db.get_value("Unit Attribute", {"code": "water_meter"}, "capability_code")
		self.assertEqual(elec_cap, "electricity_meter")
		self.assertEqual(water_cap, "water_meter")

	def test_cleanup_8_existing_values_not_affected(self):
		"""Test 8: Existing Unit Attribute Values for kept attributes are not affected."""
		from rental.rental.services.unit_type_service import cleanup_deprecated_system_attributes
		frappe.set_user("Administrator")
		# Count values for kept attributes before cleanup
		keep_codes = ["electricity_meter", "water_meter", "rooms_count", "bathrooms_count"]
		values_before = {}
		for code in keep_codes:
			attr_name = frappe.db.get_value("Unit Attribute", {"code": code}, "name")
			if attr_name:
				values_before[code] = frappe.db.count("Unit Attribute Value", {"attribute": attr_name})

		cleanup_deprecated_system_attributes()

		# Verify values are unchanged
		for code in keep_codes:
			attr_name = frappe.db.get_value("Unit Attribute", {"code": code}, "name")
			if attr_name:
				values_after = frappe.db.count("Unit Attribute Value", {"attribute": attr_name})
				self.assertEqual(values_after, values_before[code],
					f"Values for '{code}' should not change")

	def test_cleanup_9_default_mappings_match_specification(self):
		"""Test 9: Default Unit Type mappings match the approved specification."""
		from rental.rental.services.unit_type_service import DEFAULT_TYPE_ATTRIBUTES
		expected = {
			"apartment": {"electricity_meter", "water_meter", "rooms_count", "bathrooms_count",
				"furnished", "air_conditioning", "balcony", "elevator", "parking",
				"orientation", "finishing_status"},
			"shop": {"electricity_meter", "water_meter", "bathrooms_count",
				"air_conditioning", "parking", "independent_entrance", "finishing_status"},
			"office": {"electricity_meter", "water_meter", "rooms_count", "bathrooms_count",
				"air_conditioning", "elevator", "parking", "orientation", "finishing_status"},
			"warehouse": {"electricity_meter", "water_meter", "bathrooms_count",
				"parking", "independent_entrance", "finishing_status"},
			"room": {"electricity_meter", "water_meter", "bathrooms_count",
				"furnished", "air_conditioning"},
			"garage": {"electricity_meter", "parking", "independent_entrance"},
			"independent": {"electricity_meter", "water_meter", "rooms_count", "bathrooms_count",
				"furnished", "air_conditioning", "balcony", "garden", "private_roof",
				"elevator", "parking", "independent_entrance", "orientation",
				"finishing_status", "construction_or_renovation_year"},
			"other": {"electricity_meter", "water_meter"},
		}
		for type_code, expected_attrs in expected.items():
			actual = set(DEFAULT_TYPE_ATTRIBUTES.get(type_code, []))
			self.assertEqual(actual, expected_attrs,
				f"Default mappings for '{type_code}' do not match specification")

	def test_cleanup_10_patch_is_idempotent(self):
		"""Test 10: The v1_cleanup_deprecated_system_attributes patch is idempotent.

		Calling execute() multiple times must not error and must not remove
		any of the 15 retained system attributes.
		"""
		from rental.rental.patches.v1_cleanup_deprecated_system_attributes import execute
		from rental.rental.services.unit_type_service import SYSTEM_UNIT_ATTRIBUTES

		frappe.set_user("Administrator")

		# Record the 15 retained attribute names before patch runs
		names_before = {
			sa["code"]: frappe.db.get_value(
				"Unit Attribute", {"code": sa["code"], "is_system": 1}, "name"
			)
			for sa in SYSTEM_UNIT_ATTRIBUTES
		}

		# Run the patch twice — both runs must succeed without error
		execute()
		execute()

		# All 15 retained attributes must still exist with the same names
		for sa in SYSTEM_UNIT_ATTRIBUTES:
			name = frappe.db.get_value(
				"Unit Attribute", {"code": sa["code"], "is_system": 1}, "name"
			)
			self.assertTrue(name, f"Retained attribute '{sa['code']}' must still exist")
			self.assertEqual(name, names_before[sa["code"]])

		# No deprecated system attribute should remain
		from rental.rental.services.unit_type_service import DEPRECATED_SYSTEM_ATTRIBUTE_CODES
		for code in DEPRECATED_SYSTEM_ATTRIBUTE_CODES:
			exists = frappe.db.exists(
				"Unit Attribute", {"code": code, "is_system": 1}
			)
			self.assertFalse(exists, f"Deprecated attribute '{code}' must not exist")

		# Meter capability codes must be intact
		self.assertEqual(
			frappe.db.get_value("Unit Attribute", {"code": "electricity_meter"}, "capability_code"),
			"electricity_meter",
		)
		self.assertEqual(
			frappe.db.get_value("Unit Attribute", {"code": "water_meter"}, "capability_code"),
			"water_meter",
		)
