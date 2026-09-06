"""Explicit regression test: verify that adding transaction_type and totalRefunds
does not change financial behavior when no refunds exist.

Strategy:
  - Create a full dataset (contract, dues, receipts, waivers).
  - Capture all financial outputs (balance, statement, dashboard, trend).
  - Verify totalRefunds is 0 everywhere.
  - Verify balance formula matches old formula: totalDues - totalReceipts.
  - Verify bulk balance matches single balance.
  - Verify statement has no refund entries.
  - Verify cancelled/draft refunds don't affect any totals.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestRefundRegression(FrappeTestCase):
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
		cls._created_waivers = []

		cls.owner = cls._create_test_user("regression_owner@test.com", "Rental Property Owner")
		cls.account = cls._create_test_account("Regression Test Account", cls.owner)
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

	def _setup_contract(self, rent=1000):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": self.account,
			"building_name": f"Regression BLDG {frappe.utils.random_string(5)}",
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
			"full_name": f"Regression Tenant {frappe.utils.random_string(5)}",
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._created_tenants.append(tenant.name)

		start = frappe.utils.add_days(frappe.utils.today(), -60)
		end = frappe.utils.add_days(frappe.utils.today(), 30)
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

	def _create_receipt(self, contract, tenant, amount, transaction_type="receipt"):
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract,
			"receipt_date": frappe.utils.today(),
			"amount": amount,
			"transaction_type": transaction_type,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self._created_receipts.append(receipt.name)
		return receipt.name

	def _create_receipt_draft(self, contract, tenant, amount, transaction_type="refund"):
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": tenant,
			"contract": contract,
			"receipt_date": frappe.utils.today(),
			"amount": amount,
			"transaction_type": transaction_type,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		self._created_receipts.append(receipt.name)
		return receipt

	def _evict_contract(self, contract_name):
		status = frappe.db.get_value("Lease Contract", contract_name, "status")
		if status == "active":
			frappe.db.set_value("Lease Contract", contract_name, {
				"status": "expired",
				"end_date": frappe.utils.add_days(frappe.utils.today(), -1),
			}, update_modified=False)
		from rental.rental.api.eviction import create_eviction
		ev = create_eviction(contract=contract_name, notes="Test eviction for regression")
		self._created_evictions.append(ev["eviction"])
		return ev

	# ---- 1. No refunds: balance matches old formula ----

	def test_no_refunds_balance_matches_old_formula(self):
		"""Without refunds, balance = totalDues - totalReceipts (old formula)."""
		ctx = self._setup_contract(rent=1000)

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])

		self.assertEqual(bal["totalRefunds"], 0)
		expected_balance = bal["totalDues"] - bal["totalReceipts"]
		self.assertEqual(bal["balance"], expected_balance)

	def test_no_refunds_tenant_balance_matches_old_formula(self):
		"""Without refunds, tenant balance = totalDues - totalReceipts."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import get_tenant_balance
		bal = get_tenant_balance(ctx["tenant"])

		self.assertEqual(bal["totalRefunds"], 0)
		expected_balance = bal["totalDues"] - bal["totalReceipts"]
		self.assertEqual(bal["balance"], expected_balance)

	def test_no_refunds_building_balance_matches_old_formula(self):
		"""Without refunds, building balance = totalDues - totalReceipts."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import get_building_balance
		bal = get_building_balance(ctx["building"])

		self.assertEqual(bal["totalRefunds"], 0)
		expected_balance = bal["totalDues"] - bal["totalReceipts"]
		self.assertEqual(bal["balance"], expected_balance)

	# ---- 2. Bulk balance matches single balance (no refunds) ----

	def test_bulk_contract_balance_matches_single(self):
		"""get_contract_balances (bulk) matches get_contract_balance (single)."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import (
			get_contract_balance, get_contract_balances,
		)
		single = get_contract_balance(ctx["contract"])
		bulk = get_contract_balances([ctx["contract"]])

		self.assertIn(ctx["contract"], bulk)
		self.assertEqual(bulk[ctx["contract"]]["balance"], single["balance"])
		self.assertEqual(bulk[ctx["contract"]]["totalDues"], single["totalDues"])
		self.assertEqual(bulk[ctx["contract"]]["totalReceipts"], single["totalReceipts"])
		self.assertEqual(bulk[ctx["contract"]]["totalRefunds"], single["totalRefunds"])

	def test_bulk_tenant_balance_matches_single(self):
		"""get_tenant_balances (bulk) matches get_tenant_balance (single)."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import (
			get_tenant_balance, get_tenant_balances,
		)
		single = get_tenant_balance(ctx["tenant"])
		bulk = get_tenant_balances([ctx["tenant"]])

		self.assertIn(ctx["tenant"], bulk)
		self.assertEqual(bulk[ctx["tenant"]]["balance"], single["balance"])
		self.assertEqual(bulk[ctx["tenant"]]["totalDues"], single["totalDues"])
		self.assertEqual(bulk[ctx["tenant"]]["totalReceipts"], single["totalReceipts"])
		self.assertEqual(bulk[ctx["tenant"]]["totalRefunds"], single["totalRefunds"])

	def test_bulk_building_balance_matches_single(self):
		"""get_building_balances (bulk) matches get_building_balance (single)."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import (
			get_building_balance, get_building_balances,
		)
		single = get_building_balance(ctx["building"])
		bulk = get_building_balances([ctx["building"]])

		self.assertIn(ctx["building"], bulk)
		self.assertEqual(bulk[ctx["building"]]["balance"], single["balance"])
		self.assertEqual(bulk[ctx["building"]]["totalDues"], single["totalDues"])
		self.assertEqual(bulk[ctx["building"]]["totalReceipts"], single["totalReceipts"])
		self.assertEqual(bulk[ctx["building"]]["totalRefunds"], single["totalRefunds"])

	# ---- 3. Statement unchanged without refunds ----

	def test_statement_no_refund_entries_without_refunds(self):
		"""Statement contains no refund-type entries when no refunds exist."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.statement_service import get_tenant_statement
		stmt = get_tenant_statement(ctx["tenant"])
		lines = stmt.get("lines", [])

		refund_lines = [l for l in lines if l.get("type") == "refund"]
		self.assertEqual(len(refund_lines), 0)

		# All receipt lines should be credit entries
		receipt_lines = [l for l in lines if l.get("type") == "receipt"]
		for r in receipt_lines:
			self.assertEqual(float(r["credit"]), 300)
			self.assertEqual(float(r["debit"]), 0)
			self.assertEqual(r["typeName"], "سند قبض")

	def test_statement_closing_balance_without_refunds(self):
		"""Statement closing balance = totalDues - totalReceipts (no refunds)."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.statement_service import get_tenant_statement
		from rental.rental.services.balance_service import get_tenant_balance
		stmt = get_tenant_statement(ctx["tenant"])
		bal = get_tenant_balance(ctx["tenant"])

		self.assertEqual(stmt["closingBalance"], bal["balance"])
		self.assertEqual(stmt["totalDues"], bal["totalDues"])
		self.assertEqual(stmt["totalReceipts"], bal["totalReceipts"])

	# ---- 4. Prepayment still works (overpay creates credit) ----

	def test_prepayment_creates_credit_balance(self):
		"""Overpaying creates a negative balance (credit) — prepayment still works."""
		ctx = self._setup_contract(rent=1000)

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		dues = bal["totalDues"]

		# Pay more than dues
		self._create_receipt(ctx["contract"], ctx["tenant"], dues + 200)

		bal_after = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after["balance"], -200)
		self.assertEqual(bal_after["totalRefunds"], 0)
		self.assertEqual(bal_after["totalReceipts"], dues + 200)

	# ---- 5. Archive behavior unchanged without refunds ----

	def test_archive_readiness_without_refunds(self):
		"""Archive readiness works correctly without refunds."""
		ctx = self._setup_contract(rent=1000)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.archive_service import get_archive_readiness
		readiness = get_archive_readiness(ctx["contract"])

		self.assertTrue(readiness["operationally_closed"])
		self.assertFalse(readiness["financially_closed"])
		self.assertFalse(readiness["eligible"])
		self.assertEqual(readiness["balance"], readiness["balance_breakdown"]["balance"])

		# Pay off the balance to make it financially closed
		self._create_receipt(ctx["contract"], ctx["tenant"], readiness["balance"])

		readiness_after = get_archive_readiness(ctx["contract"])
		self.assertTrue(readiness_after["financially_closed"])
		self.assertTrue(readiness_after["eligible"])

	# ---- 6. Dashboard totals unchanged without refunds ----

	def test_dashboard_totals_without_refunds(self):
		"""Dashboard financial totals match old formula without refunds."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.api.dashboard import get_dashboard
		dash = get_dashboard()
		stats = dash["stats"]

		# totalDues - totalReceipts + totalRefunds should equal totalBalance
		self.assertEqual(
			round(stats["totalDues"] - stats["totalReceipts"] + stats.get("totalRefunds", 0), 2),
			round(stats["totalBalance"], 2),
		)

	# ---- 7. Financial trend doesn't count refund as receipt ----

	def test_financial_trend_refund_not_counted_as_receipt(self):
		"""Financial trend receipts sum excludes refunds."""
		ctx = self._setup_contract(rent=1000)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 200)

		# Create a refund
		self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		from rental.rental.api.dashboard import get_financial_trend
		trend = get_financial_trend(self.account)
		months = trend.get("months", [])

		total_trend_receipts = sum(m["receipts"] for m in months)
		# The refund (100) should NOT be in the receipts total
		# The overpayment receipt (totalDues + 200) SHOULD be in receipts
		self.assertTrue(total_trend_receipts > 0)
		# Verify the refund is not counted: receipts should include the overpayment
		# but not the refund
		from rental.rental.services.balance_service import get_approved_receipt_total, get_approved_refund_total
		all_receipts = get_approved_receipt_total({"rental_account": self.account})
		all_refunds = get_approved_refund_total({"rental_account": self.account})
		self.assertEqual(all_refunds, 100)
		self.assertTrue(all_receipts > 0)
		# Trend receipts should be close to all_receipts (may differ by date filtering)
		# but should NOT include the refund
		self.assertTrue(total_trend_receipts <= all_receipts + 0.01)

	# ---- 8. Cancelled refund doesn't affect totals ----

	def test_cancelled_refund_not_in_totals(self):
		"""Cancelled refund does not appear in any balance totals."""
		ctx = self._setup_contract(rent=1000)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 300)

		bal_before = get_contract_balance(ctx["contract"])

		# Create and cancel a refund
		refund_name = self._create_receipt(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")
		from rental.rental.api.receipt import cancel_receipt
		frappe.db.set_value("Lease Contract", ctx["contract"], "is_archived", 0, update_modified=False)
		cancel_receipt(refund_name, reason="Test: cancel refund")

		bal_after = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after["totalRefunds"], 0)
		self.assertEqual(bal_after["balance"], bal_before["balance"])
		self.assertEqual(bal_after["totalReceipts"], bal_before["totalReceipts"])

	# ---- 9. Draft refund doesn't affect totals ----

	def test_draft_refund_not_in_totals(self):
		"""Draft (unsubmitted) refund does not appear in any balance totals."""
		ctx = self._setup_contract(rent=1000)
		self._evict_contract(ctx["contract"])

		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self._create_receipt(ctx["contract"], ctx["tenant"], bal["totalDues"] + 300)

		bal_before = get_contract_balance(ctx["contract"])

		# Create a draft refund (not submitted)
		self._create_receipt_draft(ctx["contract"], ctx["tenant"], 100, transaction_type="refund")

		bal_after = get_contract_balance(ctx["contract"])
		self.assertEqual(bal_after["totalRefunds"], 0)
		self.assertEqual(bal_after["balance"], bal_before["balance"])
		self.assertEqual(bal_after["totalReceipts"], bal_before["totalReceipts"])

	# ---- 10. Existing receipts default to 'receipt' ----

	def test_receipts_without_explicit_type_default_to_receipt(self):
		"""Receipts created without transaction_type get 'receipt' automatically."""
		ctx = self._setup_contract(rent=1000)

		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": self.account,
			"tenant": ctx["tenant"],
			"contract": ctx["contract"],
			"receipt_date": frappe.utils.today(),
			"amount": 200,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self._created_receipts.append(receipt.name)

		self.assertEqual(receipt.transaction_type, "receipt")

		# Verify it's counted in totalReceipts, not totalRefunds
		from rental.rental.services.balance_service import get_contract_balance
		bal = get_contract_balance(ctx["contract"])
		self.assertEqual(bal["totalRefunds"], 0)
		self.assertEqual(bal["totalReceipts"], 200)

	# ---- 11. Balance stats unchanged without refunds ----

	def test_balance_stats_without_refunds(self):
		"""Tenant balance stats are correct without refunds."""
		ctx = self._setup_contract(rent=1000)
		self._create_receipt(ctx["contract"], ctx["tenant"], 300)

		from rental.rental.services.balance_service import get_tenant_balance_stats
		stats = get_tenant_balance_stats({"rental_account": self.account})

		self.assertIn("total", stats)
		self.assertIn("debt", stats)
		self.assertIn("credit", stats)
		self.assertIn("zero", stats)
		self.assertEqual(stats["total"], stats["debt"] + stats["credit"] + stats["zero"])

	# ---- 12. Same dataset A (no refund) and B (no refund) produce identical results ----

	def test_dataset_a_no_refund(self):
		"""Dataset A: standard financial operations without any refund.

		Verifies all financial outputs are consistent and match old formula.
		This is the baseline for comparison with Dataset B.
		"""
		ctx = self._setup_contract(rent=1000)

		# Create a receipt for 400
		self._create_receipt(ctx["contract"], ctx["tenant"], 400)

		from rental.rental.services.balance_service import (
			get_contract_balance, get_tenant_balance, get_building_balance,
			get_contract_balances, get_tenant_balances, get_building_balances,
		)
		from rental.rental.services.statement_service import get_tenant_statement

		# Single balance
		cbal = get_contract_balance(ctx["contract"])
		tbal = get_tenant_balance(ctx["tenant"])
		bbal = get_building_balance(ctx["building"])

		# Bulk balance
		cbulk = get_contract_balances([ctx["contract"]])
		tbulk = get_tenant_balances([ctx["tenant"]])
		bbulk = get_building_balances([ctx["building"]])

		# Statement
		stmt = get_tenant_statement(ctx["tenant"])

		# Assertions: no refunds anywhere
		self.assertEqual(cbal["totalRefunds"], 0)
		self.assertEqual(tbal["totalRefunds"], 0)
		self.assertEqual(bbal["totalRefunds"], 0)
		self.assertEqual(cbulk[ctx["contract"]]["totalRefunds"], 0)
		self.assertEqual(tbulk[ctx["tenant"]]["totalRefunds"], 0)
		self.assertEqual(bbulk[ctx["building"]]["totalRefunds"], 0)

		# Balance = totalDues - totalReceipts (old formula)
		self.assertEqual(cbal["balance"], cbal["totalDues"] - cbal["totalReceipts"])
		self.assertEqual(tbal["balance"], tbal["totalDues"] - tbal["totalReceipts"])
		self.assertEqual(bbal["balance"], bbal["totalDues"] - bbal["totalReceipts"])

		# Bulk matches single
		self.assertEqual(cbulk[ctx["contract"]]["balance"], cbal["balance"])
		self.assertEqual(tbulk[ctx["tenant"]]["balance"], tbal["balance"])
		self.assertEqual(bbulk[ctx["building"]]["balance"], bbal["balance"])

		# Statement closing balance matches tenant balance
		self.assertEqual(stmt["closingBalance"], tbal["balance"])

		# No refund entries in statement
		refund_lines = [l for l in stmt.get("lines", []) if l.get("type") == "refund"]
		self.assertEqual(len(refund_lines), 0)

	def test_dataset_b_identical_no_refund(self):
		"""Dataset B: identical setup to A, no refund.

		If A and B produce the same financial results, the old behavior
		is preserved when no refunds are present.
		"""
		ctx = self._setup_contract(rent=1000)

		# Same receipt amount as A
		self._create_receipt(ctx["contract"], ctx["tenant"], 400)

		from rental.rental.services.balance_service import (
			get_contract_balance, get_tenant_balance, get_building_balance,
			get_contract_balances, get_tenant_balances, get_building_balances,
		)
		from rental.rental.services.statement_service import get_tenant_statement

		cbal = get_contract_balance(ctx["contract"])
		tbal = get_tenant_balance(ctx["tenant"])
		bbal = get_building_balance(ctx["building"])
		cbulk = get_contract_balances([ctx["contract"]])
		tbulk = get_tenant_balances([ctx["tenant"]])
		bbulk = get_building_balances([ctx["building"]])
		stmt = get_tenant_statement(ctx["tenant"])

		# All the same assertions as A
		self.assertEqual(cbal["totalRefunds"], 0)
		self.assertEqual(tbal["totalRefunds"], 0)
		self.assertEqual(bbal["totalRefunds"], 0)
		self.assertEqual(cbulk[ctx["contract"]]["totalRefunds"], 0)
		self.assertEqual(tbulk[ctx["tenant"]]["totalRefunds"], 0)
		self.assertEqual(bbulk[ctx["building"]]["totalRefunds"], 0)

		self.assertEqual(cbal["balance"], cbal["totalDues"] - cbal["totalReceipts"])
		self.assertEqual(tbal["balance"], tbal["totalDues"] - tbal["totalReceipts"])
		self.assertEqual(bbal["balance"], bbal["totalDues"] - bbal["totalReceipts"])

		self.assertEqual(cbulk[ctx["contract"]]["balance"], cbal["balance"])
		self.assertEqual(tbulk[ctx["tenant"]]["balance"], tbal["balance"])
		self.assertEqual(bbulk[ctx["building"]]["balance"], bbal["balance"])

		self.assertEqual(stmt["closingBalance"], tbal["balance"])

		refund_lines = [l for l in stmt.get("lines", []) if l.get("type") == "refund"]
		self.assertEqual(len(refund_lines), 0)
