"""Characterization tests for the existing meter lifecycle.

These tests lock the CURRENT behavior of metered charges, meter readings,
contract approval freezing, due submit/cancel rollback, renewal capture,
and unit edit protection. They are NOT intended to assert correct behavior —
they document what the system does today so that future changes (Unit Types,
Unit Attributes, Meter Capabilities) can be verified against this baseline.

Known issues / bugs are explicitly marked with ``# KNOWN-ISSUE:`` comments
and the test assertions document the actual (possibly incorrect) behavior.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from datetime import date


class TestMeterLifecycleCharacterization(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_floors = []
		cls._created_units = []
		cls._created_tenants = []
		cls._created_contracts = []
		cls._created_dues = []
		cls._created_attr_values = []

		cls.owner = cls._create_test_user("meter_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Meter Test Account", cls.owner)
		cls._create_settings(cls.account)

		# Cache due type names for electricity and water
		cls.electricity_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "electricity"}, "name"
		)
		cls.water_due_type = frappe.db.get_value(
			"Rental Due Type", {"due_type_code": "water"}, "name"
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
					frappe.db.delete("Rental Due", name)

		for name in cls._created_contracts:
			if frappe.db.exists("Lease Contract", name):
				try:
					doc = frappe.get_doc("Lease Contract", name)
					if doc.docstatus == 1:
						doc.cancel()
					if doc.docstatus == 2:
						frappe.db.set_value("Lease Contract", name, "is_archived", 0)
				except Exception:
					pass
				try:
					frappe.delete_doc("Lease Contract", name, force=True)
				except Exception:
					frappe.db.delete("Lease Contract", name)

		for name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", name):
				try:
					frappe.delete_doc("Rental Tenant", name, force=True)
				except Exception:
					frappe.db.delete("Rental Tenant", name)

		for name in cls._created_attr_values:
			if frappe.db.exists("Unit Attribute Value", name):
				frappe.delete_doc("Unit Attribute Value", name, force=True)

		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				try:
					frappe.delete_doc("Rental Unit", name, force=True)
				except Exception:
					frappe.db.delete("Rental Unit", name)

		for name in cls._created_floors:
			if frappe.db.exists("Rental Floor", name):
				try:
					frappe.delete_doc("Rental Floor", name, force=True)
				except Exception:
					frappe.db.delete("Rental Floor", name)

		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				try:
					frappe.delete_doc("Rental Building", name, force=True)
				except Exception:
					frappe.db.delete("Rental Building", name)

		for name in cls._created_accounts:
			if frappe.db.exists("Rental Account", name):
				try:
					frappe.delete_doc("Rental Account", name, force=True)
				except Exception:
					frappe.db.delete("Rental Account", name)

		for user in cls._created_users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=True)

		super().tearDownClass()

	# ----------------------------------------------------------------------
	# Test helpers
	# ----------------------------------------------------------------------

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
			"landlord_name": "Meter Test Landlord",
			"landlord_id": "1234567890",
			"landlord_phone": "0555-123-456",
			"landlord_address": "Test Address, Test City",
			"currency": "JOD",
		})
		settings.insert(ignore_permissions=True)

	def _create_building(self, name="Meter Test Building"):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"{name} {frappe.utils.random_string(4)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit(self, building, unit_number="U-M1", **kwargs):
		frappe.set_user("Administrator")
		unit_data = {
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building,
			"unit_number": f"{unit_number}-{frappe.utils.random_string(3)}",
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
		}
		unit_data.update(kwargs)
		unit = frappe.get_doc(unit_data)
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		# Set default meter capabilities (electricity + water) for metered tests
		self._set_meter_capabilities(unit.name)
		return unit.name

	def _set_meter_capabilities(self, unit, electricity=True, water=True):
		"""Set meter capabilities on a unit for testing."""
		elec_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "electricity_meter", "is_system": 1}, "name"
		)
		water_attr = frappe.db.get_value(
			"Unit Attribute", {"code": "water_meter", "is_system": 1}, "name"
		)
		if elec_attr:
			self._set_capability_value(unit, elec_attr, 1 if electricity else 0)
		if water_attr:
			self._set_capability_value(unit, water_attr, 1 if water else 0)

	def _set_capability_value(self, unit, attr_name, value=1):
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

	def _create_tenant(self, full_name="Meter Tenant"):
		frappe.set_user("Administrator")
		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"{full_name} {frappe.utils.random_string(4)}",
			"phone": "12345678",
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
		# Build charge list: keep existing + add new metered charge
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

	def _approve_contract(self, contract_name, generate_dues=0):
		from rental.rental.api.contract import approve_contract
		return approve_contract(contract_name, generate_dues=generate_dues)

	def _get_unit_reading(self, unit_name, field="current_electricity_meter_reading"):
		return frappe.db.get_value("Rental Unit", unit_name, field)

	def _create_metered_due(self, contract_name, unit_name, due_type_name,
				current_reading, unit_price=0.5, transaction_date=None):
		"""Create a metered due directly with correct rental_account.

		Bypasses the create_due API because that API relies on
		get_current_rental_account() which returns None for System Manager,
		causing generate_due_number to fail in on_submit.
		"""
		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		if not transaction_date:
			transaction_date = frappe.utils.today()

		contract = frappe.db.get_value(
			"Lease Contract", contract_name,
			["tenant", "building", "unit", "rental_account"], as_dict=True,
		)

		prev_reading_str = get_previous_meter_reading(contract_name, unit_name, due_type_name)
		prev_reading = float(prev_reading_str or 0)
		curr_reading = float(current_reading)
		consumption = curr_reading - prev_reading
		amount = round(consumption * float(unit_price), 2)

		due = frappe.get_doc({
			"doctype": "Rental Due",
			"rental_account": contract.rental_account,
			"tenant": contract.tenant,
			"contract": contract_name,
			"building": contract.building,
			"unit": unit_name,
			"due_type": due_type_name,
			"transaction_date": transaction_date,
			"due_date": transaction_date,
			"amount": amount,
			"source_type": "manual_contract",
			"calculation_method": "metered",
			"previous_meter_reading": str(prev_reading),
			"current_meter_reading": str(curr_reading),
			"meter_consumption": str(consumption),
			"unit_price": float(unit_price),
		})
		due.insert(ignore_permissions=True)
		self._created_dues.append(due.name)
		return due.name

	def _submit_due(self, due_name):
		"""Submit a due directly, setting due_number if needed."""
		due = frappe.get_doc("Rental Due", due_name)
		# Set due_number before submit to avoid generate_due_number failing
		if not due.due_number:
			from rental.rental.doctype.rental_settings.rental_settings import generate_due_number
			try:
				due.due_number = generate_due_number(due.rental_account)
			except Exception:
				due.due_number = f"DUE-TEST-{frappe.utils.random_string(6)}"
		due.db_set("due_number", due.due_number)
		due.submit()
		return due.name

	def _cancel_due(self, due_name, reason="test cancellation"):
		"""Cancel a due via the cancellation service.

		KNOWN-ISSUE: cancellation_service.cancel_due sets cancellation_reason
		AFTER due.cancel(), but RentalDue.on_cancel requires it BEFORE.
		We pre-set cancellation_reason in the DB so on_cancel doesn't throw.
		This is a production bug — the service should set the reason on the
		doc object before calling due.cancel().
		"""
		frappe.db.set_value("Rental Due", due_name, "cancellation_reason", reason)
		from rental.rental.services.cancellation_service import cancel_due
		return cancel_due(due_name, reason, frappe.session.user)

	# ======================================================================
	# 1. Contract Charge metered validation — ELECTRICITY
	# ======================================================================

	def test_metered_electricity_charge_validated_with_opening(self):
		"""validate_contract_charges accepts metered electricity with opening reading."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		result = validate_contract_charges(
			[{
				"due_type": self.electricity_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "1000",
			}],
			self.account,
		)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["calculation_method"], "metered")
		self.assertEqual(result[0]["opening_meter_reading"], "1000.0")

	def test_metered_electricity_charge_rejected_without_opening(self):
		"""validate_contract_charges rejects metered electricity without opening reading."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges(
				[{
					"due_type": self.electricity_due_type,
					"responsibility": "tenant",
					"payment_by": "landlord",
					"calculation_method": "metered",
					"opening_meter_reading": None,
				}],
				self.account,
			)

	def test_metered_electricity_charge_rejected_with_empty_opening(self):
		"""validate_contract_charges rejects metered electricity with empty opening reading."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges(
				[{
					"due_type": self.electricity_due_type,
					"responsibility": "tenant",
					"payment_by": "landlord",
					"calculation_method": "metered",
					"opening_meter_reading": "",
				}],
				self.account,
			)

	# ======================================================================
	# 2. Contract Charge metered validation — WATER
	# ======================================================================

	def test_metered_water_charge_validated_with_opening(self):
		"""validate_contract_charges accepts metered water with opening reading."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		result = validate_contract_charges(
			[{
				"due_type": self.water_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "500",
			}],
			self.account,
		)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["calculation_method"], "metered")
		self.assertEqual(result[0]["opening_meter_reading"], "500.0")

	def test_metered_water_charge_rejected_without_opening(self):
		"""validate_contract_charges rejects metered water without opening reading."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges(
				[{
					"due_type": self.water_due_type,
					"responsibility": "tenant",
					"payment_by": "landlord",
					"calculation_method": "metered",
					"opening_meter_reading": None,
				}],
				self.account,
			)

	# ======================================================================
	# 3. Metered opening_meter_reading behavior (normalization)
	# ======================================================================

	def test_opening_meter_reading_normalized_to_float_string(self):
		"""normalize_meter_reading converts '1000' to '1000.0'."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertEqual(normalize_meter_reading("1000"), "1000.0")
		self.assertEqual(normalize_meter_reading(1000), "1000.0")
		self.assertEqual(normalize_meter_reading("1000.50"), "1000.5")
		self.assertEqual(normalize_meter_reading("  500  "), "500.0")

	def test_opening_meter_reading_none_returns_none(self):
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertIsNone(normalize_meter_reading(None))
		self.assertIsNone(normalize_meter_reading(""))

	def test_opening_meter_reading_non_numeric_returns_none(self):
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertIsNone(normalize_meter_reading("abc"))

	# ======================================================================
	# 3b. Opening reading "0" — KNOWN-ISSUE: truthy/falsy
	# ======================================================================

	def test_opening_meter_reading_zero_string_is_truthy(self):
		"""normalize_meter_reading('0') returns '0.0' — a truthy string."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		result = normalize_meter_reading("0")
		self.assertEqual(result, "0.0")
		# "0.0" string is truthy in Python
		self.assertTrue(bool("0.0"))

	def test_opening_meter_reading_zero_string_passes_validation(self):
		"""validate_contract_charges accepts opening_meter_reading='0' because '0.0' is truthy string."""
		from rental.rental.services.contract_charge_service import validate_contract_charges
		# KNOWN-ISSUE: '0' normalizes to '0.0' (string), which is truthy, so it passes.
		# This is actually correct behavior (zero opening is valid), but it works
		# for the "wrong" reason (string truthiness, not numeric check).
		result = validate_contract_charges(
			[{
				"due_type": self.electricity_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "metered",
				"opening_meter_reading": "0",
			}],
			self.account,
		)
		self.assertEqual(result[0]["opening_meter_reading"], "0.0")

	# ======================================================================
	# 4. Contract approval freezes opening reading into Unit
	# ======================================================================

	def test_approval_freezes_electricity_opening_into_unit(self):
		"""On approval, unit's current_electricity_meter_reading = charge opening."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1500")

		# Before approval, unit reading is None
		self.assertIsNone(self._get_unit_reading(unit, "current_electricity_meter_reading"))

		self._approve_contract(contract, generate_dues=0)

		# After approval, unit reading = opening reading (as string)
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(reading, "1500.0")

	def test_approval_freezes_water_opening_into_unit(self):
		"""On approval, unit's current_water_meter_reading = charge opening."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="800")

		self.assertIsNone(self._get_unit_reading(unit, "current_water_meter_reading"))

		self._approve_contract(contract, generate_dues=0)

		reading = self._get_unit_reading(unit, "current_water_meter_reading")
		self.assertEqual(reading, "800.0")

	def test_approval_does_not_freeze_landlord_metered_charge(self):
		"""Landlord charges are not metered — no freeze happens for landlord responsibility."""
		from rental.rental.services.contract_charge_service import save_contract_charges
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)

		# Add electricity as landlord responsibility (no calculation_method)
		contract_doc = frappe.get_doc("Lease Contract", contract)
		save_contract_charges(contract_doc, [{
			"due_type": self.electricity_due_type,
			"responsibility": "landlord",
		}], self.account)
		contract_doc.save(ignore_permissions=True)

		self._approve_contract(contract, generate_dues=0)

		# Unit reading should remain None — landlord charges don't freeze
		self.assertIsNone(self._get_unit_reading(unit, "current_electricity_meter_reading"))

	def test_approval_freeze_skips_empty_opening_reading(self):
		"""If opening_meter_reading is None/empty, freeze skips it (no error, no write)."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)

		# Insert a metered charge with empty opening directly into DB
		# (bypassing contract validate which would reject metered without opening)
		frappe.db.sql(
			"""INSERT INTO `tabContract Charge`
			   (name, parent, parenttype, parentfield, due_type,
			    responsibility, payment_by, calculation_method,
			    opening_meter_reading, creation, modified, modified_by, owner, docstatus)
			   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, NOW(), NOW(), 'Administrator', 'Administrator', 0)""",
			(frappe.utils.random_string(10), contract, "Lease Contract", "contract_charges",
			 self.electricity_due_type, "tenant", "landlord", "metered"),
		)

		self._approve_contract(contract, generate_dues=0)

		# Unit reading should remain None — empty opening is falsy, skipped
		self.assertIsNone(self._get_unit_reading(unit, "current_electricity_meter_reading"))

	# ======================================================================
	# 4b. Freeze with "0" opening — KNOWN-ISSUE
	# ======================================================================

	def test_approval_freezes_zero_string_opening_into_unit(self):
		"""freeze_metered_opening_readings: '0.0' string is truthy, so it IS frozen."""
		from rental.rental.services.contract_charge_service import save_contract_charges
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)

		# Use save_contract_charges which normalizes '0' -> '0.0' (truthy string)
		contract_doc = frappe.get_doc("Lease Contract", contract)
		save_contract_charges(contract_doc, [{
			"due_type": self.electricity_due_type,
			"responsibility": "tenant",
			"payment_by": "landlord",
			"calculation_method": "metered",
			"opening_meter_reading": "0",
		}], self.account)
		contract_doc.save(ignore_permissions=True)

		self._approve_contract(contract, generate_dues=0)

		# '0.0' string is truthy, so freeze writes it to the unit
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(reading, "0.0")

	# ======================================================================
	# 5. get_previous_meter_reading
	# ======================================================================

	def test_get_previous_meter_reading_from_approved_due(self):
		"""Returns last approved due's current_meter_reading when one exists."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Create and submit a metered due with current_reading=1500
		due_name = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due_name)

		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		result = get_previous_meter_reading(contract, unit, self.electricity_due_type)
		# Due's current_meter_reading is Float, returned as string
		self.assertEqual(result, "1500.0")

	def test_get_previous_meter_reading_falls_back_to_charge_opening(self):
		"""When no approved due exists, falls back to contract charge opening_meter_reading."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="2000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		result = get_previous_meter_reading(contract, unit, self.electricity_due_type)
		self.assertEqual(result, "2000.0")

	def test_get_previous_meter_reading_falls_back_to_zero(self):
		"""When no due and no charge opening, returns '0'."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)

		# Add a non-metered charge (no opening reading)
		from rental.rental.services.contract_charge_service import save_contract_charges
		contract_doc = frappe.get_doc("Lease Contract", contract)
		save_contract_charges(contract_doc, [{
			"due_type": self.electricity_due_type,
			"responsibility": "landlord",
		}], self.account)
		contract_doc.save(ignore_permissions=True)
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		result = get_previous_meter_reading(contract, unit, self.electricity_due_type)
		self.assertEqual(result, "0")

	# ======================================================================
	# 5b. get_previous_meter_reading — KNOWN-ISSUE: Float 0.0 is falsy
	# ======================================================================

	def test_get_previous_meter_reading_skips_zero_float_due(self):
		"""KNOWN-ISSUE: Due with current_meter_reading=0.0 (Float) is falsy, gets skipped.

		The truthy check at line 623 (``if last_due and last_due[0].current_meter_reading``)
		treats Float 0.0 as falsy, so it falls through to the charge opening or '0'.
		This is a bug: a real reading of 0.0 should be returned, not skipped.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Create a metered due with current_reading=0 — but the API requires
		# current >= previous, and previous would be 500.0, so 0 < 500 would fail.
		# Instead, set opening to 0 so previous=0, then current=0 is valid.
		# We need a contract with opening=0 for this test.
		building2 = self._create_building("Meter B2")
		unit2 = self._create_unit(building2, "U-M2")
		tenant2 = self._create_tenant("Meter T2")
		contract2 = self._create_contract_draft(tenant2, building2, unit2)
		self._add_metered_charge(contract2, self.electricity_due_type, opening_reading="0")
		self._approve_contract(contract2, generate_dues=0)

		# Now previous reading = "0.0" (from charge opening).
		# Create a due with current_reading=0 (valid: 0 >= 0).
		due_name = self._create_metered_due(contract2, unit2, self.electricity_due_type, 0, 0.5)
		self._submit_due(due_name)

		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		result = get_previous_meter_reading(contract2, unit2, self.electricity_due_type)

		# KNOWN-ISSUE: The due's current_meter_reading is Float 0.0, which is falsy.
		# So get_previous_meter_reading skips it and falls back to charge opening ("0.0").
		# The charge opening "0.0" is a truthy string, so it returns "0.0".
		# Result is "0.0" — same value, but arrived via fallback, not from the due.
		self.assertEqual(result, "0.0")

	# ======================================================================
	# 6. Meter Due calculation
	# ======================================================================

	def test_meter_due_calculation_consumption_and_amount(self):
		"""RentalDue.validate computes consumption = curr - prev, amount = consumption * unit_price."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		due_name = self._create_metered_due(
			contract, unit, self.electricity_due_type,
			current_reading=1500, unit_price=0.25
		)
		self._submit_due(due_name)

		due = frappe.get_doc("Rental Due", due_name)
		self.assertEqual(float(due.previous_meter_reading), 1000.0)
		self.assertEqual(float(due.current_meter_reading), 1500.0)
		self.assertEqual(float(due.meter_consumption), 500.0)
		self.assertEqual(float(due.unit_price), 0.25)
		self.assertEqual(float(due.amount), 125.0)

	def test_meter_due_calculation_with_decimal_readings(self):
		"""Meter due with decimal readings: prev=1000.5, curr=1500.75, consumption=500.25."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000.5")
		self._approve_contract(contract, generate_dues=0)

		due_name = self._create_metered_due(
			contract, unit, self.electricity_due_type,
			current_reading=1500.75, unit_price=0.5
		)
		self._submit_due(due_name)

		due = frappe.get_doc("Rental Due", due_name)
		self.assertAlmostEqual(float(due.meter_consumption), 500.25, places=2)
		# round_money rounds to 2 decimal places (currency precision)
		self.assertAlmostEqual(float(due.amount), 250.13, places=2)

	def test_meter_due_rejects_current_less_than_previous(self):
		"""RentalDue.validate throws when current < previous."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="2000")
		self._approve_contract(contract, generate_dues=0)

		# current=1500 < previous=2000 should fail
		with self.assertRaises(frappe.ValidationError):
			self._create_metered_due(
				contract, unit, self.electricity_due_type,
				current_reading=1500, unit_price=0.5
			)

	# ======================================================================
	# 7. Meter Due submit updates unit current reading
	# ======================================================================

	def test_due_submit_updates_unit_electricity_reading(self):
		"""on_submit sets unit's current_electricity_meter_reading = due's current_meter_reading."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# After approval, unit reading = "1000.0"
		self.assertEqual(self._get_unit_reading(unit, "current_electricity_meter_reading"), "1000.0")

		due_name = self._create_metered_due(
			contract, unit, self.electricity_due_type,
			current_reading=1800, unit_price=0.5
		)
		self._submit_due(due_name)

		# After due submit, unit reading = "1800.0" (Float converted to string by Frappe)
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(float(reading), 1800.0)

	def test_due_submit_updates_unit_water_reading(self):
		"""on_submit sets unit's current_water_meter_reading = due's current_meter_reading."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		due_name = self._create_metered_due(
			contract, unit, self.water_due_type,
			current_reading=750, unit_price=0.3
		)
		self._submit_due(due_name)

		reading = self._get_unit_reading(unit, "current_water_meter_reading")
		self.assertEqual(float(reading), 750.0)

	# ======================================================================
	# 8. Meter Due cancellation rolls back unit reading (no newer reading)
	# ======================================================================

	def test_due_cancel_rolls_back_unit_reading_to_previous(self):
		"""Cancelling a metered due rolls back unit reading to previous due's reading."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Create and submit due 1: current=1500
		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1500.0)

		# Cancel due 1 — should roll back to previous (charge opening = 1000.0)
		self._cancel_due(due1, "test rollback")

		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		# cancellation_service._rollback_meter falls back to charge opening_meter_reading
		self.assertEqual(float(reading), 1000.0)

	def test_due_cancel_rolls_back_to_previous_due_reading(self):
		"""Cancelling due 2 rolls back to due 1's reading (the previous approved due)."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)

		due2 = self._create_metered_due(contract, unit, self.electricity_due_type, 2000, 0.5)
		self._submit_due(due2)

		# Unit reading is now 2000
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 2000.0)

		# Cancel due 2 — should roll back to due 1's reading (1500)
		self._cancel_due(due2, "test rollback to previous due")

		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(float(reading), 1500.0)

	# ======================================================================
	# 9. Meter Due cancellation does NOT roll back if newer reading exists
	# ======================================================================

	def test_due_cancel_blocked_if_newer_reading_exists(self):
		"""Cancelling a metered due is blocked if a newer approved due exists."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)

		due2 = self._create_metered_due(contract, unit, self.electricity_due_type, 2000, 0.5)
		self._submit_due(due2)

		# Trying to cancel due 1 (older) should fail because due 2 (newer) exists
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._cancel_due(due1, "attempt rollback with newer")
		self.assertIn("أحدث", str(ctx.exception))

		# Unit reading should still be 2000 (not rolled back)
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 2000.0)

	# ======================================================================
	# 10. Renewal captures current unit meter reading as opening
	# ======================================================================

	def test_copy_contract_charges_for_renewal_captures_opening(self):
		"""copy_contract_charges_for_renewal copies metered charges and captures
		the opening reading from the unit's current meter reading.

		This is the corrected behavior: the opening reading is populated from
		the unit's current reading at copy time, so that validation (which
		requires a non-null opening reading) passes at insert time.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Set the unit's current reading to 1500
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		# Create a new draft contract (simulating a renewal) WITHOUT using the API
		renewal = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 730),
			"rent_amount": 500,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
			"renewed_from_contract": contract,
		})
		from rental.rental.services.contract_charge_service import copy_contract_charges_for_renewal
		old_doc = frappe.get_doc("Lease Contract", contract)
		copy_contract_charges_for_renewal(old_doc, renewal, self.account)

		# The metered charge should have opening captured from the unit's current reading
		metered_charges = [c for c in renewal.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered_charges), 1)
		self.assertIsNotNone(metered_charges[0].opening_meter_reading)
		self.assertEqual(float(metered_charges[0].opening_meter_reading), 1500.0)
		self.assertEqual(metered_charges[0].responsibility, "tenant")
		self.assertEqual(metered_charges[0].payment_by, "landlord")

	def test_renew_contract_api_electricity_metered_succeeds(self):
		"""REGRESSION: renew_contract API succeeds for electricity metered charges.

		The opening reading is captured from the unit's current_electricity_meter_reading
		before validation runs, so the renewal draft is created successfully.
		"""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Set unit's current electricity reading
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		self.assertIn("contract", result)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		# Verify the renewal has the metered charge with the correct opening
		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)
		self.assertEqual(float(metered[0].opening_meter_reading), 1500.0)

	def test_renew_contract_api_water_metered_succeeds(self):
		"""REGRESSION: renew_contract API succeeds for water metered charges."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Set unit's current water reading
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "750")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		self.assertIn("contract", result)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)
		self.assertEqual(float(metered[0].opening_meter_reading), 750.0)

	def test_renew_electricity_opening_from_unit_current_reading(self):
		"""REGRESSION: electricity opening reading is copied from Unit's current reading."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Set a specific unit reading
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "2345.5")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(float(metered[0].opening_meter_reading), 2345.5)

	def test_renew_water_opening_from_unit_current_reading(self):
		"""REGRESSION: water opening reading is copied from Unit's current reading."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Set a specific unit water reading
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "890.0")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(float(metered[0].opening_meter_reading), 890.0)

	def test_renew_zero_electricity_reading_preserved(self):
		"""REGRESSION: zero electricity reading is valid and preserved."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Set unit reading to "0" (valid zero)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "0")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertIsNotNone(metered[0].opening_meter_reading)
		self.assertEqual(float(metered[0].opening_meter_reading), 0.0)

	def test_renew_zero_water_reading_preserved(self):
		"""REGRESSION: zero water reading is valid and preserved."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Set unit water reading to "0" (valid zero)
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "0")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertIsNotNone(metered[0].opening_meter_reading)
		self.assertEqual(float(metered[0].opening_meter_reading), 0.0)

	def test_renew_missing_electricity_reading_rejects(self):
		"""REGRESSION: genuinely missing electricity reading rejects renewal."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Clear unit reading to None (genuinely missing)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", None)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		with self.assertRaises(frappe.ValidationError) as ctx:
			renew_contract(contract, end_date=renewal_end)
		# Clear Arabic message about missing reading
		self.assertIn("قراءة العداد", str(ctx.exception))

	def test_renew_missing_water_reading_rejects(self):
		"""REGRESSION: genuinely missing water reading rejects renewal."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Clear unit water reading to None (genuinely missing)
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", None)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		with self.assertRaises(frappe.ValidationError) as ctx:
			renew_contract(contract, end_date=renewal_end)
		self.assertIn("قراءة العداد", str(ctx.exception))

	def test_renew_non_metered_contract_unchanged(self):
		"""REGRESSION: non-metered renewal behavior remains unchanged."""
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date, rent=600)
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(end_date, 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		self.assertIn("contract", result)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		# No metered charges, rent amount preserved
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 0)
		self.assertEqual(float(renewal_doc.rent_amount), 600.0)

	def test_capture_metered_openings_from_unit_fills_opening(self):
		"""capture_metered_openings_from_unit fills opening from unit's current reading.

		Tests the service function directly: creates a renewal contract with
		a metered charge (opening=None), sets the unit's reading, then calls
		capture_metered_openings_from_unit.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Submit a due to set unit reading to 1500
		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1500.0)

		# Create an in-memory renewal with metered charge (opening=None)
		# NOTE: We set up the charge manually (not via copy_contract_charges_for_renewal)
		# because copy_contract_charges_for_renewal now captures the opening from
		# the unit reading. This test characterizes capture_metered_openings_from_unit
		# in isolation.
		renewal = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 730),
			"rent_amount": 500,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
			"renewed_from_contract": contract,
		})
		from rental.rental.services.contract_charge_service import (
			capture_metered_openings_from_unit,
		)
		old_doc = frappe.get_doc("Lease Contract", contract)
		# Manually copy charges with opening=None to test capture in isolation
		for charge in old_doc.contract_charges:
			renewal.append("contract_charges", {
				"due_type": charge.due_type,
				"responsibility": charge.responsibility,
				"calculation_method": charge.calculation_method,
				"payment_by": charge.payment_by,
				"amount": charge.amount if charge.responsibility == "tenant" else None,
				"frequency": charge.frequency if charge.calculation_method == "fixed_periodic" else None,
				"first_due_date": renewal.start_date if charge.calculation_method == "fixed_periodic" else None,
				"commitment_timing": charge.commitment_timing,
				"last_period_handling": charge.last_period_handling,
				"last_period_adjustment_amount": charge.last_period_adjustment_amount,
				"opening_meter_reading": None,
			})

		# Before capture, opening is None
		metered = [c for c in renewal.contract_charges if c.calculation_method == "metered"]
		self.assertIsNone(metered[0].opening_meter_reading)

		# Capture fills opening from unit's current reading (1500)
		capture_metered_openings_from_unit(renewal, self.account)

		self.assertIsNotNone(metered[0].opening_meter_reading)
		self.assertEqual(float(metered[0].opening_meter_reading), 1500.0)

	# ======================================================================
	# 10b. Renewal capture — KNOWN-ISSUE: skips empty unit reading
	# ======================================================================

	def test_capture_metered_openings_skips_empty_unit_reading(self):
		"""capture_metered_openings_from_unit skips when unit reading is None/empty.

		The truthy check at line 583 (``if not current_reading: continue``) means
		None and empty string are skipped. The charge's opening_meter_reading
		stays None.

		NOTE: copy_contract_charges_for_renewal now throws when the unit reading
		is missing, so we set up the renewal charge manually to test
		capture_metered_openings_from_unit in isolation.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Clear unit reading to None
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", None)
		self.assertIsNone(self._get_unit_reading(unit, "current_electricity_meter_reading"))

		# Create in-memory renewal with metered charge (manually, bypassing copy)
		renewal = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 730),
			"rent_amount": 500,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
			"renewed_from_contract": contract,
		})
		from rental.rental.services.contract_charge_service import (
			capture_metered_openings_from_unit,
		)
		old_doc = frappe.get_doc("Lease Contract", contract)
		for charge in old_doc.contract_charges:
			renewal.append("contract_charges", {
				"due_type": charge.due_type,
				"responsibility": charge.responsibility,
				"calculation_method": charge.calculation_method,
				"payment_by": charge.payment_by,
				"amount": charge.amount if charge.responsibility == "tenant" else None,
				"frequency": charge.frequency if charge.calculation_method == "fixed_periodic" else None,
				"first_due_date": renewal.start_date if charge.calculation_method == "fixed_periodic" else None,
				"commitment_timing": charge.commitment_timing,
				"last_period_handling": charge.last_period_handling,
				"last_period_adjustment_amount": charge.last_period_adjustment_amount,
				"opening_meter_reading": None,
			})

		capture_metered_openings_from_unit(renewal, self.account)

		metered = [c for c in renewal.contract_charges if c.calculation_method == "metered"]
		# Opening stays None because unit reading was None (falsy, skipped)
		self.assertIsNone(metered[0].opening_meter_reading)

	# ======================================================================
	# 11. has_active_metered_contract
	# ======================================================================

	def test_has_active_metered_contract_true_for_electricity(self):
		"""Returns True when an active contract has a metered electricity charge."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import has_active_metered_contract
		self.assertTrue(has_active_metered_contract(unit, "electricity"))

	def test_has_active_metered_contract_false_for_water_when_only_electricity(self):
		"""Returns False for water when only electricity is metered."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import has_active_metered_contract
		self.assertFalse(has_active_metered_contract(unit, "water"))

	def test_has_active_metered_contract_false_when_no_contract(self):
		"""Returns False when unit has no contracts."""
		building = self._create_building()
		unit = self._create_unit(building)

		from rental.rental.services.contract_charge_service import has_active_metered_contract
		self.assertFalse(has_active_metered_contract(unit, "electricity"))
		self.assertFalse(has_active_metered_contract(unit, "water"))

	def test_has_active_metered_contract_false_for_draft_contract(self):
		"""Returns False for draft contracts (only active within date range counts)."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		# Do NOT approve — stays draft

		from rental.rental.services.contract_charge_service import has_active_metered_contract
		self.assertFalse(has_active_metered_contract(unit, "electricity"))

	# ======================================================================
	# 11b. has_active_metered_contract — does NOT check future approved
	# ======================================================================

	def test_has_active_metered_contract_false_for_future_approved(self):
		"""KNOWN-ISSUE: Future approved contracts (start > today) are NOT counted.

		has_active_metered_contract filters: status=active, start_date <= today,
		end_date >= today. A future-approved contract (start_date > today) is
		excluded. This means unit meter readings are editable even when a
		future approved metered contract exists.
		"""
		future_start = frappe.utils.add_days(frappe.utils.today(), 30)
		future_end = frappe.utils.add_days(future_start, 365)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, future_start, future_end)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import has_active_metered_contract
		# Future approved contract is NOT counted — returns False
		self.assertFalse(has_active_metered_contract(unit, "electricity"))

	# ======================================================================
	# 12. Unit meter-reading edit protection
	# ======================================================================

	def test_meter_reading_editable_without_active_metered_contract(self):
		"""Unit meter reading fields are editable when no active metered contract exists."""
		building = self._create_building()
		unit = self._create_unit(building)

		from rental.rental.services.unit_permissions_service import get_editable_fields
		editable = get_editable_fields(unit)
		self.assertIn("current_electricity_meter_reading", editable)
		self.assertIn("current_water_meter_reading", editable)

	def test_electricity_meter_reading_not_editable_with_active_contract(self):
		"""Electricity meter reading is NOT editable with active metered electricity contract."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.unit_permissions_service import get_editable_fields
		editable = get_editable_fields(unit)
		self.assertNotIn("current_electricity_meter_reading", editable)
		# Water is still editable (no metered water contract)
		self.assertIn("current_water_meter_reading", editable)

	def test_water_meter_reading_not_editable_with_active_contract(self):
		"""Water meter reading is NOT editable with active metered water contract."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.unit_permissions_service import get_editable_fields
		editable = get_editable_fields(unit)
		self.assertNotIn("current_water_meter_reading", editable)
		# Electricity is still editable
		self.assertIn("current_electricity_meter_reading", editable)

	def test_both_meter_readings_not_editable_with_both_metered(self):
		"""Both meter readings NOT editable when both have active metered contracts."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.unit_permissions_service import get_editable_fields
		editable = get_editable_fields(unit)
		self.assertNotIn("current_electricity_meter_reading", editable)
		self.assertNotIn("current_water_meter_reading", editable)

	# ======================================================================
	# 13. Electricity and water independently
	# ======================================================================

	def test_electricity_and_water_dues_independent(self):
		"""Electricity and water metered dues on the same contract operate independently."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		# Both unit readings should be set from freeze
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1000.0)
		self.assertEqual(float(self._get_unit_reading(unit, "current_water_meter_reading")), 500.0)

		# Submit electricity due
		elec_due = self._create_metered_due(contract, unit, self.electricity_due_type, 1200, 0.5)
		self._submit_due(elec_due)
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1200.0)
		# Water reading unchanged
		self.assertEqual(float(self._get_unit_reading(unit, "current_water_meter_reading")), 500.0)

		# Submit water due
		water_due = self._create_metered_due(contract, unit, self.water_due_type, 600, 0.3)
		self._submit_due(water_due)
		self.assertEqual(float(self._get_unit_reading(unit, "current_water_meter_reading")), 600.0)
		# Electricity reading unchanged
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1200.0)

	def test_get_previous_meter_reading_independent_for_electricity_and_water(self):
		"""get_previous_meter_reading returns the correct type's reading independently."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self._approve_contract(contract, generate_dues=0)

		elec_due = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(elec_due)

		water_due = self._create_metered_due(contract, unit, self.water_due_type, 700, 0.3)
		self._submit_due(water_due)

		from rental.rental.services.contract_charge_service import get_previous_meter_reading
		self.assertEqual(get_previous_meter_reading(contract, unit, self.electricity_due_type), "1500.0")
		self.assertEqual(get_previous_meter_reading(contract, unit, self.water_due_type), "700.0")

	# ======================================================================
	# 14. Reading edge cases
	# ======================================================================

	def test_normalize_meter_reading_none(self):
		"""normalize_meter_reading(None) returns None."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertIsNone(normalize_meter_reading(None))

	def test_normalize_meter_reading_empty_string(self):
		"""normalize_meter_reading('') returns None."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertIsNone(normalize_meter_reading(""))

	def test_normalize_meter_reading_zero_string(self):
		"""normalize_meter_reading('0') returns '0.0' (truthy string)."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		result = normalize_meter_reading("0")
		self.assertEqual(result, "0.0")
		self.assertTrue(bool(result))  # truthy

	def test_normalize_meter_reading_zero_float_string(self):
		"""normalize_meter_reading('0.0') returns '0.0' (truthy string)."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		result = normalize_meter_reading("0.0")
		self.assertEqual(result, "0.0")
		self.assertTrue(bool(result))  # truthy

	def test_normalize_meter_reading_numeric_zero(self):
		"""normalize_meter_reading(0) returns '0.0' (truthy string)."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		result = normalize_meter_reading(0)
		self.assertEqual(result, "0.0")
		self.assertTrue(bool(result))  # truthy

	def test_normalize_meter_reading_float_zero(self):
		"""normalize_meter_reading(0.0) returns '0.0' (truthy string).

		Note: the INPUT 0.0 (float) is falsy, but normalize_meter_reading
		converts it to the STRING '0.0' which is truthy. This is the root
		of the truthy/falsy inconsistency: the function output is always
		a truthy string (or None), but downstream code that reads Float
		fields from the DB gets falsy 0.0.
		"""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		result = normalize_meter_reading(0.0)
		self.assertEqual(result, "0.0")
		self.assertTrue(bool(result))  # truthy string

	def test_normalize_meter_reading_nonzero(self):
		"""normalize_meter_reading('1234') returns '1234.0'."""
		from rental.rental.services.contract_charge_service import normalize_meter_reading
		self.assertEqual(normalize_meter_reading("1234"), "1234.0")
		self.assertEqual(normalize_meter_reading(1234), "1234.0")
		self.assertEqual(normalize_meter_reading("1234.56"), "1234.56")

	# ======================================================================
	# 14b. Edge case: Float 0.0 from Due is falsy in get_previous_meter_reading
	# ======================================================================

	def test_float_zero_is_falsy_in_python(self):
		"""Document that Float 0.0 is falsy in Python (root cause of the bug).

		Rental Due's current_meter_reading is a Float field. When the DB
		returns 0.0, the truthy check ``if last_due[0].current_meter_reading``
		evaluates to False, causing the reading to be skipped.
		"""
		self.assertFalse(bool(0.0))
		self.assertFalse(bool(0))
		self.assertTrue(bool("0"))
		self.assertTrue(bool("0.0"))
		self.assertTrue(bool(0.1))

	# ======================================================================
	# 14c. Edge case: Unit reading "0" (string) is truthy, 0.0 (float) is not
	# ======================================================================

	def test_unit_reading_zero_string_is_truthy(self):
		"""Unit's current_electricity_meter_reading is Data (string). '0.0' is truthy.

		This means freeze_metered_opening_readings and
		capture_metered_openings_from_unit treat '0.0' on the unit as a valid
		reading (truthy), while 0.0 on a Due (Float) is treated as empty (falsy).
		"""
		building = self._create_building()
		unit = self._create_unit(building)

		# Set unit reading to "0" string
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "0")
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(reading, "0")
		self.assertTrue(bool(reading))  # truthy string

		# Set unit reading to "0.0" string
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "0.0")
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(reading, "0.0")
		self.assertTrue(bool(reading))  # truthy string

	# ======================================================================
	# 14d. Edge case: capture_metered_openings_from_unit with "0" unit reading
	# ======================================================================

	def test_capture_openings_from_unit_with_zero_string_reading(self):
		"""capture_metered_openings_from_unit: '0' string on unit is truthy, IS captured.

		NOTE: copy_contract_charges_for_renewal now captures the opening from
		the unit reading at copy time, so we set up the renewal charge manually
		to test capture_metered_openings_from_unit in isolation.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		# Set unit reading to "0" (string, truthy)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "0")

		# Create in-memory renewal with metered charge (manually, bypassing copy)
		renewal = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 730),
			"rent_amount": 500,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
			"renewed_from_contract": contract,
		})
		from rental.rental.services.contract_charge_service import (
			capture_metered_openings_from_unit,
		)
		old_doc = frappe.get_doc("Lease Contract", contract)
		for charge in old_doc.contract_charges:
			renewal.append("contract_charges", {
				"due_type": charge.due_type,
				"responsibility": charge.responsibility,
				"calculation_method": charge.calculation_method,
				"payment_by": charge.payment_by,
				"amount": charge.amount if charge.responsibility == "tenant" else None,
				"frequency": charge.frequency if charge.calculation_method == "fixed_periodic" else None,
				"first_due_date": renewal.start_date if charge.calculation_method == "fixed_periodic" else None,
				"commitment_timing": charge.commitment_timing,
				"last_period_handling": charge.last_period_handling,
				"last_period_adjustment_amount": charge.last_period_adjustment_amount,
				"opening_meter_reading": None,
			})

		capture_metered_openings_from_unit(renewal, self.account)

		metered = [c for c in renewal.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)
		# "0" string is truthy, so capture fills opening with "0"
		self.assertIsNotNone(metered[0].opening_meter_reading)

	# ======================================================================
	# 15. is_metered_due_type_code and get_meter_field
	# ======================================================================

	def test_is_metered_due_type_code(self):
		"""is_metered_due_type_code returns True only for electricity and water."""
		from rental.rental.services.contract_charge_service import is_metered_due_type_code
		self.assertTrue(is_metered_due_type_code("electricity"))
		self.assertTrue(is_metered_due_type_code("water"))
		self.assertFalse(is_metered_due_type_code("rent"))
		self.assertFalse(is_metered_due_type_code("cleaning"))
		self.assertFalse(is_metered_due_type_code(None))
		self.assertFalse(is_metered_due_type_code(""))

	def test_get_meter_field(self):
		"""get_meter_field maps due type codes to unit meter fields."""
		from rental.rental.services.contract_charge_service import get_meter_field
		self.assertEqual(get_meter_field("electricity"), "current_electricity_meter_reading")
		self.assertEqual(get_meter_field("water"), "current_water_meter_reading")
		self.assertIsNone(get_meter_field("rent"))
		self.assertIsNone(get_meter_field(None))

	# ======================================================================
	# 16. is_allowed_calculation_method_for_due_type
	# ======================================================================

	def test_metered_allowed_for_electricity(self):
		"""metered is allowed for electricity (but not on_demand)."""
		from rental.rental.services.contract_charge_service import is_allowed_calculation_method_for_due_type
		self.assertTrue(is_allowed_calculation_method_for_due_type("electricity", "metered"))
		self.assertTrue(is_allowed_calculation_method_for_due_type("electricity", "fixed_periodic"))
		self.assertTrue(is_allowed_calculation_method_for_due_type("electricity", "actual_bill"))
		self.assertFalse(is_allowed_calculation_method_for_due_type("electricity", "on_demand"))

	def test_metered_allowed_for_water(self):
		"""metered is allowed for water (but not on_demand)."""
		from rental.rental.services.contract_charge_service import is_allowed_calculation_method_for_due_type
		self.assertTrue(is_allowed_calculation_method_for_due_type("water", "metered"))
		self.assertFalse(is_allowed_calculation_method_for_due_type("water", "on_demand"))

	def test_metered_not_allowed_for_non_metered_types(self):
		"""metered is NOT allowed for rent or custom due types."""
		from rental.rental.services.contract_charge_service import is_allowed_calculation_method_for_due_type
		self.assertFalse(is_allowed_calculation_method_for_due_type("rent", "metered"))
		self.assertFalse(is_allowed_calculation_method_for_due_type("cleaning", "metered"))
		self.assertFalse(is_allowed_calculation_method_for_due_type(None, "metered"))

	# ======================================================================
	# 17. can_create_meter_due
	# ======================================================================

	def test_can_create_meter_due_ok(self):
		"""can_create_meter_due returns ok=True for active contract with metered charge."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import can_create_meter_due
		result = can_create_meter_due(contract, self.electricity_due_type)
		self.assertTrue(result["ok"])
		self.assertIsNone(result["error"])

	def test_can_create_meter_due_rejects_draft(self):
		"""can_create_meter_due rejects draft contracts."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		# Do NOT approve

		from rental.rental.services.contract_charge_service import can_create_meter_due
		result = can_create_meter_due(contract, self.electricity_due_type)
		self.assertFalse(result["ok"])

	def test_can_create_meter_due_rejects_future_start(self):
		"""can_create_meter_due rejects when contract start_date > today."""
		future_start = frappe.utils.add_days(frappe.utils.today(), 30)
		future_end = frappe.utils.add_days(future_start, 365)
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, future_start, future_end)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import can_create_meter_due
		result = can_create_meter_due(contract, self.electricity_due_type)
		self.assertFalse(result["ok"])

	def test_can_create_meter_due_rejects_non_metered_charge(self):
		"""can_create_meter_due rejects when charge is not metered."""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		# Add electricity as landlord (no metered)
		from rental.rental.services.contract_charge_service import save_contract_charges
		contract_doc = frappe.get_doc("Lease Contract", contract)
		save_contract_charges(contract_doc, [{
			"due_type": self.electricity_due_type,
			"responsibility": "landlord",
		}], self.account)
		contract_doc.save(ignore_permissions=True)
		self._approve_contract(contract, generate_dues=0)

		from rental.rental.services.contract_charge_service import can_create_meter_due
		result = can_create_meter_due(contract, self.electricity_due_type)
		self.assertFalse(result["ok"])

	# ======================================================================
	# 18. on_cancel _rollback_unit_meter (doc-level) — simpler rollback
	# ======================================================================

	def test_on_cancel_rollback_unit_meter_matches_current(self):
		"""RentalDue.on_cancel._rollback_unit_meter rolls back when unit reading matches due's current.

		This is the doc-level rollback (simpler than cancellation_service).
		It only rolls back if the unit's current reading == the due's current reading.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)

		# Unit reading is now 1500 (matches due's current)
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 1500.0)

		# Cancel via service (which calls due.cancel() triggering on_cancel)
		self._cancel_due(due1, "test doc-level rollback")

		# on_cancel._rollback_unit_meter: unit reading (1500) == due current (1500) → rollback
		# BUT cancellation_service._rollback_meter runs FIRST and sets unit to 1000 (charge opening).
		# Then on_cancel._rollback_unit_meter checks: unit (1000) != due current (1500) → no rollback.
		# Net result: unit reading = 1000 (from cancellation_service, not from on_cancel)
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(float(reading), 1000.0)

	# ======================================================================
	# 19. Two rollback paths interaction
	# ======================================================================

	def test_cancellation_service_rollback_runs_before_doc_rollback(self):
		"""cancellation_service._rollback_meter runs before RentalDue.on_cancel._rollback_unit_meter.

		The service sets unit reading to the previous value (previous due or charge opening).
		Then on_cancel checks if unit reading == due's current — it no longer matches,
		so on_cancel does nothing. The service-level rollback is the effective one.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.electricity_due_type, opening_reading="1000")
		self._approve_contract(contract, generate_dues=0)

		due1 = self._create_metered_due(contract, unit, self.electricity_due_type, 1500, 0.5)
		self._submit_due(due1)

		due2 = self._create_metered_due(contract, unit, self.electricity_due_type, 2000, 0.5)
		self._submit_due(due2)

		# Unit reading is 2000
		self.assertEqual(float(self._get_unit_reading(unit, "current_electricity_meter_reading")), 2000.0)

		# Cancel due2: service rolls back to due1's reading (1500)
		self._cancel_due(due2, "test two rollback paths")

		# Service set unit to 1500 (due1's current_meter_reading).
		# Then on_cancel checks: unit (1500) != due2 current (2000) → no rollback.
		reading = self._get_unit_reading(unit, "current_electricity_meter_reading")
		self.assertEqual(float(reading), 1500.0)
