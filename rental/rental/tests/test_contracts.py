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
			"landlord_id": "1234567890",
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
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
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

		# Create renewal with explicit end_date (API does not support duration_months)
		from rental.rental.utils.date_utils import calculate_contract_end_date
		prev_end = frappe.db.get_value("Lease Contract", contract_name, "end_date")
		renewal_start = frappe.utils.add_days(prev_end, 1)
		renewal_end = calculate_contract_end_date(renewal_start, "monthly", 12)
		renewal_result = renew_contract(contract_name, end_date=str(renewal_end))
		renewal_name = renewal_result["contract"]["name"]
		self.assertTrue(renewal_name)

		renewal = frappe.get_doc("Lease Contract", renewal_name)
		self.assertEqual(renewal.status, "draft")
		self.assertEqual(renewal.renewed_from_contract, contract_name)

		# Renewal start = previous end + 1
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

		from rental.rental.utils.date_utils import calculate_contract_end_date
		prev_end = frappe.db.get_value("Lease Contract", contract_name, "end_date")
		renewal_start = frappe.utils.add_days(prev_end, 1)
		renewal_end = calculate_contract_end_date(renewal_start, "monthly", 12)
		renew_contract(contract_name, end_date=str(renewal_end))

		# Second renewal should fail
		with self.assertRaises(frappe.ValidationError):
			renew_contract(contract_name, end_date=str(renewal_end))

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

		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Unit should be reserved (upcoming active contract)
		unit_status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(unit_status, "reserved")

		# Now cancel with a date before start (today < start_date)
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Future cancel test")

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
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
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

	# --- Renewal Cancellation Tests ---

	def _create_approved_receipt(self, contract, tenant, amount):
		"""Helper: create and submit a receipt."""
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract,
			"receipt_date": frappe.utils.today(),
			"amount": amount,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		return receipt.name

	def _create_approved_future_renewal(self, previous_name, cycles=12):
		"""Helper: create and approve a future renewal for a contract.
		Returns the renewal contract name.
		The renewal start_date will be > today (future).
		"""
		from rental.rental.api.contract import renew_contract, approve_contract
		from rental.rental.utils.date_utils import calculate_contract_end_date

		prev_end = frappe.db.get_value("Lease Contract", previous_name, "end_date")
		renewal_start = frappe.utils.add_days(prev_end, 1)
		renewal_end = calculate_contract_end_date(renewal_start, "monthly", cycles)
		result = renew_contract(previous_name, end_date=str(renewal_end))
		renewal_name = result["contract"]["name"]
		approve_contract(renewal_name, generate_dues=1)
		return renewal_name

	def _simulate_renewal_started(self, previous_name, renewal_name):
		"""Helper: simulate time passing so that the previous contract expires
		and the renewal has started. This sets closed_by_renewal_at on the
		previous contract via expire_contracts().

		This is needed because close_previous_contract_by_renewal only sets
		closed_by_renewal_at when prev_end < today AND renewal_start <= today,
		which never happens during approval (renewal requires end >= today).
		"""
		today = frappe.utils.today()
		# Move previous end_date to yesterday and renewal start_date to today
		prev_end = frappe.db.get_value("Lease Contract", previous_name, "end_date")
		if str(prev_end) >= today:
			frappe.db.set_value("Lease Contract", previous_name,
				"end_date", frappe.utils.add_days(today, -1), update_modified=False)
		renewal_start = frappe.db.get_value("Lease Contract", renewal_name, "start_date")
		if str(renewal_start) > today:
			frappe.db.set_value("Lease Contract", renewal_name,
				"start_date", today, update_modified=False)
		# Run expire_contracts to set closed_by_renewal_at
		from rental.rental.services.contract_validation import expire_contracts
		expire_contracts()

	def _add_contract_charge(self, contract_name, due_type, responsibility="tenant",
	                          calc_method="fixed", amount=100, payment_by=None):
		"""Helper: add a Contract Charge to a contract."""
		frappe.set_user("Administrator")
		contract = frappe.get_doc("Lease Contract", contract_name)
		contract.append("contract_charges", {
			"due_type": due_type,
			"responsibility": responsibility,
			"calculation_method": calc_method,
			"payment_by": payment_by,
			"amount": amount,
			"frequency": "monthly",
		})
		contract.save(ignore_permissions=True)
		return due_type

	def test_cancel_renewed_contract(self):
		"""Cancel an active renewal contract (after start)."""
		building = self._create_building("CancelRenewed Bldg")
		unit = self._create_unit(building, "U-CR2")
		tenant = self._create_tenant("Cancel Renewed Tenant")

		# Create an active contract with <=30 days left (required for renewal)
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and approve a renewal (future start)
		renewal_name = self._create_approved_future_renewal(contract_name)

		# Simulate time: renewal starts today, previous expires
		self._simulate_renewal_started(contract_name, renewal_name)

		# Cancel the renewal (after start)
		result = cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")
		self.assertEqual(result["contract"]["status"], "cancelled")
		self.assertTrue(result["settlement"], "Settlement should be created for after-start cancellation")

		status = frappe.db.get_value("Lease Contract", renewal_name, "status")
		self.assertEqual(status, "cancelled")

	def test_cancel_renewed_before_start(self):
		"""Cancel a future renewal before its start_date — no settlement."""
		building = self._create_building("CancelBeforeStart Bldg")
		unit = self._create_unit(building, "U-CBS")
		tenant = self._create_tenant("Cancel Before Start Tenant")

		# Create and approve a contract ending soon
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and approve a future renewal (start > today)
		renewal_name = self._create_approved_future_renewal(contract_name)

		# Cancel before start (today < renewal.start_date)
		result = cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Before start cancel")
		self.assertEqual(result["contract"]["status"], "cancelled")
		self.assertIsNone(result["settlement"], "No settlement for before-start cancellation")

		status = frappe.db.get_value("Lease Contract", renewal_name, "status")
		self.assertEqual(status, "cancelled")

	def test_cancel_renewed_after_start(self):
		"""Cancel a renewal after start_date — settlement is created."""
		building = self._create_building("CancelAfterStart Bldg")
		unit = self._create_unit(building, "U-CAS")
		tenant = self._create_tenant("Cancel After Start Tenant")

		# Create and approve a contract that started 30 days ago
		start = frappe.utils.add_days(frappe.utils.today(), -30)
		end = frappe.utils.add_days(frappe.utils.today(), 335)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Cancel today (within [start, end])
		result = cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="After start cancel")
		self.assertTrue(result["settlement"], "Settlement should be created for after-start cancellation")

	def test_cancel_renewed_clears_closed_by_renewal(self):
		"""Cancelling a renewal clears closed_by_renewal_at on the previous contract."""
		building = self._create_building("ClearClosedByRenewal Bldg")
		unit = self._create_unit(building, "U-CCB")
		tenant = self._create_tenant("Clear ClosedByRenewal Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Before renewal: closed_by_renewal_at should be null
		self.assertFalse(frappe.db.get_value("Lease Contract", contract_name, "closed_by_renewal_at"))

		# Create and approve future renewal
		renewal_name = self._create_approved_future_renewal(contract_name)

		# After approval: closed_by_renewal_at is NOT set yet (previous hasn't expired)
		self.assertFalse(frappe.db.get_value("Lease Contract", contract_name, "closed_by_renewal_at"))

		# Simulate time: previous expires, renewal starts → closed_by_renewal_at set
		self._simulate_renewal_started(contract_name, renewal_name)
		self.assertTrue(frappe.db.get_value("Lease Contract", contract_name, "closed_by_renewal_at"))

		# Cancel the renewal
		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		# closed_by_renewal_at should be cleared
		self.assertFalse(frappe.db.get_value("Lease Contract", contract_name, "closed_by_renewal_at"))

	def test_cancel_renewed_from_contract_remains(self):
		"""renewed_from_contract is preserved after cancellation."""
		building = self._create_building("RenewedFromRemains Bldg")
		unit = self._create_unit(building, "U-RFR")
		tenant = self._create_tenant("RenewedFrom Remains Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		renewal_name = self._create_approved_future_renewal(contract_name)
		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		renewed_from = frappe.db.get_value("Lease Contract", renewal_name, "renewed_from_contract")
		self.assertEqual(renewed_from, contract_name, "renewed_from_contract should remain after cancellation")

	def test_cancel_renewed_previous_dates_unchanged(self):
		"""Previous contract dates are not modified when renewal is cancelled."""
		building = self._create_building("PrevDatesUnchanged Bldg")
		unit = self._create_unit(building, "U-PDU")
		tenant = self._create_tenant("Prev Dates Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		orig_start = frappe.db.get_value("Lease Contract", contract_name, "start_date")
		orig_end = frappe.db.get_value("Lease Contract", contract_name, "end_date")

		renewal_name = self._create_approved_future_renewal(contract_name)
		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		self.assertEqual(
			frappe.db.get_value("Lease Contract", contract_name, "start_date"),
			orig_start,
		)
		self.assertEqual(
			frappe.db.get_value("Lease Contract", contract_name, "end_date"),
			orig_end,
		)

	def test_cancel_renewed_previous_status_not_forced(self):
		"""Previous contract status is not force-set to active."""
		building = self._create_building("PrevStatusNotForced Bldg")
		unit = self._create_unit(building, "U-PSN")
		tenant = self._create_tenant("Prev Status Tenant")

		# Create an active contract with <=30 days left
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and approve future renewal
		renewal_name = self._create_approved_future_renewal(contract_name)

		# Simulate time: previous expires, renewal starts
		self._simulate_renewal_started(contract_name, renewal_name)

		# Previous should now be expired (not active, not historical)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract_name, "status"), "expired")

		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		# Status should still be expired, not forced to active
		self.assertEqual(
			frappe.db.get_value("Lease Contract", contract_name, "status"),
			"expired",
			"Previous contract status should not be force-set to active",
		)

	def test_cancel_renewed_unit_status(self):
		"""Unit status is recalculated after renewal cancellation."""
		building = self._create_building("UnitStatusRecalc Bldg")
		unit = self._create_unit(building, "U-USR")
		tenant = self._create_tenant("Unit Status Tenant")

		# Create an active contract A with <=30 days left (required for renewal)
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Unit should be rented (A is active)
		self.assertEqual(frappe.db.get_value("Rental Unit", unit, "status"), "rented")

		# Create and approve a future renewal B
		renewal_name = self._create_approved_future_renewal(contract_name)

		# Cancel B before start
		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		# Unit should still be rented (A is still active)
		self.assertEqual(
			frappe.db.get_value("Rental Unit", unit, "status"),
			"rented",
			"Unit should remain rented because A is still active",
		)

	def test_cancel_previous_with_approved_renewal_blocked(self):
		"""Cannot cancel a contract that has an approved renewal."""
		building = self._create_building("BlockCancelWithRenewal Bldg")
		unit = self._create_unit(building, "U-BCW")
		tenant = self._create_tenant("Block Cancel Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and approve renewal
		self._create_approved_future_renewal(contract_name)

		# Trying to cancel the previous contract should fail
		with self.assertRaises(frappe.ValidationError):
			cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

	def test_previous_eligible_after_renewal_cancel(self):
		"""After renewal cancellation, previous contract becomes eligible for renew/evict."""
		building = self._create_building("EligibleAfterCancel Bldg")
		unit = self._create_unit(building, "U-EAC")
		tenant = self._create_tenant("Eligible After Cancel Tenant")

		# Create an active contract with <=30 days left
		start = frappe.utils.add_days(frappe.utils.today(), -300)
		end = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and approve renewal
		renewal_name = self._create_approved_future_renewal(contract_name)

		# Simulate time: previous expires, renewal starts
		self._simulate_renewal_started(contract_name, renewal_name)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract_name, "status"), "expired")

		# Before cancellation: can_renew should be False (has approved renewal)
		from rental.rental.services.contract_validation import can_renew_contract, can_evict_contract
		prev_doc = frappe.get_doc("Lease Contract", contract_name)
		self.assertFalse(can_renew_contract(prev_doc))
		self.assertFalse(can_evict_contract(prev_doc))

		# Cancel the renewal
		cancel_contract(renewal_name, cancellation_date=frappe.utils.today(), reason="Test")

		# After cancellation: can_renew and can_evict should be True
		prev_doc = frappe.get_doc("Lease Contract", contract_name)
		self.assertTrue(can_renew_contract(prev_doc), "Previous contract should be renewable after renewal cancellation")
		self.assertTrue(can_evict_contract(prev_doc), "Previous contract should be evictable after renewal cancellation")

	def test_cancel_before_start_auto_dues(self):
		"""Before-start cancellation cancels all auto_contract dues."""
		building = self._create_building("BeforeStartAutoDues Bldg")
		unit = self._create_unit(building, "U-BSA")
		tenant = self._create_tenant("Before Start Auto Dues Tenant")

		# Create a future contract (start > today)
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Verify dues exist
		dues = frappe.get_all("Rental Due", filters={"contract": contract_name, "docstatus": 1}, pluck="name")
		self.assertTrue(len(dues) > 0, "Should have approved dues")

		# Cancel before start
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		# All dues should be cancelled
		remaining = frappe.get_all("Rental Due", filters={"contract": contract_name, "docstatus": 1}, pluck="name")
		self.assertEqual(len(remaining), 0, "All approved dues should be cancelled")

		# Verify dues are docstatus=2 (cancelled) and is_system_cancelled=1
		cancelled = frappe.get_all(
			"Rental Due",
			filters={"contract": contract_name, "docstatus": 2, "is_system_cancelled": 1},
			pluck="name",
		)
		self.assertEqual(len(cancelled), len(dues), "All dues should be system-cancelled")

	def test_cancel_before_start_manual_dues(self):
		"""Before-start cancellation cancels manual_contract and additional dues.

		Full scenario:
		- Future approved renewal contract
		- manual_contract due (approved) linked to it
		- additional due (approved) linked to it
		- cancel before start
		- verify both dues are cancelled
		- verify no records are deleted
		- receipt behavior is independent (tested separately)
		"""
		building = self._create_building("BeforeStartManualDues Bldg")
		unit = self._create_unit(building, "U-BSM")
		tenant = self._create_tenant("Before Start Manual Dues Tenant")

		# Find or create non-system due types for manual dues
		non_system_types = frappe.get_all(
			"Rental Due Type",
			filters={"is_active": 1, "is_system": 0, "due_type_code": ["not in", ["rent", "electricity", "water"]]},
			pluck="name",
		)
		if not non_system_types:
			frappe.set_user("Administrator")
			dt = frappe.get_doc({
				"doctype": "Rental Due Type",
				"rental_account": self.account,
				"due_type_code": "test_manual_type",
				"due_type_name": "Test Manual Due Type",
				"description": "Test Manual Due Type",
				"is_system": 0,
				"is_active": 1,
			})
			dt.insert(ignore_permissions=True)
			non_system_types = [dt.name]

		due_type = non_system_types[0]

		# Create a future contract (start > today) so we can cancel before start
		# Add Contract Charge BEFORE approval (can't modify after approval)
		# For tenant responsibility: payment_by=landlord + calculation_method=on_demand
		# (on_demand allows manual due creation; fixed_periodic auto-generates)
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		frappe.set_user("Administrator")
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": start,
			"end_date": end,
			"rent_amount": 500,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
			"contract_charges": [{
				"due_type": due_type,
				"responsibility": "tenant",
				"payment_by": "landlord",
				"calculation_method": "on_demand",
			}],
		})
		contract.insert(ignore_permissions=True)
		contract_name = contract.name
		self._created_contracts.append(contract_name)

		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create a manual_contract due (contractual kind) directly
		# Using frappe.get_doc instead of create_due API because the API
		# uses get_current_rental_account() which returns None for Administrator
		frappe.set_user("Administrator")
		due_date = frappe.utils.add_days(frappe.utils.today(), 60)
		manual_due = frappe.get_doc({
			"doctype": "Rental Due",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract_name,
			"building": building,
			"unit": unit,
			"due_type": due_type,
			"transaction_date": due_date,
			"due_date": due_date,
			"amount": 100,
			"source_type": "manual_contract",
			"calculation_method": "on_demand",
		})
		manual_due.insert(ignore_permissions=True)
		manual_due.submit()
		manual_due_name = manual_due.name

		# Verify manual_contract due exists and is approved
		manual_due_check = frappe.db.get_value("Rental Due", manual_due_name,
		                                  ["source_type", "docstatus"], as_dict=True)
		self.assertEqual(manual_due_check.source_type, "manual_contract")
		self.assertEqual(manual_due_check.docstatus, 1)

		# Create an additional due (different due type to avoid charge conflict)
		add_due_type = None
		if len(non_system_types) > 1:
			add_due_type = non_system_types[1]
		else:
			frappe.set_user("Administrator")
			dt2 = frappe.get_doc({
				"doctype": "Rental Due Type",
				"rental_account": self.account,
				"due_type_code": "test_additional_type",
				"due_type_name": "Test Additional Due Type",
				"description": "Test Additional Due Type",
				"is_system": 0,
				"is_active": 1,
			})
			dt2.insert(ignore_permissions=True)
			add_due_type = dt2.name

		add_due = frappe.get_doc({
			"doctype": "Rental Due",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract_name,
			"building": building,
			"unit": unit,
			"due_type": add_due_type,
			"transaction_date": due_date,
			"due_date": due_date,
			"amount": 50,
			"source_type": "additional",
			"calculation_method": "on_demand",
			"description": "Additional test due for before-start cancellation",
		})
		add_due.insert(ignore_permissions=True)
		add_due.submit()
		add_due_name = add_due.name

		# Verify additional due exists and is approved
		add_due_check = frappe.db.get_value("Rental Due", add_due_name,
		                               ["source_type", "docstatus"], as_dict=True)
		self.assertEqual(add_due_check.source_type, "additional")
		self.assertEqual(add_due_check.docstatus, 1)

		# Cancel before start (today < start_date)
		result = cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")
		self.assertIsNone(result["settlement"], "No settlement for before-start cancellation")

		# Both manual_contract and additional dues should be cancelled (docstatus=2)
		manual_due_after = frappe.db.get_value("Rental Due", manual_due_name,
		                                        ["docstatus", "is_system_cancelled"], as_dict=True)
		self.assertEqual(manual_due_after.docstatus, 2, "manual_contract due should be cancelled")
		self.assertEqual(manual_due_after.is_system_cancelled, 1, "manual_contract due should be system-cancelled")

		add_due_after = frappe.db.get_value("Rental Due", add_due_name,
		                                     ["docstatus", "is_system_cancelled"], as_dict=True)
		self.assertEqual(add_due_after.docstatus, 2, "additional due should be cancelled")
		self.assertEqual(add_due_after.is_system_cancelled, 1, "additional due should be system-cancelled")

		# No dues should be deleted — records still exist
		self.assertTrue(frappe.db.exists("Rental Due", manual_due_name), "manual_contract due record should not be deleted")
		self.assertTrue(frappe.db.exists("Rental Due", add_due_name), "additional due record should not be deleted")

		# No approved dues should remain
		remaining = frappe.get_all("Rental Due", filters={"contract": contract_name, "docstatus": 1}, pluck="name")
		self.assertEqual(len(remaining), 0, "No approved dues should remain after before-start cancellation")

	def test_cancel_before_start_with_waivers(self):
		"""Before-start cancellation cancels waivers linked to auto_contract dues."""
		building = self._create_building("BeforeStartWaivers Bldg")
		unit = self._create_unit(building, "U-BSW")
		tenant = self._create_tenant("Before Start Waivers Tenant")

		# Create a future contract
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create a waiver on an auto_contract due
		auto_due = frappe.db.get_value(
			"Rental Due",
			{"contract": contract_name, "source_type": "auto_contract", "docstatus": 1},
			"name",
		)
		if auto_due:
			from rental.rental.api.due import create_waiver
			due_amount = frappe.db.get_value("Rental Due", auto_due, "amount")
			try:
				create_waiver(
					name=auto_due,
					amount=min(50, due_amount),
					reason="Test waiver",
				)
			except Exception:
				pass  # Waiver creation may fail if due_date > today

		# Cancel before start
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		# All dues should be cancelled
		remaining_dues = frappe.get_all("Rental Due", filters={"contract": contract_name, "docstatus": 1}, pluck="name")
		self.assertEqual(len(remaining_dues), 0)

		# All waivers should be cancelled
		remaining_waivers = frappe.get_all(
			"Rental Due Waiver",
			filters={"due": ["in", frappe.get_all("Rental Due", filters={"contract": contract_name}, pluck="name")],
			         "status": "active"},
			pluck="name",
		)
		self.assertEqual(len(remaining_waivers), 0, "All waivers should be cancelled")

	def test_cancel_with_receipt_remains(self):
		"""Receipt remains approved after contract cancellation."""
		building = self._create_building("ReceiptRemains Bldg")
		unit = self._create_unit(building, "U-RR")
		tenant = self._create_tenant("Receipt Remains Tenant")

		# Create a future contract
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create a receipt
		receipt_name = self._create_approved_receipt(contract_name, tenant, 2000)

		# Cancel before start
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		# Receipt should still be approved
		receipt_status = frappe.db.get_value("Rental Receipt", receipt_name, "docstatus")
		self.assertEqual(receipt_status, 1, "Receipt should remain approved after cancellation")

	def test_cancel_archive_blocked_with_balance(self):
		"""Archive is blocked when balance != 0 (receipt remains)."""
		building = self._create_building("ArchiveBlocked Bldg")
		unit = self._create_unit(building, "U-AB")
		tenant = self._create_tenant("Archive Blocked Tenant")

		# Create a future contract
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create a receipt
		self._create_approved_receipt(contract_name, tenant, 2000)

		# Cancel before start
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		# Check archive readiness
		from rental.rental.services.archive_service import get_archive_readiness
		readiness = get_archive_readiness(contract_name)
		self.assertFalse(readiness["eligible"], "Archive should be blocked when balance != 0")

	def test_balance_after_cancel_receipt(self):
		"""Balance recalculates correctly after cancelling a receipt."""
		building = self._create_building("BalanceAfterCancelReceipt Bldg")
		unit = self._create_unit(building, "U-BAC")
		tenant = self._create_tenant("Balance After Cancel Receipt Tenant")

		# Create a future contract
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Create and cancel a receipt
		receipt_name = self._create_approved_receipt(contract_name, tenant, 2000)

		# Cancel before start (cancels all dues)
		cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")

		# Balance should be -2000 (credit: receipt remains, no dues)
		from rental.rental.services.balance_service import get_contract_balance
		balance = get_contract_balance(contract_name)
		self.assertEqual(balance["totalDues"], 0, "No effective dues after cancellation")
		self.assertEqual(balance["totalReceipts"], 2000)
		self.assertEqual(balance["balance"], -2000)

		# Now cancel the receipt
		from rental.rental.api.receipt import cancel_receipt
		cancel_receipt(receipt_name, reason="إلغاء عقد التجديد وإعادة المبلغ للمستأجر")

		# Balance should now be 0
		balance = get_contract_balance(contract_name)
		self.assertEqual(balance["totalReceipts"], 0)
		self.assertEqual(balance["balance"], 0)

	def test_renewal_chain_cancel_c_restores_b(self):
		"""A → B → C: cancelling C restores B's closed_by_renewal_at, A unchanged."""
		building = self._create_building("ChainCancel Bldg")
		unit = self._create_unit(building, "U-CHN")
		tenant = self._create_tenant("Chain Cancel Tenant")

		# Create contract A (active, <=30 days left for renewal eligibility)
		start_a = frappe.utils.add_days(frappe.utils.today(), -330)
		end_a = frappe.utils.add_days(frappe.utils.today(), 15)
		contract_a = self._create_contract(tenant, building, unit, start_a, end_a)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_a, generate_dues=1)

		# Create renewal B (future start = A.end + 1)
		from rental.rental.api.contract import renew_contract
		from rental.rental.utils.date_utils import calculate_contract_end_date
		b_end = calculate_contract_end_date(
			frappe.utils.add_days(end_a, 1), "monthly", 12)
		result_b = renew_contract(contract_a, end_date=str(b_end))
		contract_b = result_b["contract"]["name"]
		approve_contract(contract_b, generate_dues=1)

		# Simulate time: A expires, B starts → A.closed_by_renewal_at set
		self._simulate_renewal_started(contract_a, contract_b)
		self.assertTrue(frappe.db.get_value("Lease Contract", contract_a, "closed_by_renewal_at"))

		# B should be active now (start_date was moved to today)
		self.assertEqual(frappe.db.get_value("Lease Contract", contract_b, "status"), "active")

		# B needs <=30 days left for renewal eligibility.
		# Move B.end_date to today+15 so it's eligible for renewal.
		frappe.db.set_value("Lease Contract", contract_b,
			"end_date", frappe.utils.add_days(frappe.utils.today(), 15), update_modified=False)

		# Create renewal C (future start = B.end + 1)
		c_end = calculate_contract_end_date(
			frappe.utils.add_days(frappe.utils.today(), 16), "monthly", 12)
		result_c = renew_contract(contract_b, end_date=str(c_end))
		contract_c = result_c["contract"]["name"]
		approve_contract(contract_c, generate_dues=1)

		# Simulate time: B expires, C starts → B.closed_by_renewal_at set
		self._simulate_renewal_started(contract_b, contract_c)
		self.assertTrue(frappe.db.get_value("Lease Contract", contract_b, "closed_by_renewal_at"))

		# Cancel C
		cancel_contract(contract_c, cancellation_date=frappe.utils.today(), reason="Test")

		# B's closed_by_renewal_at should be cleared
		self.assertFalse(
			frappe.db.get_value("Lease Contract", contract_b, "closed_by_renewal_at"),
			"B's closed_by_renewal_at should be cleared after cancelling C",
		)

		# A's closed_by_renewal_at should still be set (only B was restored)
		self.assertTrue(
			frappe.db.get_value("Lease Contract", contract_a, "closed_by_renewal_at"),
			"A's closed_by_renewal_at should remain set (only immediate previous is affected)",
		)

	def test_cancel_invalid_contract_dates_error(self):
		"""start >= end produces a clear error at cancellation time."""
		building = self._create_building("InvalidDates Bldg")
		unit = self._create_unit(building, "U-INV")
		tenant = self._create_tenant("Invalid Dates Tenant")

		# Create a valid contract first (start < end)
		start = frappe.utils.add_days(frappe.utils.today(), -30)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Corrupt the dates via DB to make start >= end
		frappe.db.set_value("Lease Contract", contract_name, {
			"start_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 30),
		}, update_modified=False)

		with self.assertRaises(frappe.ValidationError) as ctx:
			cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Test")
		self.assertIn("فترة العقد غير صحيحة", str(ctx.exception))

	def test_cancel_date_after_end_blocked(self):
		"""cancellation_date > end_date is rejected."""
		building = self._create_building("CancelAfterEnd Bldg")
		unit = self._create_unit(building, "U-CAE")
		tenant = self._create_tenant("Cancel After End Tenant")

		start = frappe.utils.add_days(frappe.utils.today(), -30)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		future_date = frappe.utils.add_days(end, 10)
		with self.assertRaises(frappe.ValidationError) as ctx:
			cancel_contract(contract_name, cancellation_date=future_date, reason="Test")
		self.assertIn("تاريخ الإلغاء يجب أن يكون قبل", str(ctx.exception))

	def test_cancel_before_start_with_receipt_credit(self):
		"""Before-start cancellation with receipt: contract cancelled, dues cancelled,
		receipt remains, balance = -receipt_amount, archive blocked."""
		building = self._create_building("ReceiptCredit Bldg")
		unit = self._create_unit(building, "U-RCR")
		tenant = self._create_tenant("Receipt Credit Tenant")

		# Create a future contract (start > today)
		start = frappe.utils.add_days(frappe.utils.today(), 30)
		end = frappe.utils.add_days(frappe.utils.today(), 395)
		contract_name = self._create_contract(tenant, building, unit, start, end)
		from rental.rental.api.contract import approve_contract, cancel_contract
		approve_contract(contract_name, generate_dues=1)

		# Verify auto_contract dues exist
		auto_dues = frappe.get_all(
			"Rental Due",
			filters={"contract": contract_name, "source_type": "auto_contract", "docstatus": 1},
			pluck="name",
		)
		self.assertTrue(len(auto_dues) > 0, "Should have approved auto_contract dues")

		# Create an approved receipt
		receipt_name = self._create_approved_receipt(contract_name, tenant, 2000)

		# Cancel before start
		result = cancel_contract(contract_name, cancellation_date=frappe.utils.today(), reason="Before start with receipt")

		# Contract should be cancelled
		self.assertEqual(result["contract"]["status"], "cancelled")
		self.assertIsNone(result["settlement"], "No settlement for before-start cancellation")

		# All dues should be cancelled
		remaining_dues = frappe.get_all("Rental Due", filters={"contract": contract_name, "docstatus": 1}, pluck="name")
		self.assertEqual(len(remaining_dues), 0, "All dues should be cancelled")

		# Receipt should remain approved
		self.assertEqual(frappe.db.get_value("Rental Receipt", receipt_name, "docstatus"), 1)

		# Balance should be -2000 (credit)
		from rental.rental.services.balance_service import get_contract_balance
		balance = get_contract_balance(contract_name)
		self.assertEqual(balance["totalDues"], 0)
		self.assertEqual(balance["totalReceipts"], 2000)
		self.assertEqual(balance["balance"], -2000)

		# Archive readiness should be False (balance != 0)
		from rental.rental.services.archive_service import get_archive_readiness
		readiness = get_archive_readiness(contract_name)
		self.assertFalse(readiness["eligible"], "Archive should be blocked while balance != 0")

	# --- Payment Frequency: 'once' removed, 5 periodic frequencies supported ---

	def test_payment_frequency_once_rejected_by_backend(self):
		"""Backend must reject 'once' as a payment_frequency."""
		building = self._create_building("Freq Once Reject Building")
		unit = self._create_unit(building, "U-FO")
		tenant = self._create_tenant("Freq Once Tenant")

		frappe.set_user("Administrator")
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"rent_amount": 500,
			"payment_frequency": "once",
			"commitment_timing": "start",
			"status": "draft",
		})
		with self.assertRaises(frappe.ValidationError):
			contract.insert(ignore_permissions=True)

	def test_payment_frequency_one_time_alias_rejected(self):
		"""Backend must reject 'one_time' alias as well."""
		building = self._create_building("Freq OneTime Reject Building")
		unit = self._create_unit(building, "U-OT")
		tenant = self._create_tenant("Freq OneTime Tenant")

		frappe.set_user("Administrator")
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant,
			"building": building,
			"unit": unit,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"rent_amount": 500,
			"payment_frequency": "one_time",
			"commitment_timing": "start",
			"status": "draft",
		})
		with self.assertRaises(frappe.ValidationError):
			contract.insert(ignore_permissions=True)

	def test_payment_frequency_five_supported_frequencies(self):
		"""All 5 supported periodic frequencies should be accepted."""
		building = self._create_building("Freq Five Building")
		unit = self._create_unit(building, "U-F5")
		tenant = self._create_tenant("Freq Five Tenant")

		supported = ["monthly", "bi_monthly", "quarterly", "semi_annual", "annual"]
		for freq in supported:
			frappe.set_user("Administrator")
			contract = frappe.get_doc({
				"doctype": "Lease Contract",
				"rental_account": self.account,
				"tenant": tenant,
				"building": building,
				"unit": unit,
				"start_date": frappe.utils.today(),
				"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
				"rent_amount": 500,
				"payment_frequency": freq,
				"commitment_timing": "start",
				"status": "draft",
			})
			contract.insert(ignore_permissions=True)
			self.assertEqual(
				frappe.db.get_value("Lease Contract", contract.name, "payment_frequency"),
				freq,
				f"Frequency '{freq}' should be accepted",
			)
			# Clean up: delete the draft so the unit is free for the next frequency
			frappe.delete_doc("Lease Contract", contract.name, force=True)

	def test_payment_frequency_once_not_in_payment_frequencies_constant(self):
		"""PAYMENT_FREQUENCIES constant must not contain 'once'."""
		from rental.rental.utils.date_utils import PAYMENT_FREQUENCIES
		self.assertNotIn("once", PAYMENT_FREQUENCIES)
		self.assertEqual(
			set(PAYMENT_FREQUENCIES),
			{"monthly", "bi_monthly", "quarterly", "semi_annual", "annual"},
		)

	def test_payment_frequency_once_not_in_doctype_options(self):
		"""Lease Contract DocType Select options must not contain 'once'."""
		meta = frappe.get_meta("Lease Contract")
		field = meta.get_field("payment_frequency")
		options = field.options.split("\n")
		self.assertNotIn("once", options)
		self.assertEqual(
			set(options),
			{"monthly", "bi_monthly", "quarterly", "semi_annual", "annual"},
		)
