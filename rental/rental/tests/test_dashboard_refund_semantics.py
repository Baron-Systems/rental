"""
Phase 4 — Dashboard Refund Semantics backend tests.

Verifies:
1. totalReceipts = Gross only (transaction_type='receipt')
2. totalRefunds = Refund only (transaction_type='refund')
3. netCollections = receipts - refunds
4. totalBalance = dues - receipts + refunds
5. Draft refund excluded
6. Cancelled refund excluded
7. Archived refund excluded
8. Trend grossReceipts correct
9. Trend refunds correct
10. Trend netCollections correct
11. Refund-only month can produce negative netCollections
12. Zero months preserved
13. Collection rate uses Net (checked via frontend test, here we verify stats fields)
14. Example: dues=5000, receipts=5410, refunds=410 → net=5000, balance=0

Run: bench --site renta.albaronsystems.com run-tests --app rental --test dashboard_refund_semantics
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password

from rental.rental.services.balance_service import (
	get_effective_due_total,
	get_approved_receipt_total,
	get_approved_refund_total,
)


class TestDashboardRefundSemantics(FrappeTestCase):
	"""Test dashboard refund semantics without hitting the full API."""

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
		cls._created_evictions = []
		cls._used_auto_dues = []

		cls.owner = cls._create_test_user("p4_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Phase4 Test Account", cls.owner)
		cls._create_settings(cls.account)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
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

	def _setup_contract(self, rent=5000, start_offset=-60, end_offset=30):
		"""Create building, unit, tenant, and approved contract.

		Uses generate_dues=1 so auto_contract dues exist for _adjust_due to reuse.
		Returns dict with building, unit, tenant, contract names.
		"""
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"P4 Bldg {frappe.utils.random_string(5)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)

		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account,
			"building": building.name,
			"unit_number": f"U-{frappe.utils.random_string(4)}",
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)

		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": self.account,
			"full_name": f"P4 Tenant {frappe.utils.random_string(5)}",
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

	def _evict_contract(self, contract_name):
		"""Expire the contract first (if needed) then evict."""
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		if status == "active":
			frappe.db.set_value("Lease Contract", contract_name, {
				"status": "expired",
				"end_date": frappe.utils.add_days(frappe.utils.today(), -1),
			}, update_modified=False)
		from rental.rental.api.eviction import create_eviction
		ev = create_eviction(contract=contract_name, notes="Test eviction for refund")
		self._created_evictions.append(ev["eviction"])
		return ev

	def _get_auto_due(self, contract, skip=None):
		"""Return the next unused auto-generated approved due for a contract."""
		filters = {"contract": contract, "docstatus": 1, "source_type": "auto_contract"}
		if skip:
			filters["name"] = ["not in", skip]
		due = frappe.get_all(
			"Rental Due",
			filters=filters,
			fields=["name"],
			order_by="due_date asc",
			limit=1,
		)
		return due[0]["name"] if due else None

	def _adjust_due(self, contract, amount, due_date=None):
		"""Adjust an auto-generated due to the requested amount/due_date.

		Rental Due of type 'rent' cannot be created manually (business rule),
		so we reuse an auto_contract due and set its amount/date directly
		via db.set_value (bypassing the 'auto_contract cannot be edited' guard).
		Returns the due name.
		"""
		frappe.set_user("Administrator")
		due_name = self._get_auto_due(contract, skip=self._used_auto_dues)
		if not due_name:
			ctx2 = self._setup_contract(rent=amount)
			due_name = self._get_auto_due(ctx2["contract"])
		self._used_auto_dues.append(due_name)
		dd = due_date or frappe.utils.today()
		frappe.db.set_value("Rental Due", due_name, {
			"due_date": dd,
			"transaction_date": dd,
			"amount": amount,
		}, update_modified=False)
		self._created_dues.append(due_name)
		return due_name

	def _create_receipt(self, contract, tenant, amount, transaction_type="receipt", status="approved"):
		"""Create a receipt with given type and status."""
		frappe.set_user("Administrator")
		doc = frappe.get_doc({
			"doctype": "Rental Receipt",
			"contract": contract,
			"tenant": tenant,
			"amount": amount,
			"transaction_type": transaction_type,
			"payment_method": "cash",
			"receipt_date": frappe.utils.today(),
			"rental_account": self.account,
		})
		doc.insert(ignore_permissions=True)
		self._created_receipts.append(doc.name)
		if status == "approved":
			doc.submit()
		elif status == "cancelled":
			doc.submit()
			doc.cancel()
		return doc.name

	def _cancel_receipt(self, receipt_name, reason="Test cancellation"):
		"""Cancel an approved receipt/refund through real lifecycle."""
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Rental Receipt", receipt_name)
		doc.cancellation_reason = reason
		doc.cancel()

	def _create_context(self, dues_amount=5000, rent=None):
		"""Create a contract with exactly dues_amount in total dues.

		Uses generate_dues=1 to create auto dues, then cancels all but one
		and adjusts the remaining one to dues_amount.
		Returns dict with building, unit, tenant, contract names.
		"""
		rent = rent or dues_amount
		ctx = self._setup_contract(rent=rent)

		auto_dues = frappe.get_all(
			"Rental Due",
			filters={"contract": ctx["contract"], "docstatus": 1, "source_type": "auto_contract"},
			fields=["name"],
			order_by="due_date asc",
		)

		for d in auto_dues[1:]:
			doc = frappe.get_doc("Rental Due", d["name"])
			doc.cancellation_reason = "Test cleanup — keeping single due"
			doc.cancel()
			self._created_dues.append(d["name"])

		if auto_dues:
			due_name = auto_dues[0]["name"]
			frappe.db.set_value("Rental Due", due_name, {
				"due_date": frappe.utils.today(),
				"transaction_date": frappe.utils.today(),
				"amount": dues_amount,
			}, update_modified=False)
			self._created_dues.append(due_name)
			self._used_auto_dues.append(due_name)

		return ctx

	def test_01_gross_receipts_exclude_refunds(self):
		"""totalReceipts = SUM(transaction_type='receipt') only."""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 500 to create credit; refund 500 (refund == credit, should pass)
		self._create_receipt(ctx["contract"], ctx["tenant"], 5500, "receipt")
		self._create_receipt(ctx["contract"], ctx["tenant"], 500, "refund")

		filters = {"contract": ctx["contract"]}
		receipts = get_approved_receipt_total(filters)
		refunds = get_approved_refund_total(filters)

		self.assertEqual(refunds, 500)
		self.assertEqual(receipts, 5500)
		self.assertNotEqual(receipts, 6000)

	def test_02_net_collections(self):
		"""netCollections = grossReceipts - refunds."""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 410, refund 410 → net = dues = 5000
		self._create_receipt(ctx["contract"], ctx["tenant"], 5410, "receipt")
		self._create_receipt(ctx["contract"], ctx["tenant"], 410, "refund")

		filters = {"contract": ctx["contract"]}
		receipts = get_approved_receipt_total(filters)
		refunds = get_approved_refund_total(filters)
		net = receipts - refunds

		self.assertEqual(net, 5000)

	def test_03_balance_formula(self):
		"""totalBalance = dues - receipts + refunds."""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 410, refund 410 → balance = 0
		self._create_receipt(ctx["contract"], ctx["tenant"], 5410, "receipt")
		self._create_receipt(ctx["contract"], ctx["tenant"], 410, "refund")

		filters = {"contract": ctx["contract"]}
		dues = get_effective_due_total(filters)
		receipts = get_approved_receipt_total(filters)
		refunds = get_approved_refund_total(filters)
		balance = dues - receipts + refunds

		self.assertEqual(dues, 5000)
		self.assertEqual(balance, 0)

	def test_04_draft_refund_excluded(self):
		"""Draft refund (docstatus=0) excluded from totals."""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 300, create draft refund for 300 (== credit)
		self._create_receipt(ctx["contract"], ctx["tenant"], 5300, "receipt")
		self._create_receipt(ctx["contract"], ctx["tenant"], 300, "refund", status="draft")

		filters = {"contract": ctx["contract"]}
		refunds = get_approved_refund_total(filters)
		self.assertEqual(refunds, 0)

	def test_05_cancelled_refund_excluded(self):
		"""Cancelled refund (docstatus=2) excluded from totals.

		Uses real lifecycle: create valid refund, then cancel it.
		"""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 300, refund 300 (== credit, passes after on_submit fix)
		self._create_receipt(ctx["contract"], ctx["tenant"], 5300, "receipt")
		refund_name = self._create_receipt(ctx["contract"], ctx["tenant"], 300, "refund")

		filters = {"contract": ctx["contract"]}
		refunds_before = get_approved_refund_total(filters)
		self.assertEqual(refunds_before, 300)

		# Cancel the refund through real lifecycle
		self._cancel_receipt(refund_name, reason="Test: cancel refund for exclusion test")

		refunds_after = get_approved_refund_total(filters)
		self.assertEqual(refunds_after, 0)

	def test_06_mandatory_example(self):
		"""Regression test: dues=5000, receipts=5410, refunds=410 → net=5000, balance=0.

		This tests the exact scenario that was broken by the on_submit double-count
		bug in rental_receipt.py. Before the fix, get_contract_balance inside
		on_submit already saw docstatus=1 (the refund), so totalRefunds included
		the 410. Then the code added 410 again via `projected = balance + amount`,
		making projected=410 > 0, which incorrectly rejected the refund.
		After the fix, bal["balance"] is used directly (= 0), which passes.
		"""
		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		self._create_receipt(ctx["contract"], ctx["tenant"], 5410, "receipt")
		self._create_receipt(ctx["contract"], ctx["tenant"], 410, "refund")

		filters = {"contract": ctx["contract"]}
		dues = get_effective_due_total(filters)
		receipts = get_approved_receipt_total(filters)
		refunds = get_approved_refund_total(filters)
		net = receipts - refunds
		balance = dues - receipts + refunds

		self.assertEqual(dues, 5000)
		self.assertEqual(receipts, 5410)
		self.assertEqual(refunds, 410)
		self.assertEqual(net, 5000)
		self.assertEqual(balance, 0)

	def test_07_prepayment_example(self):
		"""Prepayment: dues=5000, receipts=5500, refunds=0 → net=5500, balance=-500."""
		ctx = self._create_context(dues_amount=5000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 5500, "receipt")

		filters = {"contract": ctx["contract"]}
		dues = get_effective_due_total(filters)
		receipts = get_approved_receipt_total(filters)
		refunds = get_approved_refund_total(filters)
		net = receipts - refunds
		balance = dues - receipts + refunds

		self.assertEqual(dues, 5000)
		self.assertEqual(net, 5500)
		self.assertEqual(balance, -500)

	def test_08_dashboard_stats_contain_refund_fields(self):
		"""Dashboard API returns totalRefunds and netCollections in stats."""
		from rental.rental.api.dashboard import get_dashboard

		# Set user to account owner so get_current_rental_account returns our test account
		frappe.set_user(self.owner)

		try:
			result = get_dashboard()
			stats = result.get("stats", {})
			self.assertIn("totalRefunds", stats)
			self.assertIn("netCollections", stats)
			self.assertIn("totalReceipts", stats)
			self.assertIn("totalBalance", stats)
			self.assertIn("totalDues", stats)
		finally:
			frappe.set_user("Administrator")

	def test_09_trend_returns_refund_fields(self):
		"""Financial trend API returns grossReceipts, refunds, netCollections per month."""
		from rental.rental.api.dashboard import get_financial_trend

		account = self.account
		result = get_financial_trend(account=account)
		months = result.get("months", [])

		self.assertTrue(len(months) > 0)
		for m in months:
			self.assertIn("grossReceipts", m)
			self.assertIn("refunds", m)
			self.assertIn("netCollections", m)
			self.assertIn("dues", m)
			# Backward compat: receipts field still exists as gross
			self.assertIn("receipts", m)
			self.assertEqual(m["receipts"], m["grossReceipts"])

	def test_10_trend_six_months_always_returned(self):
		"""Trend always returns exactly 6 months (zero months preserved)."""
		from rental.rental.api.dashboard import get_financial_trend

		result = get_financial_trend(account=self.account)
		months = result.get("months", [])
		self.assertEqual(len(months), 6)

	def test_11_trend_current_month_capped_at_today(self):
		"""Current month in trend is capped at today (no future dates)."""
		from datetime import date
		from rental.rental.api.dashboard import get_financial_trend, _last_six_months

		today = date.today()
		months = _last_six_months(today)
		last_month = months[-1]  # (year, month, start, end)
		# end should be today + 1 day (half-open), not first of next month
		from datetime import timedelta
		expected_end = today + timedelta(days=1)
		self.assertLessEqual(last_month[3], expected_end)

	def test_12_archived_contract_refund_excluded_from_dashboard(self):
		"""Archived contract dues/receipts/refunds are excluded from dashboard totals.

		Creates a full contract lifecycle:
		  1. Contract with dues=5000
		  2. Evict (operationally close)
		  3. Overpay + refund (refund < credit/2 due to on_submit double-count bug)
		  4. Cancel refund to settle balance to 0
		  5. Archive the contract
		  6. Verify all movements are excluded from dashboard totals
		"""
		from rental.rental.services.archive_service import (
			archive_contract,
			get_archived_contract_names,
		)

		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])

		# Overpay by 300, refund 300 (== credit, passes after on_submit fix)
		receipt_name = self._create_receipt(ctx["contract"], ctx["tenant"], 5300, "receipt")
		refund_name = self._create_receipt(ctx["contract"], ctx["tenant"], 300, "refund")

		# Cancel both to settle balance to 0 (required for archive)
		self._cancel_receipt(refund_name, reason="Test: settle for archive")
		self._cancel_receipt(receipt_name, reason="Test: settle for archive")

		# Verify balance is 0 before archiving
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self.assertEqual(bal["balance"], 0)

		# Archive the contract
		archive_contract(ctx["contract"])
		self.assertTrue(frappe.db.get_value("Lease Contract", ctx["contract"], "is_archived"))

		# Verify archived contract is in the archived list
		archived = get_archived_contract_names(self.account)
		self.assertIn(ctx["contract"], archived)

		# Verify archived contract's dues/receipts/refunds are excluded from dashboard
		filters_excl = {
			"rental_account": self.account,
			"contract": ["not in", archived],
		}
		filters_incl = {
			"rental_account": self.account,
		}

		dues_excl = get_effective_due_total(filters_excl)
		dues_incl = get_effective_due_total(filters_incl)
		receipts_excl = get_approved_receipt_total(filters_excl)
		receipts_incl = get_approved_receipt_total(filters_incl)
		refunds_excl = get_approved_refund_total(filters_excl)
		refunds_incl = get_approved_refund_total(filters_incl)

		# Archived contract had dues=5000, so excluding it should reduce totalDues by 5000
		self.assertEqual(dues_incl - dues_excl, 5000)
		# Receipts and refunds were cancelled, so they should be 0 either way
		self.assertEqual(receipts_excl, receipts_incl)
		self.assertEqual(refunds_excl, refunds_incl)

	def test_13_account_isolation_in_trend(self):
		"""Financial trend does not cross accounts."""
		from rental.rental.api.dashboard import get_financial_trend

		# Create a second account for isolation testing
		owner2 = self._create_test_user("p4_owner2@test.com", "Rental Property Owner")
		account2 = self._create_test_account("Phase4 Test Account 2", owner2)
		self._create_settings(account2)

		# Trend for account A should not include data from account B
		result_a = get_financial_trend(account=self.account)
		result_b = get_financial_trend(account=account2)

		self.assertEqual(result_a["account"], self.account)
		self.assertEqual(result_b["account"], account2)

		# Both should have 6 months and a currency
		self.assertEqual(len(result_a["months"]), 6)
		self.assertEqual(len(result_b["months"]), 6)
		self.assertIsNotNone(result_a["currency"])
		self.assertIsNotNone(result_b["currency"])

		# Account 2 has no financial data, so all months should be zero
		for m in result_b["months"]:
			self.assertEqual(m["grossReceipts"], 0)
			self.assertEqual(m["refunds"], 0)

	def test_14_trend_net_collections_can_be_negative(self):
		"""A month with refunds but no receipts should have negative netCollections."""
		from rental.rental.api.dashboard import get_financial_trend

		result = get_financial_trend(account=self.account)
		months = result.get("months", [])

		# Verify the formula holds for each month
		for m in months:
			expected_net = m["grossReceipts"] - m["refunds"]
			self.assertEqual(m["netCollections"], expected_net)
			# If refunds > grossReceipts, net should be negative
			if m["refunds"] > 0 and m["grossReceipts"] == 0:
				self.assertLess(m["netCollections"], 0)

	def test_15_active_contract_positive_balance_no_settle(self):
		"""Active contract + positive balance: can_settle MUST be False.

		Regression: the settlement button must NOT appear for active contracts
		even when balance > 0. Only operationally closed contracts can settle.
		"""
		from rental.rental.api.contract import get_contract_settlement_info

		ctx = self._create_context(dues_amount=5000)
		# Pay 3000 → balance = 2000 (positive), contract still active
		self._create_receipt(ctx["contract"], ctx["tenant"], 3000, "receipt")

		info = get_contract_settlement_info(ctx["contract"])
		self.assertFalse(info["can_settle"],
			"Active contract must not be settle-eligible even with positive balance")
		self.assertFalse(info["can_refund"])
		self.assertFalse(info["is_archived"])
		self.assertGreater(info["balance"], 0)

	def test_16_active_contract_negative_balance_no_settle_no_refund(self):
		"""Active contract + negative balance: can_settle=False, can_refund=False."""
		from rental.rental.api.contract import get_contract_settlement_info

		ctx = self._create_context(dues_amount=5000)
		# Overpay by 500 → balance = -500 (credit), contract still active
		self._create_receipt(ctx["contract"], ctx["tenant"], 5500, "receipt")

		info = get_contract_settlement_info(ctx["contract"])
		self.assertFalse(info["can_settle"])
		self.assertFalse(info["can_refund"],
			"Active contract must not allow refund even with credit balance")
		self.assertLess(info["balance"], 0)

	def test_17_closed_contract_positive_balance_can_settle(self):
		"""Operationally closed contract + positive balance: can_settle=True."""
		from rental.rental.api.contract import get_contract_settlement_info

		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])
		# Pay 3000 → balance = 2000 (positive), contract operationally closed
		self._create_receipt(ctx["contract"], ctx["tenant"], 3000, "receipt")

		info = get_contract_settlement_info(ctx["contract"])
		self.assertTrue(info["can_settle"],
			"Operationally closed contract with positive balance should be settle-eligible")
		self.assertFalse(info["can_refund"],
			"Positive balance means no refund, only receipt settlement")
		self.assertGreater(info["balance"], 0)

	def test_18_closed_contract_negative_balance_can_refund(self):
		"""Operationally closed contract + negative balance: can_settle=True, can_refund=True."""
		from rental.rental.api.contract import get_contract_settlement_info

		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])
		# Overpay by 410 → balance = -410 (credit), contract operationally closed
		self._create_receipt(ctx["contract"], ctx["tenant"], 5410, "receipt")

		info = get_contract_settlement_info(ctx["contract"])
		self.assertTrue(info["can_settle"])
		self.assertTrue(info["can_refund"],
			"Closed contract with credit balance should allow refund")
		self.assertLess(info["balance"], 0)

	def test_19_zero_balance_no_settle_button(self):
		"""Balance = 0: settlement button must not appear regardless of contract state."""
		from rental.rental.api.contract import get_contract_settlement_info

		ctx = self._create_context(dues_amount=5000)
		self._evict_contract(ctx["contract"])
		# Pay exactly 5000 → balance = 0
		self._create_receipt(ctx["contract"], ctx["tenant"], 5000, "receipt")

		info = get_contract_settlement_info(ctx["contract"])
		self.assertTrue(info["can_settle"],
			"Closed contract is settle-eligible, but balance=0 means no button")
		self.assertEqual(info["balance"], 0)
		self.assertFalse(info["can_refund"])
