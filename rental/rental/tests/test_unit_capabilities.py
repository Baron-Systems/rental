"""Tests for the unit capability helper (Phase 3 — H.4)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestUnitCapabilities(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_attr_values = []

		cls.owner = cls._create_test_user("cap_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Capability Test Account", cls.owner)

		# Cache attribute names
		cls.elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		cls.water_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "water_meter", "is_system": 1}, "name"
		)

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
			"building_name": f"Cap Test Bldg {frappe.utils.random_string(4)}",
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
			"unit_number": f"CAP-{frappe.utils.random_string(5)}",
			"unit_type": unit_type,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	def _set_capability(self, unit, attr_name, value=1):
		"""Create or update a Unit Attribute Value for a capability."""
		existing = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": attr_name,
		}, "name")
		if existing:
			frappe.db.set_value("Unit Attribute Value", existing, "value_check", value)
			return existing

		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr_name,
			"value_check": value,
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)
		return val.name

	# ======================================================================
	# H.4 — Capability tests
	# ======================================================================

	def test_unit_has_capability_true(self):
		"""value_check=1 → True."""
		from rental.rental.services.unit_capability_service import unit_has_capability
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		self.assertTrue(unit_has_capability(unit, "electricity_meter"))

	def test_unit_has_capability_false(self):
		"""value_check=0 → False."""
		from rental.rental.services.unit_capability_service import unit_has_capability
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 0)
		self.assertFalse(unit_has_capability(unit, "electricity_meter"))

	def test_unit_has_capability_no_value(self):
		"""No Unit Attribute Value → False."""
		from rental.rental.services.unit_capability_service import unit_has_capability
		building = self._create_building()
		unit = self._create_unit(building)
		# Don't set any capability value
		self.assertFalse(unit_has_capability(unit, "electricity_meter"))
		self.assertFalse(unit_has_capability(unit, "water_meter"))

	def test_unit_has_electricity_meter(self):
		"""Convenience function for electricity."""
		from rental.rental.services.unit_capability_service import unit_has_electricity_meter
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		self.assertTrue(unit_has_electricity_meter(unit))

	def test_unit_has_water_meter(self):
		"""Convenience function for water."""
		from rental.rental.services.unit_capability_service import unit_has_water_meter
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 1)
		self.assertTrue(unit_has_water_meter(unit))

	def test_reading_zero_does_not_affect_capability(self):
		"""current_reading='0' doesn't change capability."""
		from rental.rental.services.unit_capability_service import unit_has_electricity_meter
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)

		# Set meter reading to "0" — capability should still be True
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "0")
		self.assertTrue(unit_has_electricity_meter(unit))

		# Set meter reading to None — capability should still be True
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", None)
		self.assertTrue(unit_has_electricity_meter(unit))

	def test_meter_number_does_not_affect_capability(self):
		"""meter_number set doesn't change capability."""
		from rental.rental.services.unit_capability_service import unit_has_electricity_meter
		building = self._create_building()
		unit = self._create_unit(building)
		# No capability value set
		self.assertFalse(unit_has_electricity_meter(unit))

		# Set meter number — capability should still be False (no value_check=1)
		frappe.db.set_value("Rental Unit", unit, "electricity_meter_number", "E-12345")
		self.assertFalse(unit_has_electricity_meter(unit))

	def test_capability_check_does_not_depend_on_unit_type(self):
		"""Capability true even if type has no meter attribute mapped."""
		from rental.rental.services.unit_capability_service import unit_has_electricity_meter
		# Create a custom unit type WITHOUT electricity_meter in its attributes
		frappe.set_user("Administrator")
		custom_type = frappe.get_doc({
			"doctype": "Unit Type",
			"type_name": f"No Meter Type {frappe.utils.random_string(4)}",
			"code": f"no_meter_{frappe.utils.random_string(4).lower()}",
			"rental_account": self.account,
			"is_active": 1,
			"attributes": [],
		})
		custom_type.insert(ignore_permissions=True)

		building = self._create_building()
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building,
			"unit_number": f"NT-{frappe.utils.random_string(5)}",
			"unit_type": custom_type.name,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)

		# Set capability directly — should be True regardless of type mapping
		self._set_capability(unit.name, self.elec_attr, 1)
		self.assertTrue(unit_has_electricity_meter(unit.name))

		# Cleanup: delete unit first, then custom type
		unit_name = unit.name
		# Remove attr values for this unit
		frappe.db.delete("Unit Attribute Value", {"unit": unit_name})
		frappe.delete_doc("Rental Unit", unit_name, force=True)
		self._created_units.remove(unit_name)
		frappe.delete_doc("Unit Type", custom_type.name, force=True)

	def test_can_use_metered_for_electricity(self):
		"""can_use_metered_for_due_type maps electricity → electricity_meter."""
		from rental.rental.services.unit_capability_service import can_use_metered_for_due_type
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		self.assertTrue(can_use_metered_for_due_type(unit, "electricity"))

	def test_can_use_metered_for_water(self):
		"""can_use_metered_for_due_type maps water → water_meter."""
		from rental.rental.services.unit_capability_service import can_use_metered_for_due_type
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 1)
		self.assertTrue(can_use_metered_for_due_type(unit, "water"))

	def test_can_use_metered_false_for_non_metered_type(self):
		"""can_use_metered_for_due_type returns False for rent/custom types."""
		from rental.rental.services.unit_capability_service import can_use_metered_for_due_type
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		self.assertFalse(can_use_metered_for_due_type(unit, "rent"))
		self.assertFalse(can_use_metered_for_due_type(unit, "cleaning"))
		self.assertFalse(can_use_metered_for_due_type(unit, ""))

	def test_can_use_metered_false_without_capability(self):
		"""can_use_metered_for_due_type returns False when capability is 0."""
		from rental.rental.services.unit_capability_service import can_use_metered_for_due_type
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 0)
		self.assertFalse(can_use_metered_for_due_type(unit, "electricity"))

	def test_electricity_and_water_independent(self):
		"""Electricity capability and water capability are independent."""
		from rental.rental.services.unit_capability_service import (
			unit_has_electricity_meter, unit_has_water_meter,
			can_use_metered_for_due_type,
		)
		building = self._create_building()
		unit = self._create_unit(building)

		# Only electricity
		self._set_capability(unit, self.elec_attr, 1)
		self._set_capability(unit, self.water_attr, 0)

		self.assertTrue(unit_has_electricity_meter(unit))
		self.assertFalse(unit_has_water_meter(unit))
		self.assertTrue(can_use_metered_for_due_type(unit, "electricity"))
		self.assertFalse(can_use_metered_for_due_type(unit, "water"))


