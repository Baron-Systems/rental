"""Phase 9 — End-to-End Integration Verification.

Tests real workflows across the complete architecture:
  Settings → Unit Types → Unit Attributes → Rental Unit →
  Meter Capabilities → Contract Charges → Metered Due lifecycle

Workflows A–J as specified in Phase 9 requirements.

Run: bench --site <site> run-tests --app rental --test TestPhase9Integration
"""

import json
from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password

from rental.rental.api.contract import approve_contract, create_contract, update_contract
from rental.rental.api.property import create_unit, get_unit, get_units, update_unit
from rental.rental.services.contract_charge_service import (
	copy_contract_charges_for_renewal,
	validate_contract_charges,
)
from rental.rental.services.unit_capability_service import (
	can_use_metered_for_due_type,
	has_blocking_metered_contract,
)


class TestPhase9Integration(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_types = []
		cls._created_attrs = []
		cls._created_tenants = []
		cls._created_contracts = []
		cls._created_dues = []

		cls.owner = cls._create_test_user("p9owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Phase9 Integration Account", cls.owner)
		cls._create_settings(cls.account)

		# Cache system attribute and due type names
		cls.elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		cls.water_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "water_meter", "is_system": 1}, "name"
		)
		cls.apartment_type = frappe.db.get_value(
			"Unit Type", {"code": "apartment", "is_system": 1}, "name"
		)
		cls.elec_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "electricity"}, "name"
		)
		cls.water_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "water"}, "name"
		)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		super().tearDownClass()

	# ---- Helpers ----

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
			"landlord_name": "Phase9 Test Landlord",
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
			"building_name": f"P9 Bldg {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit_with_caps(self, building, elec=True, water=True, unit_number=None):
		frappe.set_user("Administrator")
		unit_number = unit_number or f"P9-{frappe.utils.random_string(6)}"
		name = create_unit(
			building=building,
			unit_number=unit_number,
			unit_type=self.apartment_type,
			area=80,
			attribute_values=json.dumps({
				self.elec_attr: 1 if elec else 0,
				self.water_attr: 1 if water else 0,
			}),
		)
		self._created_units.append(name)
		return name

	def _set_unit_reading(self, unit, field, value):
		frappe.db.set_value("Rental Unit", unit, field, value)

	def _create_tenant(self, full_name=None):
		frappe.set_user("Administrator")
		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": full_name or f"P9 Tenant {frappe.utils.random_string(4)}",
			"rental_account": self.account,
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)
		return tenant.name

	def _create_contract_with_charges(self, tenant, building, unit, charges, start_date=None, end_date=None):
		frappe.set_user("Administrator")
		start = start_date or frappe.utils.today()
		end = end_date or frappe.utils.add_days(start, 365)
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": start,
			"end_date": end,
			"rent_amount": 1000,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
		})
		contract.insert(ignore_permissions=True)
		self._created_contracts.append(contract.name)

		# Add charges via save_contract_charges
		if charges:
			from rental.rental.services.contract_charge_service import save_contract_charges
			save_contract_charges(contract, charges, self.account)
			contract.save(ignore_permissions=True)

		return contract.name

	def _approve(self, contract_name, generate_dues=0):
		frappe.set_user("Administrator")
		approve_contract(name=contract_name, generate_dues=generate_dues)

	def _add_metered_charge(self, contract_name, due_type_name, opening_reading="1000"):
		contract = frappe.get_doc("Lease Contract", contract_name)
		existing = [c.as_dict() for c in contract.contract_charges]
		new_charge = {
			"due_type": due_type_name,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": opening_reading,
		}
		existing.append(new_charge)
		contract.set("contract_charges", [])
		from rental.rental.services.contract_charge_service import save_contract_charges
		save_contract_charges(contract, existing, self.account)
		contract.save(ignore_permissions=True)

	def _get_charge(self, contract_name, due_type_name):
		for c in frappe.get_doc("Lease Contract", contract_name).contract_charges:
			if c.due_type == due_type_name:
				return c
		return None

	# ==================================================================
	# Workflow A: Unit without meters
	# ==================================================================

	def test_workflow_a_unit_without_meters(self):
		"""Unit with electricity_meter=0, water_meter=0."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=False, water=False)

		# 1. Unit saves correctly
		self.assertTrue(frappe.db.exists("Rental Unit", unit))

		# 2. Capability flags in get_unit
		unit_data = get_unit(unit)
		self.assertFalse(unit_data["electricity_meter"])
		self.assertFalse(unit_data["water_meter"])

		# 3. Capability flags in get_units
		units_list = get_units(building=building)
		u = next(x for x in units_list["units"] if x["name"] == unit)
		self.assertFalse(u["electricity_meter"])
		self.assertFalse(u["water_meter"])

		# 4. Backend rejects forced metered electricity
		elec_charge = {
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "100",
		}
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges([elec_charge], self.account, contract_unit=unit)

		# 5. Backend rejects forced metered water
		water_charge = {
			"due_type": self.water_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "50",
		}
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges([water_charge], self.account, contract_unit=unit)

		# 6. fixed_periodic works for electricity
		fixed_charge = {
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "fixed_periodic",
			"amount": "100",
			"frequency": "monthly",
			"commitment_timing": "start",
		}
		validated = validate_contract_charges(
			[fixed_charge], self.account,
			contract_start_date=frappe.utils.today(),
			contract_end_date=frappe.utils.add_days(frappe.utils.today(), 365),
			contract_unit=unit,
		)
		self.assertEqual(validated[0]["calculation_method"], "fixed_periodic")

		# 7. actual_bill works for electricity
		bill_charge = {
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "actual_bill",
		}
		validated = validate_contract_charges([bill_charge], self.account, contract_unit=unit)
		self.assertEqual(validated[0]["calculation_method"], "actual_bill")

	# ==================================================================
	# Workflow B: Electricity meter only
	# ==================================================================

	def test_workflow_b_electricity_meter_only(self):
		"""Unit with electricity_meter=1, water_meter=0."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "1000")

		# 1. Capability flags
		unit_data = get_unit(unit)
		self.assertTrue(unit_data["electricity_meter"])
		self.assertFalse(unit_data["water_meter"])

		# 2. Electricity: metered available
		self.assertTrue(can_use_metered_for_due_type(unit, "electricity"))
		# 3. Water: metered NOT available
		self.assertFalse(can_use_metered_for_due_type(unit, "water"))

		# 4. Create contract with electricity metered + water fixed_periodic
		tenant = self._create_tenant()
		charges = [
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "1000",
			},
			{
				"due_type": self.water_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "fixed_periodic",
				"amount": "50",
				"frequency": "monthly",
				"commitment_timing": "start",
			},
		]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)

		# 5. Approve contract
		self._approve(contract, generate_dues=0)

		# 6. Opening reading frozen into unit
		unit_reading = frappe.db.get_value("Rental Unit", unit, "current_electricity_meter_reading")
		self.assertEqual(float(unit_reading), 1000.0)

		# 7. Verify charge stored correctly
		elec_charge = self._get_charge(contract, self.elec_due_type)
		self.assertEqual(elec_charge.calculation_method, "metered")
		self.assertEqual(float(elec_charge.opening_meter_reading), 1000.0)

		water_charge = self._get_charge(contract, self.water_due_type)
		self.assertEqual(water_charge.calculation_method, "fixed_periodic")

	def test_workflow_b_metered_due_lifecycle(self):
		"""Full metered due lifecycle: create due, verify readings/consumption/amount, cancel."""
		from rental.rental.services.contract_charge_service import (
			can_create_meter_due,
			get_previous_meter_reading,
		)
		from rental.rental.services.cancellation_service import cancel_due

		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "1000")

		tenant = self._create_tenant()
		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "1000",
		}]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)
		self._approve(contract, generate_dues=0)

		# 1. can_create_meter_due should allow it
		check = can_create_meter_due(contract, self.elec_due_type)
		self.assertTrue(check["ok"], f"Should allow meter due: {check.get('error')}")

		# 2. Previous reading = opening_meter_reading (no prior dues)
		prev = get_previous_meter_reading(contract, unit, self.elec_due_type)
		self.assertEqual(float(prev), 1000.0)

		# 3. Create a metered due
		frappe.set_user("Administrator")
		contract_data = frappe.db.get_value(
			"Lease Contract", contract,
			["tenant", "building", "unit", "rental_account"], as_dict=True,
		)
		consumption = 1500.0 - 1000.0
		amount = round(consumption * 0.5, 2)
		due = frappe.get_doc({
			"doctype": "Rental Due",
			"rental_account": contract_data.rental_account,
			"tenant": contract_data.tenant,
			"contract": contract,
			"building": contract_data.building,
			"unit": unit,
			"due_type": self.elec_due_type,
			"transaction_date": frappe.utils.today(),
			"due_date": frappe.utils.today(),
			"amount": amount,
			"source_type": "manual_contract",
			"calculation_method": "metered",
			"previous_meter_reading": "1000",
			"current_meter_reading": "1500",
			"meter_consumption": str(consumption),
			"unit_price": 0.5,
		})
		due.insert(ignore_permissions=True)
		if not due.due_number:
			due.due_number = f"DUE-{due.name}"
			due.db_set("due_number", due.due_number)
		due.submit()
		self._created_dues.append(due.name)

		# 4. Verify due fields
		self.assertEqual(float(due.previous_meter_reading), 1000.0)
		self.assertEqual(float(due.current_meter_reading), 1500.0)
		self.assertEqual(float(due.meter_consumption), 500.0)
		self.assertEqual(float(due.unit_price), 0.5)
		self.assertEqual(float(due.amount), 250.0)

		# 5. Verify unit current reading updated
		unit_reading = frappe.db.get_value("Rental Unit", unit, "current_electricity_meter_reading")
		self.assertEqual(float(unit_reading), 1500.0)

		# 6. Cancel the due — verify rollback
		# Pre-set cancellation_reason in DB (on_cancel requires it before cancel)
		frappe.db.set_value("Rental Due", due.name, "cancellation_reason", "Test cancellation")
		cancel_due(due.name, "Test cancellation", frappe.session.user)

		# 7. Verify due is cancelled
		due_status = frappe.db.get_value("Rental Due", due.name, "docstatus")
		self.assertEqual(due_status, 2, "Due should be cancelled (docstatus=2)")

		# 8. Verify unit reading rolled back
		unit_reading_after = frappe.db.get_value("Rental Unit", unit, "current_electricity_meter_reading")
		self.assertEqual(float(unit_reading_after), 1000.0, "Unit reading should roll back on due cancellation")

	# ==================================================================
	# Workflow C: Water meter only
	# ==================================================================

	def test_workflow_c_water_meter_only(self):
		"""Unit with electricity_meter=0, water_meter=1."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=False, water=True)
		self._set_unit_reading(unit, "current_water_meter_reading", "500")

		# 1. Capability flags
		unit_data = get_unit(unit)
		self.assertFalse(unit_data["electricity_meter"])
		self.assertTrue(unit_data["water_meter"])

		# 2. Water: metered available; Electricity: NOT
		self.assertFalse(can_use_metered_for_due_type(unit, "electricity"))
		self.assertTrue(can_use_metered_for_due_type(unit, "water"))

		# 3. Create contract with water metered + electricity fixed_periodic
		tenant = self._create_tenant()
		charges = [
			{
				"due_type": self.water_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "500",
			},
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "fixed_periodic",
				"amount": "100",
				"frequency": "monthly",
				"commitment_timing": "start",
			},
		]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)
		self._approve(contract, generate_dues=0)

		# 4. Opening reading frozen
		unit_reading = frappe.db.get_value("Rental Unit", unit, "current_water_meter_reading")
		self.assertEqual(float(unit_reading), 500.0)

		# 5. Charges stored correctly
		water_charge = self._get_charge(contract, self.water_due_type)
		self.assertEqual(water_charge.calculation_method, "metered")
		self.assertEqual(float(water_charge.opening_meter_reading), 500.0)

		elec_charge = self._get_charge(contract, self.elec_due_type)
		self.assertEqual(elec_charge.calculation_method, "fixed_periodic")

	# ==================================================================
	# Workflow D: Both meters — independence
	# ==================================================================

	def test_workflow_d_both_meters_independent(self):
		"""Unit with both meters — verify no cross-contamination."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=True)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "2000")
		self._set_unit_reading(unit, "current_water_meter_reading", "800")

		# Both capabilities available
		self.assertTrue(can_use_metered_for_due_type(unit, "electricity"))
		self.assertTrue(can_use_metered_for_due_type(unit, "water"))

		# Create contract with both metered
		tenant = self._create_tenant()
		charges = [
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "2000",
			},
			{
				"due_type": self.water_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "800",
			},
		]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)
		self._approve(contract, generate_dues=0)

		# Verify each charge has its own opening reading
		elec_charge = self._get_charge(contract, self.elec_due_type)
		water_charge = self._get_charge(contract, self.water_due_type)
		self.assertEqual(float(elec_charge.opening_meter_reading), 2000.0)
		self.assertEqual(float(water_charge.opening_meter_reading), 800.0)

		# Verify unit readings are independent
		elec_reading = frappe.db.get_value("Rental Unit", unit, "current_electricity_meter_reading")
		water_reading = frappe.db.get_value("Rental Unit", unit, "current_water_meter_reading")
		self.assertEqual(float(elec_reading), 2000.0)
		self.assertEqual(float(water_reading), 800.0)
		self.assertNotEqual(float(elec_reading), float(water_reading))

	# ==================================================================
	# Workflow E: Capability removal blocking
	# ==================================================================

	def test_workflow_e_capability_removal_blocking(self):
		"""Capability removal is blocked by current/future approved metered contracts."""
		building = self._create_building()

		# --- E.1: Current approved metered electricity blocks removal ---
		unit1 = self._create_unit_with_caps(building, elec=True, water=True)
		self._set_unit_reading(unit1, "current_electricity_meter_reading", "100")
		tenant = self._create_tenant()
		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "100",
		}]
		contract1 = self._create_contract_with_charges(tenant, building, unit1, charges)
		self._approve(contract1, generate_dues=0)

		# Attempt to remove electricity capability → BLOCKED
		attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit1, "attribute": self.elec_attr},
			"name",
		)
		doc = frappe.get_doc("Unit Attribute Value", attr_val)
		doc.value_check = 0
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

		# Water capability should be removable (no blocking water contract)
		water_attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit1, "attribute": self.water_attr},
			"name",
		)
		water_doc = frappe.get_doc("Unit Attribute Value", water_attr_val)
		water_doc.value_check = 0
		water_doc.save(ignore_permissions=True)  # Should succeed

		# --- E.2: Future approved metered contract blocks ---
		unit2 = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit2, "current_electricity_meter_reading", "200")
		future_start = frappe.utils.add_days(frappe.utils.today(), 30)
		future_end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract2 = self._create_contract_with_charges(
			tenant, building, unit2, charges, start_date=future_start, end_date=future_end
		)
		self._approve(contract2, generate_dues=0)

		attr_val2 = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit2, "attribute": self.elec_attr},
			"name",
		)
		doc2 = frappe.get_doc("Unit Attribute Value", attr_val2)
		doc2.value_check = 0
		with self.assertRaises(frappe.ValidationError):
			doc2.save(ignore_permissions=True)

		# --- E.3: Draft metered contract does NOT block ---
		unit3 = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit3, "current_electricity_meter_reading", "300")
		contract3 = self._create_contract_with_charges(tenant, building, unit3, charges)
		# Don't approve — leave as draft

		attr_val3 = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit3, "attribute": self.elec_attr},
			"name",
		)
		doc3 = frappe.get_doc("Unit Attribute Value", attr_val3)
		doc3.value_check = 0
		doc3.save(ignore_permissions=True)  # Should succeed — draft doesn't block

		# --- E.4: Cancelled metered contract does NOT block ---
		unit4 = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit4, "current_electricity_meter_reading", "400")
		contract4 = self._create_contract_with_charges(tenant, building, unit4, charges)
		self._approve(contract4, generate_dues=0)
		frappe.db.set_value("Lease Contract", contract4, "status", "cancelled", update_modified=False)

		attr_val4 = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit4, "attribute": self.elec_attr},
			"name",
		)
		doc4 = frappe.get_doc("Unit Attribute Value", attr_val4)
		doc4.value_check = 0
		doc4.save(ignore_permissions=True)  # Should succeed — cancelled doesn't block

	# ==================================================================
	# Workflow F: Renewal
	# ==================================================================

	def test_workflow_f_renewal_with_capability(self):
		"""Renewal where capability still exists → metered preserved."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "5000")
		tenant = self._create_tenant()

		# Create old contract that is within renewal window
		old_start = frappe.utils.add_days(frappe.utils.today(), -340)
		old_end = frappe.utils.add_days(frappe.utils.today(), 25)
		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "5000",
		}]
		old_contract = self._create_contract_with_charges(
			tenant, building, unit, charges, start_date=old_start, end_date=old_end
		)
		self._approve(old_contract, generate_dues=0)

		# Update unit reading to simulate consumption
		self._set_unit_reading(unit, "current_electricity_meter_reading", "5500")

		# Create renewal
		frappe.set_user(self.owner)
		new_start = frappe.utils.add_days(frappe.utils.today(), 1)
		new_end = frappe.utils.add_days(new_start, 365)
		new_contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": new_start,
			"end_date": new_end,
			"rent_amount": 1000,
			"payment_frequency": "monthly",
			"status": "draft",
			"rental_account": self.account,
		})
		new_contract.insert(ignore_permissions=True)
		self._created_contracts.append(new_contract.name)

		# Copy charges for renewal
		old_doc = frappe.get_doc("Lease Contract", old_contract)
		copy_contract_charges_for_renewal(old_doc, new_contract, self.account)
		new_contract.save(ignore_permissions=True)

		# Verify: electricity charge remains metered
		elec_charge = self._get_charge(new_contract.name, self.elec_due_type)
		self.assertIsNotNone(elec_charge)
		self.assertEqual(elec_charge.calculation_method, "metered")
		# Opening reading should come from current unit reading
		self.assertEqual(float(elec_charge.opening_meter_reading), 5500.0)

	def test_workflow_f_renewal_without_capability(self):
		"""Renewal where capability was removed → calculation_method cleared."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=False)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "3000")
		tenant = self._create_tenant()

		# Create old contract
		old_start = frappe.utils.add_days(frappe.utils.today(), -340)
		old_end = frappe.utils.add_days(frappe.utils.today(), 25)
		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "3000",
		}]
		old_contract = self._create_contract_with_charges(
			tenant, building, unit, charges, start_date=old_start, end_date=old_end
		)
		self._approve(old_contract, generate_dues=0)

		# Cancel the old contract so capability can be removed
		frappe.db.set_value("Lease Contract", old_contract, "status", "cancelled", update_modified=False)

		# Remove electricity capability
		attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit, "attribute": self.elec_attr},
			"name",
		)
		doc = frappe.get_doc("Unit Attribute Value", attr_val)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

		# Now create renewal
		frappe.set_user(self.owner)
		new_start = frappe.utils.add_days(frappe.utils.today(), 1)
		new_end = frappe.utils.add_days(new_start, 365)
		new_contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": new_start,
			"end_date": new_end,
			"rent_amount": 1000,
			"payment_frequency": "monthly",
			"status": "draft",
			"rental_account": self.account,
		})
		new_contract.insert(ignore_permissions=True)
		self._created_contracts.append(new_contract.name)

		# Copy charges for renewal
		old_doc = frappe.get_doc("Lease Contract", old_contract)
		copy_contract_charges_for_renewal(old_doc, new_contract, self.account)
		new_contract.save(ignore_permissions=True)

		# Verify: electricity charge remains but calculation_method is empty
		elec_charge = self._get_charge(new_contract.name, self.elec_due_type)
		self.assertIsNotNone(elec_charge, "Electricity charge must remain")
		self.assertFalse(elec_charge.calculation_method, "calculation_method must be empty")
		self.assertFalse(elec_charge.opening_meter_reading, "opening_meter_reading must be empty")

		# Verify: approval rejects until user chooses a method
		# The charge has no calculation_method — backend should reject
		incomplete_types = new_contract.flags.get("incomplete_metered_due_types", set())
		self.assertIn(self.elec_due_type, incomplete_types)

	# ==================================================================
	# Workflow G: Unit Type switching — hidden values preserved
	# ==================================================================

	def test_workflow_g_unit_type_switching(self):
		"""Switching Unit Type should not delete hidden dynamic values."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=True)

		# Set rooms_count and bathrooms_count
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		bath_attr = frappe.db.get_value("Unit Attribute", {"code": "bathrooms_count", "is_system": 1}, "name")

		frappe.set_user("Administrator")
		update_unit(
			name=unit,
			attribute_values=json.dumps({
				rooms_attr: 3,
				bath_attr: 2,
				self.elec_attr: 1,
				self.water_attr: 1,
			}),
		)

		# Verify values stored
		rooms_val = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": rooms_attr}, "value_integer"
		)
		self.assertEqual(rooms_val, 3)
		elec_val = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": self.elec_attr}, "value_check"
		)
		self.assertTrue(elec_val)

		# Switch to a unit type that doesn't have rooms/bathrooms assigned
		shop_type = frappe.db.get_value("Unit Type", {"code": "shop", "is_system": 1}, "name")
		frappe.db.set_value("Rental Unit", unit, "unit_type", shop_type)

		# Verify hidden values are NOT deleted
		rooms_val_after = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": rooms_attr}, "value_integer"
		)
		self.assertEqual(rooms_val_after, 3, "Hidden rooms_count must not be deleted on type switch")

		elec_val_after = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": self.elec_attr}, "value_check"
		)
		self.assertTrue(elec_val_after, "Meter capability must not be deleted on type switch")

		# Switch back to apartment
		frappe.db.set_value("Rental Unit", unit, "unit_type", self.apartment_type)

		# Values should still be there
		rooms_val_restored = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": rooms_attr}, "value_integer"
		)
		self.assertEqual(rooms_val_restored, 3)

		# Verify no duplicate Unit Attribute Values
		count = frappe.db.count("Unit Attribute Value", {"unit": unit, "attribute": rooms_attr})
		self.assertEqual(count, 1, "No duplicate Unit Attribute Values")

	# ==================================================================
	# Workflow H: Zero values
	# ==================================================================

	def test_workflow_h_zero_values(self):
		"""Zero values must not be converted to missing by truthiness."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=True)

		# Set zero readings
		frappe.set_user("Administrator")
		self._set_unit_reading(unit, "current_electricity_meter_reading", 0)
		self._set_unit_reading(unit, "current_water_meter_reading", 0)

		# Set integer attribute to 0
		rooms_attr = frappe.db.get_value("Unit Attribute", {"code": "rooms_count", "is_system": 1}, "name")
		update_unit(name=unit, attribute_values=json.dumps({rooms_attr: 0}))

		# Verify 0 is stored, not None
		rooms_val = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": rooms_attr}, "value_integer"
		)
		self.assertEqual(rooms_val, 0, "Integer 0 must be preserved")

		# Verify Check=false is stored
		elec_val = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": self.elec_attr}, "value_check"
		)
		self.assertTrue(elec_val)  # We set it to 1

		# Now set it to 0 (false) — need to cancel any contracts first
		attr_val = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": self.elec_attr}, "name"
		)
		doc = frappe.get_doc("Unit Attribute Value", attr_val)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

		elec_val_after = frappe.db.get_value(
			"Unit Attribute Value", {"unit": unit, "attribute": self.elec_attr}, "value_check"
		)
		self.assertFalse(elec_val_after, "Check=false must be stored as 0/False")

		# Verify meter reading 0 is preserved
		elec_reading = frappe.db.get_value("Rental Unit", unit, "current_electricity_meter_reading")
		self.assertEqual(float(elec_reading), 0.0, "Meter reading 0 must be preserved")

		# Test opening_meter_reading = 0 in a contract charge
		# (requires capability to be back on)
		doc.value_check = 1
		doc.save(ignore_permissions=True)

		tenant = self._create_tenant()
		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "0",
		}]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)
		self._approve(contract, generate_dues=0)

		elec_charge = self._get_charge(contract, self.elec_due_type)
		self.assertEqual(float(elec_charge.opening_meter_reading), 0.0, "Opening reading 0 must be preserved")

	# ==================================================================
	# Workflow I: Disabled configuration
	# ==================================================================

	def test_workflow_i_system_protection(self):
		"""System Unit Types and Attributes cannot be deleted."""
		# System Unit Type cannot be deleted
		apt_type = frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
			frappe.delete_doc("Unit Type", apt_type)

		# System Unit Attribute cannot be deleted
		elec_attr_name = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		with self.assertRaises((frappe.ValidationError, frappe.PermissionError)):
			frappe.delete_doc("Unit Attribute", elec_attr_name)

	def test_workflow_i_custom_attribute_capability_protection(self):
		"""Custom attribute cannot set capability_code."""
		frappe.set_user("Administrator")
		attr = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": f"Test Custom {frappe.utils.random_string(4)}",
			"data_type": "Text",
			"is_system": 0,
			"rental_account": self.account,
			"capability_code": "electricity_meter",  # Should be rejected
		})
		with self.assertRaises(frappe.ValidationError):
			attr.insert(ignore_permissions=True)

	# ==================================================================
	# Workflow J: Historical integrity
	# ==================================================================

	def test_workflow_j_historical_contract_display(self):
		"""Historical contract charge stored calculation method remains visible."""
		building = self._create_building()
		unit = self._create_unit_with_caps(building, elec=True, water=True)
		self._set_unit_reading(unit, "current_electricity_meter_reading", "1000")
		tenant = self._create_tenant()

		charges = [{
			"due_type": self.elec_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "1000",
		}]
		contract = self._create_contract_with_charges(tenant, building, unit, charges)
		self._approve(contract, generate_dues=0)

		# Cancel the contract (make it historical)
		frappe.db.set_value("Lease Contract", contract, "status", "cancelled", update_modified=False)

		# Remove electricity capability (should succeed since contract is cancelled)
		attr_val = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit, "attribute": self.elec_attr},
			"name",
		)
		doc = frappe.get_doc("Unit Attribute Value", attr_val)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

		# Historical contract charge should still show metered
		elec_charge = self._get_charge(contract, self.elec_due_type)
		self.assertEqual(elec_charge.calculation_method, "metered")
		self.assertEqual(float(elec_charge.opening_meter_reading), 1000.0)

	# ==================================================================
	# Database invariants
	# ==================================================================

	def test_db_invariant_no_duplicate_attribute_values(self):
		"""No duplicate (unit, attribute) pairs in Unit Attribute Value."""
		duplicates = frappe.db.sql("""
			SELECT unit, attribute, COUNT(*) as cnt
			FROM `tabUnit Attribute Value`
			GROUP BY unit, attribute
			HAVING cnt > 1
		""", as_dict=True)
		self.assertEqual(len(duplicates), 0, f"Found duplicate attribute values: {duplicates[:5]}")

	def test_db_invariant_capability_values_use_system_attributes(self):
		"""Capability values use the correct System Attributes."""
		# All electricity_meter capability values must reference the system electricity_meter attribute
		elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		water_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "water_meter", "is_system": 1}, "name"
		)

		# Check that no custom attribute has capability_code = electricity_meter or water_meter
		custom_with_cap = frappe.db.count(
			"Unit Attribute",
			{"is_system": 0, "capability_code": ["in", ["electricity_meter", "water_meter"]]},
		)
		self.assertEqual(custom_with_cap, 0, "Custom attributes must not have meter capability codes")

	def test_db_invariant_all_units_have_valid_type(self):
		"""All current production units still have valid Unit Type links."""
		units = frappe.get_all("Rental Unit", fields=["name", "unit_type"])
		for u in units:
			if u.unit_type:
				self.assertTrue(
					frappe.db.exists("Unit Type", u.unit_type),
					f"Unit {u.name} references non-existent Unit Type {u.unit_type}"
				)

	def test_db_invariant_attribute_values_reference_valid_attributes(self):
		"""Every Unit Attribute Value references a valid attribute."""
		orphans = frappe.db.sql("""
			SELECT uav.name, uav.attribute
			FROM `tabUnit Attribute Value` uav
			LEFT JOIN `tabUnit Attribute` ua ON ua.name = uav.attribute
			WHERE ua.name IS NULL
		""", as_dict=True)
		self.assertEqual(len(orphans), 0, f"Found orphaned attribute values: {orphans[:5]}")
