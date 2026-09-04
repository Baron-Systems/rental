"""Regression tests for create_unit / update_unit atomicity.

Verifies that when dynamic attribute validation or save fails, the
Rental Unit is NOT left partially created or updated.

Frappe wraps each HTTP request in a single database transaction:
  - On success: ``sync_database()`` commits.
  - On exception: ``handle_exception()`` calls ``db.rollback()``.

These tests prove that invariant holds for the Phase 7 code path
where native fields are saved first and ``save_unit_attribute_values``
runs afterwards.

Test methodology:
  Each test calls ``create_unit`` / ``update_unit`` and catches the
  exception.  It then calls ``frappe.db.rollback()`` to simulate
  Frappe's HTTP exception handler, and verifies that the Rental Unit
  was not partially created or updated.

  For Tests 1 and 2, ``save_unit_attribute_values`` is monkey-patched
  to raise ``ValidationError`` after the unit is saved.  This simulates
  any validation failure that could occur during attribute save
  (e.g. a future validation rule, a data type mismatch, etc.).

  For Test 3, the real capability removal protection is used.

  For Test 4, a successful mixed update verifies both native and
  dynamic values persist.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password

from rental.rental.api import property as property_api


class TestUnitAtomicity(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_types = []
		cls._created_attrs = []

		cls.owner = cls._create_test_user("atom_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Atomicity Test Account", cls.owner)

		# Cache system attribute names
		cls.elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				frappe.delete_doc("Rental Unit", name, force=True)
		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				frappe.delete_doc("Rental Building", name, force=True)
		# Delete types first (they reference attributes via child table)
		for name in cls._created_types:
			if frappe.db.exists("Unit Type", name):
				frappe.delete_doc("Unit Type", name, force=True)
		# Delete Unit Attribute Values that reference our attrs
		for name in cls._created_attrs:
			frappe.db.delete("Unit Attribute Value", {"attribute": name})
		# Delete Unit Type Attribute assignments that reference our attrs
		for name in cls._created_attrs:
			frappe.db.delete("Unit Type Attribute", {"attribute": name})
		for name in cls._created_attrs:
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
			"building_name": f"Atom Test Bldg {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_custom_type_with_required_attr(self):
		"""Create a custom Unit Type with a required Text attribute."""
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Required Atom {frappe.utils.random_string(4)}",
			"data_type": "Text",
			"is_system": 0,
			"rental_account": self.account,
		})
		attr.insert(ignore_permissions=True)
		self._created_attrs.append(attr.name)

		utype = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"Atom Type {frappe.utils.random_string(4)}",
			"is_system": 0,
			"rental_account": self.account,
			"attributes": [{"attribute": attr.name, "is_required": 1}],
		})
		utype.insert(ignore_permissions=True)
		self._created_types.append(utype.name)
		return utype.name, attr.name

	# ==================================================================
	# Test 1: update native field + attribute save failure
	#         → request fails, native field remains unchanged
	# ==================================================================
	def test_update_rolls_back_on_attribute_failure(self):
		"""If save_unit_attribute_values fails during update, the native
		field change (area) must be rolled back."""
		building = self._create_building()
		utype, req_attr = self._create_custom_type_with_required_attr()
		frappe.set_user(self.owner)

		# Create a unit with area=100
		unit_name = property_api.create_unit(
			building=building,
			unit_number=f"ATOM-UPD-{frappe.utils.random_string(4)}",
			unit_type=utype,
			area=100,
			attribute_values=json.dumps({req_attr: "initial value"}),
		)
		self._created_units.append(unit_name)
		frappe.db.commit()

		# Verify initial state
		self.assertEqual(frappe.db.get_value("Rental Unit", unit_name, "area"), 100)

		# Monkey-patch save_unit_attribute_values to raise after unit is saved
		original_save = property_api.save_unit_attribute_values

		def failing_save(*args, **kwargs):
			raise frappe.ValidationError("Simulated attribute validation failure")

		with patch.object(property_api, "save_unit_attribute_values", failing_save):
			with self.assertRaises(frappe.ValidationError):
				property_api.update_unit(
					name=unit_name,
					area=200,
					attribute_values=json.dumps({req_attr: "new value"}),
				)

		# Simulate Frappe's HTTP exception handler
		frappe.db.rollback()

		# After rollback, area must still be 100
		self.assertEqual(
			frappe.db.get_value("Rental Unit", unit_name, "area"),
			100,
			"Native field (area) must remain unchanged after attribute save failure",
		)

	# ==================================================================
	# Test 2: create unit + attribute save failure
	#         → request fails, Rental Unit does not remain in DB
	# ==================================================================
	def test_create_rolls_back_on_attribute_failure(self):
		"""If save_unit_attribute_values fails during create, the
		Rental Unit must not remain in the database."""
		building = self._create_building()
		utype, req_attr = self._create_custom_type_with_required_attr()
		frappe.set_user(self.owner)

		unit_number = f"ATOM-CRT-{frappe.utils.random_string(4)}"

		# Monkey-patch save_unit_attribute_values to raise after unit is inserted
		def failing_save(*args, **kwargs):
			raise frappe.ValidationError("Simulated attribute validation failure")

		with patch.object(property_api, "save_unit_attribute_values", failing_save):
			with self.assertRaises(frappe.ValidationError):
				property_api.create_unit(
					building=building,
					unit_number=unit_number,
					unit_type=utype,
					area=50,
					attribute_values=json.dumps({req_attr: "valid"}),
				)

		# Simulate Frappe's HTTP exception handler
		frappe.db.rollback()

		# The unit must NOT exist in the database
		self.assertFalse(
			frappe.db.exists("Rental Unit", {"building": building, "unit_number": unit_number}),
			"Rental Unit must not remain in DB after attribute save failure during create",
		)

	# ==================================================================
	# Test 3: capability removal rejected during update
	#         → other native changes in same request are rolled back
	# ==================================================================
	def test_capability_removal_rolls_back_native_changes(self):
		"""If capability removal protection rejects the attribute save,
		the native field change (area) in the same request must be
		rolled back."""
		building = self._create_building()
		frappe.set_user(self.owner)

		# Create a unit with electricity_meter enabled
		apartment_type = frappe.db.get_value(
			"Unit Type", {"code": "apartment", "is_system": 1}, "name"
		)
		unit_name = property_api.create_unit(
			building=building,
			unit_number=f"ATOM-CAP-{frappe.utils.random_string(4)}",
			unit_type=apartment_type,
			area=80,
			attribute_values=json.dumps({self.elec_attr: 1}),
		)
		self._created_units.append(unit_name)
		frappe.db.commit()

		# Verify initial state
		self.assertEqual(frappe.db.get_value("Rental Unit", unit_name, "area"), 80)

		# Monkey-patch has_blocking_metered_contract to simulate an active
		# metered contract that blocks capability removal
		from rental.rental.services import unit_capability_service
		original = unit_capability_service.has_blocking_metered_contract

		def mock_has_blocking(unit, due_type_code):
			if due_type_code == "electricity":
				return True
			return original(unit, due_type_code)

		with patch.object(
			unit_capability_service, "has_blocking_metered_contract", mock_has_blocking
		):
			# Attempt to change area to 999 AND disable electricity meter
			with self.assertRaises(frappe.ValidationError):
				property_api.update_unit(
					name=unit_name,
					area=999,
					attribute_values=json.dumps({self.elec_attr: 0}),
				)

		# Simulate Frappe's HTTP exception handler
		frappe.db.rollback()

		# After rollback, area must still be 80
		self.assertEqual(
			frappe.db.get_value("Rental Unit", unit_name, "area"),
			80,
			"Native field (area) must remain unchanged after capability removal rejection",
		)

	# ==================================================================
	# Test 4: successful mixed native + dynamic update
	#         → both persist
	# ==================================================================
	def test_successful_mixed_update_persists_both(self):
		"""A successful update with both native and dynamic fields
		must persist both."""
		building = self._create_building()
		utype, req_attr = self._create_custom_type_with_required_attr()
		frappe.set_user(self.owner)

		unit_name = property_api.create_unit(
			building=building,
			unit_number=f"ATOM-OK-{frappe.utils.random_string(4)}",
			unit_type=utype,
			area=120,
			attribute_values=json.dumps({req_attr: "hello"}),
		)
		self._created_units.append(unit_name)
		frappe.db.commit()

		# Verify initial state
		self.assertEqual(frappe.db.get_value("Rental Unit", unit_name, "area"), 120)
		attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit_name, "attribute": req_attr},
			"value_text",
		)
		self.assertEqual(attr_val, "hello")

		# Update both native and dynamic
		property_api.update_unit(
			name=unit_name,
			area=200,
			notes="Updated notes",
			attribute_values=json.dumps({req_attr: "world"}),
		)
		frappe.db.commit()

		# Both should persist
		self.assertEqual(frappe.db.get_value("Rental Unit", unit_name, "area"), 200)
		self.assertEqual(frappe.db.get_value("Rental Unit", unit_name, "notes"), "Updated notes")
		attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit_name, "attribute": req_attr},
			"value_text",
		)
		self.assertEqual(attr_val, "world")
