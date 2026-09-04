"""Backend tests for Phase 5 capability wiring.

Tests:
  Contract validation (1-8):
    1. electricity metered + capability=1 → allowed
    2. electricity metered + capability=0 → rejected
    3. water metered + capability=1 → allowed
    4. water metered + capability=0 → rejected
    5. electricity fixed_periodic + no capability → allowed
    6. electricity actual_bill + no capability → allowed
    7. water fixed_periodic + no capability → allowed
    8. water actual_bill + no capability → allowed

  Approval (9-10):
    9. Draft metered created while capability exists, capability removed,
       approval rejected
   10. approval succeeds when capability still exists

  Removal protection (11-17):
   11. current approved metered blocks removal
   12. future approved metered blocks removal
   13. Draft does not block
   14. cancelled does not block
   15. evicted does not block
   16. expired does not block
   17. archived does not block

  Renewal (18-24):
   18. electricity metered renewal preserves metered when capability exists
   19. water metered renewal preserves metered when capability exists
   20. electricity metered renewal clears calculation_method when capability absent
   21. water metered renewal clears calculation_method when capability absent
   22. electricity/water charge itself remains present when capability absent
   23. opening reading not used after metered is cleared
   24. approval revalidates renewal capability

  Narrow scoping regression (25-28):
   25. cleared charge allowed, invalid charge still rejected
   26. cleared charge allowed, valid unrelated charge passes
   27. cleared charge still validates other rules (duplicate due type)
   28. full renewal: cleared + valid charges, approval rejects until corrected
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestCapabilityWiring(FrappeTestCase):
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
		cls._created_due_types = []

		cls.owner = cls._create_test_user("capwire_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Capability Wiring Test Account", cls.owner)
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

		for name in cls._created_due_types:
			if frappe.db.exists("Rental Due Type", name):
				try:
					frappe.delete_doc("Rental Due Type", name, force=True)
				except Exception:
					frappe.db.delete("Rental Due Type", name)

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
			"landlord_name": "Cap Wiring Test Landlord",
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
			"building_name": f"CapWire Bldg {frappe.utils.random_string(4)}",
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
			"unit_number": f"CW-{frappe.utils.random_string(5)}",
			"unit_type": unit_type,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	def _create_tenant(self, name_suffix=None):
		frappe.set_user("Administrator")
		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"CapWire Tenant {name_suffix or frappe.utils.random_string(4)}",
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

	def _add_charge(self, contract_name, due_type_name, responsibility="tenant",
			payment_by="landlord", calculation_method=None, amount=None,
			frequency=None, commitment_timing="start"):
		"""Add a charge with arbitrary calculation method."""
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
		new_charge = {
			"due_type": due_type_name,
			"responsibility": responsibility,
			"payment_by": payment_by,
			"calculation_method": calculation_method,
			"commitment_timing": commitment_timing,
		}
		if amount is not None:
			new_charge["amount"] = amount
		if frequency:
			new_charge["frequency"] = frequency
		charges.append(new_charge)
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

	def _set_capability_safe(self, unit, attr_name, value=1):
		"""Set capability, handling removal protection by using db_set."""
		existing = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": attr_name,
		}, "name")
		if existing:
			# Use db_set to bypass validate (for testing removal scenarios)
			frappe.db.set_value("Unit Attribute Value", existing, "value_check", value)
			return existing
		return self._set_capability(unit, attr_name, value)

	# ======================================================================
	# Contract validation (1-8)
	# ======================================================================

	def test_1_electricity_metered_with_capability_allowed(self):
		"""electricity metered + capability=1 → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		# Should not throw
		self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")

		# Verify charge was saved
		contract_doc = frappe.get_doc("Lease Contract", contract)
		metered = [c for c in contract_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)

	def test_2_electricity_metered_without_capability_rejected(self):
		"""electricity metered + capability=0 → rejected."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 0)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")
		self.assertIn("عداد كهرباء", str(ctx.exception))

	def test_3_water_metered_with_capability_allowed(self):
		"""water metered + capability=1 → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "500")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")

		contract_doc = frappe.get_doc("Lease Contract", contract)
		metered = [c for c in contract_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)

	def test_4_water_metered_without_capability_rejected(self):
		"""water metered + capability=0 → rejected."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 0)
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "500")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		self.assertIn("عداد مياه", str(ctx.exception))

	def test_5_electricity_fixed_periodic_no_capability_allowed(self):
		"""electricity fixed_periodic + no capability → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		# No electricity capability set (or explicitly 0)
		self._set_capability(unit, self.elec_attr, 0)

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		# Should not throw — fixed_periodic doesn't require meter capability
		self._add_charge(
			contract, self.elec_due_type,
			calculation_method="fixed_periodic",
			amount=50, frequency="monthly",
		)

		contract_doc = frappe.get_doc("Lease Contract", contract)
		fixed = [c for c in contract_doc.contract_charges if c.calculation_method == "fixed_periodic"]
		self.assertEqual(len(fixed), 1)

	def test_6_electricity_actual_bill_no_capability_allowed(self):
		"""electricity actual_bill + no capability → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 0)

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_charge(
			contract, self.elec_due_type,
			calculation_method="actual_bill",
		)

		contract_doc = frappe.get_doc("Lease Contract", contract)
		actual = [c for c in contract_doc.contract_charges if c.calculation_method == "actual_bill"]
		self.assertEqual(len(actual), 1)

	def test_7_water_fixed_periodic_no_capability_allowed(self):
		"""water fixed_periodic + no capability → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 0)

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_charge(
			contract, self.water_due_type,
			calculation_method="fixed_periodic",
			amount=30, frequency="monthly",
		)

		contract_doc = frappe.get_doc("Lease Contract", contract)
		fixed = [c for c in contract_doc.contract_charges if c.calculation_method == "fixed_periodic"]
		self.assertEqual(len(fixed), 1)

	def test_8_water_actual_bill_no_capability_allowed(self):
		"""water actual_bill + no capability → allowed."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 0)

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_charge(
			contract, self.water_due_type,
			calculation_method="actual_bill",
		)

		contract_doc = frappe.get_doc("Lease Contract", contract)
		actual = [c for c in contract_doc.contract_charges if c.calculation_method == "actual_bill"]
		self.assertEqual(len(actual), 1)

	# ======================================================================
	# Approval re-validation (9-10)
	# ======================================================================

	def test_9_draft_metered_capability_removed_approval_rejected(self):
		"""Draft metered created while capability exists, capability removed,
		approval rejected."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")

		# Remove capability (use db_set to bypass removal protection since it's draft)
		self._set_capability_safe(unit, self.elec_attr, 0)

		# Approval must fail
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._approve_contract(contract)
		self.assertIn("عداد كهرباء", str(ctx.exception))

	def test_10_approval_succeeds_when_capability_exists(self):
		"""approval succeeds when capability still exists."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")

		# Approval should succeed
		self._approve_contract(contract)
		status = frappe.db.get_value("Lease Contract", contract, "status")
		self.assertEqual(status, "active")

	# ======================================================================
	# Removal protection (11-17)
	# ======================================================================

	def _create_approved_metered_contract(self, unit, due_type_name, start_date=None, end_date=None):
		"""Create a draft contract with a metered charge, then approve it."""
		building = frappe.db.get_value("Rental Unit", unit, "building")
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, due_type_name, opening_reading="1000")
		self._approve_contract(contract)
		return contract

	def test_11_current_approved_metered_blocks_removal(self):
		"""current approved metered blocks removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		# Create an active contract
		self._create_approved_metered_contract(unit, self.elec_due_type)

		# Try to remove capability via the doc (should be blocked)
		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc.save(ignore_permissions=True)
		self.assertIn("عداد الكهرباء", str(ctx.exception))

	def test_12_future_approved_metered_blocks_removal(self):
		"""future approved metered blocks removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		# Create a future-dated active contract
		future_start = frappe.utils.add_days(frappe.utils.today(), 30)
		future_end = frappe.utils.add_days(frappe.utils.today(), 395)
		self._create_approved_metered_contract(unit, self.elec_due_type, future_start, future_end)

		# Try to remove capability
		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc.save(ignore_permissions=True)
		self.assertIn("عداد الكهرباء", str(ctx.exception))

	def test_13_draft_does_not_block_removal(self):
		"""Draft does not block removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		# Create a draft contract (not approved)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit)
		self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")

		# Removal should succeed (draft doesn't block)
		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		doc.save(ignore_permissions=True)  # Should not throw

	def test_14_cancelled_does_not_block_removal(self):
		"""cancelled does not block removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		# Create and approve, then cancel
		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		frappe.db.set_value("Lease Contract", contract, "status", "cancelled", update_modified=False)
		frappe.db.set_value("Lease Contract", contract, "cancelled_at", frappe.utils.now(), update_modified=False)

		# Removal should succeed
		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

	def test_15_evicted_does_not_block_removal(self):
		"""evicted does not block removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		frappe.db.set_value("Lease Contract", contract, "status", "evicted", update_modified=False)

		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

	def test_16_expired_does_not_block_removal(self):
		"""expired does not block removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		frappe.db.set_value("Lease Contract", contract, "status", "expired", update_modified=False)

		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

	def test_17_archived_does_not_block_removal(self):
		"""archived does not block removal."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")

		contract = self._create_approved_metered_contract(unit, self.elec_due_type)
		frappe.db.set_value("Lease Contract", contract, "status", "expired", update_modified=False)
		frappe.db.set_value("Lease Contract", contract, "is_archived", 1, update_modified=False)

		attr_val_name = frappe.db.get_value("Unit Attribute Value", {
			"unit": unit, "attribute": self.elec_attr,
		}, "name")
		doc = frappe.get_doc("Unit Attribute Value", attr_val_name)
		doc.value_check = 0
		doc.save(ignore_permissions=True)

	# ======================================================================
	# Renewal (18-24)
	# ======================================================================

	def _create_renewable_metered_contract(self, unit, due_type_name, opening="1000"):
		"""Create an approved metered contract that is eligible for renewal."""
		building = frappe.db.get_value("Rental Unit", unit, "building")
		# Contract must be within 30 days of end for renewal eligibility
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		tenant = self._create_tenant()
		contract = self._create_contract_draft(tenant, building, unit, start_date, end_date)
		self._add_metered_charge(contract, due_type_name, opening_reading=opening)
		self._approve_contract(contract)
		return contract

	def test_18_electricity_metered_renewal_preserves_metered(self):
		"""electricity metered renewal preserves metered when capability exists."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)

		contract = self._create_renewable_metered_contract(unit, self.elec_due_type)

		# After approval, freeze_metered_opening_readings sets unit reading to 1000.
		# Set a new current reading to verify renewal captures it.
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)
		self.assertEqual(float(metered[0].opening_meter_reading), 1500.0)

	def test_19_water_metered_renewal_preserves_metered(self):
		"""water metered renewal preserves metered when capability exists."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 1)

		contract = self._create_renewable_metered_contract(unit, self.water_due_type, opening="500")

		# After approval, set a new current reading
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "750")

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)
		self.assertEqual(float(metered[0].opening_meter_reading), 750.0)

	def test_20_electricity_metered_renewal_clears_calc_method(self):
		"""electricity metered renewal clears calculation_method when capability absent."""
		building = self._create_building()
		unit = self._create_unit(building)
		# Start with capability, create the contract, then remove it
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		contract = self._create_renewable_metered_contract(unit, self.elec_due_type)

		# Remove capability (use db_set to bypass removal protection — contract is active)
		# But active metered contract blocks removal, so we need to set it via db
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.elec_attr,
			}, "name"),
			"value_check", 0
		)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		# The charge should still exist
		elec_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "electricity"]
		self.assertEqual(len(elec_charges), 1)
		# But calculation_method should be None/empty (cleared)
		self.assertFalse(elec_charges[0].calculation_method)
		# opening_meter_reading should not be used
		self.assertFalse(elec_charges[0].opening_meter_reading)

	def test_21_water_metered_renewal_clears_calc_method(self):
		"""water metered renewal clears calculation_method when capability absent."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.water_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "750")

		contract = self._create_renewable_metered_contract(unit, self.water_due_type, opening="500")

		# Remove capability via db
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.water_attr,
			}, "name"),
			"value_check", 0
		)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		water_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "water"]
		self.assertEqual(len(water_charges), 1)
		self.assertFalse(water_charges[0].calculation_method)
		self.assertFalse(water_charges[0].opening_meter_reading)

	def test_22_charge_remains_present_when_capability_absent(self):
		"""electricity/water charge itself remains present when capability absent."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		contract = self._create_renewable_metered_contract(unit, self.elec_due_type)

		# Remove capability via db
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.elec_attr,
			}, "name"),
			"value_check", 0
		)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		# The electricity charge must still be present
		elec_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "electricity"]
		self.assertEqual(len(elec_charges), 1)
		# Responsibility and payment_by should be preserved
		self.assertEqual(elec_charges[0].responsibility, "tenant")
		self.assertEqual(elec_charges[0].payment_by, "landlord")

	def test_23_opening_reading_not_used_after_metered_cleared(self):
		"""opening reading not used after metered is cleared."""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		contract = self._create_renewable_metered_contract(unit, self.elec_due_type)

		# Remove capability via db
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.elec_attr,
			}, "name"),
			"value_check", 0
		)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		elec_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "electricity"]
		self.assertEqual(len(elec_charges), 1)
		# opening_meter_reading must be None/empty — not used after metered is cleared
		self.assertFalse(elec_charges[0].opening_meter_reading)
		# calculation_method must be None/empty
		self.assertFalse(elec_charges[0].calculation_method)

	def test_24_approval_revalidates_renewal_capability(self):
		"""approval revalidates renewal capability.

		Create a renewal draft with metered charge while capability exists.
		Remove capability. Approval must fail.
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1500")

		contract = self._create_renewable_metered_contract(unit, self.elec_due_type)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		# Verify the renewal has metered charge
		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		metered = [c for c in renewal_doc.contract_charges if c.calculation_method == "metered"]
		self.assertEqual(len(metered), 1)

		# Remove capability via db (bypass removal protection)
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.elec_attr,
			}, "name"),
			"value_check", 0
		)

		# Approval must fail
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._approve_contract(renewal_name)
		self.assertIn("عداد كهرباء", str(ctx.exception))

	# ======================================================================
	# Narrow scoping regression tests (25-28)
	# Verifies that allow_incomplete_due_types only relaxes the
	# "calculation_method required" check for the specific cleared due types.
	# All other charges still receive full validation.
	# ======================================================================

	def test_25_cleared_charge_allowed_invalid_charge_rejected(self):
		"""validate_contract_charges with allow_incomplete_due_types:
		- the cleared due type is allowed to be incomplete
		- another charge with invalid data is still rejected.
		"""
		from rental.rental.services.contract_charge_service import validate_contract_charges

		# Create a custom due type for the "other" charge
		other_due_type = self._create_custom_due_type("test_other_25", "Other Test 25")

		charges = [
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": None,  # incomplete — should be allowed
			},
			{
				"due_type": other_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": None,  # incomplete — NOT in allow set
			},
		]

		# Without allow_incomplete: both should be rejected
		with self.assertRaises(frappe.ValidationError):
			validate_contract_charges(charges, self.account)

		# With allow_incomplete for electricity only:
		# - electricity (in set) → allowed
		# - other (not in set) → rejected
		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_contract_charges(
				charges, self.account,
				allow_incomplete_due_types={self.elec_due_type},
			)
		self.assertIn("طريقة الاحتساب مطلوبة", str(ctx.exception))

	def test_26_cleared_charge_allowed_valid_charge_passes(self):
		"""validate_contract_charges with allow_incomplete_due_types:
		- the cleared due type is allowed to be incomplete
		- a valid unrelated charge passes normally.
		"""
		from rental.rental.services.contract_charge_service import validate_contract_charges

		other_due_type = self._create_custom_due_type("test_other_26", "Other Test 26")

		charges = [
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": None,  # incomplete — should be allowed
			},
			{
				"due_type": other_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "fixed_periodic",
				"amount": 50,
				"frequency": "monthly",
				"commitment_timing": "start",
			},
		]

		result = validate_contract_charges(
			charges, self.account,
			contract_start_date=frappe.utils.today(),
			contract_end_date=frappe.utils.add_days(frappe.utils.today(), 365),
			allow_incomplete_due_types={self.elec_due_type},
		)

		# Both charges should be in the result
		self.assertEqual(len(result), 2)
		# The incomplete charge should have calculation_method=None
		elec = [c for c in result if c["due_type"] == self.elec_due_type][0]
		self.assertIsNone(elec["calculation_method"])
		# The valid charge should have calculation_method=fixed_periodic
		other = [c for c in result if c["due_type"] == other_due_type][0]
		self.assertEqual(other["calculation_method"], "fixed_periodic")

	def test_27_cleared_charge_still_validates_other_rules(self):
		"""The cleared charge still gets validated for other rules
		(duplicate due type, invalid responsibility, etc.).
		"""
		from rental.rental.services.contract_charge_service import validate_contract_charges

		# Two charges with the SAME due type — one incomplete, one valid
		# This should fail because of duplicate due type, even with allow_incomplete
		charges = [
			{
				"due_type": self.elec_due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": None,  # incomplete
			},
			{
				"due_type": self.elec_due_type,  # duplicate!
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "fixed_periodic",
				"amount": 50,
				"frequency": "monthly",
				"commitment_timing": "start",
			},
		]

		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_contract_charges(
				charges, self.account,
				allow_incomplete_due_types={self.elec_due_type},
			)
		self.assertIn("تكرار", str(ctx.exception))  # "لا يمكن تكرار نوع الالتزام"

	def test_28_renewal_multiple_charges_cleared_allowed_invalid_rejected(self):
		"""Full renewal flow with multiple charges:
		- electricity metered (capability cleared) → incomplete, allowed in draft
		- water metered (capability exists) → valid, passes
		- approval rejects the incomplete charge until corrected
		"""
		building = self._create_building()
		unit = self._create_unit(building)
		self._set_capability(unit, self.elec_attr, 1)
		self._set_capability(unit, self.water_attr, 1)
		frappe.db.set_value("Rental Unit", unit, "current_electricity_meter_reading", "1000")
		frappe.db.set_value("Rental Unit", unit, "current_water_meter_reading", "500")

		# Create old contract with BOTH electricity and water metered charges
		# Must add both charges BEFORE approval (can't modify active contracts)
		building_name = frappe.db.get_value("Rental Unit", unit, "building")
		tenant = self._create_tenant()
		start_date = frappe.utils.add_days(frappe.utils.today(), -340)
		end_date = frappe.utils.add_days(frappe.utils.today(), 25)
		contract = self._create_contract_draft(tenant, building_name, unit, start_date, end_date)
		# Add electricity metered charge
		self._add_metered_charge(contract, self.elec_due_type, opening_reading="1000")
		# Add water metered charge
		self._add_metered_charge(contract, self.water_due_type, opening_reading="500")
		# Now approve the contract with both charges
		self._approve_contract(contract)

		# Remove electricity capability only (water still has capability)
		frappe.db.set_value("Unit Attribute Value",
			frappe.db.get_value("Unit Attribute Value", {
				"unit": unit, "attribute": self.elec_attr,
			}, "name"),
			"value_check", 0
		)

		from rental.rental.api.contract import renew_contract
		renewal_end = frappe.utils.add_days(frappe.utils.add_days(
			frappe.db.get_value("Lease Contract", contract, "end_date"), 1), 365)
		result = renew_contract(contract, end_date=renewal_end)
		renewal_name = result["contract"]["name"]
		self._created_contracts.append(renewal_name)

		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)

		# Electricity charge: should be present but with no calculation_method
		elec_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "electricity"]
		self.assertEqual(len(elec_charges), 1)
		self.assertFalse(elec_charges[0].calculation_method)

		# Water charge: should be present with metered calculation_method
		water_charges = [c for c in renewal_doc.contract_charges
			if frappe.db.get_value("Rental Due Type", c.due_type, "due_type_code") == "water"]
		self.assertEqual(len(water_charges), 1)
		self.assertEqual(water_charges[0].calculation_method, "metered")

		# Approval must fail because electricity charge is incomplete
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._approve_contract(renewal_name)
		self.assertIn("طريقة الاحتساب مطلوبة", str(ctx.exception))

		# Fix the electricity charge by setting a valid calculation_method
		# Use direct DB update to bypass validate() which rejects edits
		# to non-draft contracts (status may have been left non-draft by
		# the failed approval's atomicity revert)
		frappe.db.set_value("Lease Contract", renewal_name, "status", "draft", update_modified=False)
		renewal_doc = frappe.get_doc("Lease Contract", renewal_name)
		for charge in renewal_doc.contract_charges:
			if frappe.db.get_value("Rental Due Type", charge.due_type, "due_type_code") == "electricity":
				frappe.db.set_value("Contract Charge", charge.name, "calculation_method", "actual_bill")

		# Now approval should succeed (electricity=actual_bill, water=metered)
		self._approve_contract(renewal_name)
		status = frappe.db.get_value("Lease Contract", renewal_name, "status")
		self.assertEqual(status, "active")

	def _create_custom_due_type(self, code, name):
		"""Create a custom (non-system) Rental Due Type for testing."""
		existing = frappe.db.get_value("Rental Due Type", {"due_type_code": code}, "name")
		if existing:
			return existing
		dt = frappe.get_doc({
			"doctype": "Rental Due Type",
			"due_type_code": code,
			"due_type_name": name,
			"is_system": 0,
			"is_active": 1,
			"rental_account": self.account,
		})
		dt.insert(ignore_permissions=True)
		self._created_due_types.append(dt.name)
		return dt.name
