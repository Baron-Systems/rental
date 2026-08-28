"""Tests for the contract lifecycle: create, approve, cancel, renew, evict, archive.

Ported test logic from the source-of-truth test suite.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from datetime import date, timedelta


class TestContracts(FrappeTestCase):
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

		cls.owner = cls._create_test_user("contract_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Contract Test Account", cls.owner)

		# Create settings for the account
		cls._create_settings(cls.account)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		# Delete contracts first
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
					# Direct DB delete as fallback (bypasses on_trash validation)
					frappe.db.delete("Lease Contract", name)

		for name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", name):
				try:
					frappe.delete_doc("Rental Tenant", name, force=True)
				except Exception:
					frappe.db.delete("Rental Tenant", name)

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
			"landlord_name": "Test Landlord",
			"landlord_id": "ID-123456",
			"landlord_phone": "0555-123-456",
			"landlord_address": "Test Address, Test City",
			"currency": "JOD",
		})
		settings.insert(ignore_permissions=True)

	def _create_building(self, name="Test Building"):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": name,
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_unit(self, building, unit_number="U-1"):
		frappe.set_user("Administrator")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building,
			"unit_number": unit_number,
			"unit_type": "apartment",
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	def _create_tenant(self, full_name="Test Tenant"):
		frappe.set_user("Administrator")
		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": full_name,
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)
		return tenant.name

	def _create_contract(self, tenant, building, unit, start_date=None, end_date=None, rent=500):
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

	# --- Contract CRUD ---

	def test_create_draft_contract(self):
		building = self._create_building("Contract CRUD Building")
		unit = self._create_unit(building, "U-CC")
		tenant = self._create_tenant("CRUD Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		contract = frappe.get_doc("Lease Contract", contract_name)

		self.assertEqual(contract.status, "draft")
		self.assertTrue(contract.contract_number)
		self.assertEqual(contract.rent_amount, 500)

	def test_only_draft_can_be_edited(self):
		building = self._create_building("Edit Test Building")
		unit = self._create_unit(building, "U-ET")
		tenant = self._create_tenant("Edit Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		contract = frappe.get_doc("Lease Contract", contract_name)

		# Should be editable as draft
		contract.rent_amount = 600
		contract.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract_name, "rent_amount"), 600)

	def test_only_draft_can_be_deleted(self):
		building = self._create_building("Delete Test Building")
		unit = self._create_unit(building, "U-DT")
		tenant = self._create_tenant("Delete Tenant")

		contract_name = self._create_contract(tenant, building, unit)

		# Approve first
		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		# Should not be deletable
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Lease Contract", contract_name, ignore_permissions=True)

	# --- Contract approval ---

	def test_approve_contract_generates_dues(self):
		building = self._create_building("Approve Dues Building")
		unit = self._create_unit(building, "U-AD")
		tenant = self._create_tenant("Approve Dues Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		contract = frappe.get_doc("Lease Contract", contract_name)
		self.assertEqual(contract.status, "active")

		# Check dues were generated
		dues = frappe.get_all("Rental Due", filters={"contract": contract_name})
		self.assertTrue(len(dues) > 0, "Dues should be generated on approval")

	def test_approve_sets_unit_rented(self):
		building = self._create_building("Unit Status Building")
		unit = self._create_unit(building, "U-US")
		tenant = self._create_tenant("Unit Status Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "rented")

	def test_approve_freezes_lessor_snapshot(self):
		building = self._create_building("Snapshot Building")
		unit = self._create_unit(building, "U-SN")
		tenant = self._create_tenant("Snapshot Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		snapshot = frappe.db.get_value("Lease Contract", contract_name, "lessor_snapshot")
		self.assertTrue(snapshot, "Lessor snapshot should be frozen on approval")

	# --- Overlap detection ---

	def test_overlap_prevents_approval(self):
		building = self._create_building("Overlap Building")
		unit = self._create_unit(building, "U-OL")
		tenant = self._create_tenant("Overlap Tenant 1")
		tenant2 = self._create_tenant("Overlap Tenant 2")

		# First contract
		c1 = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract
		approve_contract(c1, generate_dues=1)

		# Second overlapping contract
		c2 = self._create_contract(tenant2, building, unit)
		with self.assertRaises(frappe.ValidationError):
			approve_contract(c2, generate_dues=1)

	# --- Contract cancellation ---

	def test_cancel_active_contract(self):
		building = self._create_building("Cancel Building")
		unit = self._create_unit(building, "U-CN")
		tenant = self._create_tenant("Cancel Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		cancel_date = frappe.utils.today()
		cancel_contract(contract_name, cancellation_date=cancel_date, reason="Test cancellation")

		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		self.assertEqual(status, "cancelled")

		# Check settlement was created
		settlement = frappe.db.exists(
			"Contract Cancellation Settlement", {"contract": contract_name}
		)
		self.assertTrue(settlement, "Cancellation settlement should be created")

	# --- Contract expiration ---

	def test_expire_contracts(self):
		building = self._create_building("Expire Building")
		unit = self._create_unit(building, "U-EX")
		tenant = self._create_tenant("Expire Tenant")

		# Create a contract that ended in the past
		past_start = frappe.utils.add_days(frappe.utils.today(), -30)
		past_end = frappe.utils.add_days(frappe.utils.today(), -1)
		contract_name = self._create_contract(tenant, building, unit, past_start, past_end)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		# Status should be expired (past period)
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		self.assertEqual(status, "expired")

	# --- Renewal ---

	def test_renew_contract(self):
		building = self._create_building("Renew Building")
		unit = self._create_unit(building, "U-RN")
		tenant = self._create_tenant("Renew Tenant")

		# Create a contract that ends soon
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)

		from rental.rental.api.contract import approve_contract, renew_contract
		approve_contract(contract_name, generate_dues=1)

		# Create renewal
		renewal_result = renew_contract(contract_name, duration_months=12)
		renewal_name = renewal_result["contract"]["name"]
		self.assertTrue(renewal_name)

		renewal = frappe.get_doc("Lease Contract", renewal_name)
		self.assertEqual(renewal.status, "draft")
		self.assertEqual(renewal.renewed_from_contract, contract_name)

		# Renewal start = previous end + 1
		prev_end = frappe.db.get_value("Lease Contract", contract_name, "end_date")
		expected_start = frappe.utils.add_days(prev_end, 1)
		self.assertEqual(str(renewal.start_date), str(expected_start))

	def test_only_one_renewal_allowed(self):
		building = self._create_building("Single Renew Building")
		unit = self._create_unit(building, "U-SR")
		tenant = self._create_tenant("Single Renew Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)

		from rental.rental.api.contract import approve_contract, renew_contract
		approve_contract(contract_name, generate_dues=1)

		renew_contract(contract_name, duration_months=12)

		# Second renewal should fail
		with self.assertRaises(frappe.ValidationError):
			renew_contract(contract_name, duration_months=12)

	# --- Archive ---

	def test_archive_evicted_contract(self):
		building = self._create_building("Archive Building")
		unit = self._create_unit(building, "U-AR")
		tenant = self._create_tenant("Archive Tenant")

		# Create and approve a past contract
		start = frappe.utils.add_days(frappe.utils.today(), -60)
		end = frappe.utils.add_days(frappe.utils.today(), -30)
		contract_name = self._create_contract(tenant, building, unit, start, end)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		# Evict
		from rental.rental.api.eviction import create_eviction
		create_eviction(contract=contract_name, notes="Test eviction")

		# Archive
		from rental.rental.api.contract import archive_contract_api
		archive_contract_api(contract_name)

		is_archived = frappe.db.get_value("Lease Contract", contract_name, "is_archived")
		self.assertTrue(is_archived)

	# --- Unit status with cancelledAt ---

	def test_cancelled_after_start_keeps_unit_rented(self):
		"""A cancelled contract with cancelledAt >= startDate keeps unit rented."""
		building = self._create_building("CancelledRented Building")
		unit = self._create_unit(building, "U-CR")
		tenant = self._create_tenant("Cancelled Rented Tenant")

		contract_name = self._create_contract(tenant, building, unit)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Cancel today (which is >= startDate)
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "rented", "Cancelled-after-start should keep unit rented")

	def test_cancelled_before_start_does_not_keep_rented(self):
		"""A future-dated cancelled contract (cancelledAt < startDate) does NOT keep unit rented."""
		building = self._create_building("FutureCancel Building")
		unit = self._create_unit(building, "U-FC")
		tenant = self._create_tenant("Future Cancel Tenant")

		# Create a future contract
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 365)
		contract_name = self._create_contract(tenant, building, unit, start, end)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		# Unit should be reserved (upcoming active contract)
		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "reserved")

		# Now cancel with a date before start
		frappe.db.set_value("Lease Contract", contract_name, {
			"status": "cancelled",
			"cancelled_at": frappe.utils.now(),
			"cancellation_reason": "Future cancel test",
		}, update_modified=False)

		# Recalculate
		from rental.rental.services.contract_validation import recalculate_unit_status
		recalculate_unit_status(unit)

		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "empty", "Cancelled-before-start should not keep unit rented")

	# --- Account Isolation Tests (source: §4) ---

	def test_account_isolation_tenant_from_other_account(self):
		"""Account A cannot create a draft using a tenant from Account B."""
		# Create a second account
		owner2 = self._create_test_user("contract_owner2@test.com", "Rental Property Owner")
		account2 = self._create_test_account("Contract Test Account 2", owner2)

		# Create a tenant in account2
		frappe.set_user("Administrator")
		tenant2 = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": account2,
			"full_name": "Account B Tenant",
			"phone": "99999999",
		}).insert(ignore_permissions=True).name
		self._created_tenants.append(tenant2)

		# Create building/unit in account A
		building = self._create_building("Iso Building")
		unit = self._create_unit(building, "U-ISO")

		# Try to create a contract in account A using tenant from account B
		from rental.rental.api.contract import create_contract
		try:
			name = create_contract(
				tenant=tenant2,
				building=building,
				unit=unit,
				start_date=frappe.utils.today(),
				end_date=frappe.utils.add_days(frappe.utils.today(), 365),
				rent_amount=500,
				payment_frequency="monthly",
			)
			# If it was created, that's a bug — clean up and fail
			if frappe.db.exists("Lease Contract", name):
				frappe.delete_doc("Lease Contract", name, force=True)
			self.fail("Should not allow creating contract with tenant from another account")
		except frappe.exceptions.ValidationError:
			pass  # Expected

	def test_account_isolation_unit_from_other_account(self):
		"""Account A cannot create a draft using a unit from Account B."""
		owner2 = self._create_test_user("contract_owner3@test.com", "Rental Property Owner")
		account2 = self._create_test_account("Contract Test Account 3", owner2)

		frappe.set_user("Administrator")
		building2 = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": account2,
			"building_name": "Account B Building",
			"address": "Test",
		}).insert(ignore_permissions=True).name
		self._created_buildings.append(building2)

		unit2 = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account2,
			"building": building2,
			"unit_number": "U-B2",
			"unit_type": "apartment",
		}).insert(ignore_permissions=True).name
		self._created_units.append(unit2)

		tenant = self._create_tenant("Iso Tenant A")

		from rental.rental.api.contract import create_contract
		try:
			name = create_contract(
				tenant=tenant,
				building=building2,
				unit=unit2,
				start_date=frappe.utils.today(),
				end_date=frappe.utils.add_days(frappe.utils.today(), 365),
				rent_amount=500,
				payment_frequency="monthly",
			)
			if frappe.db.exists("Lease Contract", name):
				frappe.delete_doc("Lease Contract", name, force=True)
			self.fail("Should not allow creating contract with unit from another account")
		except frappe.exceptions.ValidationError:
			pass  # Expected

	# --- Duplicate Due Prevention Test (source: INV-CON-017) ---

	def test_duplicate_rent_generation_prevented(self):
		"""Approving a contract twice should not generate duplicate rent dues."""
		building = self._create_building("Dup Due Building")
		unit = self._create_unit(building, "U-DUP")
		tenant = self._create_tenant("Dup Due Tenant")

		contract_name = self._create_contract(tenant, building, unit)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		# Count rent dues
		rent_due_type = frappe.db.get_value("Rental Due Type", {"due_type_code": "rent"}, "name")
		dues_count = frappe.db.count("Rental Due", {
			"contract": contract_name,
			"source_type": "auto_contract",
			"due_type": rent_due_type,
		})
		self.assertGreater(dues_count, 0, "Rent dues should have been generated")

		# Try to generate again directly
		from rental.rental.services.due_generation_service import generate_contract_dues
		contract_doc = frappe.get_doc("Lease Contract", contract_name)
		try:
			generate_contract_dues(contract_doc, self.account, generate=True)
			self.fail("Should not allow duplicate rent due generation")
		except frappe.exceptions.ValidationError:
			pass  # Expected

	# --- Historical Contract Test (source: INV-CON-011) ---

	def test_historical_contract_does_not_affect_overlap(self):
		"""A historical contract should not block a new contract on the same unit."""
		building = self._create_building("Historical Building")
		unit = self._create_unit(building, "U-HIST")
		tenant = self._create_tenant("Historical Tenant")

		# Create a past-period contract (will become historical on approval)
		past_start = frappe.utils.add_days(frappe.utils.today(), -730)
		past_end = frappe.utils.add_days(frappe.utils.today(), -365)
		contract1 = self._create_contract(tenant, building, unit, past_start, past_end)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract1, generate_dues=0)

		# Verify it's historical
		is_hist = frappe.db.get_value("Lease Contract", contract1, "is_historical")
		self.assertEqual(is_hist, 1, "Past-period contract should be historical")

		# Now create a new contract on the same unit — should not be blocked
		contract2 = self._create_contract(
			tenant, building, unit,
			frappe.utils.today(),
			frappe.utils.add_days(frappe.utils.today(), 365),
		)
		# This should succeed (no overlap error)
		approve_contract(contract2, generate_dues=1)
		self.assertEqual(
			frappe.db.get_value("Lease Contract", contract2, "status"),
			"active",
		)

	# --- Approval Rollback Test (source: §13) ---

	def test_approval_rollback_on_failure(self):
		"""If approval fails after status change, contract should revert to draft."""
		building = self._create_building("Rollback Building")
		unit = self._create_unit(building, "U-RB")
		tenant = self._create_tenant("Rollback Tenant")

		contract_name = self._create_contract(tenant, building, unit)

		# Mock: make generate_contract_dues fail
		from unittest.mock import patch
		from rental.rental.api import contract as contract_api

		with patch(
			"rental.rental.api.contract.generate_contract_dues",
			side_effect=Exception("Simulated due generation failure"),
		):
			try:
				contract_api.approve_contract(contract_name, generate_dues=1)
				self.fail("Approval should have failed")
			except Exception:
				pass  # Expected

		# Contract should be reverted to draft
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		self.assertEqual(status, "draft", "Contract should revert to draft on approval failure")

		# Lessor snapshot should be cleared
		snapshot = frappe.db.get_value("Lease Contract", contract_name, "lessor_snapshot")
		self.assertIsNone(snapshot, "Lessor snapshot should be cleared on rollback")

	# --- Future Contract Test (source: INV-CON-008) ---

	def test_future_contract_sets_unit_reserved(self):
		"""An approved future contract should set unit status to reserved."""
		building = self._create_building("Future Building")
		unit = self._create_unit(building, "U-FUT")
		tenant = self._create_tenant("Future Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract_name, generate_dues=1)

		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "reserved", "Future contract should set unit to reserved")
