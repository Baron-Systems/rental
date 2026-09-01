"""Tests for the archive-as-final-closure feature.

Covers:
  - Archive readiness (operational + financial balance == 0)
  - archive_contract rejects when balance != 0 or not operationally closed
  - Archived contract becomes read-only (no dues/receipts/waivers/eviction/
    cancellation-settlement/renewal mutations)
  - get_dues / get_receipts exclude archived contracts by default
  - Rental Receipt.contract is mandatory
  - Archived contracts cannot be re-archived
  - Archived contract status does not change
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from datetime import date, timedelta


class TestArchive(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_units = []
		cls._created_tenants = []
		cls._created_contracts = []
		cls._created_dues = []
		cls._created_receipts = []
		cls._created_waivers = []
		cls._created_evictions = []
		cls._created_settlements = []

		cls.owner = cls._create_test_user("archive_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Archive Test Account", cls.owner)
		cls._create_settings(cls.account)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for name in cls._created_settlements:
			if frappe.db.exists("Contract Cancellation Settlement", name):
				try:
					frappe.delete_doc("Contract Cancellation Settlement", name, force=True)
				except Exception:
					frappe.db.delete("Contract Cancellation Settlement", name)

		for name in cls._created_evictions:
			if frappe.db.exists("Rental Eviction", name):
				try:
					doc = frappe.get_doc("Rental Eviction", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Eviction", name, force=True)
				except Exception:
					frappe.db.delete("Rental Eviction", name)

		for name in cls._created_waivers:
			if frappe.db.exists("Rental Due Waiver", name):
				try:
					frappe.delete_doc("Rental Due Waiver", name, force=True)
				except Exception:
					frappe.db.delete("Rental Due Waiver", name)

		for name in cls._created_receipts:
			if frappe.db.exists("Rental Receipt", name):
				try:
					doc = frappe.get_doc("Rental Receipt", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Receipt", name, force=True)
				except Exception:
					pass

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
					# Clear archive flag so we can cancel/delete
					frappe.db.set_value("Lease Contract", name, "is_archived", 0, update_modified=False)
					doc = frappe.get_doc("Lease Contract", name)
					if doc.docstatus == 1:
						doc.cancel()
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

	def _setup_contract(self, rent=500, start_offset=-60, end_offset=30):
		"""Create a building, unit, tenant, and approved contract.

		By default creates an ACTIVE contract (start in past, end in future)
		so is_historical=0 and eviction is possible. For past contracts that
		are approved as expired+historical, pass end_offset < 0.
		"""
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"Arch Building {frappe.utils.random_string(5)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)

		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building.name,
			"unit_number": f"U-{frappe.utils.random_string(4)}",
			"unit_type": "apartment",
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)

		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"Arch Tenant {frappe.utils.random_string(5)}",
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)

		start = frappe.utils.add_days(frappe.utils.today(), start_offset)
		end = frappe.utils.add_days(frappe.utils.today(), end_offset)
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": self.account,
			"tenant": tenant.name,
			"building": building.name,
			"unit": unit.name,
			"start_date": start,
			"end_date": end,
			"rent_amount": rent,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
		})
		contract.insert(ignore_permissions=True)
		self._created_contracts.append(contract.name)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract.name, generate_dues=1)

		return {
			"building": building.name,
			"unit": unit.name,
			"tenant": tenant.name,
			"contract": contract.name,
		}

	def _expire_contract(self, contract_name):
		"""Manually set a contract to expired (not historical, not closed by renewal).

		This simulates a contract that was active and has naturally expired
		without being closed by a renewal.
		"""
		frappe.db.set_value("Lease Contract", contract_name, {
			"status": "expired",
			"end_date": frappe.utils.add_days(frappe.utils.today(), -1),
		}, update_modified=False)

	def _evict_contract(self, contract_name):
		"""Expire the contract first (if needed) then evict.

		Eviction requires status=expired or cancelled and is_historical=0.
		"""
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		if status == "active":
			self._expire_contract(contract_name)
		from rental.rental.api.eviction import create_eviction
		ev = create_eviction(contract=contract_name, notes="Test eviction")
		self._created_evictions.append(ev["eviction"])
		return ev

	def _get_first_due(self, contract_name):
		due = frappe.get_all(
			"Rental Due",
			filters={"contract": contract_name, "docstatus": 1},
			fields=["name", "amount"],
			order_by="due_date asc",
			limit=1,
		)
		return due[0] if due else None

	def _create_receipt(self, contract, tenant, amount):
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
		self._created_receipts.append(receipt.name)
		return receipt.name

	# --- Archive readiness ---

	def test_readiness_active_contract_not_eligible(self):
		"""An active contract is not operationally closed → not eligible."""
		ctx = self._setup_contract(start_offset=0, end_offset=365)
		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertFalse(r["eligible"])
		self.assertFalse(r["operationally_closed"])

	def test_readiness_evicted_with_balance_not_eligible(self):
		"""Evicted but balance != 0 → not eligible (financially not closed)."""
		ctx = self._setup_contract()
		self._evict_contract(ctx["contract"])
		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertTrue(r["operationally_closed"])
		self.assertFalse(r["financially_closed"])
		self.assertFalse(r["eligible"])
		self.assertTrue(any("رصيد" in reason for reason in r["reasons"]))

	def test_readiness_evicted_balance_zero_eligible(self):
		"""Evicted + balance == 0 → eligible."""
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		# Pay off all dues
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertTrue(r["operationally_closed"])
		self.assertTrue(r["financially_closed"])
		self.assertTrue(r["eligible"])

	def test_readiness_expired_not_closed_by_renewal_not_eligible(self):
		"""Expired but not historical and not closed by renewal → not eligible."""
		ctx = self._setup_contract(start_offset=-60, end_offset=30)
		# Expire it (active → expired, is_historical stays 0)
		self._expire_contract(ctx["contract"])
		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertFalse(r["operationally_closed"])
		self.assertFalse(r["eligible"])

	def test_readiness_expired_historical_eligible(self):
		"""Expired + historical + balance 0 → eligible."""
		# Past contract → approved as expired + is_historical=1
		ctx = self._setup_contract(start_offset=-60, end_offset=-30)

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		if bal["balance"] > 0:
			self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertTrue(r["operationally_closed"])
		self.assertTrue(r["eligible"])

	# --- archive_contract ---

	def test_archive_evicted_balance_zero_succeeds(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		is_archived = frappe.db.get_value("Lease Contract", ctx["contract"], "is_archived")
		archived_at = frappe.db.get_value("Lease Contract", ctx["contract"], "archived_at")
		self.assertTrue(is_archived)
		self.assertTrue(archived_at)

	def test_archive_evicted_with_balance_fails(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.archive_service import archive_contract
		with self.assertRaises(frappe.ValidationError):
			archive_contract(ctx["contract"])

		is_archived = frappe.db.get_value("Lease Contract", ctx["contract"], "is_archived")
		self.assertFalse(is_archived)

	def test_archive_active_contract_fails(self):
		ctx = self._setup_contract(start_offset=0, end_offset=365)
		from rental.rental.services.archive_service import archive_contract
		with self.assertRaises(frappe.ValidationError):
			archive_contract(ctx["contract"])

	def test_archive_does_not_change_status(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		status = frappe.db.get_value("Lease Contract", ctx["contract"], "status")
		self.assertEqual(status, "evicted")

	def test_cannot_re_archive_archived_contract(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Second archive should fail
		with self.assertRaises(frappe.ValidationError):
			archive_contract(ctx["contract"])

	# --- Read-only protection ---

	def test_archived_contract_cannot_create_due(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Try to create a manual due
		from rental.rental.api.due import create_due
		with self.assertRaises(frappe.ValidationError):
			create_due(
				contract=ctx["contract"],
				due_type=frappe.db.get_value("Rental Due Type", {"due_type_code": "rent"}, "name"),
				due_date=frappe.utils.today(),
				amount=100,
			)

	def test_archived_contract_cannot_create_receipt(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		from rental.rental.api.receipt import create_receipt
		with self.assertRaises(frappe.ValidationError):
			create_receipt(
				tenant=ctx["tenant"],
				contract=ctx["contract"],
				receipt_date=frappe.utils.today(),
				amount=50,
				payment_method="cash",
			)

	def test_archived_contract_cannot_create_waiver(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		# Don't pay — leave a balance so there's a due to waive, then archive
		# by waiving the balance to zero instead.
		due = self._get_first_due(ctx["contract"])
		# Create a waiver to bring balance to 0
		from rental.rental.api.due import create_waiver
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		# Waive all dues to bring balance to 0
		dues = frappe.get_all("Rental Due", filters={"contract": ctx["contract"], "docstatus": 1}, pluck="name")
		for d in dues:
			amt = frappe.db.get_value("Rental Due", d, "amount")
			try:
				wname = create_waiver(d, amount=amt, reason="test")
				self._created_waivers.append(wname)
			except Exception:
				pass

		bal = get_contract_balance(ctx["contract"])
		self.assertTrue(abs(bal["balance"]) < 0.01, f"Balance should be 0, got {bal['balance']}")

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Now try to create another waiver — should fail
		if due:
			with self.assertRaises(frappe.ValidationError):
				create_waiver(due["name"], amount=10, reason="test")

	def test_archived_contract_cannot_create_eviction(self):
		ctx = self._setup_contract(rent=500)
		# Evict, settle, archive
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Try to create another eviction
		from rental.rental.api.eviction import create_eviction
		with self.assertRaises(frappe.ValidationError):
			create_eviction(contract=ctx["contract"], notes="test")

	def test_archived_contract_cannot_be_edited(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		contract = frappe.get_doc("Lease Contract", ctx["contract"])
		contract.rent_amount = 999
		with self.assertRaises(frappe.ValidationError):
			contract.save(ignore_permissions=True)

	def test_archived_contract_cannot_be_deleted(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Lease Contract", ctx["contract"], ignore_permissions=True)

	# --- Rental Receipt.contract mandatory ---

	def test_receipt_without_contract_rejected(self):
		ctx = self._setup_contract(rent=500)
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			# No contract
			"receipt_date": frappe.utils.today(),
			"amount": 100,
			"payment_method": "cash",
		})
		with self.assertRaises(frappe.ValidationError):
			receipt.insert(ignore_permissions=True)

	# --- get_dues / get_receipts exclude archived ---

	def test_get_dues_excludes_archived_by_default(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		from rental.rental.api.due import get_dues
		result = get_dues()
		contract_names = [d["contract"] for d in result.get("dues", [])]
		self.assertNotIn(ctx["contract"], contract_names)

	def test_get_dues_includes_archived_when_contract_specified(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		from rental.rental.api.due import get_dues
		result = get_dues(contract=ctx["contract"])
		contract_names = [d["contract"] for d in result.get("dues", [])]
		self.assertIn(ctx["contract"], contract_names)

	def test_get_receipts_excludes_archived_by_default(self):
		ctx = self._setup_contract(rent=500)
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		from rental.rental.api.receipt import get_receipts
		result = get_receipts()
		contract_names = [r["contract"] for r in result.get("receipts", [])]
		self.assertNotIn(ctx["contract"], contract_names)

	# --- Inspection of legacy archived contracts ---

	def test_inspect_archived_contracts_returns_list(self):
		from rental.rental.services.archive_service import inspect_archived_contracts
		report = inspect_archived_contracts()
		self.assertIsInstance(report, list)
		# Each entry has the expected fields
		for entry in report:
			self.assertIn("name", entry)
			self.assertIn("meets_new_rules", entry)
			self.assertIn("operationally_closed", entry)
			self.assertIn("financially_closed", entry)
			self.assertIn("balance", entry)
			self.assertIn("blocking_reasons", entry)

	# ================================================================
	# Additional regression tests (requested in review)
	# ================================================================

	def _archive_zero_balance_evicted(self, ctx):
		"""Helper: evict + settle balance to 0 + archive."""
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])
		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

	def test_archived_cancel_receipt_blocked(self):
		"""archived contract → cancel Receipt blocked."""
		ctx = self._setup_contract(rent=500)
		self._archive_zero_balance_evicted(ctx)

		# Find the receipt we created
		receipt_name = frappe.get_value("Rental Receipt", {"contract": ctx["contract"], "docstatus": 1}, "name")
		self.assertTrue(receipt_name)

		from rental.rental.api.receipt import cancel_receipt
		with self.assertRaises(frappe.ValidationError):
			cancel_receipt(receipt_name, reason="test cancel")

	def test_archived_cancel_due_blocked(self):
		"""archived contract → cancel Due blocked."""
		ctx = self._setup_contract(rent=500)
		self._archive_zero_balance_evicted(ctx)

		# Find an approved due
		due_name = frappe.get_value("Rental Due", {"contract": ctx["contract"], "docstatus": 1}, "name")
		self.assertTrue(due_name)

		from rental.rental.api.due import cancel_due_api
		with self.assertRaises(frappe.ValidationError):
			cancel_due_api(due_name, reason="test cancel")

	def test_archived_cancel_waiver_blocked(self):
		"""archived contract → cancel Waiver blocked."""
		ctx = self._setup_contract(rent=500)
		# Create a waiver first, then archive
		from rental.rental.api.due import create_waiver
		due = self._get_first_due(ctx["contract"])
		wname = create_waiver(due["name"], amount=due["amount"], reason="test")
		self._created_waivers.append(wname)

		# Now settle remaining balance and archive
		self._evict_contract(ctx["contract"])
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		if bal["balance"] > 0:
			self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Try to cancel the waiver
		from rental.rental.api.due import cancel_waiver
		with self.assertRaises(frappe.ValidationError):
			cancel_waiver(due["name"], wname, reason="test cancel")

	def test_archived_cancellation_settlement_blocked(self):
		"""archived contract → Cancellation Settlement mutation/completion blocked."""
		ctx = self._setup_contract(rent=500, start_offset=0, end_offset=365)

		# Cancel the contract (creates a pending settlement)
		from rental.rental.api.contract import cancel_contract
		cancel_contract(ctx["contract"], cancellation_date=frappe.utils.today(), reason="test")

		# Find the settlement
		settlement_name = frappe.get_value("Contract Cancellation Settlement", {"contract": ctx["contract"]}, "name")
		self.assertTrue(settlement_name)
		self._created_settlements.append(settlement_name)

		# Settle balance to 0 via receipts (so financial closure is met)
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		if bal["balance"] > 0:
			self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		# Manually mark settlement as completed (we're testing archive protection,
		# not the settlement completion flow itself)
		frappe.db.set_value("Contract Cancellation Settlement", settlement_name, "status", "completed", update_modified=False)

		# Now archive the contract (cancelled + completed settlement + balance 0)
		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])

		# Try to complete the settlement after archiving — should be blocked
		from rental.rental.api.cancellation_settlement import complete_settlement
		with self.assertRaises(frappe.ValidationError):
			complete_settlement(settlement_id=settlement_name)

	def test_get_receipts_includes_archived_when_contract_specified(self):
		"""archived contract → get_receipts(contract=...) still returns its historical receipts."""
		ctx = self._setup_contract(rent=500)
		self._archive_zero_balance_evicted(ctx)

		from rental.rental.api.receipt import get_receipts
		result = get_receipts(contract=ctx["contract"])
		contract_names = [r["contract"] for r in result.get("receipts", [])]
		self.assertIn(ctx["contract"], contract_names)

	def test_tenant_statement_contains_archived_movements(self):
		"""Tenant Statement still contains archived-contract historical movements."""
		ctx = self._setup_contract(rent=500)
		self._archive_zero_balance_evicted(ctx)

		from rental.rental.services.statement_service import get_tenant_statement
		stmt = get_tenant_statement(ctx["tenant"])
		lines = stmt.get("lines", [])
		# The statement should contain lines referencing the archived contract
		archived_lines = [l for l in lines if l.get("contract") == ctx["contract"]]
		self.assertTrue(len(archived_lines) > 0, "Statement should contain archived contract movements")

	def test_tenant_balance_correct_after_archiving_zero_balance(self):
		"""Tenant Balance remains mathematically correct after archiving a zero-balance contract."""
		ctx = self._setup_contract(rent=500)
		self._archive_zero_balance_evicted(ctx)

		from rental.rental.services.balance_service import get_tenant_balance
		bal = get_tenant_balance(ctx["tenant"])
		# Archived contract has balance 0, so tenant balance should be 0
		self.assertTrue(abs(bal["balance"]) < 0.01, f"Tenant balance should be 0, got {bal['balance']}")

	def test_cancelled_completed_settlement_zero_balance_archive_allowed(self):
		"""cancelled + completed settlement + zero balance → archive allowed."""
		ctx = self._setup_contract(rent=500, start_offset=0, end_offset=365)

		# Cancel the contract
		from rental.rental.api.contract import cancel_contract
		cancel_contract(ctx["contract"], cancellation_date=frappe.utils.today(), reason="test")

		settlement_name = frappe.get_value("Contract Cancellation Settlement", {"contract": ctx["contract"]}, "name")
		self._created_settlements.append(settlement_name)

		# Pay off all dues with receipts to bring balance to 0
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		if bal["balance"] > 0:
			self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		# Manually mark settlement as completed (we're testing archive readiness,
		# not the settlement completion flow itself)
		frappe.db.set_value("Contract Cancellation Settlement", settlement_name, "status", "completed", update_modified=False)

		# Now check readiness — should be eligible
		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertTrue(r["operationally_closed"], f"Should be operationally closed, reasons: {r['reasons']}")
		self.assertTrue(r["financially_closed"], f"Should be financially closed, balance: {r['balance']}")
		self.assertTrue(r["eligible"], f"Should be eligible, reasons: {r['reasons']}")

		# Archive should succeed
		from rental.rental.services.archive_service import archive_contract
		archive_contract(ctx["contract"])
		self.assertTrue(frappe.db.get_value("Lease Contract", ctx["contract"], "is_archived"))

	def test_cancelled_pending_settlement_archive_blocked(self):
		"""cancelled + pending/incomplete settlement → archive blocked."""
		ctx = self._setup_contract(rent=500, start_offset=0, end_offset=365)

		# Cancel the contract (creates a pending settlement)
		from rental.rental.api.contract import cancel_contract
		cancel_contract(ctx["contract"], cancellation_date=frappe.utils.today(), reason="test")

		settlement_name = frappe.get_value("Contract Cancellation Settlement", {"contract": ctx["contract"]}, "name")
		self._created_settlements.append(settlement_name)

		# Settle balance to 0 (so only the operational closure fails)
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		if bal["balance"] > 0:
			self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"])

		# Check readiness — should NOT be eligible (settlement is pending)
		from rental.rental.services.archive_service import get_archive_readiness
		r = get_archive_readiness(ctx["contract"])
		self.assertFalse(r["eligible"])
		self.assertFalse(r["operationally_closed"])
		# The reason should mention settlement
		self.assertTrue(any("تسوية" in reason for reason in r["reasons"]),
			f"Reasons should mention settlement: {r['reasons']}")

		# Archive should fail
		from rental.rental.services.archive_service import archive_contract
		with self.assertRaises(frappe.ValidationError):
			archive_contract(ctx["contract"])