class TestBlockingMeteredContract(FrappeTestCase):
	"""Test has_blocking_metered_contract — the capability removal protection.

	Business rule: block removal ONLY when the unit has an approved metered
	contract that still depends on the capability:

	- current approved metered → BLOCK
	- future approved metered → BLOCK
	- draft → does NOT block
	- cancelled → does NOT block
	- evicted → does NOT block
	- expired → does NOT block
	- archived → does NOT block
	- electricity/water remain independent
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_tenants = []
		cls._created_contracts = []
		cls._created_attr_values = []
		cls._created_dues = []

		cls.owner = cls._create_test_user("block_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Blocking Test Account", cls.owner)
		cls._create_settings(cls.account)

		# Cache attribute and due type names
		cls.elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		cls.water_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "water_meter", "is_system": 1}, "name"
		)
		cls.elec_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "electricity", "is_system": 1}, "name"
		)
		cls.water_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "water", "is_system": 1}, "name"
		)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

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
				# Contracts in this system use status field, not docstatus.
				# Just try to delete; if it fails, force-delete via DB.
				try:
					frappe.delete_doc("Lease Contract", name, force=True)
				except Exception:
					frappe.db.delete("Lease Contract", name)

		for name in cls._created_attr_values:
			if frappe.db.exists("Unit Attribute Value", name):
				frappe.delete_doc("Unit Attribute Value", name, force=True)

		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				try:
					frappe.delete_doc("Rental Unit", name, force=True)
				except Exception:
					# Unit has usage records (contracts) that can't be fully deleted;
					# use direct DB delete to bypass on_trash validation
					frappe.db.delete("Rental Unit", name)

		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				try:
					frappe.delete_doc("Rental Building", name, force=True)
				except Exception:
					frappe.db.delete("Rental Building", name)

		for name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", name):
				try:
					frappe.delete_doc("Rental Tenant", name, force=True)
				except Exception:
					frappe.db.delete("Rental Tenant", name)

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

	@classmethod
	def _create_settings(cls, account):
		if frappe.db.exists("Rental Settings", {"rental_account": account}):
			return
		settings = frappe.get_doc({
			"doctype": "Rental Settings",
			"rental_account": account,
			"landlord_type": "person",
			"landlord_name": "Block Test Landlord",
			"landlord_id": "1234567890",
			"landlord_phone": "0555-123-456",
			"landlord_address": "Test Address, Test City",
			"currency": "JOD",
		})
		settings.insert(ignore_permissions=True)

	def _create_building(self):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"Block Test Bldg {frappe.utils.random_string(4)}",
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
			"unit_number": f"BLK-{frappe.utils.random_string(5)}",
			"unit_type": unit_type,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		# Set default meter capabilities for metered contract tests
		self._set_capability(unit.name, self.elec_attr, 1)
		self._set_capability(unit.name, self.water_attr, 1)
		# Set default meter readings
		frappe.db.set_value("Rental Unit", unit.name, "current_electricity_meter_reading", "1000")
		frappe.db.set_value("Rental Unit", unit.name, "current_water_meter_reading", "500")
		return unit.name

	def _create_tenant(self, name_suffix=None):
		frappe.set_user("Administrator")
		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"Block Tenant {name_suffix or frappe.utils.random_string(4)}",
			"phone": "1234567890",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)
		return tenant.name

	def _create_contract_draft(self, tenant, building, unit, start_date=None, end_date=None, rent=500):
		frappe.set_user("Administrator")
		if not start_date:
			start_date = frappe.utils.today()
		if not end_date:
			end_date = frappe.utils.add_days(frappe.utils.today(), 365)
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": start_date,
			"end_date": end_date,
			"rent_amount": rent,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
		})
		contract.insert(ignore_permissions=True)
		self._created_contracts.append(contract.name)
		return contract.name

	def _add_metered_charge(self, contract_name, due_type_name, opening_reading="1000"):
		"""Add a metered tenant charge to a draft contract via save_contract_charges."""
		from rental.rental.services.contract_charge_service import save_contract_charges
		contract = frappe.get_doc("Lease Contract", contract_name)
		charges = []
		for c in contract.contract_charges:
			charges.append({
				"due_type": c.due_type,
				"responsibility": c.responsibility,
				"payment_by": c.payment_by,
				"calculation_method": c.calculation_method,
				"amount": c.amount,
				"frequency": c.frequency,
				"first_due_date": c.first_due_date,
				"commitment_timing": c.commitment_timing,
				"last_period_handling": c.last_period_handling,
				"last_period_adjustment_amount": c.last_period_adjustment_amount,
				"opening_meter_reading": c.opening_meter_reading,
			})
		charges.append({
			"due_type": due_type_name,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": opening_reading,
		})
		save_contract_charges(contract, charges, self.account)
		contract.save(ignore_permissions=True)

	def _approve_contract(self, contract_name):
		from rental.rental.api.contract import approve_contract
		return approve_contract(contract_name, generate_dues=0)

	def _set_capability(self, unit, attr_name, value=1):
		existing = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": attr_name,
		}, "name")
		if existing:
			frappe.db.set_value("Unit Attribute Value", existing, "value_check", value)
			return existing
		val = frappe.get_doc({
			"doctype": "Unit Attribute Value",
			"rental_account": self.account,
			"unit": unit,
			"attribute": attr_name,
			"value_check": value,
		})
		val.insert(ignore_permissions=True)
		self._created_attr_values.append(val.name)
		return val.name

	def _create_approved_metered_contract(self, unit, due_type_name, start_date=None, end_date=None):
		"""Create a draft contract with a metered charge, then approve it."""
		building = frappe.db.get_value("Rental Unit", unit, "building")
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, due_type_name)
		self._approve_contract(contract)
		return contract

	# ======================================================================
	# H.4 — has_blocking_metered_contract test matrix
	# ======================================================================

	def test_1_current_approved_metered_blocks(self):
		"""Current approved metered contract → BLOCKS removal."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create an active contract (start=today, end=+365 days)
		self._create_approved_metered_contract(unit, self.elec_due_type)
		self.assertTrue(has_blocking_metered_contract(unit, "electricity"))

	def test_2_future_approved_metered_blocks(self):
		"""Future approved metered contract → BLOCKS removal."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create a future-dated active contract (start=+30 days, end=+395 days)
		future_start = frappe.utils.add_days(frappe.utils.today(), 30)
		future_end = frappe.utils.add_days(frappe.utils.today(), 395)
		self._create_approved_metered_contract(unit, self.elec_due_type, future_start, future_end)
		self.assertTrue(has_blocking_metered_contract(unit, "electricity"))

	def test_3_draft_metered_does_not_block(self):
		"""Draft metered contract → does NOT block."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create a draft contract with metered charge (not approved)
		building_name = frappe.db.get_value("Rental Unit", unit, "building")
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building_name, unit)
		self._add_metered_charge(contract, self.elec_due_type)
		# Contract is still draft
		self.assertEqual(frappe.db.get_value("Lease Contract", contract, "status"), "draft")
		self.assertFalse(has_blocking_metered_contract(unit, "electricity"))

	def test_4_cancelled_metered_does_not_block(self):
		"""Cancelled metered contract → does NOT block."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create and approve a metered contract, then cancel it
		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		# Cancel the contract by setting status directly
		# (approve_contract uses db.set_value for status, not docstatus submission)
		frappe.db.set_value("Lease Contract", contract, "status", "cancelled", update_modified=False)
		frappe.db.set_value("Lease Contract", contract, "cancelled_at", frappe.utils.now(), update_modified=False)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract, "status"), "cancelled")
		self.assertFalse(has_blocking_metered_contract(unit, "electricity"))

	def test_5_evicted_metered_does_not_block(self):
		"""Evicted metered contract → does NOT block."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create and approve a metered contract
		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		# Set status to evicted directly (simulating eviction)
		frappe.db.set_value("Lease Contract", contract, "status", "evicted", update_modified=False)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract, "status"), "evicted")
		self.assertFalse(has_blocking_metered_contract(unit, "electricity"))

	def test_6_expired_metered_does_not_block(self):
		"""Expired metered contract → does NOT block."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create and approve a metered contract
		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		# Set status to expired directly
		frappe.db.set_value("Lease Contract", contract, "status", "expired", update_modified=False)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract, "status"), "expired")
		self.assertFalse(has_blocking_metered_contract(unit, "electricity"))

	def test_7_archived_metered_does_not_block(self):
		"""Archived metered contract → does NOT block."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create and approve a metered contract
		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		# Expire it first, then archive it
		frappe.db.set_value("Lease Contract", contract, "status", "expired", update_modified=False)
		frappe.db.set_value("Lease Contract", contract, "is_archived", 1, update_modified=False)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract, "is_archived"), 1)
		self.assertFalse(has_blocking_metered_contract(unit, "electricity"))

	def test_8_electricity_water_independent(self):
		"""Electricity and water blocking are independent."""
		from rental.rental.services.unit_capability_service import has_blocking_metered_contract
		building = self._create_building()
		unit = self._create_unit(building)
		# Create an active electricity metered contract only
		self._create_approved_metered_contract(unit, self.elec_due_type)
		# Electricity should block
		self.assertTrue(has_blocking_metered_contract(unit, "electricity"))
		# Water should NOT block (no water metered contract)
		self.assertFalse(has_blocking_metered_contract(unit, "water"))
